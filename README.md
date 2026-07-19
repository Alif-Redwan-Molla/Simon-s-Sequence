# Simon's Sequence
A Memory Tile Game Built with 2D Computer Graphics Algorithms and Digital Image Processing Techniques
CSE 452 - Graphics and Image Processing

## Run it

```bash
pip install -r requirements.txt
python main.py
```

Controls: click tiles in the flashed order. `P` pauses/resumes, `Esc` quits,
`M` on the Game Over screen opens the Matplotlib filter comparison.

## Where each course topic lives

| Topic | File | What it does |
|---|---|---|
| DDA line algorithm | `graphics_algorithms.py: dda_line` | Used for the decorative field diagonal |
| Bresenham line algorithm | `graphics_algorithms.py: bresenham_line` | Tile borders, polygon outlines |
| Bresenham circle algorithm | `graphics_algorithms.py: bresenham_circle` | Available circle primitive |
| Midpoint circle algorithm | `graphics_algorithms.py: midpoint_circle` | HUD score-panel accent dot |
| Scanline polygon fill | `graphics_algorithms.py: fill_polygon` | Fills every tile and glow shape |
| 2D transformations (matrix, homogeneous coords) | `transformations.py` | Tile press/scale + rotation, composed via translate→rotate→scale→translate-back |
| Line clipping (Cohen-Sutherland) | `clipping.py: cohen_sutherland_clip` | Clips the decorative diagonal to the play-field rectangle |
| Polygon clipping (Sutherland-Hodgman) | `clipping.py: sutherland_hodgman_clip` | Clips each tile's glow circle to its own tile boundary |
| Correlation | `image_filters.py: correlate2d` | Core sliding-window multiply-and-sum used by every filter |
| Convolution | `image_filters.py: convolve2d` | Correlation with a 180°-rotated kernel |
| Mean/blur filter | `image_filters.py: mean_filter` | Blue tile live effect |
| Median filter | `image_filters.py: median_filter` | Purple tile live effect (6-tile board) |
| Sharpen filter | `image_filters.py: sharpen_filter` | Red tile live effect |
| Sobel edge detection | `image_filters.py: sobel_edge_detection` | Green tile live effect |
| Emboss filter | `image_filters.py: emboss_filter` | Yellow tile live effect |

## Project structure

```
main.py                 entry point
game.py                 game states, board, scoring, HUD, menu, pause, high score
game_objects.py          Tile class (draw + animate + clip)
graphics_algorithms.py  DDA / Bresenham / midpoint circle / scanline fill
transformations.py      2D homogeneous transform matrices
clipping.py             Cohen-Sutherland + Sutherland-Hodgman
image_filters.py        correlation, convolution, the 5 spatial filters
audio.py                 procedurally generated tile/correct/wrong tones
highscore.json           created automatically to persist the high score
```

## Bonus features implemented
- Difficulty levels (Easy / Normal / Hard) controlling flash speed and time limit
- 4-tile or 6-tile board size selectable from the menu
- Countdown timer bar and a lives system
- Persistent high-score tracking (`highscore.json`)
- Procedurally generated per-tile tones plus correct/incorrect sound stingers
- Combo multiplier for consecutive correct hits
- Pause menu (`P` key)
- Post-round Matplotlib comparison of the original screen vs. mean/blur,
  sharpen, Sobel-edge and emboss filtered versions
