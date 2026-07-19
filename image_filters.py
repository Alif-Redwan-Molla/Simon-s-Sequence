"""
image_filters.py

Hand-written spatial filtering: correlation, convolution, and the five
filters used by the game (mean/blur, median, sharpen, Sobel edge
detection, emboss). Implemented directly on NumPy pixel arrays with
padding + sliding-window math -- no cv2 and no scipy.signal helpers.
"""
import numpy as np


def _pad(image, pad_h, pad_w):
    return np.pad(image, ((pad_h, pad_h), (pad_w, pad_w)), mode="edge")


def correlate2d(channel, kernel):
    """Direct spatial correlation of a single-channel image with a kernel.

    The math is the textbook correlation formula
        out[i,j] = sum_{u,v} region[i+u, j+v] * kernel[u,v]
    implemented by hand (no scipy.signal / cv2.filter2D). Sliding windows
    are gathered with sliding_window_view purely so the per-pixel
    multiply-and-sum runs fast enough for live, per-frame use in game."""
    kh, kw = kernel.shape
    pad_h, pad_w = kh // 2, kw // 2
    padded = _pad(channel.astype(float), pad_h, pad_w)

    windows = np.lib.stride_tricks.sliding_window_view(padded, (kh, kw))
    # windows has shape (h, w, kh, kw); explicit elementwise multiply + sum
    # over the last two axes is the correlation formula above.
    out = np.sum(windows * kernel, axis=(2, 3))
    return out


def convolve2d(channel, kernel):
    """True convolution = correlation with a 180-degree rotated kernel."""
    flipped = kernel[::-1, ::-1]
    return correlate2d(channel, flipped)


def _apply_per_channel(image, func, *args):
    """Apply a single-channel filter function to each of R, G, B and
    stack the results back into an (H, W, 3) uint8 image."""
    if image.ndim == 2:
        result = func(image, *args)
        return np.clip(result, 0, 255).astype(np.uint8)
    channels = []
    for c in range(3):
        channels.append(func(image[:, :, c], *args))
    stacked = np.stack(channels, axis=-1)
    return np.clip(stacked, 0, 255).astype(np.uint8)


def mean_filter(image, size=3):
    kernel = np.ones((size, size)) / (size * size)
    return _apply_per_channel(image, convolve2d, kernel)


def median_filter(image, size=3):
    def _median_channel(channel, k):
        pad = k // 2
        padded = _pad(channel.astype(float), pad, pad)
        windows = np.lib.stride_tricks.sliding_window_view(padded, (k, k))
        return np.median(windows, axis=(2, 3))
    return _apply_per_channel(image, _median_channel, size)


def sharpen_filter(image):
    kernel = np.array([
        [0, -1, 0],
        [-1, 5, -1],
        [0, -1, 0],
    ], dtype=float)
    return _apply_per_channel(image, convolve2d, kernel)


def sobel_edge_detection(image):
    """Sobel edge detection: gradient magnitude from Gx and Gy convolutions,
    computed on the grayscale version of the image."""
    if image.ndim == 3:
        gray = (0.299 * image[:, :, 0] + 0.587 * image[:, :, 1] + 0.114 * image[:, :, 2])
    else:
        gray = image.astype(float)

    gx_kernel = np.array([
        [-1, 0, 1],
        [-2, 0, 2],
        [-1, 0, 1],
    ], dtype=float)
    gy_kernel = np.array([
        [-1, -2, -1],
        [0, 0, 0],
        [1, 2, 1],
    ], dtype=float)

    gx = convolve2d(gray, gx_kernel)
    gy = convolve2d(gray, gy_kernel)
    magnitude = np.sqrt(gx ** 2 + gy ** 2)
    magnitude = np.clip(magnitude, 0, 255).astype(np.uint8)

    if image.ndim == 3:
        return np.stack([magnitude, magnitude, magnitude], axis=-1)
    return magnitude


def emboss_filter(image):
    kernel = np.array([
        [-2, -1, 0],
        [-1, 1, 1],
        [0, 1, 2],
    ], dtype=float)
    result = _apply_per_channel(image, convolve2d, kernel)
    return np.clip(result.astype(int) + 0, 0, 255).astype(np.uint8)
