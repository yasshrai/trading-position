from typing import Optional, Tuple
from .models import OrderEvent

VALID_TYPES = {"BUY", "SELL"}


def validate_row(row: dict) -> Tuple[Optional[OrderEvent], Optional[str]]:
    """Validate a raw CSV row dict"""
    event_id = (row.get("event_id") or "").strip()
    symbol = (row.get("symbol") or "").strip()
    transaction_type = (row.get("transaction_type") or "").strip()
    quantity_raw = (row.get("quantity") or "").strip()

    if not event_id:
        return None, "blank event_id"
    if not symbol:
        return None, "blank symbol"
    if transaction_type not in VALID_TYPES:
        return None, f"invalid transaction_type: '{transaction_type}'"
    if not quantity_raw:
        return None, "blank quantity"

    try:
        quantity = int(quantity_raw)
    except ValueError:
        return None, f"non-integer quantity: '{quantity_raw}'"

    if quantity <= 0:
        return None, f"non-positive quantity: {quantity}"

    return (
        OrderEvent(
            event_id=event_id,
            symbol=symbol,
            transaction_type=transaction_type,
            quantity=quantity,
        ),
        None,
    )
