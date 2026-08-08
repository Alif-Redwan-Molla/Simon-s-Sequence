"""
renderer/picking.py

Converts a mouse click into a 3D ray and tests it against each tile's
axis-aligned bounding box, so tiles in the 3D board are actually
clickable -- this is what makes the OpenGL board interactive rather
than just decorative.
"""
import numpy as np


def mouse_to_ray(mouse_x, mouse_y, width, height, view, projection):
    """Unproject a mouse pixel into a world-space ray (origin, direction)."""
    ndc_x = (2.0 * mouse_x) / width - 1.0
    ndc_y = 1.0 - (2.0 * mouse_y) / height

    inv_vp = np.linalg.inv(projection @ view)

    near_clip = np.array([ndc_x, ndc_y, -1.0, 1.0])
    far_clip = np.array([ndc_x, ndc_y, 1.0, 1.0])

    near_world = inv_vp @ near_clip
    near_world /= near_world[3]
    far_world = inv_vp @ far_clip
    far_world /= far_world[3]

    origin = near_world[:3]
    direction = far_world[:3] - near_world[:3]
    direction = direction / np.linalg.norm(direction)
    return origin, direction


def ray_aabb_intersect(origin, direction, box_min, box_max):
    """Slab method. Returns the intersection distance t, or None."""
    t_min, t_max = -np.inf, np.inf
    for i in range(3):
        if abs(direction[i]) < 1e-9:
            if origin[i] < box_min[i] or origin[i] > box_max[i]:
                return None
            continue
        t1 = (box_min[i] - origin[i]) / direction[i]
        t2 = (box_max[i] - origin[i]) / direction[i]
        if t1 > t2:
            t1, t2 = t2, t1
        t_min = max(t_min, t1)
        t_max = min(t_max, t2)
        if t_min > t_max:
            return None
    return t_min if t_min >= 0 else None


def pick_tile(mouse_pos, width, height, view, projection, tiles, half_size=0.9):
    """tiles: list of dicts with 'x', 'z' (and optional 'height').
    Returns the index of the closest hit tile, or None."""
    origin, direction = mouse_to_ray(mouse_pos[0], mouse_pos[1], width, height, view, projection)

    best_index, best_t = None, np.inf
    for i, t in enumerate(tiles):
        h = t.get("height", 1.0)
        box_min = np.array([t["x"] - half_size, -0.5, t["z"] - half_size])
        box_max = np.array([t["x"] + half_size, -0.5 + h, t["z"] + half_size])
        hit_t = ray_aabb_intersect(origin, direction, box_min, box_max)
        if hit_t is not None and hit_t < best_t:
            best_t = hit_t
            best_index = i
    return best_index
