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
- GET /api/v1/control/switches - Get all switch statuses
- GET /api/v1/control/time_acceleration - Get time acceleration
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

## Demo Scenarios

The following demo scenarios showcase various switch combinations and their effects on the dashboard metrics. Each scenario includes the switch states and expected dashboard reactions, including power flows, energy accumulations, CO2 savings, and token earnings.

### 1. Nighttime Baseline (Default Settings)
- **Switches**: daytime=false, grid_connected=true, market_enabled=false, battery_reserve_pct=10, manual_load_delta_kw=0, sun_cloud_factor=1.0, ev_plug=false, ev_mode="off", fault_inject={}, time_acceleration=1.0
- **Dashboard Reaction**: 
  - Power flows: Grid import ~2kW (household load), PV=0, Battery=0, Net= -2kW
  - Energies: Cumulative import increases steadily, export remains 0
  - CO2: Moderate emissions from grid import
  - Tokens: No earnings or spending
  - Status: Grid-dependent consumption

### 2. Daytime PV Generation
- **Switches**: daytime=true, grid_connected=true, market_enabled=false, battery_reserve_pct=10, manual_load_delta_kw=0, sun_cloud_factor=1.0, ev_plug=false, ev_mode="off", fault_inject={}, time_acceleration=1.0
- **Dashboard Reaction**: 
  - Power flows: PV ~4kW generation, Grid import reduced to ~0.5kW, Battery=0, Net= -0.5kW
  - Energies: Export starts accumulating, import slows
  - CO2: Significant reduction due to solar generation
  - Tokens: Potential earnings if market enabled, but here none
  - Status: Self-generation covering most load

### 3. Battery Management (Daytime Charging)
- **Switches**: daytime=true, grid_connected=true, market_enabled=false, battery_reserve_pct=50, manual_load_delta_kw=0, sun_cloud_factor=1.0, ev_plug=false, ev_mode="off", fault_inject={}, time_acceleration=1.0
- **Dashboard Reaction**: 
  - Power flows: PV ~4kW, Battery charging ~1kW, Grid import ~0.5kW, Net= -0.5kW
  - Energies: Battery SOC increases, export minimal
  - CO2: Reduced compared to grid-only, battery stores clean energy
  - Tokens: No marketplace activity
  - Status: Energy storage building reserves

### 4. Battery Backup (Nighttime Discharging)
- **Switches**: daytime=false, grid_connected=true, market_enabled=false, battery_reserve_pct=10, manual_load_delta_kw=0, sun_cloud_factor=1.0, ev_plug=false, ev_mode="off", fault_inject={}, time_acceleration=1.0
- **Dashboard Reaction**: 
  - Power flows: Battery discharging ~2kW, Grid import ~0kW, PV=0, Net=0kW
  - Energies: Battery SOC decreases, import remains stable
  - CO2: Zero if battery fully charged from solar, otherwise mixed
  - Tokens: No activity
  - Status: Battery providing backup power

### 5. Marketplace Selling (Excess PV Export)
- **Switches**: daytime=true, grid_connected=true, market_enabled=true, battery_reserve_pct=10, manual_load_delta_kw=0, sun_cloud_factor=1.0, ev_plug=false, ev_mode="off", fault_inject={}, time_acceleration=1.0
- **Dashboard Reaction**: 
  - Power flows: PV ~4kW, Grid export ~1.5kW (selling excess), Net= +1.5kW
  - Energies: Export increases rapidly, token earnings accumulate
  - CO2: Negative emissions (net export of clean energy)
  - Tokens: Earnings from selling excess PV to grid/market
  - Status: Prosumer actively selling surplus

### 6. Marketplace Buying (Battery Recharging)
- **Switches**: daytime=false, grid_connected=true, market_enabled=true, battery_reserve_pct=10, manual_load_delta_kw=0, sun_cloud_factor=1.0, ev_plug=false, ev_mode="off", fault_inject={}, time_acceleration=1.0
- **Dashboard Reaction**: 
  - Power flows: Battery discharging ~2kW, Grid import ~0kW, but marketplace buy order fills battery
  - Energies: Battery SOC maintained or increased via purchases
  - CO2: Depends on market energy source, potentially higher if fossil-based
  - Tokens: Spending on energy purchases
  - Status: Smart purchasing to maintain reserves

