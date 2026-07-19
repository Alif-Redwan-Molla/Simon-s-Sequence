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
TEXT_COLOR = (235, 235, 240)
ACCENT_COLOR = (90, 200, 255)

DIFFICULTIES = {
    "Easy":   {"flash_time": 0.65, "gap_time": 0.30, "round_time": 6.0, "lives": 5},
    "Normal": {"flash_time": 0.45, "gap_time": 0.18, "round_time": 4.0, "lives": 3},
    "Hard":   {"flash_time": 0.30, "gap_time": 0.10, "round_time": 2.5, "lives": 1},
}

TILE_DEFS_4 = [
    {"name": "Blue",   "color": (60, 120, 235), "freq": 261.6, "filter": mean_filter},
    {"name": "Red",    "color": (225, 70, 70),  "freq": 329.6, "filter": sharpen_filter},
    {"name": "Green",  "color": (70, 200, 110), "freq": 392.0, "filter": sobel_edge_detection},
    {"name": "Yellow", "color": (235, 205, 60), "freq": 523.3, "filter": emboss_filter},
]

TILE_DEFS_6 = TILE_DEFS_4 + [
    {"name": "Purple", "color": (170, 90, 220), "freq": 196.0, "filter": median_filter},
    {"name": "Cyan",   "color": (70, 210, 210), "freq": 440.0,
     "filter": lambda img: sharpen_filter(sobel_edge_detection(img))},
]


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
        color = ACCENT_COLOR if active else PANEL_COLOR
        pts = clip.rect_to_polygon(self.rect.x, self.rect.y, self.rect.w, self.rect.h)
        ga.fill_polygon(surface, pts, color)
        ga.draw_polygon_outline(surface, pts, TEXT_COLOR, algorithm=ga.bresenham_line, thickness=1)
        text = font.render(self.label, True, TEXT_COLOR if active else TEXT_COLOR)
        surface.blit(text, text.get_rect(center=self.rect.center))

    def clicked(self, pos):
        return self.rect.collidepoint(pos)


