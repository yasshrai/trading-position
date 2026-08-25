import threading
from .models import OrderEvent


class PositionStore:
    """Thread-safe in-memory store for net positions and seen event IDs."""

    def __init__(self):
        self._lock = threading.Lock()
        self._positions: dict[str, int] = {}
        self._seen_ids: set[str] = set()

    def apply_event(self, event: OrderEvent) -> bool:
        """Apply an event. Returns True if applied, False if it was a duplicate."""
        with self._lock:
            if event.event_id in self._seen_ids:
                return False

            self._seen_ids.add(event.event_id)
            delta = (
                event.quantity if event.transaction_type == "BUY" else -event.quantity
            )
            self._positions[event.symbol] = self._positions.get(event.symbol, 0) + delta
            return True

    def get_positions(self) -> dict[str, int]:
        with self._lock:
            return dict(self._positions)
