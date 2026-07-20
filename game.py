"""
game.py

Simon's Sequence - the full playable game described in the project
proposal:
  - Grid of colored tiles, random sequence playback, player must repeat it
  - Round count increases and a tile is appended each successful round
  - Every visual element drawn with the hand-written algorithms
  - Tile flash/press animated with 2D transform matrices
  - Glow clipped to tile bounds
  - Each tile color applies its own spatial filter to the screen on a
    correct hit (mean, sharpen, sobel edge, emboss, median, combo)
  - Bonus features: difficulty/speed levels, timer + lives, high score,
    per-tile sound effects, combo multiplier, pause menu
"""
import json
import math
import os
import random
import sys

import numpy as np
import pygame

import graphics_algorithms as ga
import clipping as clip
from game_objects import Tile
from audio import SoundBank
from visualizer import AlgorithmVisualizer
from replay import ReplayRecorder, ReplayPlayer
from image_filters import (
    mean_filter, median_filter, sharpen_filter,
    sobel_edge_detection, emboss_filter,
)

WIDTH, HEIGHT = 900, 700
BOARD_MARGIN = 60
FPS = 60
HIGH_SCORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "highscore.json")

BG_COLOR = (18, 18, 24)
PANEL_COLOR = (30, 30, 40)
TEXT_COLOR = (200, 210, 220)  # slightly softer than pure white for better contrast
ACCENT_COLOR = (80, 185, 240)

DIFFICULTIES = {
    "Easy":   {"flash_time": 0.65, "gap_time": 0.30, "round_time": 6.0, "lives": 5},
    "Normal": {"flash_time": 0.45, "gap_time": 0.18, "round_time": 4.0, "lives": 3},
    "Hard":   {"flash_time": 0.30, "gap_time": 0.10, "round_time": 2.5, "lives": 1},
}

TILE_DEFS_4 = [
    {"name": "Blue",   "color": (70, 130, 230), "freq": 261.6, "filter": mean_filter},
    {"name": "Red",    "color": (215, 85, 95),  "freq": 329.6, "filter": sharpen_filter},
    {"name": "Green",  "color": (80, 195, 120), "freq": 392.0, "filter": sobel_edge_detection},
    {"name": "Yellow", "color": (230, 185, 60), "freq": 523.3, "filter": emboss_filter},
]

TILE_DEFS_6 = TILE_DEFS_4 + [
    {"name": "Purple", "color": (160, 95, 205), "freq": 196.0, "filter": median_filter},
    {"name": "Cyan",   "color": (60, 195, 185), "freq": 440.0,
     "filter": lambda img: sharpen_filter(sobel_edge_detection(img))},
]


def _lighten(color, amount):
    return tuple(min(255, int(c + (255 - c) * amount)) for c in color)


def _darken(color, amount):
    return tuple(max(0, int(c * (1 - amount))) for c in color)


def load_high_score():
    try:
        with open(HIGH_SCORE_FILE, "r") as f:
            return json.load(f).get("high_score", 0)
    except (FileNotFoundError, json.JSONDecodeError):
        return 0


def save_high_score(value):
    try:
        with open(HIGH_SCORE_FILE, "w") as f:
            json.dump({"high_score": value}, f)
    except OSError:
        pass


class Button:
    def __init__(self, rect, label, value=None):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.value = value

    def draw(self, surface, font, active=False):
        radius = min(14, self.rect.h / 2)
        pts = ga.rounded_rect_points(self.rect.x, self.rect.y, self.rect.w, self.rect.h,
                                      radius, segments=6)
        if active:
            top_c, bottom_c = _lighten(ACCENT_COLOR, 0.15), _darken(ACCENT_COLOR, 0.30)
            outline_c = _lighten(ACCENT_COLOR, 0.4)
        else:
            top_c, bottom_c = _lighten(PANEL_COLOR, 0.15), PANEL_COLOR
            outline_c = (90, 90, 105)
        ga.fill_polygon_gradient(surface, pts, top_c, bottom_c)
        ga.draw_polygon_outline(surface, pts, outline_c, algorithm=ga.bresenham_line, thickness=2)
        text = font.render(self.label, True, TEXT_COLOR)
        surface.blit(text, text.get_rect(center=self.rect.center))

    def clicked(self, pos):
        return self.rect.collidepoint(pos)


