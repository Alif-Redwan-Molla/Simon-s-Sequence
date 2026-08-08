"""
renderer/gl_context.py

Two ways to get a ModernGL context:
  - create_window_context(): opens a real Pygame window with an OpenGL
    surface attached -- this is what the actual game uses.
  - moderngl.create_context(standalone=True, backend='egl') is used
    directly by the test scripts to render off-screen and verify pixel
    output without needing a real display (see tests/).
"""
import os

import moderngl
import pygame
from pygame.locals import DOUBLEBUF, OPENGL

_SHADER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shaders")


def create_window_context(width, height, title="Simon's Sequence - 3D"):
    pygame.init()
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
    pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE, 24)
    pygame.display.set_mode((width, height), DOUBLEBUF | OPENGL)
    pygame.display.set_caption(title)

    ctx = moderngl.create_context()
    ctx.enable(moderngl.DEPTH_TEST)
    ctx.enable(moderngl.CULL_FACE)
    return ctx


def load_tile_program(ctx):
    with open(os.path.join(_SHADER_DIR, "tile.vert")) as f:
        vert_src = f.read()
    with open(os.path.join(_SHADER_DIR, "tile.frag")) as f:
        frag_src = f.read()
    return ctx.program(vertex_shader=vert_src, fragment_shader=frag_src)
