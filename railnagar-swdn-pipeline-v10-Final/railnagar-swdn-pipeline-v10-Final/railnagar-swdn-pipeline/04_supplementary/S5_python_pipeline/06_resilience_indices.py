"""
06_resilience_indices.py
========================
Computes three published resilience indices at the design peak-hour demand:

  - Todini's Resilience Index (I_r) — Todini (2000).
        I_r = (Σ q_i (H_i − H_i*)) / (Σ q_i H_i* + Σ Q_r H_r − Σ q_i H_i*)
    where q_i is design demand, H_i actual head, H_i* required head
    (elevation + 15 m minimum pressure), Q_r reservoir/tank supply, H_r
    reservoir head.

  - Modified Resilience Index (MRI) — Jayaram & Srinivasan (2008).
        MRI = Σ q_i (H_i − H_i*) / Σ q_i H_i*

  - Network Resilience Index (NRI) — Prasad & Park (2004), simplified form.
        NRI = I_r × C
    with C = 1 uniform connectivity term (this dendritic network has no loops).

Referenced in Table 7 of the manuscript.
"""
import wntr
import json
import numpy as np
from pathlib import Path
from importlib import import_module

_ss = import_module("01_steady_state")

MIN_REQUIRED_PRESSURE_M = 15.0


def run(inp_path, out_dir, seed=42):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)

    wn = wntr.network.WaterNetworkModel(inp_path)
    wn = _ss._peak_hour_setup(wn)
    res = wntr.sim.EpanetSimulator(wn).run_sim()

    p = res.node['pressure'].iloc[0]
    h = res.node['head'].iloc[0]
    d = res.node['demand'].iloc[0]

    # Junction values only
    j_ids = [n for n in wn.junction_name_list]
    q  = np.array([d[n]   for n in j_ids])               # m³/s (positive = demand)
    H  = np.array([h[n]   for n in j_ids])               # m
    z  = np.array([wn.get_node(n).elevation for n in j_ids])
    H_req = z + MIN_REQUIRED_PRESSURE_M                   # required head

    # Tank / reservoir supply
    tank_id  = 'TA1'
    Q_r = -d[tank_id]                                     # m³/s (positive out of tank)
    H_r =  h[tank_id]

    # Delivered head-power surplus
    numerator   = np.sum(q * (H - H_req))
    denom_total = q @ H_req + Q_r * H_r
    denom_req   = np.sum(q * H_req)

    I_r = numerator / (denom_total - denom_req) if (denom_total - denom_req) != 0 else np.nan
    MRI = numerator / denom_req if denom_req != 0 else np.nan
    NRI = I_r                    # C = 1 for dendritic network

    summary = {
        "todini_resilience_index":     float(I_r),
        "modified_resilience_index":   float(MRI),
        "network_resilience_index":    float(NRI),
        "min_required_pressure_m":     MIN_REQUIRED_PRESSURE_M,
        "num_junctions":               len(j_ids),
        "tank_head_m":                 float(H_r),
        "tank_outflow_LPS":            float(Q_r * 1000),
        "junctions_deficient_lt_15m":  int(np.sum(p.drop(tank_id).values < 15)),
        "interpretation": (
            "Negative I_r indicates design-stress: available head-power at "
            "junctions is less than the minimum required. Literature typical "
            "range for well-designed networks: 0.3–0.6. See Todini (2000)."
        ),
    }
    (out / "06_resilience_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"    Todini I_r      : {I_r:.4f}")
    print(f"    Modified RI     : {MRI:.4f}")
    print(f"    Network RI      : {NRI:.4f}")
    print(f"    Wrote 06_resilience_summary.json in {out}")


if __name__ == "__main__":
    import sys
    run(inp_path=sys.argv[1] if len(sys.argv) > 1
        else "../S4_network_topology/rail_nagar.inp",
        out_dir="results", seed=42)
