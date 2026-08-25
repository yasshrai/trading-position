import argparse
import logging

import uvicorn
from fastapi import FastAPI

from .models import OrderEvent
from .state import PositionStore

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("position_service")

app = FastAPI(title="Position Maintaining Service")
store = PositionStore()


@app.post("/events")
def receive_event(event: OrderEvent):
    applied = store.apply_event(event)
    if applied:
        logger.info(
            f"Applied event_id={event.event_id} {event.transaction_type} "
            f"{event.quantity} {event.symbol}"
        )
        return {"status": "applied"}
    else:
        logger.info(f"Ignored duplicate event_id={event.event_id}")
        return {"status": "duplicate"}


@app.get("/position")
def get_position():
    return store.get_positions()


def main():
    parser = argparse.ArgumentParser(description="Position Maintaining Service")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()

    logger.info(f"Starting Position Maintaining Service on {args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
