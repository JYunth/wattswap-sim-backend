from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime

class Measurements(BaseModel):
    v_rms: float
    i_rms: float
    p_active: float
    q_reactive: float
    apparent_power: float
    frequency: float
    power_factor: float
    flow_dir: str

class PVState(BaseModel):
    pv_power_kw: float
    pv_irradiance_wpm2: float
    pv_temp_c: float
    pv_status: str
    mppt_setpoint_kw: Optional[float]

class BatteryState(BaseModel):
    soc_pct: float
    battery_power_kw: float
    battery_voltage_v: float
    battery_current_a: float
    available_charge_kwh: float
    available_discharge_kwh: float
    p_max_charge_kw: float
    p_max_discharge_kw: float
    bms_status: str
    efficiency_roundtrip: float

class LoadState(BaseModel):
    load_power_kw: float
    appliance: Dict[str, float]
    load_profile: str

class GridState(BaseModel):
    grid_status: str
    grid_price_currency_per_kwh: float
    grid_available_capacity_kw: float

class DerivedState(BaseModel):
    net_power_kw: float
    self_consumption_pct: float
    autonomy_hours: Optional[float]
    time_to_full_hours: Optional[float]
    time_to_empty_hours: Optional[float]

class MarketState(BaseModel):
    pending_orders: int
    current_market_price: float
    last_trade: Optional[Dict]

class Alarm(BaseModel):
    code: str
    level: str
    msg: str

class MeterSnapshot(BaseModel):
    meter_id: str
    timestamp: datetime
    tz: str
    hardware: Dict[str, str]
    measurements: Measurements
    pv: PVState
    battery: BatteryState
    loads: LoadState
    grid: GridState
    derived: DerivedState
    market: MarketState
    alarms: List[Alarm]

# Additional models for API

class ControlSwitchRequest(BaseModel):
    meter_id: str
    switch: str
    value: float | bool | Dict  # Depending on switch

class MarketOrderRequest(BaseModel):
    meter_id: str
    side: str  # sell or buy
    type: str  # sell_limit, buy_limit, etc.
    quantity_kwh: float
    duration_sec: int
    price: Optional[float]
    min_fill_kwh: float
    ttl_sec: int

class MarketOrderResponse(BaseModel):
    order_id: str
    status: str
    reserved_kwh: float

class OrderStatus(BaseModel):
    order_id: str
    status: str
    reserved_kwh: float
    filled_kwh: float
    remaining_kwh: float
    executions: List[Dict]

class HealthResponse(BaseModel):
    tick_rate: float
    time_acceleration: float
    queue_lengths: Dict[str, int]