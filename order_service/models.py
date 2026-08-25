from typing import Literal
from pydantic import BaseModel


class OrderEvent(BaseModel):
    event_id: str
    symbol: str
    transaction_type: Literal["BUY", "SELL"]
    quantity: int
