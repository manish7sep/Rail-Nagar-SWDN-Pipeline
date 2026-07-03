"""
02_extended_period_simulation.py
================================
24-h extended-period simulation with CPHEEO 1999 diurnal demand pattern
(peak x2.0 at 07:00 and 19:00). Produces the tank cycling, pressure
envelope, and inflow curves used for Figure 8 and Table 4.
"""
import wntr
import pandas as pd
import numpy as np
import json
from pathlib import Path

# CPHEEO 1999 diurnal multipliers (24 hourly values, mean = 1.0)
DIURNAL = [
    0.60, 0.55, 0.50, 0.55, 0.75, 1.20,      # 00–05
    1.80, 2.00, 1.80, 1.30, 1.00, 0.90,      # 06–11
    0.85, 0.85, 0.90, 1.10, 1.40, 1.75,      # 12–17
    1.95, 2.00, 1.75, 1.30, 0.95, 0.75,      # 18–23
]
_mean = sum(DIURNAL) / 24
DIURNAL_NORM = [m / _mean for m in DIURNAL]


def run(inp_path, out_dir, seed=42):
    wn = wntr.network.WaterNetworkModel(inp_path)

    # Set the diurnal pattern
    wn.get_pattern('demand').multipliers = DIURNAL_NORM
    wn.options.hydraulic.demand_multiplier = 1.0     # pattern carries the variation
    wn.options.time.duration = 24 * 3600
    wn.options.time.hydraulic_timestep = 3600
    wn.options.time.pattern_timestep = 3600
    wn.options.time.report_timestep = 3600

    sim = wntr.sim.EpanetSimulator(wn)
    res = sim.run_sim()

    # Tank level trajectory
    tank_head = res.node['head']['TA1']         # HGL at tank
    tank_elev = wn.get_node('TA1').elevation
    tank_level = tank_head - tank_elev          # water depth

    # Pressure envelope across all junctions per timestep
    junc_p = res.node['pressure'].drop(columns=['TA1'])
    pressure_min = junc_p.min(axis=1)
    pressure_mean = junc_p.mean(axis=1)
    pressure_max = junc_p.max(axis=1)

    # System inflow (tank outflow, positive when tank discharges)
    tank_demand = res.node['demand']['TA1']     # -ve for source outflow
    system_inflow = -tank_demand * 1000         # L/s (positive)

    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)

    eps_df = pd.DataFrame({
        'time_h':         np.arange(len(tank_level)),
        'tank_level_m':   tank_level.values,
        'pressure_min_m': pressure_min.values,
        'pressure_mean_m':pressure_mean.values,
        'pressure_max_m': pressure_max.values,
        'system_inflow_LPS': system_inflow.values,
        'pattern_multiplier': [DIURNAL_NORM[i % 24] for i in range(len(tank_level))],
    })
    eps_df.to_csv(out / "02_eps_timeseries.csv", index=False)

    summary = {
        "duration_h":            24,
        "tank_level_min_m":      float(tank_level.min()),
        "tank_level_max_m":      float(tank_level.max()),
        "tank_level_range_m":    float(tank_level.max() - tank_level.min()),
        "system_inflow_min_LPS": float(system_inflow.min()),
        "system_inflow_max_LPS": float(system_inflow.max()),
        "network_pressure_min_m":float(pressure_min.min()),
        "pressure_min_ge_15m":   bool(pressure_min.min() >= 15),
        "peak_hours":            [
            int(system_inflow.idxmax()),
            int(system_inflow.sort_values().index[-2]) if len(system_inflow) > 1 else None
        ],
    }
    (out / "02_eps_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"    Tank cycle       : {summary['tank_level_min_m']:.2f} — "
          f"{summary['tank_level_max_m']:.2f} m "
          f"(δ = {summary['tank_level_range_m']:.2f} m)")
    print(f"    System inflow    : {summary['system_inflow_min_LPS']:.2f} — "
          f"{summary['system_inflow_max_LPS']:.2f} L/s")
    print(f"    Global min P     : {summary['network_pressure_min_m']:.2f} m "
          f"({'≥ 15m ✓' if summary['pressure_min_ge_15m'] else '< 15m ✗'})")
    print(f"    Wrote 02_eps_*.csv/json in {out}")


if __name__ == "__main__":
    import sys
    run(inp_path=sys.argv[1] if len(sys.argv) > 1
        else "../S4_network_topology/rail_nagar.inp",
        out_dir="results", seed=42)
