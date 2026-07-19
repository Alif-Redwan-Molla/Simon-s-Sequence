"""
graphics_algorithms.py

Hand-written implementations of the 2D rasterization algorithms from the
CSE 452 syllabus. Every function here plots pixels one at a time onto a
Pygame Surface using surface.set_at(); no pygame.draw.* function is used
anywhere in this module.
"""


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
    half = thickness // 2
    for ox in range(-half, half + 1):
        for oy in range(-half, half + 1):
            put_pixel(surface, x + ox, y + oy, color)


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


def fill_polygon(surface, points, color):
    """Scanline polygon fill: for every raster row that crosses the
    polygon, find the x-intersections with each edge, sort them, and
    plot pixels between intersection pairs using put_pixel."""
    if len(points) < 3:
        return
    ys = [p[1] for p in points]
    y_min = max(0, int(min(ys)))
    y_max = min(surface.get_height() - 1, int(max(ys)))
    n = len(points)

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
            x_start = int(round(xs[i]))
            x_end = int(round(xs[i + 1]))
            for x in range(x_start, x_end + 1):
                put_pixel(surface, x, y, color)


def draw_polygon_outline(surface, points, color, algorithm=bresenham_line, thickness=1):
    """Draw the edges of a polygon using one of the manual line algorithms."""
    n = len(points)
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        algorithm(surface, x1, y1, x2, y2, color, thickness)
