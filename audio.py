"""
audio.py

Generates simple sine-wave tones with NumPy and hands them to Pygame's
mixer via sndarray, so the game needs no external .wav assets. Each tile
gets its own frequency ("one tone per tile"), plus separate
correct/incorrect stingers.
"""
import numpy as np
import pygame

SAMPLE_RATE = 44100


def _make_tone(frequency, duration=0.18, volume=0.35):
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
    wave = np.sin(frequency * t * 2 * np.pi)
    # simple fade-out envelope to avoid clicking
    envelope = np.linspace(1.0, 0.0, wave.size) ** 0.5
    wave = wave * envelope * volume
    audio = np.int16(wave * 32767)
    stereo = np.column_stack([audio, audio])
    return pygame.sndarray.make_sound(np.ascontiguousarray(stereo))


class SoundBank:
    def __init__(self, tile_frequencies):
        pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2)
        self.tile_sounds = [_make_tone(f) for f in tile_frequencies]
        self.correct_sound = _make_tone(880, duration=0.12, volume=0.3)
        self.wrong_sound = _make_tone(140, duration=0.35, volume=0.4)

    def play_tile(self, index):
        if 0 <= index < len(self.tile_sounds):
            self.tile_sounds[index].play()

    def play_correct(self):
        self.correct_sound.play()

    def play_wrong(self):
        self.wrong_sound.play()