class Game:
    STATE_MENU = "menu"
    STATE_SHOW_SEQUENCE = "show_sequence"
    STATE_PLAYER_TURN = "player_turn"
    STATE_PAUSED = "paused"
    STATE_GAME_OVER = "game_over"

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Simon's Sequence")
        self.clock = pygame.time.Clock()
        self.font_small = pygame.font.SysFont("arial", 18)
        self.font_med = pygame.font.SysFont("arial", 26, bold=True)
        self.font_big = pygame.font.SysFont("arial", 48, bold=True)

        self.high_score = load_high_score()
        self.difficulty_name = "Normal"
        self.tile_count = 4
        self.state = Game.STATE_MENU
        self.sound = None

        self._build_menu_buttons()
        self.reset_run(full=True)

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
        board_w = WIDTH - 2 * BOARD_MARGIN
        board_h = 380
        gap = 16
        tile_w = (board_w - gap * (cols - 1)) / cols
        tile_h = (board_h - gap * (rows - 1)) / rows

        self.tiles = []
        for i, d in enumerate(defs):
            r, c = divmod(i, cols)
            x = BOARD_MARGIN + c * (tile_w + gap)
            y = 140 + r * (tile_h + gap)
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
        self.state = Game.STATE_SHOW_SEQUENCE
        self._append_sequence_tile()
        self.playback_index = 0
        self.playback_timer = 0.0
        self._start_next_flash()

    def _append_sequence_tile(self):
        self.sequence.append(random.randrange(len(self.tiles)))
        self.round_num += 1
        self.player_index = 0

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
    def _start_next_flash(self):
        if self.playback_index < len(self.sequence):
            tile = self.tiles[self.sequence[self.playback_index]]
            tile.start_flash(DIFFICULTIES[self.difficulty_name]["flash_time"])
            self.sound.play_tile(tile.index)
            self.playback_timer = 0.0

    def _update(self, dt):
        for tile in self.tiles:
            tile.update(dt)

        if self.active_filter_surface is not None:
            surf, remaining = self.active_filter_surface
            remaining -= dt
            self.active_filter_surface = (surf, remaining) if remaining > 0 else None

        if self.state == Game.STATE_SHOW_SEQUENCE:
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
            self.timer -= dt
            if self.timer <= 0:
                self.sound.play_wrong()
                self._end_round(life_lost=True)

    # ------------------------------------------------------------ draw --
    def _draw(self):
        self.screen.fill(BG_COLOR)
        if self.state == Game.STATE_MENU:
            self._draw_menu()
        else:
            self._draw_board()
            self._draw_hud()
            if self.state == Game.STATE_PAUSED:
                self._draw_pause_overlay()
            elif self.state == Game.STATE_GAME_OVER:
                self._draw_game_over_overlay()
            if self.active_filter_surface is not None:
                surf, _ = self.active_filter_surface
                self.screen.blit(surf, (0, 0))

    def _draw_menu(self):
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
            "Click tiles in the flashed order. P = pause, Esc = quit.", True, TEXT_COLOR)
        self.screen.blit(help_text, help_text.get_rect(center=(WIDTH // 2, 600)))

    def _draw_board(self):
        # Play-field border, drawn with the manual line algorithm and
        # demonstrating line clipping against the field boundary.
        field = (BOARD_MARGIN - 20, 120, WIDTH - 2 * (BOARD_MARGIN - 20), 420)
        fx, fy, fw, fh = field
        border_pts = clip.rect_to_polygon(fx, fy, fw, fh)
        ga.draw_polygon_outline(self.screen, border_pts, PANEL_COLOR,
                                 algorithm=ga.bresenham_line, thickness=3)

        # A decorative diagonal is clipped to the field rectangle using
        # Cohen-Sutherland line clipping, illustrating that algorithm too.
        clipped = clip.cohen_sutherland_clip(fx - 40, fy - 40, fx + fw + 40, fy + fh + 40,
                                              fx, fy, fx + fw, fy + fh)
        if clipped:
            cx1, cy1, cx2, cy2 = clipped
            ga.dda_line(self.screen, cx1, cy1, cx2, cy2, (26, 26, 34), thickness=1)

        for tile in self.tiles:
            tile.draw(self.screen)

    def _draw_hud(self):
        info = [
            f"Round: {self.round_num}",
            f"Score: {self.score}",
            f"Combo x{1 + self.combo // 3}",
            f"Lives: {self.lives}",
            f"Difficulty: {self.difficulty_name}",
        ]
        for i, line in enumerate(info):
            text = self.font_small.render(line, True, TEXT_COLOR)
            self.screen.blit(text, (BOARD_MARGIN - 20, 20 + i * 22))

        if self.state == Game.STATE_PLAYER_TURN:
            bar_w = 300
            pct = max(0.0, self.timer / DIFFICULTIES[self.difficulty_name]["round_time"])
            bar_bg = clip.rect_to_polygon(WIDTH - bar_w - 40, 20, bar_w, 18)
            ga.fill_polygon(self.screen, bar_bg, PANEL_COLOR)
            bar_fg = clip.rect_to_polygon(WIDTH - bar_w - 40, 20, bar_w * pct, 18)
            if pct > 0:
                ga.fill_polygon(self.screen, bar_fg, ACCENT_COLOR)

        # Midpoint-circle-drawn score panel accent (bottom corner)
        ga.midpoint_circle(self.screen, WIDTH - 40, HEIGHT - 40, 16, ACCENT_COLOR, filled=True)

    def _draw_pause_overlay(self):
        overlay_pts = clip.rect_to_polygon(0, 0, WIDTH, HEIGHT)
        ga.fill_polygon(self.screen, overlay_pts, (10, 10, 14))
        text = self.font_big.render("PAUSED", True, ACCENT_COLOR)
        self.screen.blit(text, text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 20)))
        sub = self.font_small.render("Press P or click to resume", True, TEXT_COLOR)
        self.screen.blit(sub, sub.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 30)))

    def _draw_game_over_overlay(self):
        overlay_pts = clip.rect_to_polygon(0, 0, WIDTH, HEIGHT)
        ga.fill_polygon(self.screen, overlay_pts, (10, 10, 14))
        text = self.font_big.render("GAME OVER", True, (225, 80, 80))
        self.screen.blit(text, text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 60)))
        score_text = self.font_med.render(
            f"Score: {self.score}   High Score: {self.high_score}", True, TEXT_COLOR)
        self.screen.blit(score_text, score_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 10)))
        sub = self.font_small.render(
            "Press M for the filtered image comparison  |  click to return to menu",
            True, TEXT_COLOR)
        self.screen.blit(sub, sub.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 40)))


def main():
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
