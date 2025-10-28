import asyncio
import math
import random
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from collections import deque

from models import (
    MeterSnapshot, Measurements, PVState, BatteryState, LoadState, GridState,
    DerivedState, MarketState, Alarm, MarketOrderRequest, OrderStatus,
    FlowDirection, PVStatus, BMSStatus, LoadProfile, GridStatus, AlarmLevel
)

class Simulator:
    # Default parameters
    PV_CAPACITY_KW = 4.0
    BATTERY_CAPACITY_KWH = 10.0
    BATTERY_SOC_START_PCT = 60.0
    EFFICIENCY_ROUNDTRIP = 0.92
    P_MAX_CHARGE = 3.0
    P_MAX_DISCHARGE = 3.0
    INVERTER_EFFICIENCY = 0.96
    BASE_LOAD_KW = 1.5
    GRID_PRICE = 8.5
    TIME_ACCELERATION = 1.0
    SUNRISE_SECONDS = 900
    SUNSET_SECONDS = 900
    MAX_IRRADIANCE = 1000  # W/m² STC
    STC_IRRADIANCE = 1000  # W/m²
    BATTERY_TEMP_C = 25  # Assume constant for now
    GRID_VOLTAGE = 230  # V
    GRID_FREQUENCY = 50  # Hz

    def __init__(self, meter_id: str, tz: str = "Asia/Kolkata"):
        self.meter_id = meter_id
        self.tz = tz
        self.current_time = datetime.now(timezone.utc).replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))  # Asia/Kolkata UTC+5:30

        # State variables
        self.soc_kwh = self.BATTERY_CAPACITY_KWH * self.BATTERY_SOC_START_PCT / 100
        self.pv_power_kw = 0.0
        self.load_kw = self.BASE_LOAD_KW
        self.battery_power_kw = 0.0
        self.grid_import_kw = 0.0
        self.grid_export_kw = 0.0
        self.energy_imported = 0.0
        self.energy_exported = 0.0
        self.pv_energy = 0.0
        self.unserved_load_kw = 0.0
        self.co2_savings = 0.0
        self.token_earnings = 0.0

        # Knobs
        self.daytime = False
        self.sun_cloud_factor = 1.0
        self.grid_connected = True
        self.market_enabled = True
        self.battery_reserve_pct = 10.0
        self.manual_load_delta_kw = 0.0
        self.ev_plugged = False
        self.ev_mode = 'off'
        self.fault_inject = {}  # e.g., {'bias_pct': 0.01, 'spike_prob': 0.01}
        self.time_acceleration = self.TIME_ACCELERATION

        # Orders
        self.active_orders: List[Dict] = []
        self.order_counter = 0

        # Timeseries ring buffer (last 3600 samples, 1 hour at 1Hz)
        self.timeseries: deque[MeterSnapshot] = deque(maxlen=3600)

        # Events
        self.events: List[Dict] = []

        # Hardware
        self.hardware = {
            "firmware_version": "1.0.0",
            "meter_location": "Demo Site"
        }

        # Alarms
        self.alarms: List[Alarm] = []

        # Initial snapshot
        self.latest_snapshot = self.get_snapshot(230, 1, 0)

    def daylight_curve(self, t: datetime) -> float:
        # Simple ramp up/down over sunrise/sunset seconds
        # Assume day starts at 6am, ends at 6pm
        hour = t.hour + t.minute / 60 + t.second / 3600
        if 6 <= hour < 6 + self.SUNRISE_SECONDS / 3600:
            factor = (hour - 6) / (self.SUNRISE_SECONDS / 3600)
        elif 6 + self.SUNRISE_SECONDS / 3600 <= hour < 18 - self.SUNSET_SECONDS / 3600:
            factor = 1.0
        elif 18 - self.SUNSET_SECONDS / 3600 <= hour < 18:
            factor = (18 - hour) / (self.SUNSET_SECONDS / 3600)
        else:
            factor = 0.0
        return factor if self.daytime else 0.0

    def pv_temp_derate(self, temp_c: float) -> float:
        # Simple derate, assume optimal at 25C, -0.005%/C
        return 1.0 - 0.00005 * (temp_c - 25)

    def tick(self, dt: float = 1.0):
        # Advance time
        self.current_time += timedelta(seconds=dt)

        # PV generation
        irradiance_factor = self.daylight_curve(self.current_time)
        pv_irradiance = self.MAX_IRRADIANCE * irradiance_factor * self.sun_cloud_factor
        pv_power_kw = (self.PV_CAPACITY_KW * (pv_irradiance / self.STC_IRRADIANCE) *
                       self.pv_temp_derate(self.BATTERY_TEMP_C) * self.INVERTER_EFFICIENCY)
        pv_power_kw = max(0, pv_power_kw)
        self.pv_power_kw = pv_power_kw

        # Load
        self.load_kw = self.BASE_LOAD_KW + self.manual_load_delta_kw
        if random.random() < 0.01:  # 1% chance per tick for spike
            self.load_kw += random.uniform(0.5, 2.0)
        if self.ev_plugged and self.ev_mode == 'fast':
            self.load_kw += 3.0  # EV charging

        # Process orders and compute trade demands
        trade_sell_kw = 0.0
        trade_buy_kw = 0.0
        for order in self.active_orders:
            if order['side'] == 'sell':
                # Calculate required power
                remaining = order['quantity_kwh'] - order.get('filled_kwh', 0)
                if remaining > 0:
                    p_trade = min(self.P_MAX_DISCHARGE, remaining / (order['duration_sec'] / 3600))
                    trade_sell_kw += p_trade
            # Similar for buy, but for now focus on sell

        # Battery scheduling
        available_charge = min(self.P_MAX_CHARGE, (self.BATTERY_CAPACITY_KWH - self.soc_kwh) / (dt / 3600) / self.EFFICIENCY_ROUNDTRIP)
        available_discharge = min(self.P_MAX_DISCHARGE, (self.soc_kwh - self.BATTERY_CAPACITY_KWH * self.battery_reserve_pct / 100) / (dt / 3600) * self.EFFICIENCY_ROUNDTRIP)

        pv_available = self.pv_power_kw
        load_deficit = self.load_kw - pv_available
        excess_pv = max(0, pv_available - self.load_kw)

        battery_power_kw = 0.0
        if load_deficit > 0:
            # Discharge to cover load
            discharge_needed = min(load_deficit, available_discharge)
            battery_power_kw = discharge_needed  # positive for discharge
            load_deficit -= discharge_needed
        else:
            # Charge with excess
            charge_possible = min(excess_pv, available_charge)
            battery_power_kw = -charge_possible  # negative for charge

        # Add trade demands
        if trade_sell_kw > 0:
            additional_discharge = min(trade_sell_kw, available_discharge - abs(battery_power_kw))
            battery_power_kw += additional_discharge

        self.battery_power_kw = battery_power_kw

        # Update SOC
        if battery_power_kw > 0:  # discharging
            soc_change = -battery_power_kw * dt / 3600 / self.EFFICIENCY_ROUNDTRIP
        else:  # charging
            soc_change = -battery_power_kw * dt / 3600 * self.EFFICIENCY_ROUNDTRIP
        self.soc_kwh += soc_change
        self.soc_kwh = max(0, min(self.BATTERY_CAPACITY_KWH, self.soc_kwh))

        # Grid
        net_power = self.pv_power_kw + self.battery_power_kw - self.load_kw
        if net_power > 0:
            self.grid_export_kw = min(net_power, 5.0)  # grid_available_capacity
            self.grid_import_kw = 0
        else:
            self.grid_import_kw = min(-net_power, 5.0) if self.grid_connected else 0
            self.grid_export_kw = 0
            if self.grid_connected == False and -net_power > 5.0:
                self.unserved_load_kw = -net_power - 5.0

        # Update counters
        delta_import = self.grid_import_kw * dt / 3600
        delta_export = self.grid_export_kw * dt / 3600
        self.energy_imported += delta_import
        self.energy_exported += delta_export
        self.pv_energy += self.pv_power_kw * dt / 3600
        self.co2_savings += delta_export * 0.45
        self.token_earnings += delta_export * 0.08

        # Update orders
        for order in self.active_orders[:]:
            if order['side'] == 'sell':
                filled_this_tick = self.battery_power_kw * dt / 3600 if self.battery_power_kw > 0 else 0
                order['filled_kwh'] = order.get('filled_kwh', 0) + filled_this_tick
                if order['filled_kwh'] >= order['quantity_kwh']:
                    order['status'] = 'executed'
                    self.active_orders.remove(order)
                    self.events.append({'type': 'order_executed', 'order_id': order['order_id'], 'timestamp': self.current_time.isoformat()})

        # Add noise
        noise_sigma = self.fault_inject.get('sigma_pct', 0.01)
        v_rms = self.GRID_VOLTAGE + random.gauss(0, self.GRID_VOLTAGE * noise_sigma)
        i_rms = abs(net_power) / v_rms + random.gauss(0, abs(net_power) / v_rms * noise_sigma)
        p_active = net_power + random.gauss(0, abs(net_power) * noise_sigma)

        # Build snapshot
        snapshot = self.get_snapshot(v_rms, i_rms, p_active)
        self.latest_snapshot = snapshot
        self.timeseries.append(snapshot)

    def get_snapshot(self, v_rms, i_rms, p_active) -> MeterSnapshot:
        flow_dir = FlowDirection.EXPORT if p_active > 0 else FlowDirection.IMPORT if p_active < 0 else FlowDirection.IDLE
        apparent_power = math.sqrt(p_active**2 + 0.02**2)  # assume q=0.02
        power_factor = p_active / apparent_power if apparent_power > 0 else 1.0

        measurements = Measurements(
            v_rms=v_rms,
            i_rms=i_rms,
            p_active=p_active,
            q_reactive=0.02,
            apparent_power=apparent_power,
            frequency=self.GRID_FREQUENCY + random.gauss(0, 0.1),
            power_factor=power_factor,
            flow_dir=flow_dir,
            thd_voltage_pct=2.5 + random.gauss(0, 0.5)
        )

        pv = PVState(
            pv_power_kw=self.pv_power_kw,
            pv_irradiance_wpm2=self.MAX_IRRADIANCE * self.daylight_curve(self.current_time) * self.sun_cloud_factor,
            pv_temp_c=self.BATTERY_TEMP_C,
            pv_status=PVStatus.ON if self.daytime else PVStatus.STANDBY,
            mppt_setpoint_kw=self.PV_CAPACITY_KW
        )

        battery = BatteryState(
            soc_pct=self.soc_kwh / self.BATTERY_CAPACITY_KWH * 100,
            battery_power_kw=self.battery_power_kw,
            battery_voltage_v=400,
            battery_current_a=self.battery_power_kw * 1000 / 400,
            available_charge_kwh=(self.BATTERY_CAPACITY_KWH - self.soc_kwh) * self.EFFICIENCY_ROUNDTRIP,
            available_discharge_kwh=(self.soc_kwh - self.BATTERY_CAPACITY_KWH * self.battery_reserve_pct / 100) * self.EFFICIENCY_ROUNDTRIP,
            p_max_charge_kw=self.P_MAX_CHARGE,
            p_max_discharge_kw=self.P_MAX_DISCHARGE,
            bms_status=BMSStatus.IDLE if self.battery_power_kw == 0 else (BMSStatus.CHARGING if self.battery_power_kw < 0 else BMSStatus.DISCHARGING),
            efficiency_roundtrip=self.EFFICIENCY_ROUNDTRIP
        )

        loads = LoadState(
            load_power_kw=self.load_kw,
            appliance={'hvac_kw': 1.1, 'ev_charger_kw': 3.0 if self.ev_plugged and self.ev_mode == 'fast' else 0.0, 'fridge_kw': 0.15, 'lighting_kw': 0.2},
            load_profile=LoadProfile.SPIKY
        )

        grid = GridState(
            grid_status=GridStatus.CONNECTED if self.grid_connected else GridStatus.ISLAND,
            grid_price_currency_per_kwh=self.GRID_PRICE,
            grid_available_capacity_kw=5.0
        )

        net_power = self.pv_power_kw + self.battery_power_kw - self.load_kw
        self_consumption = min(self.pv_power_kw, self.load_kw + abs(self.battery_power_kw) if self.battery_power_kw < 0 else self.load_kw)
        autonomy_hours = self.soc_kwh / self.load_kw if self.load_kw > 0 else float('inf')
        time_to_full = (self.BATTERY_CAPACITY_KWH - self.soc_kwh) / self.P_MAX_CHARGE if self.P_MAX_CHARGE > 0 else None
        time_to_empty = self.soc_kwh / self.P_MAX_DISCHARGE if self.P_MAX_DISCHARGE > 0 else None

        derived = DerivedState(
            net_power_kw=net_power,
            self_consumption_pct=self_consumption / self.pv_power_kw * 100 if self.pv_power_kw > 0 else 0,
            autonomy_hours=autonomy_hours,
            time_to_full_hours=time_to_full,
            time_to_empty_hours=time_to_empty,
            energy_imported_kwh=self.energy_imported,
            energy_exported_kwh=self.energy_exported,
            co2_savings_kg=self.co2_savings,
            token_earnings_apt=self.token_earnings,
            system_status="All systems operational",
            status_badge="Online"
        )

        market = MarketState(
            pending_orders=len(self.active_orders),
            current_market_price=self.GRID_PRICE + random.uniform(-1, 1),
            last_trade=self.events[-1] if self.events else None
        )

        return MeterSnapshot(
            meter_id=self.meter_id,
            timestamp=self.current_time,
            tz=self.tz,
            hardware=self.hardware,
            measurements=measurements,
            pv=pv,
            battery=battery,
            loads=loads,
            grid=grid,
            derived=derived,
            market=market,
            alarms=self.alarms
        )

    def add_order(self, order_req: MarketOrderRequest) -> str:
        order_id = f"order_{self.order_counter}"
        self.order_counter += 1
        order = order_req.dict()
        order['order_id'] = order_id
        order['status'] = 'accepted'
        order['filled_kwh'] = 0
        order['start_time'] = self.current_time.isoformat()
        self.active_orders.append(order)
        return order_id

    def cancel_order(self, order_id: str) -> bool:
        for order in self.active_orders:
            if order['order_id'] == order_id:
                self.active_orders.remove(order)
                return True
        return False

    def get_order_status(self, order_id: str) -> Optional[OrderStatus]:
        for order in self.active_orders:
            if order['order_id'] == order_id:
                return OrderStatus(
                    order_id=order_id,
                    status=order['status'],
                    reserved_kwh=order['quantity_kwh'],
                    filled_kwh=order.get('filled_kwh', 0),
                    remaining_kwh=order['quantity_kwh'] - order.get('filled_kwh', 0),
                    executions=[]
                )
        return None