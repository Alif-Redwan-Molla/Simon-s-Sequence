"""
visualizer.py

Bonus feature: Live Algorithm Visualizer Mode.

Toggled with the V key, this draws a small panel that continuously
animates one of the course's rasterization algorithms plotting a sample
shape one step at a time, printing the algorithm's decision variable
at each step (err for Bresenham's line, p for the midpoint circle).
It cycles automatically between DDA, Bresenham's Line, and the
Midpoint Circle algorithm so a viewer can see exactly how each one
decides its next pixel.
"""
import graphics_algorithms as ga


class AlgorithmVisualizer:
    ALGO_NAMES = ["DDA Line", "Bresenham Line", "Midpoint Circle"]

    def __init__(self):
        self.algo_index = 0
        self.step_index = 0
        self.step_timer = 0.0
        self.step_interval = 0.15
        self.hold_timer = 0.0
        self.hold_duration = 1.4
        self.steps = self._compute_steps(self.algo_index)

    # ------------------------------------------------------- stepping --
    def _compute_steps(self, algo_index):
        if algo_index == 0:
            return self._dda_steps(0, 0, 10, 6)
        if algo_index == 1:
            return self._bresenham_line_steps(0, 6, 10, 0)
        return self._midpoint_circle_steps(5)

    def _dda_steps(self, x1, y1, x2, y2):
        steps = []
        dx, dy = x2 - x1, y2 - y1
        n = max(abs(dx), abs(dy))
        if n == 0:
            return [{"x": x1, "y": y1, "info": "single point"}]
        x_inc, y_inc = dx / n, dy / n
        x, y = float(x1), float(y1)
        for _ in range(n + 1):
            steps.append({"x": round(x), "y": round(y), "info": f"x={x:.2f}, y={y:.2f}"})
            x += x_inc
            y += y_inc
        return steps

    def _bresenham_line_steps(self, x1, y1, x2, y2):
        steps = []
        dx, dy = abs(x2 - x1), abs(y2 - y1)
        sx = 1 if x2 > x1 else -1
        sy = 1 if y2 > y1 else -1
        err = dx - dy
        x, y = x1, y1
        while True:
            steps.append({"x": x, "y": y, "info": f"err={err}"})
            if x == x2 and y == y2:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
        return steps

    def _midpoint_circle_steps(self, radius):
        """One octant of the midpoint circle algorithm, showing the
        decision parameter p at every step."""
        steps = []
        x, y = 0, radius
        p = 1 - radius
        steps.append({"x": x, "y": y, "info": f"p={p}"})
        while x < y:
            x += 1
            if p < 0:
                p += 2 * x + 1
            else:
                y -= 1
                p += 2 * (x - y) + 1
            steps.append({"x": x, "y": y, "info": f"p={p}"})
        return steps

    # ---------------------------------------------------------- update --
    def update(self, dt):
        if self.step_index >= len(self.steps) - 1:
            self.hold_timer += dt
            if self.hold_timer >= self.hold_duration:
                self.hold_timer = 0.0
                self.algo_index = (self.algo_index + 1) % len(self.ALGO_NAMES)
                self.steps = self._compute_steps(self.algo_index)
                self.step_index = 0
            return
        self.step_timer += dt
        if self.step_timer >= self.step_interval:
            self.step_timer = 0.0
            self.step_index += 1

    # ------------------------------------------------------------ draw --
    def draw(self, surface, rect, font_title, font_mono):
        x0, y0, w, h = rect
        panel_pts = [(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h)]
        ga.fill_polygon(surface, panel_pts, (22, 22, 30))
        ga.draw_polygon_outline(surface, panel_pts, (90, 200, 255),
                                 algorithm=ga.bresenham_line, thickness=1)

        title = font_title.render(f"Live Visualizer: {self.ALGO_NAMES[self.algo_index]}",
                                   True, (90, 200, 255))
        surface.blit(title, (x0 + 8, y0 + 6))

        cell = 12
        grid_x, grid_y = x0 + 16, y0 + 34
        grid_w, grid_h = w - 32, h - 70

        # Faint grid, drawn with the manual line algorithm too.
        cols = grid_w // cell
        rows = grid_h // cell
        for c in range(cols + 1):
            gx = grid_x + c * cell
            ga.dda_line(surface, gx, grid_y, gx, grid_y + rows * cell, (40, 40, 50))
        for r in range(rows + 1):
            gy = grid_y + r * cell
            ga.dda_line(surface, grid_x, gy, grid_x + cols * cell, gy, (40, 40, 50))

        shown = self.steps[:self.step_index + 1]
        for i, s in enumerate(shown):
            px = grid_x + s["x"] * cell
            py = grid_y + s["y"] * cell
            color = (255, 205, 60) if i == len(shown) - 1 else (90, 200, 255)
            for ox in range(1, cell - 1):
                for oy in range(1, cell - 1):
                    ga.put_pixel(surface, px + ox, py + oy, color)

        if shown:
            info_text = font_mono.render(
                f"step {len(shown)}/{len(self.steps)}   {shown[-1]['info']}",
                True, (230, 230, 235))
            surface.blit(info_text, (x0 + 8, y0 + h - 22))