### 7. Island Mode (Off-Grid Operation)
- **Switches**: daytime=false, grid_connected=false, market_enabled=false, battery_reserve_pct=10, manual_load_delta_kw=0, sun_cloud_factor=1.0, ev_plug=false, ev_mode="off", fault_inject={}, time_acceleration=1.0
- **Dashboard Reaction**: 
  - Power flows: Battery discharging ~2kW, Grid=0, PV=0, Net=0kW
  - Energies: Battery depletes, no grid interaction
  - CO2: Zero grid emissions, but limited by battery capacity
  - Tokens: No activity
  - Status: Off-grid operation, vulnerable to battery depletion

### 8. Full System Optimization
- **Switches**: daytime=true, grid_connected=true, market_enabled=true, battery_reserve_pct=50, manual_load_delta_kw=0, sun_cloud_factor=1.0, ev_plug=false, ev_mode="off", fault_inject={}, time_acceleration=1.0
- **Dashboard Reaction**: 
  - Power flows: PV ~4kW, Battery charging ~1kW, Grid minimal, Net ~0kW
  - Energies: Balanced import/export, battery charging, potential selling
  - CO2: Maximally reduced, net-zero or negative
  - Tokens: Earnings from excess sales
  - Status: Optimal prosumer operation

### 9. Grid Failure Simulation
- **Switches**: daytime=false, grid_connected=false, market_enabled=true, battery_reserve_pct=10, manual_load_delta_kw=0, sun_cloud_factor=1.0, ev_plug=false, ev_mode="off", fault_inject={}, time_acceleration=1.0
- **Dashboard Reaction**: 
  - Power flows: Battery discharging ~2kW, Grid=0, PV=0, Net=0kW
  - Energies: Battery SOC drops, marketplace attempts to buy but fails (no grid)
  - CO2: Zero grid emissions
  - Tokens: Failed transactions, no spending
  - Status: Emergency backup mode

### 10. Load Spike Testing
- **Switches**: daytime=true, grid_connected=true, market_enabled=false, battery_reserve_pct=10, manual_load_delta_kw=2.0, sun_cloud_factor=1.0, ev_plug=false, ev_mode="off", fault_inject={}, time_acceleration=1.0
- **Dashboard Reaction**: 
  - Power flows: PV ~4kW, Battery discharging ~2kW, Grid import increased, Net= -2kW
  - Energies: Import spikes, battery used to buffer
  - CO2: Increased due to higher grid usage
  - Tokens: No activity
  - Status: Testing load response and battery buffering

### 11. EV Charging (Fast Mode)
- **Switches**: daytime=true, grid_connected=true, market_enabled=false, battery_reserve_pct=10, manual_load_delta_kw=0, sun_cloud_factor=1.0, ev_plug=true, ev_mode="fast", fault_inject={}, time_acceleration=1.0
- **Dashboard Reaction**: 
  - Power flows: PV ~4kW, EV charging ~3kW, Grid import ~1kW, Net= -1kW
  - Energies: Higher consumption, potential export reduced
  - CO2: Moderate, EV using solar power
  - Tokens: No activity
  - Status: EV fast charging from solar

### 12. Fault Injection (Sensor Bias)
- **Switches**: daytime=true, grid_connected=true, market_enabled=false, battery_reserve_pct=10, manual_load_delta_kw=0, sun_cloud_factor=1.0, ev_plug=false, ev_mode="off", fault_inject={"bias_pct": 10}, time_acceleration=1.0
- **Dashboard Reaction**: 
  - Power flows: Measurements biased, apparent higher/lower flows
  - Energies: Inaccurate accumulations
  - CO2: Miscalculated savings
  - Tokens: Potential incorrect earnings
  - Status: Fault simulation for testing diagnostics