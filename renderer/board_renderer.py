"""
renderer/board_renderer.py

Owns the GPU-side resources (vertex buffers, VAOs, the shader program)
and draws the board: one cube per tile plus a ground plane. Takes
plain data in (no dependency on game.py's Tile/Game classes) so it can
be tested and reused independently.
"""
import numpy as np

from . import glm
from .mesh import create_cube_mesh, create_plane_mesh


class BoardRenderer:
    def __init__(self, ctx, program):
        self.ctx = ctx
        self.program = program

        cube_vertices, cube_indices = create_cube_mesh(size=1.0)
        self.cube_vbo = ctx.buffer(cube_vertices.tobytes())
        self.cube_ibo = ctx.buffer(cube_indices.tobytes())
        self.cube_vao = ctx.vertex_array(
            program, [(self.cube_vbo, "3f 3f", "in_position", "in_normal")],
            self.cube_ibo,
        )

        plane_vertices, plane_indices = create_plane_mesh(size=24.0)
        self.plane_vbo = ctx.buffer(plane_vertices.tobytes())
        self.plane_ibo = ctx.buffer(plane_indices.tobytes())
        self.plane_vao = ctx.vertex_array(
            program, [(self.plane_vbo, "3f 3f", "in_position", "in_normal")],
            self.plane_ibo,
        )

    def render(self, camera, tiles, light_dir=(-0.4, -1.0, -0.3),
               background=(0.06, 0.06, 0.09, 1.0)):
        """tiles: list of dicts with keys
             x, z            -- world-space board position
             color            -- (r, g, b) in 0..1
             height           -- cube Y scale (press animation squashes this)
             lift              -- extra Y offset (press animation dips down)
             emissive          -- 0..1 brightness boost (flash feedback)
        """
        self.ctx.clear(*background, depth=1.0)
        view = camera.view_matrix()
        projection = camera.projection_matrix()

        self.program["view"].write(glm.to_gl_bytes(view))
        self.program["projection"].write(glm.to_gl_bytes(projection))
        self.program["light_dir"].value = light_dir
        self.program["view_pos"].value = tuple(camera.position)

        # Ground plane.
        model = glm.translation(0.0, -0.55, 0.0)
        self.program["model"].write(glm.to_gl_bytes(model))
        self.program["normal_matrix"].write(
            np.ascontiguousarray(glm.normal_matrix(model).T, dtype=np.float32).tobytes())
        self.program["base_color"].value = (0.12, 0.12, 0.16)
        self.program["emissive"].value = 0.0
        self.plane_vao.render()

        # Tiles.
        for t in tiles:
            height = t.get("height", 1.0)
            lift = t.get("lift", 0.0)
            model = (
                glm.translation(t["x"], height / 2.0 - 0.5 - lift, t["z"])
                @ glm.scaling(1.0, height, 1.0)
            )
            self.program["model"].write(glm.to_gl_bytes(model))
            self.program["normal_matrix"].write(
                np.ascontiguousarray(glm.normal_matrix(model).T, dtype=np.float32).tobytes())
            self.program["base_color"].value = tuple(t["color"])
            self.program["emissive"].value = t.get("emissive", 0.0)
            self.cube_vao.render()
