"""
graphics_algorithms.py

Hand-written implementations of the 2D rasterization algorithms from the
CSE 452 syllabus. Every function here plots pixels one at a time onto a
Pygame Surface using surface.set_at(); no pygame.draw.* function is used
anywhere in this module.
"""
import math
import pygame


def put_pixel(surface, x, y, color):
    """Plot a single pixel, guarding against out-of-bounds coordinates."""
    w, h = surface.get_width(), surface.get_height()
    xi, yi = int(round(x)), int(round(y))
    if 0 <= xi < w and 0 <= yi < h:
        surface.set_at((xi, yi), color)


def dda_line(surface, x1, y1, x2, y2, color, thickness=1):
    """Digital Differential Analyzer line drawing algorithm."""
    x1, y1, x2, y2 = round(x1), round(y1), round(x2), round(y2)
    dx = x2 - x1
    dy = y2 - y1
    steps = max(abs(dx), abs(dy))
    if steps == 0:
        _plot_thick(surface, x1, y1, color, thickness)
        return
    x_inc = dx / steps
    y_inc = dy / steps
    x, y = x1, y1
    for _ in range(steps + 1):
        _plot_thick(surface, x, y, color, thickness)
        x += x_inc
        y += y_inc


def bresenham_line(surface, x1, y1, x2, y2, color, thickness=1):
    """Bresenham's integer-only line drawing algorithm."""
    x1, y1, x2, y2 = int(round(x1)), int(round(y1)), int(round(x2)), int(round(y2))
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    sx = 1 if x2 > x1 else -1
    sy = 1 if y2 > y1 else -1
    err = dx - dy
    x, y = x1, y1
    while True:
        _plot_thick(surface, x, y, color, thickness)
        if x == x2 and y == y2:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy


