from fastapi import FastAPI, HTTPException, Query
from contextlib import asynccontextmanager
import asyncio
from typing import List
from datetime import datetime

from simulator import Simulator
from models import (
    MeterSnapshot, ControlSwitchRequest, MarketOrderRequest, MarketOrderResponse,
    OrderStatus, HealthResponse
)

simulator = Simulator("demo_meter")
lock = asyncio.Lock()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start simulation task
    task = asyncio.create_task(simulation_loop())
    yield
    task.cancel()

async def simulation_loop():
    while True:
        async with lock:
            simulator.tick()
        await asyncio.sleep(1 / simulator.time_acceleration)

app = FastAPI(lifespan=lifespan)

@app.get("/api/v1/meter/{meter_id}/snapshot", response_model=MeterSnapshot)
async def get_snapshot(meter_id: str):
    if meter_id != simulator.meter_id:
        raise HTTPException(status_code=404, detail="Meter not found")
    async with lock:
        return simulator.latest_snapshot

@app.get("/api/v1/meter/{meter_id}/timeseries")
async def get_timeseries(meter_id: str, start: str = Query(...), end: str = Query(...), resolution: str = "1s"):
    if meter_id != simulator.meter_id:
        raise HTTPException(status_code=404, detail="Meter not found")
    start_dt = datetime.fromisoformat(start)
    end_dt = datetime.fromisoformat(end)
    async with lock:
        filtered = [s for s in simulator.timeseries if start_dt <= s.timestamp <= end_dt]
        # For simplicity, return all, downsample if needed
        return {"data": filtered}

@app.post("/api/v1/control/switch")
async def control_switch(request: ControlSwitchRequest):
    if request.meter_id != simulator.meter_id:
        raise HTTPException(status_code=404, detail="Meter not found")
    async with lock:
        if request.switch == "daytime":
            simulator.daytime = bool(request.value)
        elif request.switch == "grid_connected":
            simulator.grid_connected = bool(request.value)
        elif request.switch == "market_enabled":
            simulator.market_enabled = bool(request.value)
        elif request.switch == "battery_reserve_pct":
            simulator.battery_reserve_pct = float(request.value)
        elif request.switch == "manual_load_delta_kw":
            simulator.manual_load_delta_kw = float(request.value)
        elif request.switch == "sun_cloud_factor":
            simulator.sun_cloud_factor = float(request.value)
        elif request.switch == "ev_plug":
            simulator.ev_plugged = bool(request.value)
        elif request.switch == "ev_mode":
            simulator.ev_mode = str(request.value)
        elif request.switch == "fault_inject":
            simulator.fault_inject = dict(request.value)
        elif request.switch == "time_acceleration":
            simulator.time_acceleration = float(request.value)
        else:
            raise HTTPException(status_code=400, detail="Unknown switch")
    return {"status": "ok"}

@app.post("/api/v1/market/order", response_model=MarketOrderResponse)
async def create_order(request: MarketOrderRequest):
    if request.meter_id != simulator.meter_id:
        raise HTTPException(status_code=404, detail="Meter not found")
    async with lock:
        order_id = simulator.add_order(request)
        reserved = request.quantity_kwh
    return MarketOrderResponse(order_id=order_id, status="accepted", reserved_kwh=reserved)

@app.get("/api/v1/market/order/{order_id}", response_model=OrderStatus)
async def get_order_status(order_id: str):
    async with lock:
        status = simulator.get_order_status(order_id)
    if not status:
        raise HTTPException(status_code=404, detail="Order not found")
    return status

@app.post("/api/v1/market/cancel")
async def cancel_order(order_id: str):
    async with lock:
        success = simulator.cancel_order(order_id)
    if not success:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"status": "cancelled"}

@app.get("/api/v1/health", response_model=HealthResponse)
async def get_health():
    async with lock:
        return HealthResponse(
            tick_rate=1.0,  # assuming
            time_acceleration=simulator.time_acceleration,
            queue_lengths={"orders": len(simulator.active_orders)}
        )

@app.get("/api/v1/events")
async def get_events(limit: int = 50):
    async with lock:
        return {"events": simulator.events[-limit:]}
