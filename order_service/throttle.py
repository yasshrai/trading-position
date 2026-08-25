import time


class Throttle:
    """Simple fixed-interval throttle"""

    def __init__(self, max_per_second: float):
        self.min_interval = 1.0 / max_per_second if max_per_second > 0 else 0
        self._last = 0.0

    def wait(self):
        if self.min_interval <= 0:
            return
        now = time.monotonic()
        elapsed = now - self._last
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last = time.monotonic()
