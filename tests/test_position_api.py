import pytest
from fastapi.testclient import TestClient
from position_service.main import app, store


@pytest.fixture(autouse=True)
def reset_store():
    store._positions.clear()
    store._seen_ids.clear()
    yield


client = TestClient(app)


def test_post_event_and_get_position():
    resp = client.post(
        "/events",
        json={
            "event_id": "evt-100",
            "symbol": "TCS",
            "transaction_type": "BUY",
            "quantity": 50,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "applied"

    resp2 = client.get("/position")
    assert resp2.json() == {"TCS": 50}


def test_duplicate_via_api():
    client.post(
        "/events",
        json={
            "event_id": "evt-dup",
            "symbol": "RELIANCE",
            "transaction_type": "BUY",
            "quantity": 20,
        },
    )
    resp = client.post(
        "/events",
        json={
            "event_id": "evt-dup",
            "symbol": "RELIANCE",
            "transaction_type": "SELL",
            "quantity": 999,
        },
    )
    assert resp.json()["status"] == "duplicate"
    assert client.get("/position").json() == {"RELIANCE": 20}


def test_invalid_transaction_type_rejected_by_api():
    resp = client.post(
        "/events",
        json={
            "event_id": "evt-bad",
            "symbol": "TCS",
            "transaction_type": "HOLD",
            "quantity": 10,
        },
    )
    assert resp.status_code == 422


def test_negative_quantity_rejected_by_api():
    resp = client.post(
        "/events",
        json={
            "event_id": "evt-neg",
            "symbol": "TCS",
            "transaction_type": "BUY",
            "quantity": -5,
        },
    )
    assert resp.status_code == 422
