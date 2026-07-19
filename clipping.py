"""
clipping.py

Line clipping (Cohen-Sutherland) and polygon clipping (Sutherland-Hodgman)
used to constrain drawing and highlight/glow effects within the boundaries
of each tile and the overall play field.
"""

INSIDE, LEFT, RIGHT, BOTTOM, TOP = 0, 1, 2, 4, 8


def _compute_code(x, y, xmin, ymin, xmax, ymax):
    code = INSIDE
    if x < xmin:
        code |= LEFT
    elif x > xmax:
        code |= RIGHT
    if y < ymin:
        code |= TOP
    elif y > ymax:
        code |= BOTTOM
    return code


def cohen_sutherland_clip(x1, y1, x2, y2, xmin, ymin, xmax, ymax):
    """Clip a line segment against a rectangular window. Returns the
    clipped (x1, y1, x2, y2) or None if the segment is entirely outside."""
    code1 = _compute_code(x1, y1, xmin, ymin, xmax, ymax)
    code2 = _compute_code(x2, y2, xmin, ymin, xmax, ymax)

    while True:
        if code1 == 0 and code2 == 0:
            return x1, y1, x2, y2
        if code1 & code2 != 0:
            return None

        code_out = code1 if code1 != 0 else code2
        x, y = 0.0, 0.0

        if code_out & TOP:
            x = x1 + (x2 - x1) * (ymin - y1) / (y2 - y1)
            y = ymin
        elif code_out & BOTTOM:
            x = x1 + (x2 - x1) * (ymax - y1) / (y2 - y1)
            y = ymax
        elif code_out & RIGHT:
            y = y1 + (y2 - y1) * (xmax - x1) / (x2 - x1)
            x = xmax
        elif code_out & LEFT:
            y = y1 + (y2 - y1) * (xmin - x1) / (x2 - x1)
            x = xmin

        if code_out == code1:
            x1, y1 = x, y
            code1 = _compute_code(x1, y1, xmin, ymin, xmax, ymax)
        else:
            x2, y2 = x, y
            code2 = _compute_code(x2, y2, xmin, ymin, xmax, ymax)


def _inside(p, edge_start, edge_end):
    x, y = p
    x1, y1 = edge_start
    x2, y2 = edge_end
    return (x2 - x1) * (y - y1) - (y2 - y1) * (x - x1) >= 0


def _intersect(p1, p2, edge_start, edge_end):
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = edge_start
    x4, y4 = edge_end
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if denom == 0:
        return p2
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))


def sutherland_hodgman_clip(subject_polygon, clip_polygon):
    """Clip subject_polygon against the convex clip_polygon (both lists
    of (x, y) points, given in consistent winding order)."""
    output = list(subject_polygon)
    n = len(clip_polygon)

    for i in range(n):
        if not output:
            break
        edge_start = clip_polygon[i]
        edge_end = clip_polygon[(i + 1) % n]
        input_list = output
        output = []
        m = len(input_list)
        for j in range(m):
            current = input_list[j]
            previous = input_list[j - 1]
            current_in = _inside(current, edge_start, edge_end)
            previous_in = _inside(previous, edge_start, edge_end)
            if current_in:
                if not previous_in:
                    output.append(_intersect(previous, current, edge_start, edge_end))
                output.append(current)
            elif previous_in:
                output.append(_intersect(previous, current, edge_start, edge_end))
    return output


def rect_to_polygon(x, y, w, h):
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
