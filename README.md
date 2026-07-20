# Simon's Sequence
A Memory Tile Game Built with 2D Computer Graphics Algorithms and Digital Image Processing Techniques
CSE 452 - Graphics and Image Processing

## Run it

```bash
pip install -r requirements.txt
python main.py
```

Controls: click tiles in the flashed order.
`P` pause/resume | `Esc` quit | `V` toggle the Live Algorithm Visualizer
`M` on Game Over: Matplotlib filter comparison | `R` on Game Over: watch the replay

## Where each course topic lives

| Topic | File | What it does |
|---|---|---|
| DDA line algorithm | `graphics_algorithms.py: dda_line` | Field diagonal, visualizer grid |
| Bresenham line algorithm | `graphics_algorithms.py: bresenham_line` | Tile borders, all polygon outlines |
| Bresenham circle algorithm | `graphics_algorithms.py: bresenham_circle` | Available circle primitive |
| Midpoint circle algorithm | `graphics_algorithms.py: midpoint_circle` | HUD accent dot, flower victory pattern |
| Scanline polygon fill | `graphics_algorithms.py: fill_polygon` | Fills tiles, glow highlights, victory shapes |
| Gradient scanline fill | `graphics_algorithms.py: fill_polygon_gradient` | Glossy tile/panel gradients (bonus) |
| Flood fill | `graphics_algorithms.py: flood_fill` | Victory pattern fill (bonus feature) |
| Rounded-rect point generation | `graphics_algorithms.py: rounded_rect_points` | Rounded corners on tiles/panels (bonus) |
| 2D transformations (matrix, homogeneous coords) | `transformations.py` | Tile press scale + rotation |
| Line clipping (Cohen-Sutherland) | `clipping.py: cohen_sutherland_clip` | Clips the decorative diagonal to the play field |
| Polygon clipping (Sutherland-Hodgman) | `clipping.py: sutherland_hodgman_clip` | Clips each tile's glow to its own boundary |
| Correlation | `image_filters.py: correlate2d` | Core sliding-window multiply-and-sum |
| Convolution | `image_filters.py: convolve2d` | Correlation with a 180-degree-rotated kernel |
| Mean/blur, median, sharpen, Sobel edge, emboss | `image_filters.py` | Per-tile live filters |

## Bonus features

**1. Live Algorithm Visualizer Mode** (`visualizer.py`, toggle with `V`)
A floating panel that continuously animates DDA, Bresenham's Line, and the
Midpoint Circle algorithm one step at a time, printing the algorithm's
decision variable (`err` / `p`) at every step, cycling automatically.

**2. Flood Fill Victory Pattern** (`game.py: _generate_victory_pattern`)
Every 5th round, a random decorative shape (star / flower / diamond) is
drawn with the manual line/circle algorithms, then its interior is filled
using a hand-written stack-based flood fill (`graphics_algorithms.py:
flood_fill`) and shown briefly in a glass panel.

**3. Replay System with Frame-by-Frame Filter Playback** (`replay.py`)
Every flash, click, and round transition is timestamped during play. When
the game ends, pressing `R` on the Game Over screen replays the entire
session automatically -- including every tile's live filter effect --
without the player touching anything.

## Visual style (glass/glow redesign)
- Cached vertical-gradient background (built once, not per frame)
- Rounded, gradient-filled tiles with a soft additive glow halo
- Rounded, translucent "glass" panels for the HUD, menu, and overlays
- Rounded, gradient-filled countdown timer bar

All of the above are still built entirely from the hand-written
`fill_polygon` / `fill_polygon_gradient` / `draw_polygon_outline` /
`rounded_rect_points` functions -- no `pygame.draw.*` is used anywhere.
Large fills use `pygame.PixelArray` to write each horizontal scanline
span in one slice (instead of one Python call per pixel) purely for
speed; the scanline math itself is unchanged.

## Original bonus features (from the base game)
- Difficulty levels (Easy / Normal / Hard)
- 4-tile or 6-tile board size
- Countdown timer bar and a lives system
- Persistent high-score tracking (`highscore.json`)
- Procedurally generated per-tile tones plus correct/incorrect stingers
- Combo multiplier
- Pause menu (`P` key)
- Post-round Matplotlib comparison (original vs. mean/sharpen/Sobel/emboss)

## Project structure

```
main.py                 entry point
game.py                 game states, board, scoring, HUD, menu, pause, high score,
                         cached backgrounds/panels, victory pattern, replay wiring
game_objects.py          Tile class (draw + animate + clip + glow)
graphics_algorithms.py  DDA / Bresenham / midpoint circle / scanline fill /
                         gradient fill / flood fill / rounded-rect points
transformations.py      2D homogeneous transform matrices
clipping.py             Cohen-Sutherland + Sutherland-Hodgman
image_filters.py        correlation, convolution, the 5 spatial filters
audio.py                 procedurally generated tile/correct/wrong tones
visualizer.py            Live Algorithm Visualizer Mode (bonus)
replay.py                Replay recorder/player (bonus)
highscore.json           created automatically to persist the high score
```
