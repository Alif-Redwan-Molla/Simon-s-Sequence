"""
replay.py

Bonus feature: Replay System with Frame-by-Frame Filter Playback.

ReplayRecorder timestamps every flash/click/round event during a live
game. When the game ends, Game.snapshot() packages that log along with
the board configuration. ReplayPlayer then drives the same Tile objects
and the same live-filter callback the real game uses, so the entire
session -- flashes, presses, and every per-tile filter effect -- can be
watched again without the player touching anything.
"""


class ReplayRecorder:
    def __init__(self):
        self.events = []
        self.clock = 0.0

    def tick(self, dt):
        self.clock += dt

    def record_flash(self, tile_index):
        self.events.append({"t": self.clock, "type": "flash", "tile": tile_index})

    def record_click(self, tile_index):
        self.events.append({"t": self.clock, "type": "click", "tile": tile_index})

    def record_round(self, round_num):
        self.events.append({"t": self.clock, "type": "round", "round": round_num})

    def snapshot(self, tile_count, difficulty_name, final_score):
        return {
            "events": list(self.events),
            "tile_count": tile_count,
            "difficulty": difficulty_name,
            "score": final_score,
        }


class ReplayPlayer:
    def __init__(self, snapshot):
        self.events = snapshot["events"]
        self.tile_count = snapshot["tile_count"]
        self.difficulty = snapshot["difficulty"]
        self.score = snapshot["score"]
        self.timer = 0.0
        self.next_index = 0
        self.round_num = 0
        self.finished = len(self.events) == 0

    def update(self, dt, tiles, apply_filter_by_index):
        self.timer += dt
        while self.next_index < len(self.events) and self.events[self.next_index]["t"] <= self.timer:
            ev = self.events[self.next_index]
            if ev["type"] == "flash":
                tiles[ev["tile"]].start_flash()
            elif ev["type"] == "click":
                tiles[ev["tile"]].start_press()
                apply_filter_by_index(ev["tile"])
            elif ev["type"] == "round":
                self.round_num = ev["round"]
            self.next_index += 1

        if self.next_index >= len(self.events):
            self.finished = True
