"""
game_objects.py

The Tile class ties the three graphics topics together for one visual
element:
  - drawn using the hand-written line/circle/fill/rounded-rect algorithms
    (graphics_algorithms.py)
  - animated (flash / pulse / press) using composed 2D transform
    matrices (transformations.py)
  - its glow effect constrained to its own boundary using polygon
    clipping (clipping.py)

Visual style: rounded corners, a top-to-bottom gradient fill, and a
soft additive glow halo behind each tile for a more modern, polished
look.
"""
import math

import pygame

import graphics_algorithms as ga
import transformations as tf
import clipping as clip

CORNER_SEGMENTS = 4
CORNER_RADIUS_RATIO = 0.16


def _circle_polygon(cx, cy, radius, segments=28):
    pts = []
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        pts.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return pts


def _lighten(color, amount):
    return tuple(min(255, int(c + (255 - c) * amount)) for c in color)


def _darken(color, amount):
    return tuple(max(0, int(c * (1 - amount))) for c in color)


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
        self.border_color = _darken(color, 0.45)

        # Reusable per-pixel-alpha surface for the flash ring (redrawn
        # rarely). Ambient outline is drawn each frame but clipped to
        # the tile boundary to avoid overlapping neighbouring tiles.
        self._glow_size = int(size * 2.6)
        self._flash_glow_surface = pygame.Surface(
            (self._glow_size, self._glow_size), pygame.SRCALPHA)

    @property
    def center(self):
        return (self.x + self.size / 2, self.y + self.size / 2)

    @property
    def rect_points(self):
        radius = self.size * CORNER_RADIUS_RATIO
        return ga.rounded_rect_points(self.x, self.y, self.size, self.size, radius,
                                       segments=CORNER_SEGMENTS)

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

    # ------------------------------------------------------------ draw --
    def _draw_glow(self, surface, cx, cy, phase, clip_window):
        """Blit the precomputed ambient glow (cheap: just a blit), and
        only when actively flashing, additionally render a pulsing ring
        on a small reusable surface (perimeter-cost, not area-cost)."""
        # --- Ambient outline (subtle) clipped to the tile boundary so
        # it doesn't overlap adjacent tiles. Thinner and lower alpha
        # for a cleaner look. ---
        ambient_radius = self.size * 0.62
        ambient_poly = _circle_polygon(cx, cy, ambient_radius, segments=16)
        clipped_ambient = clip.sutherland_hodgman_clip(ambient_poly, clip_window)
        if clipped_ambient:
            ambient_color = (*self.color, 30)
            ga.draw_polygon_outline(surface, clipped_ambient, ambient_color,
                                     algorithm=ga.bresenham_line, thickness=2)

        if phase > 0:
            self._flash_glow_surface.fill((0, 0, 0, 0))
            g_center = self._glow_size / 2
            flash_radius = self.size * (0.68 + 0.45 * phase)
            flash_pts = _circle_polygon(g_center, g_center, flash_radius, segments=18)
            flash_color = (*_lighten(self.color, 0.35), int(180 * phase))
            ga.draw_polygon_outline(self._flash_glow_surface, flash_pts, flash_color,
                                     algorithm=ga.bresenham_line, thickness=5)
            surface.blit(self._flash_glow_surface,
                         (cx - g_center, cy - g_center),
                         special_flags=pygame.BLEND_RGBA_ADD)

    def draw(self, surface):
        cx, cy = self.center

        # --- Press animation: brief scale-down + slight rotation via a
        # composed homogeneous transform matrix, applied about the tile
        # center (transformations.py). ---
        scale = 1.0
        rotation = 0.0
        if self.state == Tile.STATE_PRESS:
            phase = math.sin(self.anim_t * math.pi)
            scale = 1.0 - 0.12 * phase
            rotation = 6.0 * phase

        flash_phase = 0.0
        if self.state == Tile.STATE_FLASH:
            flash_phase = math.sin(self.anim_t * math.pi)

        base_pts = self.rect_points
        drawn_pts = tf.transform_about_center(base_pts, (cx, cy), scale=scale, angle=rotation)
        self._draw_glow(surface, cx, cy, flash_phase, drawn_pts)

        top_color = _lighten(self.color, 0.22 if self.state != Tile.STATE_PRESS else 0.32)
        bottom_color = _darken(self.color, 0.18)
        ga.fill_polygon_gradient(surface, drawn_pts, top_color, bottom_color)
        ga.draw_polygon_outline(surface, drawn_pts, self.border_color,
                                 algorithm=ga.bresenham_line, thickness=1)

        # --- Flash / highlight glow, clipped to the tile boundary using
        # Sutherland-Hodgman polygon clipping (clipping.py) so the glow
        # never bleeds past the tile's own (rounded) edges. ---
        if self.state == Tile.STATE_FLASH:
            glow_radius = self.size * 0.75 * (0.4 + 0.6 * flash_phase)
            glow_poly = _circle_polygon(cx, cy, glow_radius, segments=16)
            clip_window = self.rect_points
            clipped = clip.sutherland_hodgman_clip(glow_poly, clip_window)
            if clipped:
                glow_color = _lighten(self.color, 0.55 * flash_phase + 0.15)
                ga.fill_polygon(surface, clipped, glow_color)
                ga.draw_polygon_outline(surface, drawn_pts, self.border_color,
                                         algorithm=ga.bresenham_line, thickness=1)
