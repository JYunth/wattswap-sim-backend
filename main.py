from fastapi import FastAPI, HTTPException, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
from typing import List, Literal, Union, Dict
from datetime import datetime

from simulator import Simulator
from models import (
    MeterSnapshot, MarketOrderRequest, MarketOrderResponse,
    OrderStatus, HealthResponse, TimeseriesResponse, EventsResponse,
    ControlResponse, CancelResponse, ConstantsResponse
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

app = FastAPI(
    title="WattSwap Smart Meter Simulator API",
    description="""
    A comprehensive simulation backend for prosumer smart meters with PV, battery storage, and energy marketplace.

    ## Features

    * **Real-time Simulation**: 1Hz updates with configurable time acceleration
    * **Hardware Modeling**: PV inverter, battery storage, loads, grid connection
    * **Marketplace**: Buy/sell energy orders with execution tracking
    * **Control Knobs**: Adjust environmental conditions and behavior
    * **Analytics**: Self-consumption, autonomy, efficiency metrics

    ## Usage

    Start the simulator, then use /control/switch to adjust parameters.
    Monitor live state via /snapshot, historical data via /timeseries.
    Place market orders and track execution via /market endpoints.

    ## Authentication

    Currently no authentication - single meter simulation.
    """,
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware to allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

@app.get("/api/v1/meter/{meter_id}/snapshot", response_model=MeterSnapshot)
async def get_snapshot(meter_id: str):
    """
    Get the current real-time snapshot of the smart meter.

    This endpoint returns the latest instantaneous measurements, PV status, battery state,
    load information, grid connection details, derived analytics, and current market state.

    Includes:
    - **Measurements**: Voltage, current, power, frequency, power factor, flow direction, THD voltage
    - **PV State**: Power output, irradiance, temperature, status
    - **Battery State**: SoC, power, voltage, current, charge/discharge limits, status
    - **Load State**: Total power, appliance breakdown, profile type
    - **Grid State**: Connection status, pricing, capacity
    - **Derived Analytics**: Net power, self-consumption, autonomy, cumulative energies, CO2 savings, token earnings, system status
    - **Market State**: Pending orders, market price, last trade
    - **Alarms**: Active system alerts

    - **meter_id**: Unique identifier for the meter (currently "demo_meter")
    - **Returns**: Complete meter snapshot with all hardware and derived signals
    - **Updates**: At 1Hz simulation rate, reflecting live state changes
    """
    if meter_id != simulator.meter_id:
        raise HTTPException(status_code=404, detail="Meter not found")
    async with lock:
        return simulator.latest_snapshot

@app.get("/api/v1/meter/{meter_id}/timeseries", response_model=TimeseriesResponse)
async def get_timeseries(meter_id: str, start: str = Query(...), end: str = Query(...), resolution: str = "1s"):
    """
    Retrieve historical timeseries data for the meter.

    Returns an array of snapshots between the specified start and end times.
    Data is stored in a ring buffer (last 1 hour at 1Hz).

    Each snapshot includes complete meter data:
    - **Measurements**: Voltage, current, power, frequency, power factor, flow direction, THD voltage
    - **PV/Battery/Load/Grid States**: All current status and parameters
    - **Derived Analytics**: Net power, self-consumption, autonomy, cumulative energies, CO2 savings, token earnings
    - **Market & Alarms**: Trading activity and system alerts

    - **meter_id**: Unique identifier for the meter
    - **start**: ISO8601 timestamp for start of range (e.g., "2025-10-29T10:00:00")
    - **end**: ISO8601 timestamp for end of range
    - **resolution**: Data resolution ("1s" for 1-second intervals)
    - **Returns**: List of meter snapshots within the time range
    """
    if meter_id != simulator.meter_id:
        raise HTTPException(status_code=404, detail="Meter not found")
    start_dt = datetime.fromisoformat(start)
    end_dt = datetime.fromisoformat(end)
    async with lock:
        filtered = [s for s in simulator.timeseries if start_dt <= s.timestamp <= end_dt]
        # For simplicity, return all, downsample if needed
        return {"data": filtered}

@app.post("/api/v1/control/switch", response_model=ControlResponse)
async def control_switch(
    meter_id: str = Form(default="demo_meter", description="Meter identifier"),
    switch: Literal["daytime", "grid_connected", "market_enabled", "battery_reserve_pct", "manual_load_delta_kw", "sun_cloud_factor", "ev_plug", "ev_mode", "fault_inject", "time_acceleration"] = Form(..., description="Control switch to adjust"),
    value: str = Form(..., description="New value for the switch (as string, parsed based on switch type)")
):
    """
    Control simulation knobs and switches.

    Allows real-time adjustment of environmental and behavioral parameters.
    Changes take effect immediately in the next simulation tick.

    Supported switches:
    - **daytime** (bool): Enable/disable PV generation (solar irradiance curve) - use 'true'/'false'
    - **grid_connected** (bool): Connect/disconnect from grid (affects import/export) - use 'true'/'false'
    - **market_enabled** (bool): Enable/disable marketplace trading - use 'true'/'false'
    - **battery_reserve_pct** (float): Minimum SoC reserve (0-100%) - use number as string
    - **manual_load_delta_kw** (float): Add/subtract load for testing spikes - use number as string
    - **sun_cloud_factor** (float): Multiplier for PV irradiance (0-1, simulates clouds) - use number as string
    - **ev_plug** (bool): Plug/unplug EV charger - use 'true'/'false'
    - **ev_mode** (str): EV charging mode ("off", "fast", "scheduled") - use exact string
    - **fault_inject** (dict): Inject sensor faults (bias_pct, spike_prob, dropout_prob) - use JSON string
    - **time_acceleration** (float): Simulation speed multiplier (1.0 = real-time) - use number as string

    - **meter_id**: Must match the simulator's meter ID
    - **switch**: Name of the control to adjust
    - **value**: New value for the switch (strictly enforced by type)
    """
    if meter_id != simulator.meter_id:
        raise HTTPException(status_code=404, detail="Meter not found")
    
    # Parse value based on switch type
    if switch in ["daytime", "grid_connected", "market_enabled", "ev_plug"]:
        if value not in ["true", "false"]:
            raise HTTPException(status_code=400, detail=f"Value for {switch} must be 'true' or 'false'")
        parsed_value = value == "true"
    elif switch in ["battery_reserve_pct", "manual_load_delta_kw", "sun_cloud_factor", "time_acceleration"]:
        try:
            parsed_value = float(value)
            if switch == "battery_reserve_pct" and not (0 <= parsed_value <= 100):
                raise HTTPException(status_code=400, detail="battery_reserve_pct must be between 0 and 100")
            if switch == "sun_cloud_factor" and not (0 <= parsed_value <= 1):
                raise HTTPException(status_code=400, detail="sun_cloud_factor must be between 0 and 1")
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Value for {switch} must be a valid number")
    elif switch == "ev_mode":
        if value not in ["off", "fast", "scheduled"]:
            raise HTTPException(status_code=400, detail="ev_mode must be 'off', 'fast', or 'scheduled'")
        parsed_value = value
    elif switch == "fault_inject":
        try:
            import json
            parsed_value = json.loads(value)
            if not isinstance(parsed_value, dict):
                raise HTTPException(status_code=400, detail="fault_inject must be a JSON object")
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="fault_inject must be valid JSON")
    else:
        raise HTTPException(status_code=400, detail="Unknown switch")
    
    async with lock:
        if switch == "daytime":
            simulator.daytime = bool(parsed_value)
        elif switch == "grid_connected":
            simulator.grid_connected = bool(parsed_value)
        elif switch == "market_enabled":
            simulator.market_enabled = bool(parsed_value)
        elif switch == "battery_reserve_pct":
            simulator.battery_reserve_pct = float(parsed_value)
        elif switch == "manual_load_delta_kw":
            simulator.manual_load_delta_kw = float(parsed_value)
        elif switch == "sun_cloud_factor":
            simulator.sun_cloud_factor = float(parsed_value)
        elif switch == "ev_plug":
            simulator.ev_plugged = bool(parsed_value)
        elif switch == "ev_mode":
            simulator.ev_mode = str(parsed_value)
        elif switch == "fault_inject":
            simulator.fault_inject = dict(parsed_value)
        elif switch == "time_acceleration":
            simulator.time_acceleration = float(parsed_value)
        else:
            raise HTTPException(status_code=400, detail="Unknown switch")
    return {"status": "ok"}

@app.get("/api/v1/control/time_acceleration")
async def get_time_acceleration():
    """
    Get the current time acceleration factor.

    Returns the simulation speed multiplier (1.0 = real-time).
    Useful for monitoring simulation performance.

    - **Returns**: Current time acceleration value
    """
    async with lock:
        return {"time_acceleration": simulator.time_acceleration}

@app.get("/api/v1/control/switches", response_model=Dict[str, Union[bool, float, str, Dict]])
async def get_switches():
    """
    Get the current status of all control switches.

    Returns the current values of all simulator control knobs and switches.
    Useful for UI state synchronization and debugging.

    - **Returns**: Dictionary with switch names as keys and their current values
    """
    async with lock:
        return {
            "daytime": simulator.daytime,
            "grid_connected": simulator.grid_connected,
            "market_enabled": simulator.market_enabled,
            "battery_reserve_pct": simulator.battery_reserve_pct,
            "manual_load_delta_kw": simulator.manual_load_delta_kw,
            "sun_cloud_factor": simulator.sun_cloud_factor,
            "ev_plug": simulator.ev_plugged,
            "ev_mode": simulator.ev_mode,
            "fault_inject": simulator.fault_inject,
            "time_acceleration": simulator.time_acceleration,
        }
    """
    Get the current status of all control switches.

    Returns the current values of all simulator control knobs and switches.
    Useful for UI state synchronization and debugging.

    - **Returns**: Dictionary with switch names as keys and their current values
    """
    async with lock:
        return {
            "daytime": simulator.daytime,
            "grid_connected": simulator.grid_connected,
            "market_enabled": simulator.market_enabled,
            "battery_reserve_pct": simulator.battery_reserve_pct,
            "manual_load_delta_kw": simulator.manual_load_delta_kw,
            "sun_cloud_factor": simulator.sun_cloud_factor,
            "ev_plug": simulator.ev_plugged,
            "ev_mode": simulator.ev_mode,
            "fault_inject": simulator.fault_inject,
            "time_acceleration": simulator.time_acceleration,
        }

@app.post("/api/v1/market/order", response_model=MarketOrderResponse)
async def create_order(request: MarketOrderRequest):
    """
    Place a new market order for energy trading.

    Creates buy or sell orders that are executed over time based on available energy.
    Orders can be market (immediate execution) or limit (price-based).

    Order types:
    - **sell_market**: Sell energy at current market price
    - **buy_market**: Buy energy at current market price
    - **sell_limit**: Sell at specified price or better
    - **buy_limit**: Buy at specified price or better

    Execution:
    - Sell orders discharge battery or use excess PV
    - Buy orders increase grid import or charge battery
    - Partial fills possible if insufficient energy
    - Duration spreads execution over time

    - **meter_id**: Meter identifier
    - **side**: "sell" or "buy"
    - **type**: Order type (sell_market, buy_market, etc.)
    - **quantity_kwh**: Total energy to trade
    - **duration_sec**: Time over which to execute (affects power rate)
    - **price**: Limit price (optional for market orders)
    - **min_fill_kwh**: Minimum partial fill size
    - **ttl_sec**: Time-to-live before expiration
    - **Returns**: Order ID and initial status
    """
    if request.meter_id != simulator.meter_id:
        raise HTTPException(status_code=404, detail="Meter not found")
    async with lock:
        order_id = simulator.add_order(request)
        reserved = request.quantity_kwh
    return MarketOrderResponse(order_id=order_id, status="accepted", reserved_kwh=reserved)

@app.get("/api/v1/market/order/{order_id}", response_model=OrderStatus)
async def get_order_status(order_id: str):
    """
    Get the current status of a market order.

    Shows execution progress, filled quantity, remaining energy, and status.

    Status values:
    - **accepted**: Order received, not yet executed
    - **partially_filled**: Some energy traded, more pending
    - **executed**: Fully completed
    - **failed**: Could not execute (e.g., insufficient energy, grid disconnected)
    - **expired**: TTL reached without full execution

    - **order_id**: Unique order identifier from creation response
    - **Returns**: Detailed order status with execution history
    """
    async with lock:
        status = simulator.get_order_status(order_id)
    if not status:
        raise HTTPException(status_code=404, detail="Order not found")
    return status

@app.post("/api/v1/market/cancel", response_model=CancelResponse)
async def cancel_order(order_id: str):
    """
    Cancel a pending market order.

    Removes the order from execution queue. Already executed portions
    cannot be reversed. Only affects orders that are not yet fully executed.

    - **order_id**: ID of the order to cancel
    - **Returns**: Success confirmation or 404 if order not found
    """
    async with lock:
        success = simulator.cancel_order(order_id)
    if not success:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"status": "cancelled"}

