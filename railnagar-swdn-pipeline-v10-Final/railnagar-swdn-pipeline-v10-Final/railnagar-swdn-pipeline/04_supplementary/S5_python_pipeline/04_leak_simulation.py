"""
04_leak_simulation.py
=====================
Pressure-dependent leak simulation using the WNTR emitter model.
Four simulated leaks are placed at representative junctions with:
    orifice area A     = 5 × 10⁻⁵ m² (≈ 8 mm hole)
    discharge coeff C_d = 0.75
    emitter exponent    = 0.5
Records the leak flow per node, resulting pressure at the leak node,
and total system inflow increase due to leaks.

Referenced in Table 6 and Figures 10a–d of the manuscript.
"""
import wntr
import pandas as pd
import numpy as np
import json
from pathlib import Path
from importlib import import_module

_eps = import_module("02_extended_period_simulation")

LEAK_NODES = ['JU8', 'JU22', 'JU45', 'JU59']    # dispersed across the network
LEAK_AREA_M2 = 5e-5
CD = 0.75


def run(inp_path, out_dir, seed=42):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)

    # --- Baseline (no leaks) EPS to get baseline pressures ---
    wn_base = wntr.network.WaterNetworkModel(inp_path)
    wn_base.get_pattern('demand').multipliers = _eps.DIURNAL_NORM
    wn_base.options.time.duration = 24 * 3600
    res_base = wntr.sim.EpanetSimulator(wn_base).run_sim()

    # --- With leaks: add emitters at LEAK_NODES ---
    wn_leak = wntr.network.WaterNetworkModel(inp_path)
    wn_leak.get_pattern('demand').multipliers = _eps.DIURNAL_NORM
    wn_leak.options.time.duration = 24 * 3600

    for nid in LEAK_NODES:
        j = wn_leak.get_node(nid)
        # Emitter coefficient K such that q = K * P^0.5 (WNTR convention: L/s)
        # For a physical orifice: q = C_d × A × sqrt(2 g P)
        # In WNTR SI: q (m³/s) = K × P^0.5 → K = C_d × A × sqrt(2g)
        K = CD * LEAK_AREA_M2 * np.sqrt(2 * 9.81)
        j.add_leak(wn_leak, area=LEAK_AREA_M2, discharge_coeff=CD, start_time=0)

    # Use WNTRSimulator for leak model (EpanetSimulator can't do leaks natively)
    sim = wntr.sim.WNTRSimulator(wn_leak)
    res_leak = sim.run_sim()

    # Aggregate leak flows
    leak_records = []
    for nid in LEAK_NODES:
        # WNTR stores leak demand as part of node demand; use 'leak_demand' if
        # accessible; otherwise back-derive as (leak−baseline)
        try:
            leak_ts = res_leak.node['leak_demand'][nid]     # m³/s
        except KeyError:
            base = res_base.node['demand'][nid]
            with_leak = res_leak.node['demand'][nid]
            leak_ts = with_leak - base

        base_p_ts = res_base.node['pressure'][nid]
        leak_p_ts = res_leak.node['pressure'][nid]
        leak_records.append({
            'node_id':               nid,
            'mean_leak_flow_LPS':    float(leak_ts.mean() * 1000),
            'mean_pressure_baseline_m': float(base_p_ts.mean()),
            'mean_pressure_with_leak_m': float(leak_p_ts.mean()),
            'pressure_drop_m':       float(base_p_ts.mean() - leak_p_ts.mean()),
        })

    df = pd.DataFrame(leak_records)
    df.to_csv(out / "04_leak_simulation.csv", index=False)

    # System-level totals
    total_leak_LPS = float(df.mean_leak_flow_LPS.sum())
    baseline_inflow_LPS = -float(res_base.node['demand']['TA1'].mean() * 1000)
    leaky_inflow_LPS    = -float(res_leak.node['demand']['TA1'].mean() * 1000)
    nrw_pct = total_leak_LPS / leaky_inflow_LPS * 100

    summary = {
        "num_leaks":              len(LEAK_NODES),
        "leak_nodes":             LEAK_NODES,
        "orifice_area_m2":        LEAK_AREA_M2,
        "discharge_coefficient":  CD,
        "total_leak_flow_LPS":    total_leak_LPS,
        "total_leak_flow_m3_day": total_leak_LPS * 86.4,
        "baseline_inflow_LPS":    baseline_inflow_LPS,
        "leaky_inflow_LPS":       leaky_inflow_LPS,
        "non_revenue_water_pct":  nrw_pct,
        "pressure_drop_range_m":  [float(df.pressure_drop_m.min()),
                                    float(df.pressure_drop_m.max())],
    }
    (out / "04_leak_simulation_summary.json").write_text(json.dumps(summary, indent=2))

    print(f"    Total leak flow      : {total_leak_LPS:.2f} L/s "
          f"({total_leak_LPS*86.4:.1f} m³/day)")
    print(f"    Non-revenue-water    : {nrw_pct:.1f} % of system inflow")
    print(f"    Pressure drop range  : {summary['pressure_drop_range_m'][0]:.2f} — "
          f"{summary['pressure_drop_range_m'][1]:.2f} m")
    print(f"    Wrote 04_leak_simulation*.csv/json in {out}")


if __name__ == "__main__":
    import sys
    run(inp_path=sys.argv[1] if len(sys.argv) > 1
        else "../S4_network_topology/rail_nagar.inp",
        out_dir="results", seed=42)
