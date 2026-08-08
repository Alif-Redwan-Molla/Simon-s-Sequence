"""
opengl_demo.py

Phase 1 + 2 of the OpenGL Migration Plan: a real, running, interactive
3D version of the tile board.

  - Each tile is a lit 3D cube (renderer/board_renderer.py + shaders)
  - Drag the RIGHT mouse button to orbit the camera, scroll to zoom
  - LEFT-click a tile to "press" it (real 3D squash + dip, not the 2D
    scale trick) -- proves the rendering pipeline is genuinely
    interactive, not just a spinning demo
  - SPACE plays a random flash sequence across the board, like the
    real game's "watch the sequence" phase, so you can preview how it
    will look once wired into game.py's state machine
  - Esc quits

This intentionally does NOT yet touch game.py's state machine (score,
rounds, difficulty) -- see OpenGL_Migration_Plan.md, Phase 3 onward,
for wiring this renderer into the real game loop. This file is the
rendering/interaction foundation that the rest builds on.
"""
import math
import random
import sys

import numpy as np
import pygame

from renderer import gl_context, picking
from renderer.board_renderer import BoardRenderer
from renderer.camera import OrbitCamera

WIDTH, HEIGHT = 900, 700

# Same palette as the 2D game's TILE_DEFS_4, converted to 0..1 floats.
TILE_COLORS = [
    (70 / 255, 130 / 255, 230 / 255),   # Blue
    (215 / 255, 85 / 255, 95 / 255),    # Red
    (80 / 255, 195 / 255, 120 / 255),   # Green
    (230 / 255, 185 / 255, 60 / 255),   # Yellow
]

GRID_COLS = 2
TILE_SPACING = 2.6


def build_board_layout(count):
    """2-column grid of tile positions on the XZ plane, centered on
    the origin -- mirrors the 2D game's 2-column board layout."""
    rows = math.ceil(count / GRID_COLS)
    layout = []
    for i in range(count):
        r, c = divmod(i, GRID_COLS)
        x = (c - (GRID_COLS - 1) / 2.0) * TILE_SPACING
        z = (r - (rows - 1) / 2.0) * TILE_SPACING
        layout.append((x, z))
    return layout


class DemoTile:
    """Minimal 3D counterpart of game_objects.Tile: same idea (idle /
    flash / press states driving an animation timer), just producing
    render parameters for a cube instead of calling 2D draw functions."""

    STATE_IDLE, STATE_FLASH, STATE_PRESS = "idle", "flash", "press"

    def __init__(self, index, x, z, color):
        self.index = index
        self.x, self.z = x, z
        self.color = color
        self.state = DemoTile.STATE_IDLE
        self.anim_t = 0.0
        self.anim_duration = 0.0

    def start_flash(self, duration=0.5):
        self.state, self.anim_t, self.anim_duration = DemoTile.STATE_FLASH, 0.0, duration

    def start_press(self, duration=0.25):
        self.state, self.anim_t, self.anim_duration = DemoTile.STATE_PRESS, 0.0, duration

    def update(self, dt):
        if self.state in (DemoTile.STATE_FLASH, DemoTile.STATE_PRESS):
            self.anim_duration = max(self.anim_duration, 1e-6)
            self.anim_t += dt / self.anim_duration
            if self.anim_t >= 1.0:
                self.anim_t, self.state = 1.0, DemoTile.STATE_IDLE

    def render_params(self):
        height, lift, emissive = 1.0, 0.0, 0.0
        if self.state == DemoTile.STATE_PRESS:
            phase = math.sin(self.anim_t * math.pi)
            height = 1.0 - 0.35 * phase
            lift = 0.18 * phase
            emissive = 0.25 * phase
        elif self.state == DemoTile.STATE_FLASH:
            phase = math.sin(self.anim_t * math.pi)
            height = 1.0 + 0.15 * phase
            emissive = 0.6 * phase
        return {"x": self.x, "z": self.z, "color": self.color,
                "height": height, "lift": lift, "emissive": emissive}


class SequencePlayer:
    """Tiny stand-in for game.py's show-sequence phase, just to
    demonstrate the flash animation driven by real game-style logic."""

    def __init__(self, tiles):
        self.tiles = tiles
        self.sequence = []
        self.index = 0
        self.timer = 0.0
        self.flash_time = 0.45
        self.gap_time = 0.2
        self.active = False

    def start(self, length=4):
        self.sequence = [random.randrange(len(self.tiles)) for _ in range(length)]
        self.index = 0
        self.timer = 0.0
        self.active = True
        self.tiles[self.sequence[0]].start_flash(self.flash_time)

    def update(self, dt):
        if not self.active:
            return
        self.timer += dt
        if self.timer >= self.flash_time + self.gap_time:
            self.timer = 0.0
            self.index += 1
            if self.index >= len(self.sequence):
                self.active = False
            else:
                self.tiles[self.sequence[self.index]].start_flash(self.flash_time)


def main():
    ctx = gl_context.create_window_context(WIDTH, HEIGHT)
    program = gl_context.load_tile_program(ctx)
    renderer = BoardRenderer(ctx, program)

    layout = build_board_layout(len(TILE_COLORS))
    tiles = [DemoTile(i, x, z, TILE_COLORS[i]) for i, (x, z) in enumerate(layout)]
    sequence_player = SequencePlayer(tiles)

    camera = OrbitCamera(target=(0.0, 0.0, 0.0), distance=11.0, yaw=-60.0, pitch=32.0,
                          aspect=WIDTH / HEIGHT)

    clock = pygame.time.Clock()
    dragging = False
    last_mouse = (0, 0)

    running = True
    while running:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    sequence_player.start(length=random.randint(3, 6))
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 3:  # right mouse: start orbit drag
                    dragging = True
                    last_mouse = event.pos
                elif event.button == 1:  # left mouse: pick a tile
                    view = camera.view_matrix()
                    proj = camera.projection_matrix(near=0.1, far=100.0)
                    picked = picking.pick_tile(
                        event.pos, WIDTH, HEIGHT, view, proj,
                        [{"x": t.x, "z": t.z, "height": t.render_params()["height"]}
                         for t in tiles])
                    if picked is not None:
                        tiles[picked].start_press()
                elif event.button == 4:
                    camera.zoom(1.0)
                elif event.button == 5:
                    camera.zoom(-1.0)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 3:
                dragging = False
            elif event.type == pygame.MOUSEMOTION and dragging:
                mx, my = event.pos
                camera.orbit(mx - last_mouse[0], my - last_mouse[1])
                last_mouse = (mx, my)

        for t in tiles:
            t.update(dt)
        sequence_player.update(dt)

        render_data = [t.render_params() for t in tiles]
        renderer.render(camera, render_data)
        pygame.display.flip()

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
