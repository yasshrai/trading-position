import logging
import requests
from .models import OrderEvent

logger = logging.getLogger("order_service")


class EventSender:
    def __init__(self, target_url: str, timeout: float = 5.0):
        self.target_url = target_url
        self.timeout = timeout
        self.session = requests.Session()

    def send(self, event: OrderEvent) -> bool:
        try:
            resp = self.session.post(
                self.target_url, json=event.model_dump(), timeout=self.timeout
            )
            if resp.status_code == 200:
                logger.info(f"Sent event_id={event.event_id}")
                return True
            logger.error(
                f"Delivery rejected for event_id={event.event_id}: "
                f"HTTP {resp.status_code} {resp.text}"
            )
            return False
        except requests.RequestException as e:
            logger.error(f"Delivery error for event_id={event.event_id}: {e}")
            return False
