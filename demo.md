# WattSwap Demo Scenarios

This document provides step-by-step demo scenarios with curl commands to test the WattSwap simulator and observe frontend behavior.

**Base URL**: `http://46.62.231.61:8000`

---

## 1. Nighttime Baseline (Default Settings)

Default state with no solar generation, grid-connected, no marketplace activity.

```bash
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=daytime&value=false" && \
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=grid_connected&value=true" && \
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=market_enabled&value=false"
```

**Expected Frontend Behavior:**
- **Dashboard Metrics**: Voltage ~230V, Current ~8.7A, Active Power ~2kW (import from grid)
- **Import Energy Widget**: Shows steadily increasing consumption (red trending indicator)
- **Export Energy Widget**: Remains at 0 kWh
- **Power Factor**: ~0.92-0.98 (Good rating)
- **Status Badge**: "Online" with green indicator
- **Analytics Charts**: 
  - Active Power chart shows constant ~2kW consumption
  - Import/Export chart shows only import line rising
  - Token Earnings remain at 0
  - CO₂ Savings remain at 0

---

## 2. Daytime PV Generation

Enable solar generation during daytime hours.

```bash
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=daytime&value=true" && \
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=sun_cloud_factor&value=1.0"
```

**Expected Frontend Behavior:**
- **Dashboard Metrics**: Active Power drops to ~0.5kW (most load covered by solar)
- **Voltage**: Slightly higher (~232V) due to PV backfeed
- **Current**: Reduced to ~2.2A
- **Export Energy Widget**: Begins accumulating (green trending indicator showing +18.7%)
- **Import Energy Widget**: Slows significantly or pauses
- **Status Badge**: Changes to indicate "Self-generation active"
- **Analytics Charts**:
  - Active Power chart shows reduced grid dependency
  - Import/Export chart shows export line (green) rising
  - CO₂ Savings chart begins accumulating (blue line rising)
  - Power Factor remains stable

---

## 3. Battery Management (Daytime Charging)

Enable higher battery reserve to store excess solar energy.

```bash
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=daytime&value=true" && \
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=battery_reserve_pct&value=50.0"
```

**Expected Frontend Behavior:**
- **Dashboard Metrics**: Active Power ~0.5-1.0kW (battery charging load visible)
- **Battery Widget** (if present): SoC percentage rising, charging indicator active
- **Export Energy**: Minimal or zero (energy diverted to battery storage)
- **Import Energy**: Slight increase to charge battery faster
- **Status Badge**: "Battery Charging" or "Storing Energy"
- **Analytics Charts**:
  - Export Energy line flattens (less immediate export)
  - Token Earnings slow down temporarily
  - CO₂ Savings rate decreases slightly
  - Battery state indicator shows "Charging" mode

---

## 4. Battery Backup (Nighttime Discharging)

Let battery discharge during nighttime to reduce grid import.

```bash
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=daytime&value=false" && \
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=battery_reserve_pct&value=10.0"
```

**Expected Frontend Behavior:**
- **Dashboard Metrics**: Active Power ~0kW from grid (battery supplying load)
- **Current**: Low or near-zero grid current
- **Battery Widget**: SoC decreasing, discharging indicator active
- **Import Energy**: Flat or minimal increase
- **Status Badge**: "Battery Backup Active"
- **Analytics Charts**:
  - Import Energy line flattens (minimal grid usage)
  - Power chart shows negative battery power (discharging)
  - Battery efficiency metrics visible
  - Autonomy hours displayed based on remaining SoC

---

## 5. Marketplace Selling (Excess PV Export)

Enable marketplace and sell excess solar energy.

### Step 1: Setup switches for selling conditions
```bash
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=daytime&value=true" && \
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=grid_connected&value=true" && \
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=market_enabled&value=true"
```

### Step 2: Place sell order
```bash
curl -X POST "http://46.62.231.61:8000/api/v1/market/order" \
  -H "Content-Type: application/json" \
  -d '{
    "meter_id": "demo_meter",
    "side": "sell",
    "type": "sell_market",
    "quantity_kwh": 1.5,
    "duration_sec": 900,
    "min_fill_kwh": 0.1,
    "ttl_sec": 600
  }'
```