@app.get("/api/v1/health", response_model=HealthResponse)
async def get_health():
    """
    Get simulator health and performance metrics.

    Useful for monitoring simulation status and queue depths.

    - **tick_rate**: Current simulation update frequency (Hz)
    - **time_acceleration**: Speed multiplier (1.0 = real-time)
    - **queue_lengths**: Dictionary of internal queue sizes (orders, events, etc.)
    - **Returns**: Health status for load balancing and monitoring
    """
    async with lock:
        return HealthResponse(
            tick_rate=1.0,  # assuming
            time_acceleration=simulator.time_acceleration,
            queue_lengths={"orders": len(simulator.active_orders)}
        )

@app.get("/api/v1/constants", response_model=ConstantsResponse)
async def get_constants():
    """
    Get frontend configuration constants.

    Provides values for CO2 factor, token rate, and refresh intervals
    used by the dashboard for calculations and polling.
    """
    return ConstantsResponse()

@app.get("/api/v1/events", response_model=EventsResponse)
async def get_events(limit: int = 50):
    """
    Get recent simulation events and order executions.

    Events include order placements, executions, failures, and system alerts.
    Useful for audit trails and real-time notifications.

    Event types:
    - **order_accepted**: New order received
    - **order_executed**: Order fully completed
    - **order_failed**: Order could not be fulfilled
    - **battery_alarm**: SoC or temperature warnings
    - **grid_disconnect**: Islanding events

    - **limit**: Maximum number of recent events to return (default 50)
    - **Returns**: Array of event objects with timestamps and details
    """
    async with lock:
        return {"events": simulator.events[-limit:]}
