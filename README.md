# WattSwap Sim Backend

A FastAPI-based simulator for a prosumer smart-meter with PV, battery, and marketplace.

## Installation

Use uv for dependency management.

```bash
uv sync
```

## Running Locally

```bash
uv run uvicorn main:app --reload
```

The API will be available at http://localhost:8000

## Docker

Build and run with Docker:

```bash
docker build -t wattswap-sim-backend .
docker run -p 8000:8000 wattswap-sim-backend
```

## API Endpoints

- GET /api/v1/meter/{meter_id}/snapshot - Current snapshot
- GET /api/v1/meter/{meter_id}/timeseries?start=ISO&end=ISO - Timeseries data
- POST /api/v1/control/switch - Control knobs
- POST /api/v1/market/order - Place market order
- GET /api/v1/market/order/{order_id} - Order status
- POST /api/v1/market/cancel - Cancel order
- GET /api/v1/health - Health check
- GET /api/v1/events - Recent events

## Testing

1. Start the server.
2. Toggle daytime: POST /api/v1/control/switch {"meter_id": "demo_meter", "switch": "daytime", "value": true}
3. Observe PV power increase in snapshot.
4. Place sell order: POST /api/v1/market/order {"meter_id": "demo_meter", "side": "sell", "type": "market", "quantity_kwh": 1.5, "duration_sec": 900}
5. Observe SOC decrease and export power.
6. Disconnect grid: POST /api/v1/control/switch {"meter_id": "demo_meter", "switch": "grid_connected", "value": false}
7. Try buy order, should fail.