**Expected Frontend Behavior:**
- **Dashboard Metrics**: Active Power shows negative (exporting ~1.5kW)
- **Export Energy Widget**: Rapidly increasing with upward trend (+18.7%)
- **Market Widget** (if present): Shows pending sell order, execution progress bar
- **Token Earnings Chart**: Green line (APT) rising steadily (0.08 APT per kWh)
- **CO₂ Savings Chart**: Blue line accelerating (0.45 kg CO₂ per kWh saved)
- **Status Badge**: "Selling to Market" or "Prosumer Active"
- **Events Panel**: Shows "Order Accepted" notification
- **Order Status**: Updates from "accepted" → "partially_filled" → "executed"
- **Notifications**: Toast/alert when order completes successfully

---

## 6. Marketplace Buying (Battery Recharging)

Enable marketplace buying to recharge battery during nighttime.

### Step 1: Setup switches for buying conditions
```bash
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=daytime&value=false" && \
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=grid_connected&value=true" && \
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=market_enabled&value=true"
```

### Step 2: Place buy order
```bash
curl -X POST "http://46.62.231.61:8000/api/v1/market/order" \
  -H "Content-Type: application/json" \
  -d '{
    "meter_id": "demo_meter",
    "side": "buy",
    "type": "buy_market",
    "quantity_kwh": 2.0,
    "duration_sec": 600,
    "min_fill_kwh": 0.1,
    "ttl_sec": 900
  }'
```

**Expected Frontend Behavior:**
- **Dashboard Metrics**: Active Power increases temporarily (~3-4kW import)
- **Import Energy Widget**: Increases as market purchases energy
- **Battery Widget**: SoC rising, charging indicator active
- **Market Widget**: Shows pending buy order with progress
- **Token Earnings**: Decreasing (spending APT tokens on purchases)
- **Status Badge**: "Purchasing from Market"
- **Events Panel**: Shows "Buy Order Accepted" notification
- **Order History**: Displays buy transaction details
- **Notifications**: Alert when battery reaches target SoC
- **Grid Price Display**: Shows current market price per kWh

---

## 7. Island Mode (Off-Grid Operation)

Disconnect from grid to simulate off-grid/island mode.

```bash
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=grid_connected&value=false" && \
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=daytime&value=false"
```

**Expected Frontend Behavior:**
- **Dashboard Metrics**: Grid status changes to "Islanded"
- **Voltage/Frequency**: May show slight variations (island operation)
- **Import/Export Energy**: Both flat (no grid interaction)
- **Battery Widget**: Discharging to supply load, SoC decreasing
- **Status Badge**: Changes to "Off-Grid" or "Island Mode" (amber/warning color)
- **Alarm Widget**: May show "Grid Disconnected" info-level alarm
- **Autonomy Metric**: Displays hours remaining on battery (e.g., "4.2 hours")
- **Market Widget**: Disabled/grayed out (no marketplace access)
- **Analytics Charts**: Grid import/export lines become flat
- **Warning Indicators**: Low battery warning if SoC drops below threshold

---

## 8. Full System Optimization

Optimal prosumer operation with balanced generation, storage, and trading.

```bash
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=daytime&value=true" && \
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=grid_connected&value=true" && \
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=market_enabled&value=true" && \
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=battery_reserve_pct&value=50.0"
```

**Expected Frontend Behavior:**
- **Dashboard Metrics**: Near-zero net grid power (balanced operation)
- **Active Power**: Minimal import/export (~0-0.5kW)
- **Self-Consumption**: High percentage (>80%)
- **Battery Widget**: Maintaining target SoC, smart charge/discharge cycles
- **Status Badge**: "Optimal Operation" (green)
- **All Widgets**: Balanced values, no alarms
- **Analytics Charts**:
  - Power chart shows stable, low grid dependency
  - CO₂ Savings maximized (steep blue curve)
  - Token Earnings steady growth
  - Import/Export roughly balanced
- **Efficiency Metrics**: High round-trip efficiency displayed
- **System Health**: All indicators green

---

## 9. Grid Failure Simulation

Simulate grid outage with marketplace enabled (should fail gracefully).

### Step 1: Setup grid failure
```bash
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=grid_connected&value=false" && \
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=daytime&value=false" && \
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=market_enabled&value=true"
```

