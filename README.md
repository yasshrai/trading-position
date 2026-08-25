# Trading Position Assessment

Two independent services that process a stream of trading order updates and maintain
the current net position per symbol.

- **Order Update Service** — reads `order_updates.csv` incrementally, validates each row,
  and forwards valid events to the Position Maintaining Service at a throttled rate.
- **Position Maintaining Service** — a FastAPI HTTP service that receives events, maintains
  an in-memory net position per symbol, deduplicates by `event_id`, and exposes the current
  state via `GET /position`.

---

## Architecture & Design Decisions

### Why two separate processes
The assessment requires independently runnable services communicating over a defined
interface. Splitting ingestion (I/O-bound, sequential) from state-keeping (concurrent
reads/writes) also mirrors how this would look in a real trading system, where an
order-flow ingester and a book/position service are usually separate concerns.

### Why HTTP (not gRPC / Redis / raw TCP)
| Option | Why not chosen |
|---|---|
| gRPC | Requires proto compilation and adds complexity with no throughput benefit at ~50 events/sec |
| Redis Streams / Pub-Sub | Requires standing up external infrastructure, which the assessment explicitly says is not required |
| Raw TCP socket | More code and more edge cases (message framing, partial reads) for no real gain |
| **HTTP (chosen)** | Simplest mechanism that satisfies every requirement: one dependency (`requests`/`httpx`), trivially testable with `curl`, and in-order delivery falls out naturally because each POST completes before the next one is sent. |

**Mechanism:** Order Update Service sends one `POST /events` request per valid event, with a
JSON body. It waits for each response before throttling and sending the next, which
preserves CSV ordering across the wire without any extra coordination.

**Event payload / schema:**
```json
{
  "event_id": "evt-0001",
  "symbol": "RELIANCE",
  "transaction_type": "BUY",
  "quantity": 90
}
```

**Error / delivery-failure handling:** If the Position Service is unreachable, times out,
or returns a non-200 response, the Order Update Service logs the failure (with `event_id`
and reason) and **continues to the next row** — it does not retry, queue, or crash.

**Known delivery limitations (by design, per assessment scope):**
- No retry, backoff, or dead-letter handling on delivery failure.
- No durability — if the Position Service is down when an event is sent, that event is
  lost (logged, not persisted or replayed).
- No recovery after a full process restart of either service — in-memory state (positions
  and seen `event_id`s) resets when the Position Service restarts.
- Exact 50/sec throttling is approximate (fixed-interval spacing), not a precision
  real-time guarantee, per the assessment's stated tolerance.

### Validation
Validation happens in two layers:
1. **Order Update Service** (`order_service/validator.py`) — validates each raw CSV row
   against the event contract (`event_id`, `symbol`, `transaction_type`, `quantity`)
   before it is ever sent. Invalid rows are logged with a reason and skipped; processing
   continues.
2. **Position Maintaining Service** (Pydantic model on the `/events` endpoint) — a second,
   independent validation layer, so a malformed or unexpected payload can never corrupt
   in-memory state, even if it arrived from a source other than the Order Update Service.

### Idempotency
The **first valid event received for a given `event_id` wins**. The Position Maintaining
Service keeps a `set` of seen `event_id`s in memory; any later event with a duplicate ID
is logged and ignored, regardless of whether its other fields differ.

### Concurrency safety
All reads and writes to position state go through a single `threading.Lock`
(`position_service/state.py`). This guarantees `GET /position` never observes a partially
applied update, while still allowing the endpoint to remain responsive while events are
actively being processed.

---
## Project Structure

```text
trading-position/
├── order_updates.csv          # sample/synthetic input data
├── pyproject.toml
├── uv.lock
├── conftest.py                # makes services importable by pytest
├── order_service/
│   ├── __init__.py
│   ├── models.py              # OrderEvent (Pydantic)
│   ├── validator.py           # row -> OrderEvent | error reason
│   ├── reader.py              # streaming CSV reader
│   ├── throttle.py            # fixed-interval rate limiter
│   ├── sender.py              # HTTP client to Position Service
│   └── main.py                # CLI entrypoint
├── position_service/
│   ├── __init__.py
│   ├── models.py              # OrderEvent (Pydantic, API contract)
│   ├── state.py               # thread-safe in-memory position store
│   └── main.py                # FastAPI app + CLI entrypoint
└── tests/
    ├── test_validator.py
    ├── test_position_state.py
    └── test_position_api.py
```