class Game:
    STATE_MENU = "menu"
    STATE_SHOW_SEQUENCE = "show_sequence"
    STATE_PLAYER_TURN = "player_turn"
    STATE_PAUSED = "paused"
    STATE_GAME_OVER = "game_over"
    STATE_REPLAY = "replay"

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Simon's Sequence")
        self.clock = pygame.time.Clock()
        self.font_small = pygame.font.SysFont("arial", 18)
        self.font_med = pygame.font.SysFont("arial", 26, bold=True)
        self.font_big = pygame.font.SysFont("arial", 48, bold=True)
        self.font_mono = pygame.font.SysFont("consolas", 14)

        self.high_score = load_high_score()
        self.difficulty_name = "Normal"
        self.tile_count = 4
        self.state = Game.STATE_MENU
        self.sound = None

        # Bonus feature: Live Algorithm Visualizer Mode (toggle with V)
        self.visualizer = AlgorithmVisualizer()
        self.show_visualizer = False

        # Bonus feature: Flood Fill Victory Pattern (every 5th round)
        self.victory_pattern_surface = None
        self.victory_pattern_timer = 0.0

        # Bonus feature: Replay System
        self.recorder = ReplayRecorder()
        self.last_replay = None
        self.replay_player = None

        self._build_menu_buttons()
        self.bg_surface = self._build_background()
        self._build_static_panels()
        self.reset_run(full=True)

    def _build_background(self):
        """Precompute a vertical gradient background once (rather than a
        flat fill) for a more polished look, cached as a surface so we
        only pay the per-pixel cost a single time."""
        top = np.array([26, 28, 40], dtype=float)
        bottom = np.array([12, 12, 18], dtype=float)
        t = np.linspace(0, 1, HEIGHT).reshape(HEIGHT, 1, 1)
        column = (top * (1 - t) + bottom * t).astype(np.uint8)      # (H, 1, 3)
        arr = np.repeat(column, WIDTH, axis=1)                       # (H, W, 3)
        arr = np.transpose(arr, (1, 0, 2))                           # -> (W, H, 3)
        return pygame.surfarray.make_surface(arr)

    def _build_glass_panel(self, w, h, radius=16, alpha=150,
                            base_color=PANEL_COLOR, border_color=None):
        """Render one rounded, translucent, gradient-shaded panel onto
        its own small surface. Every call site below has a fixed size,
        so these are all built once up front and simply blitted each
        frame -- filling a few hundred small surfaces at startup is
        instant, but doing this per-frame for a 900x700 window is not."""
        w, h = int(w), int(h)
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        pts = ga.rounded_rect_points(0, 0, w, h, radius, segments=7)
        top_c = (*_lighten(base_color, 0.12), alpha)
        bottom_c = (*base_color, alpha)
        ga.fill_polygon_gradient(panel, pts, top_c, bottom_c)
        ga.draw_polygon_outline(panel, pts, (*(border_color or ACCENT_COLOR), 130),
                                 algorithm=ga.bresenham_line, thickness=1)
        return panel

    def _build_static_panels(self):
        hud_rect = (BOARD_MARGIN - 30, 10, 230, 128)
        # Ensure the play-field panel doesn't start underneath the HUD;
        # if the default field y would overlap the HUD, push it down.
        default_field_y = 120
        hud_bottom = hud_rect[1] + hud_rect[3]
        field_y = max(default_field_y, hud_bottom + 8)
        field = (BOARD_MARGIN - 20, field_y, WIDTH - 2 * (BOARD_MARGIN - 20), 420)
        menu_card = (WIDTH // 2 - 260, 60, 520, 560)
        pause_rect = (WIDTH // 2 - 190, HEIGHT // 2 - 80, 380, 160)
        gameover_rect = (WIDTH // 2 - 230, HEIGHT // 2 - 115, 460, 230)
        replay_rect = (WIDTH // 2 - 260, HEIGHT - 70, 520, 50)
        victory_w, victory_h = 240 + 28, 200 + 48

        self.panel_rects = {
            "field": field, "hud": hud_rect, "menu_card": menu_card,
            "pause": pause_rect, "gameover": gameover_rect, "replay": replay_rect,
        }
        self.panel_surfaces = {
            "field": self._build_glass_panel(field[2], field[3], radius=22, alpha=70,
                                              base_color=(22, 22, 30)),
            "hud": self._build_glass_panel(hud_rect[2], hud_rect[3], radius=16, alpha=140),
            "menu_card": self._build_glass_panel(menu_card[2], menu_card[3], radius=24, alpha=120),
            "pause": self._build_glass_panel(pause_rect[2], pause_rect[3], radius=20, alpha=210),
            "gameover": self._build_glass_panel(gameover_rect[2], gameover_rect[3], radius=22,
                                                 alpha=210, border_color=(225, 80, 80)),
            "replay": self._build_glass_panel(replay_rect[2], replay_rect[3], radius=14, alpha=180),
            "victory": self._build_glass_panel(victory_w, victory_h, radius=18, alpha=190,
                                                base_color=(16, 16, 22)),
        }

    # ---------------------------------------------------------- setup --
    def _build_menu_buttons(self):
        self.difficulty_buttons = [
            Button((WIDTH // 2 - 210 + i * 150, 300, 130, 46), name, name)
            for i, name in enumerate(DIFFICULTIES)
        ]
        self.tile_count_buttons = [
            Button((WIDTH // 2 - 90 + i * 100, 380, 80, 46), f"{n} tiles", n)
            for i, n in enumerate((4, 6))
        ]
        self.start_button = Button((WIDTH // 2 - 90, 470, 180, 56), "Start Game")

    def reset_run(self, full=False):
        defs = TILE_DEFS_4 if self.tile_count == 4 else TILE_DEFS_6
        cols = 2
        rows = math.ceil(len(defs) / cols)
        # Calculate tile grid inside the field panel but avoid the HUD
        # overlap area so tiles never appear beneath the HUD.
        field = self.panel_rects["field"]
        hud = self.panel_rects["hud"]
        fx, fy, fw, fh = field
        hx, hy, hw, hh = hud

        gap = 16
        inner_pad = 12

        # If HUD intrudes into the field from the left, shift the tile
        # grid rightwards by the overlapping amount plus padding.
        overlap_left = max(0, (hx + hw) - fx)
        x_start = fx + inner_pad + overlap_left
        available_w = fw - (x_start - fx) - inner_pad

        # Ensure tiles start below the HUD's bottom edge.
        hud_bottom = hy + hh
        y_start = max(fy + inner_pad, hud_bottom + inner_pad)
        available_h = fh - (y_start - fy) - inner_pad

        tile_w = (available_w - gap * (cols - 1)) / cols
        tile_h = (available_h - gap * (rows - 1)) / rows

        self.tiles = []
        for i, d in enumerate(defs):
            r, c = divmod(i, cols)
            x = x_start + c * (tile_w + gap)
            y = y_start + r * (tile_h + gap)
            self.tiles.append(Tile(i, x, y, min(tile_w, tile_h), d["color"]))
        self.tile_defs = defs
        if self.sound is None or full:
            self.sound = SoundBank([d["freq"] for d in defs])

        self.sequence = []
        self.player_index = 0
        self.round_num = 0
        self.score = 0
        self.combo = 0
        self.lives = DIFFICULTIES[self.difficulty_name]["lives"]
        self.timer = 0.0
        self.playback_index = 0
        self.playback_timer = 0.0
        self.active_filter_surface = None
        self.last_result_images = None  # (original, filtered, filter_name) for post-round analysis

    def start_game(self):
        self.reset_run()
        self.recorder = ReplayRecorder()
        self.victory_pattern_surface = None
        self.victory_pattern_timer = 0.0
        self.state = Game.STATE_SHOW_SEQUENCE
        self._append_sequence_tile()
        self.playback_index = 0
        self.playback_timer = 0.0
        self._start_next_flash()

    def _append_sequence_tile(self):
        self.sequence.append(random.randrange(len(self.tiles)))
        self.round_num += 1
        self.player_index = 0
        self.recorder.record_round(self.round_num)
        # Bonus feature: Flood Fill Victory Pattern every 5th round.
        if self.round_num % 5 == 0:
            self.victory_pattern_surface = self._generate_victory_pattern()
            self.victory_pattern_timer = 2.5

    # ------------------------------------------------------- game loop --
    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                self._handle_event(event)
            self._update(dt)
            self._draw()
            pygame.display.flip()

    def _handle_event(self, event):
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit(0)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p and self.state in (Game.STATE_PLAYER_TURN, Game.STATE_SHOW_SEQUENCE):
                self.state = Game.STATE_PAUSED
            elif event.key == pygame.K_p and self.state == Game.STATE_PAUSED:
                self.state = Game.STATE_PLAYER_TURN
            elif event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit(0)
            elif event.key == pygame.K_m and self.state == Game.STATE_GAME_OVER:
                self.show_post_round_matplotlib()
            elif event.key == pygame.K_v:
                self.show_visualizer = not self.show_visualizer
            elif event.key == pygame.K_r and self.state == Game.STATE_GAME_OVER and self.last_replay:
                self._start_replay()
            elif event.key == pygame.K_r and self.state == Game.STATE_REPLAY and self.replay_player.finished:
                self.state = Game.STATE_MENU

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self.state == Game.STATE_MENU:
                self._handle_menu_click(pos)
            elif self.state == Game.STATE_PLAYER_TURN:
                self._handle_tile_click(pos)
            elif self.state == Game.STATE_PAUSED:
                self.state = Game.STATE_PLAYER_TURN
            elif self.state == Game.STATE_GAME_OVER:
                self.state = Game.STATE_MENU
            elif self.state == Game.STATE_REPLAY and self.replay_player.finished:
                self.state = Game.STATE_MENU

    def _handle_menu_click(self, pos):
        for b in self.difficulty_buttons:
            if b.clicked(pos):
                self.difficulty_name = b.value
        for b in self.tile_count_buttons:
            if b.clicked(pos):
                self.tile_count = b.value
        if self.start_button.clicked(pos):
            self.start_game()

    def _handle_tile_click(self, pos):
        for tile in self.tiles:
            if tile.contains_point(*pos):
                self._process_click(tile)
                return

    def _process_click(self, tile):
        tile.start_press()
        expected = self.sequence[self.player_index]
        if tile.index == expected:
            self.sound.play_tile(tile.index)
            self._apply_live_filter(tile)
            self.recorder.record_click(tile.index)
            self.player_index += 1
            self.combo += 1
            self.score += 10 * max(1, self.combo // 3 + 1)
            self.timer = DIFFICULTIES[self.difficulty_name]["round_time"]
            if self.player_index >= len(self.sequence):
                self.state = Game.STATE_SHOW_SEQUENCE
                self._append_sequence_tile()
                self.playback_index = 0
                self.playback_timer = 0.0
                self._start_next_flash()
        else:
            self.sound.play_wrong()
            self._end_round(life_lost=True)

    def _apply_live_filter(self, tile):
        """Capture the current frame and run this tile's spatial filter
        on it live, per the 'Effect Tiles' section of the proposal."""
        arr = pygame.surfarray.array3d(self.screen)  # (W, H, 3)
        arr = np.transpose(arr, (1, 0, 2))            # -> (H, W, 3)
        filt = self.tile_defs[tile.index]["filter"]
        filtered = filt(arr)
        filtered_img = np.transpose(filtered, (1, 0, 2))
        surf = pygame.surfarray.make_surface(filtered_img)
        self.active_filter_surface = (surf, 0.35)  # (surface, seconds remaining)
        self.last_original_frame = arr
        self.last_filtered_frame = filtered
        self.last_filter_name = self.tile_defs[tile.index]["name"]

    def _generate_victory_pattern(self):
        """Bonus feature: draw a decorative shape outline with the manual
        line/circle algorithms, then fill its interior using flood_fill.
        Shown briefly every 5th round as a small celebration."""
        size = (240, 200)
        surf = pygame.Surface(size)
        surf.fill((15, 15, 20))
        cx, cy = size[0] // 2, size[1] // 2
        outline_color = (230, 230, 235)
        shape = random.choice(["star", "flower", "diamond"])

        if shape == "star":
            pts = []
            for i in range(10):
                angle = math.pi / 5 * i - math.pi / 2
                r = 82 if i % 2 == 0 else 34
                pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
            ga.draw_polygon_outline(surf, pts, outline_color, algorithm=ga.bresenham_line, thickness=2)
        elif shape == "flower":
            ga.midpoint_circle(surf, cx, cy, 30, outline_color, filled=False)
            for i in range(6):
                angle = math.pi / 3 * i
                ox, oy = cx + 42 * math.cos(angle), cy + 42 * math.sin(angle)
                ga.midpoint_circle(surf, int(ox), int(oy), 28, outline_color, filled=False)
        else:  # diamond
            pts = [(cx, cy - 85), (cx + 60, cy), (cx, cy + 85), (cx - 60, cy)]
            ga.draw_polygon_outline(surf, pts, outline_color, algorithm=ga.bresenham_line, thickness=2)

        fill_color = random.choice([
            (90, 200, 255), (225, 120, 60), (120, 220, 140), (210, 90, 210),
        ])
        ga.flood_fill(surf, cx, cy, fill_color, boundary_color=outline_color)
        return surf

    def _end_round(self, life_lost):
        if life_lost:
            self.lives -= 1
            self.combo = 0
        if self.lives <= 0:
            self.state = Game.STATE_GAME_OVER
            if self.score > self.high_score:
                self.high_score = self.score
                save_high_score(self.high_score)
            self._prepare_post_round_analysis()
            self.last_replay = self.recorder.snapshot(self.tile_count, self.difficulty_name, self.score)
        else:
            # retry same sequence from the start
            self.player_index = 0
            self.state = Game.STATE_SHOW_SEQUENCE
            self.playback_index = 0
            self.playback_timer = 0.0
            self._start_next_flash()

    def _prepare_post_round_analysis(self):
        """Take a final screenshot and run all filters on it for the
        Matplotlib side-by-side comparison shown after Game Over."""
        arr = pygame.surfarray.array3d(self.screen)
        arr = np.transpose(arr, (1, 0, 2))
        self.last_result_images = {
            "Original": arr,
            "Mean/Blur": mean_filter(arr),
            "Sharpen": sharpen_filter(arr),
            "Sobel Edge": sobel_edge_detection(arr),
            "Emboss": emboss_filter(arr),
        }

    def show_post_round_matplotlib(self):
        if not self.last_result_images:
            return
        import matplotlib.pyplot as plt
        items = list(self.last_result_images.items())
        fig, axes = plt.subplots(1, len(items), figsize=(4 * len(items), 4))
        for ax, (name, img) in zip(axes, items):
            ax.imshow(img)
            ax.set_title(name)
            ax.axis("off")
        fig.suptitle(f"Round {self.round_num} - Final Score {self.score}")
        plt.tight_layout()
        plt.show()

    # ----------------------------------------------------------- flash --
    def _start_replay(self):
        """Bonus feature: rebuild the board from the recorded snapshot
        and step through every flash/click/round event automatically."""
        self.tile_count = self.last_replay["tile_count"]
        self.difficulty_name = self.last_replay["difficulty"]
        self.reset_run()
        self.replay_player = ReplayPlayer(self.last_replay)
        self.state = Game.STATE_REPLAY

    def _start_next_flash(self):
        if self.playback_index < len(self.sequence):
            tile = self.tiles[self.sequence[self.playback_index]]
            tile.start_flash(DIFFICULTIES[self.difficulty_name]["flash_time"])
            self.sound.play_tile(tile.index)
            self.recorder.record_flash(tile.index)
            self.playback_timer = 0.0

    def _update(self, dt):
        for tile in self.tiles:
            tile.update(dt)

        # Bonus feature: Live Algorithm Visualizer Mode keeps animating
        # regardless of game state, so it can be toggled on at any time.
        self.visualizer.update(dt)

        if self.victory_pattern_timer > 0:
            self.victory_pattern_timer -= dt
            if self.victory_pattern_timer <= 0:
                self.victory_pattern_timer = 0.0
                self.victory_pattern_surface = None

        if self.active_filter_surface is not None:
            surf, remaining = self.active_filter_surface
            remaining -= dt
            self.active_filter_surface = (surf, remaining) if remaining > 0 else None

        if self.state == Game.STATE_SHOW_SEQUENCE:
            self.recorder.tick(dt)
            self.playback_timer += dt
            gap = DIFFICULTIES[self.difficulty_name]["gap_time"]
            flash_time = DIFFICULTIES[self.difficulty_name]["flash_time"]
            if self.playback_timer >= flash_time + gap:
                self.playback_index += 1
                if self.playback_index >= len(self.sequence):
                    self.state = Game.STATE_PLAYER_TURN
                    self.timer = DIFFICULTIES[self.difficulty_name]["round_time"]
                else:
                    self._start_next_flash()

        elif self.state == Game.STATE_PLAYER_TURN:
            self.recorder.tick(dt)
            self.timer -= dt
            if self.timer <= 0:
                self.sound.play_wrong()
                self._end_round(life_lost=True)

        elif self.state == Game.STATE_REPLAY:
            self.replay_player.update(
                dt, self.tiles, lambda idx: self._apply_live_filter(self.tiles[idx]))
            self.round_num = self.replay_player.round_num

    # ------------------------------------------------------------ draw --
    def _draw(self):
        self.screen.blit(self.bg_surface, (0, 0))
        if self.state == Game.STATE_MENU:
            self._draw_menu()
        else:
            self._draw_board()
            self._draw_hud()
            if self.state == Game.STATE_PAUSED:
                self._draw_pause_overlay()
            elif self.state == Game.STATE_GAME_OVER:
                self._draw_game_over_overlay()
            elif self.state == Game.STATE_REPLAY:
                self._draw_replay_overlay()
            if self.active_filter_surface is not None:
                surf, _ = self.active_filter_surface
                self.screen.blit(surf, (0, 0))
            if self.victory_pattern_surface is not None:
                self._draw_victory_pattern()

        # Bonus feature: Live Algorithm Visualizer Mode, toggled with V,
        # drawn last so it floats above everything else.
        if self.show_visualizer:
            self.visualizer.draw(self.screen, (20, HEIGHT - 190, 280, 170),
                                  self.font_small, self.font_mono)

    def _blit_panel(self, key, extra_offset=(0, 0)):
        """Blit a precomputed static glass panel (see _build_static_panels)."""
        x, y, _, _ = self.panel_rects[key]
        self.screen.blit(self.panel_surfaces[key], (x + extra_offset[0], y + extra_offset[1]))

    def _draw_menu(self):
        # Glass card behind all menu content.
        self._blit_panel("menu_card")

        # Soft glow behind the title, built from several low-alpha,
        # slightly offset copies of the text.
        glow_layer = pygame.Surface((WIDTH, 100), pygame.SRCALPHA)
        title_glow = self.font_big.render("Simon's Sequence", True, (*ACCENT_COLOR, 55))
        for ox, oy in [(-3, -3), (3, -3), (-3, 3), (3, 3), (0, 4), (0, -4), (4, 0), (-4, 0)]:
            glow_layer.blit(title_glow, title_glow.get_rect(center=(WIDTH // 2 + ox, 50 + oy)))
        self.screen.blit(glow_layer, (0, 70), special_flags=pygame.BLEND_RGBA_ADD)

        title = self.font_big.render("Simon's Sequence", True, ACCENT_COLOR)
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, 120)))
        sub = self.font_small.render(
            "2D Graphics Algorithms + Digital Image Processing", True, TEXT_COLOR)
        self.screen.blit(sub, sub.get_rect(center=(WIDTH // 2, 165)))

        label = self.font_med.render("Difficulty", True, TEXT_COLOR)
        self.screen.blit(label, (WIDTH // 2 - 210, 265))
        for b in self.difficulty_buttons:
            b.draw(self.screen, self.font_small, active=(b.value == self.difficulty_name))

        label2 = self.font_med.render("Board Size", True, TEXT_COLOR)
        self.screen.blit(label2, (WIDTH // 2 - 90, 345))
        for b in self.tile_count_buttons:
            b.draw(self.screen, self.font_small, active=(b.value == self.tile_count))

        self.start_button.draw(self.screen, self.font_med, active=True)

        hs = self.font_small.render(f"High Score: {self.high_score}", True, TEXT_COLOR)
        self.screen.blit(hs, hs.get_rect(center=(WIDTH // 2, 560)))

        help_text = self.font_small.render(
            "Click tiles in the flashed order.  P = pause   Esc = quit   V = algorithm visualizer",
            True, TEXT_COLOR)
        self.screen.blit(help_text, help_text.get_rect(center=(WIDTH // 2, 600)))

    def _draw_board(self):
        # Play-field border: a rounded panel with a soft accent glow,
        # drawn with the manual line/fill algorithms.
        field = self.panel_rects["field"]
        fx, fy, fw, fh = field
        self._blit_panel("field")
        border_pts = ga.rounded_rect_points(fx, fy, fw, fh, 22, segments=5)
        ga.draw_polygon_outline(self.screen, border_pts, ACCENT_COLOR,
                                 algorithm=ga.bresenham_line, thickness=1)

        # A decorative diagonal is clipped to the field rectangle using
        # Cohen-Sutherland line clipping, illustrating that algorithm too.
        clipped = clip.cohen_sutherland_clip(fx - 40, fy - 40, fx + fw + 40, fy + fh + 40,
                                              fx, fy, fx + fw, fy + fh)
        if clipped:
            cx1, cy1, cx2, cy2 = clipped
            ga.dda_line(self.screen, cx1, cy1, cx2, cy2, (34, 34, 44), thickness=1)

        for tile in self.tiles:
            tile.draw(self.screen)

    def _draw_hud(self):
        panel_rect = self.panel_rects["hud"]
        self._blit_panel("hud")

        info = [
            f"Round: {self.round_num}",
            f"Score: {self.score}",
            f"Combo x{1 + self.combo // 3}",
            f"Lives: {self.lives}",
            f"Difficulty: {self.difficulty_name}",
        ]
        for i, line in enumerate(info):
            text = self.font_small.render(line, True, TEXT_COLOR)
            self.screen.blit(text, (panel_rect[0] + 14, panel_rect[1] + 12 + i * 22))

        if self.state == Game.STATE_PLAYER_TURN:
            bar_w, bar_h = 300, 18
            bx, by = WIDTH - bar_w - 40, 20
            pct = max(0.0, self.timer / DIFFICULTIES[self.difficulty_name]["round_time"])
            track_pts = ga.rounded_rect_points(bx, by, bar_w, bar_h, bar_h / 2, segments=6)
            ga.fill_polygon(self.screen, track_pts, PANEL_COLOR)
            ga.draw_polygon_outline(self.screen, track_pts, (70, 70, 85),
                                     algorithm=ga.bresenham_line, thickness=1)
            if pct > 0:
                fg_w = max(bar_h, bar_w * pct)
                fg_pts = ga.rounded_rect_points(bx, by, fg_w, bar_h, min(bar_h / 2, fg_w / 2),
                                                 segments=6)
                ga.fill_polygon_gradient(self.screen, fg_pts,
                                          _lighten(ACCENT_COLOR, 0.25), _darken(ACCENT_COLOR, 0.1))

        # Midpoint-circle-drawn score panel accent (bottom corner), with
        # a soft additive glow behind it.
        glow = pygame.Surface((80, 80), pygame.SRCALPHA)
        ga.midpoint_circle(glow, 40, 40, 26, (*ACCENT_COLOR, 70), filled=True)
        self.screen.blit(glow, (WIDTH - 80, HEIGHT - 80), special_flags=pygame.BLEND_RGBA_ADD)
        ga.midpoint_circle(self.screen, WIDTH - 40, HEIGHT - 40, 16, ACCENT_COLOR, filled=True)

    def _draw_victory_pattern(self):
        """Bonus feature: Flood Fill Victory Pattern, shown briefly
        every 5th round inside a rounded glass frame."""
        w, h = self.victory_pattern_surface.get_size()
        px, py = WIDTH // 2 - w // 2, HEIGHT // 2 - h // 2 - 20
        self.screen.blit(self.panel_surfaces["victory"], (px - 14, py - 34))
        label = self.font_med.render(f"Round {self.round_num} Milestone!", True, ACCENT_COLOR)
        self.screen.blit(label, label.get_rect(center=(WIDTH // 2, py - 12)))
        self.screen.blit(self.victory_pattern_surface, (px, py))

    def _draw_replay_overlay(self):
        """Bonus feature: Replay System HUD label."""
        label = self.font_med.render("REPLAY MODE", True, (255, 205, 60))
        self.screen.blit(label, label.get_rect(center=(WIDTH // 2, 30)))
        if self.replay_player.finished:
            self._blit_panel("replay")
            text = self.font_small.render(
                f"Replay finished - final score {self.replay_player.score}.  "
                "Click or press R to return to the menu.", True, TEXT_COLOR)
            self.screen.blit(text, text.get_rect(center=(WIDTH // 2, HEIGHT - 45)))

    def _draw_pause_overlay(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((6, 6, 10, 200))
        self.screen.blit(overlay, (0, 0))
        self._blit_panel("pause")
        text = self.font_big.render("PAUSED", True, ACCENT_COLOR)
        self.screen.blit(text, text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 20)))
        sub = self.font_small.render("Press P or click to resume", True, TEXT_COLOR)
        self.screen.blit(sub, sub.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 30)))

    def _draw_game_over_overlay(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((6, 6, 10, 210))
        self.screen.blit(overlay, (0, 0))
        self._blit_panel("gameover")
        text = self.font_big.render("GAME OVER", True, (225, 80, 80))
        self.screen.blit(text, text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 60)))
        score_text = self.font_med.render(
            f"Score: {self.score}   High Score: {self.high_score}", True, TEXT_COLOR)
        self.screen.blit(score_text, score_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 10)))
        sub1 = self.font_small.render(
            "Press M for the filtered image comparison", True, TEXT_COLOR)
        self.screen.blit(sub1, sub1.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 35)))
        sub2 = self.font_small.render(
            "Press R to watch the replay  |  click to return to menu", True, TEXT_COLOR)
        self.screen.blit(sub2, sub2.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 60)))


def main():
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
