from order_service.validator import validate_row


def test_valid_buy():
    event, err = validate_row(
        {
            "event_id": "evt-1",
            "symbol": "TCS",
            "transaction_type": "BUY",
            "quantity": "10",
        }
    )
    assert err is None
    assert event.quantity == 10


def test_valid_sell():
    event, err = validate_row(
        {
            "event_id": "evt-2",
            "symbol": "TCS",
            "transaction_type": "SELL",
            "quantity": "5",
        }
    )
    assert err is None
    assert event.transaction_type == "SELL"


def test_invalid_transaction_type():
    event, err = validate_row(
        {
            "event_id": "evt-3",
            "symbol": "TCS",
            "transaction_type": "HOLD",
            "quantity": "5",
        }
    )
    assert event is None
    assert "invalid transaction_type" in err


def test_zero_quantity_rejected():
    event, _ = validate_row(
        {
            "event_id": "evt-4",
            "symbol": "TCS",
            "transaction_type": "BUY",
            "quantity": "0",
        }
    )
    assert event is None


def test_negative_quantity_rejected():
    event, _ = validate_row(
        {
            "event_id": "evt-5",
            "symbol": "TCS",
            "transaction_type": "BUY",
            "quantity": "-5",
        }
    )
    assert event is None


def test_non_integer_quantity_rejected():
    event, _ = validate_row(
        {
            "event_id": "evt-6",
            "symbol": "TCS",
            "transaction_type": "BUY",
            "quantity": "abc",
        }
    )
    assert event is None


def test_blank_quantity_rejected():
    event, _ = validate_row(
        {
            "event_id": "evt-7",
            "symbol": "TCS",
            "transaction_type": "BUY",
            "quantity": "",
        }
    )
    assert event is None


def test_blank_event_id_rejected():
    event, _ = validate_row(
        {"event_id": "", "symbol": "TCS", "transaction_type": "BUY", "quantity": "5"}
    )
    assert event is None


def test_blank_symbol_rejected():
    event, _ = validate_row(
        {"event_id": "evt-8", "symbol": "", "transaction_type": "BUY", "quantity": "5"}
    )
    assert event is None


def test_continues_after_invalid_row():
    """Simulates processing multiple rows where one is invalid — later rows still validate fine."""
    rows = [
        {
            "event_id": "evt-9",
            "symbol": "TCS",
            "transaction_type": "HOLD",
            "quantity": "5",
        },
        {
            "event_id": "evt-10",
            "symbol": "TCS",
            "transaction_type": "BUY",
            "quantity": "5",
        },
    ]
    results = [validate_row(r) for r in rows]
    assert results[0][0] is None
    assert results[1][0] is not None
