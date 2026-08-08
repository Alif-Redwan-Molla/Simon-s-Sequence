"""
renderer/camera.py

An orbit camera: it always looks at a fixed target point (the center
of the board) and can be rotated around it (drag) and zoomed (scroll).
This is what turns the board from a flat, fixed 2D view into something
the player can actually inspect from any angle -- a basic but genuine
interactive-3D-simulation feature.
"""
import numpy as np

from . import glm


class OrbitCamera:
    def __init__(self, target=(0.0, 0.0, 0.0), distance=14.0,
                 yaw=-90.0, pitch=32.0, aspect=900 / 700):
        self.target = np.array(target, dtype=np.float64)
        self.distance = distance
        self.yaw = yaw
        self.pitch = pitch
        self.aspect = aspect

        self.min_distance = 4.0
        self.max_distance = 28.0
        self.min_pitch = 8.0
        self.max_pitch = 85.0

    @property
    def position(self):
        yaw_r = np.radians(self.yaw)
        pitch_r = np.radians(self.pitch)
        x = self.target[0] + self.distance * np.cos(pitch_r) * np.cos(yaw_r)
        y = self.target[1] + self.distance * np.sin(pitch_r)
        z = self.target[2] + self.distance * np.cos(pitch_r) * np.sin(yaw_r)
        return np.array([x, y, z], dtype=np.float64)

    def orbit(self, dx_pixels, dy_pixels, sensitivity=0.3):
        self.yaw += dx_pixels * sensitivity
        self.pitch = float(np.clip(self.pitch - dy_pixels * sensitivity,
                                    self.min_pitch, self.max_pitch))

    def zoom(self, amount):
        self.distance = float(np.clip(self.distance - amount,
                                       self.min_distance, self.max_distance))

    def view_matrix(self):
        return glm.look_at(self.position, self.target, (0.0, 1.0, 0.0))

    def projection_matrix(self, fov_degrees=45.0, near=0.1, far=100.0):
        return glm.perspective(fov_degrees, self.aspect, near, far)
