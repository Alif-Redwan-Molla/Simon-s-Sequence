"""
renderer/mesh.py

Generates simple vertex/index buffers for the shapes the renderer
needs: a cube (each tile becomes a 3D cube instead of a flat square)
and a flat plane (the table the board sits on).

Each vertex is (position.xyz, normal.xyz) = 6 floats, so the fragment
shader can do real per-pixel lighting instead of the flat/gradient
fill tricks used in the 2D renderer.
"""
import numpy as np


def create_cube_mesh(size=1.0):
    """24 vertices (4 per face, so each face gets its own flat normal)
    and 36 indices (6 faces * 2 triangles * 3 indices)."""
    s = size / 2.0
    faces = [
        ((0, 0, 1),  [(-s, -s, s), (s, -s, s), (s, s, s), (-s, s, s)]),    # +Z front
        ((0, 0, -1), [(s, -s, -s), (-s, -s, -s), (-s, s, -s), (s, s, -s)]),  # -Z back
        ((1, 0, 0),  [(s, -s, s), (s, -s, -s), (s, s, -s), (s, s, s)]),    # +X right
        ((-1, 0, 0), [(-s, -s, -s), (-s, -s, s), (-s, s, s), (-s, s, -s)]),  # -X left
        ((0, 1, 0),  [(-s, s, s), (s, s, s), (s, s, -s), (-s, s, -s)]),    # +Y top
        ((0, -1, 0), [(-s, -s, -s), (s, -s, -s), (s, -s, s), (-s, -s, s)]),  # -Y bottom
    ]

    vertices = []
    indices = []
    base = 0
    for normal, corners in faces:
        for corner in corners:
            vertices.append((*corner, *normal))
        indices += [base, base + 1, base + 2, base, base + 2, base + 3]
        base += 4

    vertex_data = np.array(vertices, dtype="f4")
    index_data = np.array(indices, dtype="i4")
    return vertex_data, index_data


def create_plane_mesh(size=20.0):
    """A single quad lying flat on the XZ plane, facing +Y (up)."""
    s = size / 2.0
    normal = (0, 1, 0)
    corners = [(-s, 0, -s), (s, 0, -s), (s, 0, s), (-s, 0, s)]
    vertices = [(*c, *normal) for c in corners]
    indices = [0, 1, 2, 0, 2, 3]
    return np.array(vertices, dtype="f4"), np.array(indices, dtype="i4")
