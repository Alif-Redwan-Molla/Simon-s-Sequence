"""
renderer/

OpenGL rendering layer for Simon's Sequence (Phase 1 + 2 of the OpenGL
Migration Plan: foundation + 3D board/camera). This package is
intentionally independent of game.py's Pygame 2D drawing code -- it
only needs plain data (tile positions/colors/animation state) and
knows nothing about score, rounds, or difficulty.
"""