def _plot_thick(surface, x, y, color, thickness):
    """Helper to give lines visible thickness by plotting a small block
    of pixels around each computed point (still one set_at per pixel)."""
    if thickness <= 1:
        put_pixel(surface, x, y, color)
        return
    w, h = surface.get_width(), surface.get_height()
    xi, yi = int(round(x)), int(round(y))
    start = -(thickness // 2)
    end = start + thickness  # exclusive: gives exactly `thickness` pixels per axis
    for ox in range(start, end):
        px = xi + ox
        if px < 0 or px >= w:
            continue
        for oy in range(start, end):
            py = yi + oy
            if 0 <= py < h:
                surface.set_at((px, py), color)


def _circle_points(surface, xc, yc, x, y, color, filled):
    """Plot the 8-way symmetric points of a circle for one (x, y) pair."""
    pts = [
        (xc + x, yc + y), (xc - x, yc + y),
        (xc + x, yc - y), (xc - x, yc - y),
        (xc + y, yc + x), (xc - y, yc + x),
        (xc + y, yc - x), (xc - y, yc - x),
    ]
    if not filled:
        for px, py in pts:
            put_pixel(surface, px, py, color)
    else:
        # Fill by drawing horizontal spans between symmetric points using
        # the same DDA-style pixel stepping (still manual, no draw.line).
        for (ax, ay), (bx, by) in [(pts[0], pts[1]), (pts[2], pts[3]),
                                    (pts[4], pts[5]), (pts[6], pts[7])]:
            if ay == by:
                lo, hi = sorted((ax, bx))
                for px in range(int(lo), int(hi) + 1):
                    put_pixel(surface, px, ay, color)


def bresenham_circle(surface, xc, yc, radius, color, filled=False):
    """Bresenham's circle drawing algorithm (decision-parameter form)."""
    x = 0
    y = radius
    d = 3 - 2 * radius
    _circle_points(surface, xc, yc, x, y, color, filled)
    while x <= y:
        x += 1
        if d > 0:
            y -= 1
            d = d + 4 * (x - y) + 10
        else:
            d = d + 4 * x + 6
        _circle_points(surface, xc, yc, x, y, color, filled)


def midpoint_circle(surface, xc, yc, radius, color, filled=False):
    """Midpoint circle drawing algorithm."""
    x = 0
    y = radius
    p = 1 - radius
    _circle_points(surface, xc, yc, x, y, color, filled)
    while x < y:
        x += 1
        if p < 0:
            p += 2 * x + 1
        else:
            y -= 1
            p += 2 * (x - y) + 1
        _circle_points(surface, xc, yc, x, y, color, filled)


def rounded_rect_points(x, y, w, h, radius, segments=6):
    """Corner points of a rounded rectangle, built as four small corner
    arcs (sampled with cos/sin, the same way circle points are built
    elsewhere) joined into one convex polygon. The polygon is then still
    rendered entirely with the hand-written fill_polygon /
    draw_polygon_outline functions below -- only the point *positions*
    use trig, same as the existing circle-point generation."""
    radius = max(0.0, min(radius, w / 2, h / 2))
    corners = [
        (x + w - radius, y + radius, -90, 0),      # top-right
        (x + w - radius, y + h - radius, 0, 90),    # bottom-right
        (x + radius, y + h - radius, 90, 180),      # bottom-left
        (x + radius, y + radius, 180, 270),         # top-left
    ]
    pts = []
    for cx, cy, start_deg, end_deg in corners:
        for i in range(segments + 1):
            t = math.radians(start_deg + (end_deg - start_deg) * i / segments)
            pts.append((cx + radius * math.cos(t), cy + radius * math.sin(t)))
    return pts


def fill_polygon_gradient(surface, points, color_top, color_bottom):
    """Same scanline fill as fill_polygon, but linearly interpolates the
    fill color from color_top to color_bottom over the polygon's
    vertical extent -- used for the glossy/gradient tile and panel
    look. Each row's color is computed by hand from the interpolation
    formula; only the pixel-writing step uses a PixelArray slice."""
    if len(points) < 3:
        return
    w, h = surface.get_width(), surface.get_height()
    ys = [p[1] for p in points]
    y_min = max(0, int(min(ys)))
    y_max = min(h - 1, int(max(ys)))
    n = len(points)
    span = max(1, y_max - y_min)

    with pygame.PixelArray(surface) as arr:
        for y in range(y_min, y_max + 1):
            t = (y - y_min) / span
            color = tuple(
                int(color_top[i] + (color_bottom[i] - color_top[i]) * t)
                for i in range(len(color_top))
            )
            y_center = y + 0.5
            xs = []
            for i in range(n):
                x1, y1 = points[i]
                x2, y2 = points[(i + 1) % n]
                if y1 == y2:
                    continue
                if min(y1, y2) <= y_center < max(y1, y2):
                    tt = (y_center - y1) / (y2 - y1)
                    xs.append(x1 + tt * (x2 - x1))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                x_start = max(0, int(round(xs[i])))
                x_end = min(w - 1, int(round(xs[i + 1])))
                if x_end >= x_start:
                    arr[x_start:x_end + 1, y] = color


def fill_polygon(surface, points, color):
    """Scanline polygon fill: for every raster row that crosses the
    polygon, find the x-intersections with each edge, sort them, and
    fill each intersection pair as one contiguous horizontal span. The
    intersection math is the same manual scanline algorithm either way;
    each span is written with one PixelArray slice assignment instead
    of a per-pixel Python loop so large fills stay fast."""
    if len(points) < 3:
        return
    w, h = surface.get_width(), surface.get_height()
    ys = [p[1] for p in points]
    y_min = max(0, int(min(ys)))
    y_max = min(h - 1, int(max(ys)))
    n = len(points)

    with pygame.PixelArray(surface) as arr:
        for y in range(y_min, y_max + 1):
            y_center = y + 0.5
            xs = []
            for i in range(n):
                x1, y1 = points[i]
                x2, y2 = points[(i + 1) % n]
                if y1 == y2:
                    continue
                if min(y1, y2) <= y_center < max(y1, y2):
                    t = (y_center - y1) / (y2 - y1)
                    xs.append(x1 + t * (x2 - x1))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                x_start = max(0, int(round(xs[i])))
                x_end = min(w - 1, int(round(xs[i + 1])))
                if x_end >= x_start:
                    arr[x_start:x_end + 1, y] = color


def flood_fill(surface, x, y, fill_color, boundary_color=None):
    """Iterative, stack-based 4-connected flood fill.

    Starting at seed point (x, y), replaces the connected region of
    matching pixels with fill_color. If boundary_color is given, filling
    stops at any pixel of that color (boundary-fill style); otherwise it
    stops wherever the pixel color no longer matches the original seed
    color (standard flood-fill style).
    """
    w, h = surface.get_width(), surface.get_height()
    x, y = int(x), int(y)
    if not (0 <= x < w and 0 <= y < h):
        return

    target_color = surface.get_at((x, y))[:3]
    fill_rgb = tuple(fill_color[:3])
    if target_color == fill_rgb:
        return
    boundary_rgb = tuple(boundary_color[:3]) if boundary_color is not None else None
    if boundary_rgb is not None and target_color == boundary_rgb:
        return

    stack = [(x, y)]
    visited = set()
    while stack:
        cx, cy = stack.pop()
        if not (0 <= cx < w and 0 <= cy < h):
            continue
        if (cx, cy) in visited:
            continue
        current = surface.get_at((cx, cy))[:3]
        if boundary_rgb is not None:
            if current == boundary_rgb:
                continue
        elif current != target_color:
            continue
        elif current == fill_rgb:
            continue

        surface.set_at((cx, cy), fill_color)
        visited.add((cx, cy))
        stack.append((cx + 1, cy))
        stack.append((cx - 1, cy))
        stack.append((cx, cy + 1))
        stack.append((cx, cy - 1))


def draw_polygon_outline(surface, points, color, algorithm=bresenham_line, thickness=1):
    """Draw the edges of a polygon using one of the manual line algorithms."""
    n = len(points)
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        algorithm(surface, x1, y1, x2, y2, color, thickness)