### Step 2: Attempt buy order (should fail)
```bash
curl -X POST "http://46.62.231.61:8000/api/v1/market/order" \
  -H "Content-Type: application/json" \
  -d '{
    "meter_id": "demo_meter",
    "side": "buy",
    "type": "buy_market",
    "quantity_kwh": 1.0,
    "duration_sec": 300,
    "min_fill_kwh": 0.1,
    "ttl_sec": 600
  }'
```

**Expected Frontend Behavior:**
- **Dashboard Status**: "Emergency Backup Mode" (red/warning)
- **Grid Status Widget**: Shows "Disconnected" or "Fault"
- **Alarm Panel**: "Grid Disconnect" error-level alarm visible
- **Battery Widget**: Critical discharge mode, SoC dropping
- **Autonomy Display**: Countdown timer prominent (e.g., "2.3 hours remaining")
- **Market Widget**: Shows failed order with error message "Grid unavailable"
- **Order Status**: Changes to "failed" with reason displayed
- **Notifications**: Error toast: "Cannot execute buy order - grid disconnected"
- **Events Panel**: Shows failed transaction event
- **Import/Export Widgets**: Both frozen at last values
- **Load Shedding Indicator** (if implemented): May show non-critical loads disabled

---

## 10. Load Spike Testing

Simulate sudden load increase (e.g., AC unit starts).

```bash
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=daytime&value=true" && \
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=manual_load_delta_kw&value=2.0"
```

**Expected Frontend Behavior:**
- **Dashboard Metrics**: Active Power jumps to ~4kW (load spike visible)
- **Current**: Increases significantly (from ~8A to ~17A)
- **Power Factor**: May temporarily drop due to spike
- **Battery Widget**: Begins discharging to buffer the spike
- **Import Energy**: Increases more rapidly
- **Real-time Chart** (if present): Shows sharp upward spike in power curve
- **Status Badge**: "High Load Detected"
- **Alarms**: May show info-level "Load spike detected" alert
- **Analytics**:
  - Active Power chart shows sudden vertical jump
  - Self-consumption percentage may temporarily drop
  - Battery responds within seconds to smooth the load

---

## 11. EV Charging (Fast Mode)

Plug in EV and enable fast charging mode.

```bash
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=daytime&value=true" && \
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=ev_plug&value=true" && \
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=ev_mode&value=fast"
```

**Expected Frontend Behavior:**
- **Dashboard Metrics**: Active Power increases by ~3kW (EV charging load)
- **Current**: Significant increase (~13A additional)
- **EV Widget** (if present): Shows "EV Connected - Fast Charging"
- **Load Breakdown**: Appliance list shows "EV Charger: 3.0 kW"
- **Import Energy**: Increases if PV insufficient
- **Battery**: May discharge to supplement PV for EV charging
- **Status Badge**: "EV Charging Active"
- **Analytics**:
  - Power chart shows sustained ~3kW increase
  - Import/Export balance shifts toward import
  - CO₂ savings still positive (using solar to charge EV)
- **EV Charge Progress**: Progress bar showing charge level (if implemented)

---

## 12. Fault Injection (Sensor Bias)

Inject sensor bias to test fault detection and diagnostics.

```bash
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=daytime&value=true" && \
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'meter_id=demo_meter&switch=fault_inject&value={"bias_pct": 10.0}'
```

**Expected Frontend Behavior:**
- **Dashboard Metrics**: All power readings biased ~10% higher
- **Voltage/Current**: Displayed values 10% above actual
- **THD Voltage**: May show "Acceptable" changing to "Warning" if threshold crossed
- **Alarms Panel**: "Sensor Calibration Warning" alert appears
- **Analytics Charts**: All curves shifted upward by bias percentage
- **Energy Calculations**: Cumulative values accumulate faster than actual
- **Token Earnings**: Slightly inflated due to biased export readings
- **CO₂ Savings**: Also inflated proportionally
- **Diagnostics Widget** (if implemented): Shows "Bias detected in measurements"
- **Status Badge**: May change to "Diagnostics Required" (amber)
- **Validation Indicators**: Cross-checks between power/voltage/current may flag inconsistencies

---

## 13. Cloud Cover Simulation

Simulate partial cloud cover reducing PV output.

```bash
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=daytime&value=true" && \
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=sun_cloud_factor&value=0.5"
```

