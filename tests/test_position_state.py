from position_service.models import OrderEvent
from position_service.state import PositionStore


def make_event(event_id, symbol, tx_type, qty):
    return OrderEvent(
        event_id=event_id, symbol=symbol, transaction_type=tx_type, quantity=qty
    )


def test_buy_increases_position():
    store = PositionStore()
    store.apply_event(make_event("e1", "TCS", "BUY", 10))
    assert store.get_positions() == {"TCS": 10}


def test_sell_decreases_position():
    store = PositionStore()
    store.apply_event(make_event("e1", "TCS", "SELL", 10))
    assert store.get_positions() == {"TCS": -10}


def test_multiple_symbols():
    store = PositionStore()
    store.apply_event(make_event("e1", "TCS", "BUY", 10))
    store.apply_event(make_event("e2", "RELIANCE", "SELL", 5))
    assert store.get_positions() == {"TCS": 10, "RELIANCE": -5}


def test_zero_net_position_is_retained():
    store = PositionStore()
    store.apply_event(make_event("e1", "TCS", "BUY", 10))
    store.apply_event(make_event("e2", "TCS", "SELL", 10))
    assert store.get_positions() == {"TCS": 0}


def test_duplicate_event_id_ignored():
    store = PositionStore()
    applied_1 = store.apply_event(make_event("e1", "TCS", "BUY", 10))
    applied_2 = store.apply_event(make_event("e1", "TCS", "SELL", 999))
    assert applied_1 is True
    assert applied_2 is False
    assert store.get_positions() == {"TCS": 10}
