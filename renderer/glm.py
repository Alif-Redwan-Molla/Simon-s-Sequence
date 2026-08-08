"""
renderer/glm.py

A small, dependency-free 4x4 matrix library.

Convention: every matrix here is built so that `M @ v` (v as a column
vector) transforms a point the way you'd write it on paper -- the same
convention used in transformations.py for the 2D case, just one more
row/column. GLSL's `mat4` expects its raw float buffer in COLUMN-MAJOR
order, so `to_gl_bytes()` transposes before uploading. Every matrix
should be uploaded through that one function so this detail only has
to be handled in a single place.
"""
import numpy as np


def identity():
    return np.identity(4, dtype=np.float64)


def to_gl_bytes(matrix):
    """Convert a matrix built with this module's convention into the
    flat, column-major float32 buffer GLSL expects for a mat4 uniform."""
    return np.ascontiguousarray(matrix.T, dtype=np.float32).tobytes()


def translation(tx, ty, tz):
    m = identity()
    m[0, 3] = tx
    m[1, 3] = ty
    m[2, 3] = tz
    return m


def scaling(sx, sy, sz):
    m = identity()
    m[0, 0] = sx
    m[1, 1] = sy
    m[2, 2] = sz
    return m


def rotation_y(degrees):
    t = np.radians(degrees)
    c, s = np.cos(t), np.sin(t)
    m = identity()
    m[0, 0], m[0, 2] = c, s
    m[2, 0], m[2, 2] = -s, c
    return m


def rotation_x(degrees):
    t = np.radians(degrees)
    c, s = np.cos(t), np.sin(t)
    m = identity()
    m[1, 1], m[1, 2] = c, -s
    m[2, 1], m[2, 2] = s, c
    return m


def look_at(eye, target, up):
    eye = np.asarray(eye, dtype=np.float64)
    target = np.asarray(target, dtype=np.float64)
    up = np.asarray(up, dtype=np.float64)

    f = target - eye
    f = f / np.linalg.norm(f)
    s = np.cross(f, up)
    s = s / np.linalg.norm(s)
    u = np.cross(s, f)

    m = identity()
    m[0, 0:3] = s
    m[1, 0:3] = u
    m[2, 0:3] = -f
    m[0, 3] = -np.dot(s, eye)
    m[1, 3] = -np.dot(u, eye)
    m[2, 3] = np.dot(f, eye)
    return m


def perspective(fov_degrees, aspect, near, far):
    f = 1.0 / np.tan(np.radians(fov_degrees) / 2.0)
    m = np.zeros((4, 4), dtype=np.float64)
    m[0, 0] = f / aspect
    m[1, 1] = f
    m[2, 2] = (far + near) / (near - far)
    m[2, 3] = (2 * far * near) / (near - far)
    m[3, 2] = -1.0
    return m


def normal_matrix(model):
    """Upper-left 3x3 of the inverse-transpose of the model matrix --
    needed so normals stay correct under non-uniform scaling."""
    m3 = model[:3, :3]
    return np.linalg.inv(m3).T
