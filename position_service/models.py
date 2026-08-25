from typing import Literal
from pydantic import BaseModel, Field, constr


class OrderEvent(BaseModel):
    event_id: constr(min_length=1)
    symbol: constr(min_length=1)
    transaction_type: Literal["BUY", "SELL"]
    quantity: int = Field(gt=0)
