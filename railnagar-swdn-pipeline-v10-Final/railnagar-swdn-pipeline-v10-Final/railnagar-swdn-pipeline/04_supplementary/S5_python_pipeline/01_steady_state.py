"""
01_steady_state.py
==================
Peak-hour steady-state hydraulic analysis using the IS 1172:1993 peak
factor of 3.0. Produces the flow, pressure, velocity and head-loss table
used to generate Figure 7 and Table 3 of the manuscript.
"""
import wntr
import pandas as pd
import numpy as np
import json
from pathlib import Path

PEAK_FACTOR = 3.0
PVC_DIAMS_M = {147.6: 0.1476, 101.6: 0.1016, 81.4: 0.0814}


def _peak_hour_setup(wn):
    """Configure water-network model for peak-hour steady-state analysis."""
    # Overwrite demand pattern with a flat 1.0 pattern so demand = base × multiplier
    if 'demand' in wn.pattern_name_list:
        wn.get_pattern('demand').multipliers = [1.0] * 24
    wn.options.hydraulic.demand_multiplier = PEAK_FACTOR
    wn.options.time.duration = 0     # steady state
    return wn


def run(inp_path, out_dir, seed=42):
    wn = wntr.network.WaterNetworkModel(inp_path)
    wn = _peak_hour_setup(wn)

    sim = wntr.sim.EpanetSimulator(wn)
    res = sim.run_sim()

    # --- Node results ---
    p = res.node['pressure'].iloc[0]
    h = res.node['head'].iloc[0]
    d = res.node['demand'].iloc[0]

    nodes = pd.DataFrame({
        'node_id':       p.index,
        'elevation_m':   [wn.get_node(n).elevation if hasattr(wn.get_node(n), 'elevation') else np.nan for n in p.index],
        'head_m':        h.values,
        'pressure_m':    p.values,
        'demand_LPS':    d.values * 1000,
    })
    junctions = nodes[nodes.node_id != 'TA1'].copy()

    # --- Link results ---
    q = res.link['flowrate'].iloc[0]      # m³/s
    v = res.link['velocity'].iloc[0]      # m/s
    hl = res.link['headloss'].iloc[0]     # m

    links = pd.DataFrame({
        'link_id':       q.index,
        'flow_LPS':      q.values * 1000,
        'velocity_ms':   v.values,
        'headloss_m':    hl.values,
    })
    # Attach length + diameter
    lengths = {name: link.length for name, link in wn.pipes()}
    diameters = {name: link.diameter * 1000 for name, link in wn.pipes()}
    links['length_m']    = links.link_id.map(lengths)
    links['diameter_mm'] = links.link_id.map(diameters)
    links['unit_headloss_m_per_km'] = links.headloss_m / (links.length_m / 1000)

    # --- Save ---
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    junctions.to_csv(out / "01_steady_state_junctions.csv", index=False)
    links.to_csv(    out / "01_steady_state_links.csv",     index=False)

    # --- Summary ---
    summary = {
        "peak_factor":        PEAK_FACTOR,
        "total_demand_LPS":   float(junctions.demand_LPS.sum()),
        "P1_flow_LPS":        float(links[links.link_id == 'P1'].flow_LPS.iloc[0]),
        "P1_velocity_ms":     float(links[links.link_id == 'P1'].velocity_ms.iloc[0]),
        "pressure_min_m":     float(junctions.pressure_m.min()),
        "pressure_min_at":    str(junctions.loc[junctions.pressure_m.idxmin(), 'node_id']),
        "pressure_max_m":     float(junctions.pressure_m.max()),
        "pressure_max_at":    str(junctions.loc[junctions.pressure_m.idxmax(), 'node_id']),
        "junctions_ge_15m":   int((junctions.pressure_m >= 15).sum()),
        "total_junctions":    int(len(junctions)),
        "junctions_ge_15m_pct": float((junctions.pressure_m >= 15).sum() / len(junctions) * 100),
        "velocity_range_ms":  [float(links.velocity_ms.min()), float(links.velocity_ms.max())],
        "flow_range_LPS":     [float(links.flow_LPS.min()), float(links.flow_LPS.max())],
    }
    (out / "01_steady_state_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"    Total peak demand : {summary['total_demand_LPS']:.2f} L/s")
    print(f"    P1 flow / vel     : {summary['P1_flow_LPS']:.2f} L/s / "
          f"{summary['P1_velocity_ms']:.2f} m/s")
    print(f"    Pressure range    : {summary['pressure_min_m']:.2f} @ "
          f"{summary['pressure_min_at']} → {summary['pressure_max_m']:.2f} @ "
          f"{summary['pressure_max_at']}")
    print(f"    Junctions ≥ 15 m  : {summary['junctions_ge_15m']}/"
          f"{summary['total_junctions']} ({summary['junctions_ge_15m_pct']:.1f} %)")
    print(f"    Wrote 01_steady_state_*.csv/json in {out}")


if __name__ == "__main__":
    import sys
    run(inp_path=sys.argv[1] if len(sys.argv) > 1
        else "../S4_network_topology/rail_nagar.inp",
        out_dir="results", seed=42)