**Expected Frontend Behavior:**
- **Dashboard Metrics**: Active Power shows reduced PV generation (~50% of normal)
- **PV Widget** (if present): Irradiance drops to ~500 W/m² (from ~1000)
- **Export Energy**: Slows or stops, may switch to import
- **Status Badge**: "Reduced Solar" or "Clouds Detected"
- **Real-time Chart**: Shows gradual or sudden drop in PV power curve
- **Battery**: May start discharging to compensate for reduced PV
- **Import Energy**: Increases to cover shortfall
- **Analytics**:
  - Active Power chart shows dip in generation
  - Self-consumption percentage drops
  - Token earnings rate slows
- **Weather Indicator** (if implemented): Cloud icon displayed

---

## 14. Limit Order Selling

Place a limit sell order at specific price (only executes if market price favorable).

### Step 1: Setup switches
```bash
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=daytime&value=true" && \
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=market_enabled&value=true"
```

### Step 2: Place limit sell order
```bash
curl -X POST "http://46.62.231.61:8000/api/v1/market/order" \
  -H "Content-Type: application/json" \
  -d '{
    "meter_id": "demo_meter",
    "side": "sell",
    "type": "sell_limit",
    "quantity_kwh": 2.0,
    "duration_sec": 1200,
    "price": 0.25,
    "min_fill_kwh": 0.1,
    "ttl_sec": 3600
  }'
```

**Expected Frontend Behavior:**
- **Market Widget**: Shows "Limit Sell Order Pending @ $0.25/kWh"
- **Order Book** (if present): Displays limit order in queue
- **Order Status**: Shows "accepted" status, waiting for price match
- **Market Price Display**: Shows current price vs. limit price comparison
- **Export Energy**: Only increases if market price >= $0.25/kWh
- **Battery**: May store energy while waiting for favorable price
- **Notifications**: Alert when order starts executing (price matched)
- **Order Progress**: Shows partial fills as market price fluctuates
- **Token Earnings**: Only increases when order executes
- **Status Badge**: "Limit Order Active" or "Waiting for Price"

---

## 15. Scheduled EV Charging

Set EV to scheduled mode (charges during off-peak/low-price hours).

```bash
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=ev_plug&value=true" && \
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=ev_mode&value=scheduled" && \
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=daytime&value=false"
```

**Expected Frontend Behavior:**
- **EV Widget**: Shows "EV Connected - Scheduled Charging"
- **Schedule Indicator**: Displays charging window (if implemented)
- **Load Power**: EV charging only activates during scheduled time/price window
- **Status Badge**: "EV Scheduled Mode"
- **Grid Price Tracking**: Shows waiting for off-peak pricing
- **Battery**: May supplement EV charging during scheduled window
- **Notifications**: Alert when scheduled charging begins/ends
- **Cost Optimization**: Dashboard shows savings from scheduled vs. immediate charging
- **Load Breakdown**: EV charger appears in appliance list only during active charging

---

## 16. Combined Stress Test

Multiple simultaneous activities: PV generation, EV charging, marketplace selling, load spike.

### Step 1: Setup all switches
```bash
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=daytime&value=true" && \
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=market_enabled&value=true" && \
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=ev_plug&value=true" && \
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=ev_mode&value=fast" && \
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=manual_load_delta_kw&value=1.5"
```

### Step 2: Place sell order
```bash
curl -X POST "http://46.62.231.61:8000/api/v1/market/order" \
  -H "Content-Type: application/json" \
  -d '{
    "meter_id": "demo_meter",
    "side": "sell",
    "type": "sell_market",
    "quantity_kwh": 1.0,
    "duration_sec": 600,
    "min_fill_kwh": 0.1,
    "ttl_sec": 900
  }'
```

**Expected Frontend Behavior:**
- **Dashboard Metrics**: Complex power flows visible
  - Active Power fluctuating between import/export
  - High current (~20A) due to multiple loads
  - Voltage stable despite high load
- **All Widgets Simultaneously Active**:
  - PV generating ~4kW
  - Battery cycling charge/discharge
  - EV charging 3kW
  - Manual load +1.5kW
  - Selling 1kW to market
- **Status Badge**: "High Activity" or "Complex Operation"
- **Analytics Charts**: Multiple overlapping trends
  - Power chart shows complex waveform
  - Import/Export both active
  - Token earnings and CO₂ savings rising
- **System Load Indicator**: Shows high utilization percentage
- **Performance Metrics**: Response time, queue depth displayed
- **Alarms**: May show info alerts for high system activity
- **Real-time Updates**: Frontend refresh rate may increase (if implemented)

