from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Literal
from datetime import datetime
from enum import Enum

# Enums for better schema documentation
class FlowDirection(str, Enum):
    IMPORT = "import"
    EXPORT = "export"
    IDLE = "idle"

class PVStatus(str, Enum):
    ON = "on"
    STANDBY = "standby"
    FAULT = "fault"

class BMSStatus(str, Enum):
    IDLE = "idle"
    CHARGING = "charging"
    DISCHARGING = "discharging"
    FAULT = "fault"

class LoadProfile(str, Enum):
    STEADY = "steady"
    SPIKY = "spiky"
    THERMOSTAT_CONTROLLED = "thermostat_controlled"

class GridStatus(str, Enum):
    CONNECTED = "connected"
    ISLAND = "islanded"

class AlarmLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

class OrderSide(str, Enum):
    SELL = "sell"
    BUY = "buy"

class OrderType(str, Enum):
    SELL_MARKET = "sell_market"
    BUY_MARKET = "buy_market"
    SELL_LIMIT = "sell_limit"
    BUY_LIMIT = "buy_limit"

class EVMode(str, Enum):
    OFF = "off"
    FAST = "fast"
    SCHEDULED = "scheduled"

class Measurements(BaseModel):
    v_rms: float
    i_rms: float
    p_active: float
    q_reactive: float
    apparent_power: float
    frequency: float
    power_factor: float
    flow_dir: FlowDirection
    thd_voltage_pct: float = Field(default=2.5, description="Total Harmonic Distortion in voltage")

class PVState(BaseModel):
    pv_power_kw: float
    pv_irradiance_wpm2: float
    pv_temp_c: float
    pv_status: PVStatus
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
    bms_status: BMSStatus
    efficiency_roundtrip: float

class LoadState(BaseModel):
    load_power_kw: float
    appliance: Dict[str, float]
    load_profile: LoadProfile

class GridState(BaseModel):
    grid_status: GridStatus
    grid_price_currency_per_kwh: float
    grid_available_capacity_kw: float

class DerivedState(BaseModel):
    net_power_kw: float
    self_consumption_pct: float
    autonomy_hours: Optional[float]
    time_to_full_hours: Optional[float]
    time_to_empty_hours: Optional[float]
    energy_imported_kwh: float = Field(description="Cumulative energy imported from grid")
    energy_exported_kwh: float = Field(description="Cumulative energy exported to grid")
    co2_savings_kg: float = Field(description="Cumulative CO2 savings from exports")
    token_earnings_apt: float = Field(description="Cumulative token earnings from exports")
    system_status: str = Field(default="All systems operational", description="Overall system status")
    status_badge: str = Field(default="Online", description="Status badge text")

class MarketState(BaseModel):
    pending_orders: int
    current_market_price: float
    last_trade: Optional[Dict]

class Alarm(BaseModel):
    code: str
    level: AlarmLevel
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
    meter_id: str = Field(default="demo_meter", description="Meter identifier")
    switch: Literal["daytime", "grid_connected", "market_enabled", "battery_reserve_pct", "manual_load_delta_kw", "sun_cloud_factor", "ev_plug", "ev_mode", "fault_inject", "time_acceleration"] = Field(default="daytime", description="Control switch to adjust", examples=["daytime", "grid_connected", "market_enabled"])
    value: float | bool | Dict | str = Field(default=True, description="New value for the switch (type depends on switch)")

class MarketOrderRequest(BaseModel):
    meter_id: str = Field(default="demo_meter", description="Meter identifier")
    side: OrderSide = Field(default=OrderSide.SELL, description="Order side: sell or buy")
    type: OrderType = Field(default=OrderType.SELL_MARKET, description="Order type")
    quantity_kwh: float = Field(default=1.5, description="Total energy quantity in kWh")
    duration_sec: int = Field(default=900, description="Execution duration in seconds")
    price: Optional[float] = Field(default=None, description="Limit price (optional for market orders)")
    min_fill_kwh: float = Field(default=0.1, description="Minimum partial fill quantity")
    ttl_sec: int = Field(default=600, description="Time-to-live before expiration")

class MarketOrderResponse(BaseModel):
    order_id: str = Field(description="Unique order identifier")
    status: str = Field(default="accepted", description="Order status")
    reserved_kwh: float = Field(description="Reserved energy quantity")

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

class TimeseriesResponse(BaseModel):
    data: List[MeterSnapshot] = Field(description="List of meter snapshots in the requested time range")

class EventsResponse(BaseModel):
    events: List[Dict] = Field(description="List of recent simulation events")

class ControlResponse(BaseModel):
    status: str = Field(default="ok", description="Operation status")

class CancelResponse(BaseModel):
    status: str = Field(default="cancelled", description="Cancellation status")

class ConstantsResponse(BaseModel):
    co2_factor: float = Field(default=0.45, description="kg CO₂ per kWh")
    token_rate: float = Field(default=0.08, description="APT per kWh")
    refresh_interval_ms: int = Field(default=5000, description="Frontend refresh interval")