## Setup

This project uses [`uv`](https://docs.astral.sh/uv/) for dependency management.

```bash
# clone the repo
git clone https://github.com/yasshrai/trading-position

cd trading-position

# install dependencies (creates .venv automatically)
uv sync

# install the project itself in editable mode, so order_service/position_service
# are importable from anywhere (including by pytest)
uv pip install -e .
```

> If you're not using `uv`: `pip install -r requirements.txt` and `pip install -e .`
> work identically.

---

## Running the Services

Each service is independently runnable and configured via CLI flags — no hardcoded
paths or ports.

**Terminal 1 — start the Position Maintaining Service:**
```bash
source .venv/bin/activate
uv run python -m position_service.main --host 0.0.0.0 --port 8001
```

**Terminal 2 — start the Order Update Service, pointing at Terminal 1's address:**
```bash

source .venv/bin/activate
uv run python -m order_service.main \
  --csv-path order_updates.csv \
  --target-url http://localhost:8001/events \
  --max-events-per-sec 50
```

The Order Update Service will stream through the CSV, log each accepted/rejected/sent
event, and log a completion message when the file is exhausted. The Position Maintaining
Service's `/position` endpoint remains available throughout and after.

---

## Configuration Options

| Flag | Service | Default | Description |
|---|---|---|---|
| `--csv-path` | Order Update | *(required)* | Path to the input CSV file |
| `--target-url` | Order Update | `http://localhost:8001/events` | Position Service ingest endpoint |
| `--max-events-per-sec` | Order Update | `50` | Throttle rate; configurable, not hardcoded |
| `--host` | Position Maintaining | `0.0.0.0` | Bind address |
| `--port` | Position Maintaining | `8001` | Bind port |

---

## API Usage

### `POST /events`
Ingests a single order event.

**Request:**
```bash
curl -X POST http://localhost:8001/events \
  -H "Content-Type: application/json" \
  -d '{"event_id": "evt-0001", "symbol": "RELIANCE", "transaction_type": "BUY", "quantity": 90}'
```

**Response (applied):**
```json
{"status": "applied"}
```

**Response (duplicate `event_id`):**
```json
{"status": "duplicate"}
```

**Response (invalid payload — handled by Pydantic validation):**
`422 Unprocessable Entity` with a field-level error body.

### `GET /position`
Returns the current net position for every symbol seen in an accepted event, including
symbols whose net position has returned to zero.

**Request:**
```bash
curl http://localhost:8001/position
```

**Response:**
```json
{
  "RELIANCE": 90,
  "TCS": -75
}
```

---

## Running Tests

```bash
uv run pytest tests/ -v
```

**Test coverage includes:**
- BUY and SELL position calculations
- Multiple symbols, including negative and zero net positions
- Duplicate `event_id` handling (both at the store level and via the HTTP API)
- Invalid `transaction_type` values
- Zero, negative, non-integer, and blank quantities
- Blank `event_id` and blank `symbol`
- Continuing to process subsequent rows after an invalid row
- The `GET /position` response shape and contents

An end-to-end test spanning both running processes was considered but intentionally
left out per the assessment's guidance to avoid timing-dependent flakiness; instead,
the Position Service's HTTP layer is tested directly via FastAPI's `TestClient`, and
the Order Service's parsing/validation/throttling logic is tested as pure functions.

---

## Known Limitations & Trade-offs

- **No persistence.** All state (positions, seen event IDs) is in-memory and lost on
  restart of the Position Maintaining Service. This is explicitly out of scope per the
  assessment.
- **No delivery guarantees beyond best-effort.** If the Position Service is down or
  unreachable when an event is sent, that event is logged as failed and not retried.
- **Throttle precision.** The 50 events/sec limit is enforced via fixed-interval spacing,
  not a precise token-bucket or leaky-bucket algorithm — sufficient per the assessment's
  stated tolerance for "not sub-millisecond" timing.
- **Single-instance only.** No support for multiple Position Service replicas or load
  balancing — a single in-memory store is the source of truth by design.
- **No authentication.** Explicitly out of scope per the assessment.

---

## AI-Assisted Tools
AI-Assited tools (Claude) heavily used in documentation and testcase
