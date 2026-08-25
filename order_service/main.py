import argparse
import logging

from .reader import read_csv_rows
from .validator import validate_row
from .sender import EventSender
from .throttle import Throttle

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("order_service")


def run(csv_path: str, target_url: str, max_events_per_sec: float):
    sender = EventSender(target_url)
    throttle = Throttle(max_events_per_sec)

    accepted = rejected = sent = 0

    for row in read_csv_rows(csv_path):
        event, error = validate_row(row)

        if error:
            rejected += 1
            logger.warning(f"Rejected row {row}: {error}")
            continue

        accepted += 1
        logger.info(f"Accepted event_id={event.event_id}")

        throttle.wait()
        if sender.send(event):
            sent += 1

    logger.info(
        f"Input processing complete. accepted={accepted} rejected={rejected} sent={sent}"
    )


def main():
    parser = argparse.ArgumentParser(description="Order Update Service")
    parser.add_argument("--csv-path", required=True, help="Path to order_updates.csv")
    parser.add_argument(
        "--target-url",
        default="http://localhost:8001/events",
        help="Position service events endpoint",
    )
    parser.add_argument(
        "--max-events-per-sec",
        type=float,
        default=50,
        help="Throttle rate (default: 50)",
    )
    args = parser.parse_args()

    run(args.csv_path, args.target_url, args.max_events_per_sec)


if __name__ == "__main__":
    main()
