"""
game_objects.py

The Tile class ties the three graphics topics together for one visual
element:
  - drawn using the hand-written line/circle/fill algorithms
    (graphics_algorithms.py)
  - animated (flash / pulse / press) using composed 2D transform
    matrices (transformations.py)
  - its glow effect constrained to its own boundary using polygon
    clipping (clipping.py)
"""
import math

import graphics_algorithms as ga
import transformations as tf
import clipping as clip


def _circle_polygon(cx, cy, radius, segments=28):
    pts = []
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        pts.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return pts


def _lighten(color, amount):
    return tuple(min(255, int(c + (255 - c) * amount)) for c in color)


class Tile:
    """One clickable tile on the game board."""

    STATE_IDLE = "idle"
    STATE_FLASH = "flash"
    STATE_PRESS = "press"

    def __init__(self, index, x, y, size, color):
        self.index = index
        self.x = x
        self.y = y
        self.size = size
        self.color = color
        self.state = Tile.STATE_IDLE
        self.anim_t = 0.0        # 0..1 progress through current animation
        self.anim_duration = 0.0
        self.border_color = (20, 20, 25)

    @property
    def center(self):
        return (self.x + self.size / 2, self.y + self.size / 2)

    @property
    def rect_points(self):
        return tf.rect_points(self.x, self.y, self.size, self.size)

    def start_flash(self, duration=0.45):
        self.state = Tile.STATE_FLASH
        self.anim_t = 0.0
        self.anim_duration = duration

    def start_press(self, duration=0.2):
        self.state = Tile.STATE_PRESS
        self.anim_t = 0.0
        self.anim_duration = duration

    def update(self, dt):
        if self.state in (Tile.STATE_FLASH, Tile.STATE_PRESS):
            self.anim_duration = max(self.anim_duration, 1e-6)
            self.anim_t += dt / self.anim_duration
            if self.anim_t >= 1.0:
                self.anim_t = 1.0
                self.state = Tile.STATE_IDLE

    def contains_point(self, px, py):
        return self.x <= px <= self.x + self.size and self.y <= py <= self.y + self.size

    def draw(self, surface):
        cx, cy = self.center

        # --- Press animation: brief scale-down + slight rotation via a
        # composed homogeneous transform matrix, applied about the tile
        # center (transformations.py). ---
        scale = 1.0
        rotation = 0.0
        if self.state == Tile.STATE_PRESS:
            # ease-out: shrink to 0.88 then back to 1.0
            phase = math.sin(self.anim_t * math.pi)
            scale = 1.0 - 0.12 * phase
            rotation = 6.0 * phase

        base_pts = self.rect_points
        drawn_pts = tf.transform_about_center(base_pts, (cx, cy), scale=scale, angle=rotation)

        fill_color = self.color
        if self.state == Tile.STATE_PRESS:
            fill_color = _lighten(self.color, 0.15)

        ga.fill_polygon(surface, drawn_pts, fill_color)
        ga.draw_polygon_outline(surface, drawn_pts, self.border_color,
                                 algorithm=ga.bresenham_line, thickness=2)

        # --- Flash / highlight glow, clipped to the tile boundary using
        # Sutherland-Hodgman polygon clipping (clipping.py) so the glow
        # never bleeds past the tile's own edges. ---
        if self.state == Tile.STATE_FLASH:
            phase = math.sin(self.anim_t * math.pi)  # 0 -> 1 -> 0
            glow_radius = self.size * 0.75 * (0.4 + 0.6 * phase)
            glow_poly = _circle_polygon(cx, cy, glow_radius)
            clip_window = self.rect_points
            clipped = clip.sutherland_hodgman_clip(glow_poly, clip_window)
            if clipped:
                glow_color = _lighten(self.color, 0.55 * phase + 0.1)
                ga.fill_polygon(surface, clipped, glow_color)
                ga.draw_polygon_outline(surface, drawn_pts, self.border_color,
                                         algorithm=ga.bresenham_line, thickness=2)
