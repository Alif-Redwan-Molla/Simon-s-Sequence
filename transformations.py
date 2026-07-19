"""
transformations.py

2D geometric transformations expressed as 3x3 homogeneous matrices, built
and multiplied with NumPy. All animation (tile flashing, pulsing, press
feedback) is driven by composing these matrices rather than by simply
redrawing shapes at new coordinates/sizes.
"""
import math
import numpy as np


def identity_matrix():
    return np.identity(3)


def translation_matrix(tx, ty):
    return np.array([
        [1, 0, tx],
        [0, 1, ty],
        [0, 0, 1],
    ], dtype=float)


def scaling_matrix(sx, sy):
    return np.array([
        [sx, 0, 0],
        [0, sy, 0],
        [0, 0, 1],
    ], dtype=float)


def rotation_matrix(theta_degrees):
    t = math.radians(theta_degrees)
    c, s = math.cos(t), math.sin(t)
    return np.array([
        [c, -s, 0],
        [s, c, 0],
        [0, 0, 1],
    ], dtype=float)


def combine(*matrices):
    """Compose several transform matrices, applied right-to-left."""
    result = identity_matrix()
    for m in matrices:
        result = result @ m
    return result


def apply_transform(matrix, points):
    """Apply a homogeneous 3x3 matrix to a list of (x, y) points."""
    out = []
    for x, y in points:
        vec = np.array([x, y, 1.0])
        tx, ty, tw = matrix @ vec
        out.append((tx / tw, ty / tw))
    return out


def transform_about_center(points, center, scale=1.0, angle=0.0):
    """Scale and rotate a set of points about a given center point,
    built by composing translation -> rotation -> scaling -> translation-back."""
    cx, cy = center
    m = combine(
        translation_matrix(cx, cy),
        rotation_matrix(angle),
        scaling_matrix(scale, scale),
        translation_matrix(-cx, -cy),
    )
    return apply_transform(m, points)


def rect_points(x, y, w, h):
    """Corner points of an axis-aligned rectangle, ready for transforming."""
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