---

## 17. Time Acceleration

Speed up simulation for faster testing (10x real-time).

```bash
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=time_acceleration&value=10.0" && \
curl -X POST "http://46.62.231.61:8000/api/v1/control/switch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "meter_id=demo_meter&switch=daytime&value=true"
```

**Expected Frontend Behavior:**
- **Time Display**: Shows accelerated timestamp progression (10 seconds per real second)
- **All Metrics**: Update 10x faster than real-time
- **Energy Accumulation**: Import/Export values increase rapidly
- **Token Earnings/CO₂ Savings**: Steep curves in analytics charts
- **Battery SoC**: Changes visibly faster
- **Status Badge**: "Accelerated Mode 10x" indicator
- **Animations**: Refresh/polling visual indicators faster
- **Order Execution**: Market orders complete in 1/10th the normal time
- **Chart Compression**: Time-series charts may auto-adjust axis range
- **Warning** (if implemented): "Simulation running faster than real-time" notice

---

## Utility Endpoints

### Get Current Switch States
```bash
curl -X GET "http://46.62.231.61:8000/api/v1/control/switches"
```

### Get Current Snapshot
```bash
curl -X GET "http://46.62.231.61:8000/api/v1/meter/demo_meter/snapshot"
```

### Get Recent Events
```bash
curl -X GET "http://46.62.231.61:8000/api/v1/events?limit=10"
```

### Get Order Status
```bash
curl -X GET "http://46.62.231.61:8000/api/v1/market/order/{order_id}"
```
*(Replace `{order_id}` with actual order ID from create order response)*

### Cancel Order
```bash
curl -X POST "http://46.62.231.61:8000/api/v1/market/cancel?order_id={order_id}"
```

### Get System Health
```bash
curl -X GET "http://46.62.231.61:8000/api/v1/health"
```

### Get Frontend Constants
```bash
curl -X GET "http://46.62.231.61:8000/api/v1/constants"
```

---

## Frontend Implementation Notes

Based on the provided frontend schema, the following components should respond to these demos:

### Dashboard Page
- **Metrics Grid**: 8 metric cards (voltage, current, active power, power factor, frequency, import energy, export energy, THD voltage)
- **Status Badge**: Online/Offline indicator with system status text
- **Real-time Updates**: Poll `/snapshot` endpoint every 5 seconds (refreshIntervalMs: 5000)

### Analytics Page
- **Time Filter Selector**: 1h, 24h, 7d, 30d options
- **Five Charts**:
  1. Active Power vs Time (scaled to kW with 0.001 multiplier)
  2. Import vs Export Energy (dual-line chart)
  3. Power Factor Trend
  4. Cumulative CO₂ Savings (calculated: exportEnergy × 0.45 kg/kWh)
  5. Token Earnings (calculated: exportEnergy × 0.08 APT/kWh)
- **CSV Export**: Download analytics data with "wattswap-analytics" prefix

### Derived Calculations
- **CO₂ Savings**: Multiply exportEnergy by co2Factor (0.45)
- **Token Earnings**: Multiply exportEnergy by tokenRate (0.08)
- **Scale Active Power**: Divide activePower by 1000 to convert W to kW

### Market Widget (if implemented)
- Display pending orders count
- Show current market price
- Order status with progress indicators
- Transaction history/recent trades

### Real-time Data Flow
1. Frontend polls `/api/v1/meter/demo_meter/snapshot` every 5 seconds
2. Parse snapshot response to extract metrics by key
3. Apply scale factors and precision formatting per schema
4. Update dashboard cards with trend indicators
5. Append data points to analytics charts
6. Calculate cumulative values for CO₂ and tokens
7. Display system status and alarms

---

## Testing Checklist

- [ ] Verify all 17 demo scenarios execute successfully
- [ ] Confirm dashboard widgets update in real-time (5s refresh)
- [ ] Validate metric precision and units match schema
- [ ] Test buy/sell order flow from placement to execution
- [ ] Verify alarm indicators appear for fault scenarios
- [ ] Check analytics charts render correctly for all time filters
- [ ] Confirm CO₂ and token calculations match constants (0.45, 0.08)
- [ ] Test responsive behavior during time acceleration
- [ ] Validate error handling for failed orders (grid disconnect)
- [ ] Verify status badge changes reflect system state accurately
