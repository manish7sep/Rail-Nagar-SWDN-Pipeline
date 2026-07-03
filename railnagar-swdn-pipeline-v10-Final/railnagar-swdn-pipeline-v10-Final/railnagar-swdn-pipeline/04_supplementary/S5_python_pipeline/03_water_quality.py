"""
03_water_quality.py
===================
Water-quality simulation:
  (a) First-order chlorine decay (bulk k_b = 0.5 day⁻¹) with 1 mg/L source
      at the tank.
  (b) Water age analysis (7-day spin-up).
Both used for Figure 9 and Table 5.
"""
import wntr
import pandas as pd
import numpy as np
import json
from pathlib import Path
from importlib import import_module

_eps = import_module("02_extended_period_simulation")


def run(inp_path, out_dir, seed=42):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)

    # ------- (a) Chlorine decay (3-day steady state) -------
    wn = wntr.network.WaterNetworkModel(inp_path)
    wn.get_pattern('demand').multipliers = _eps.DIURNAL_NORM
    wn.options.time.duration = 3 * 24 * 3600
    wn.options.quality.parameter = 'CHEMICAL'
    wn.options.quality.chemical_name = 'chlorine'
    # Bulk decay is set inside the .inp via [REACTIONS]

    sim = wntr.sim.EpanetSimulator(wn)
    res_cl = sim.run_sim()

    # Take the last-day timestep values as "steady" 3-day residual
    cl = res_cl.node['quality'].iloc[-1]
    cl_junc = cl.drop('TA1')

    # ------- (b) Water age (7-day spin-up) -------
    wn2 = wntr.network.WaterNetworkModel(inp_path)
    wn2.get_pattern('demand').multipliers = _eps.DIURNAL_NORM
    wn2.options.time.duration = 7 * 24 * 3600
    wn2.options.quality.parameter = 'AGE'

    sim2 = wntr.sim.EpanetSimulator(wn2)
    res_age = sim2.run_sim()

    age_seconds = res_age.node['quality'].iloc[-1]
    age_hours = age_seconds / 3600.0
    age_junc = age_hours.drop('TA1')

    # ------- Save results -------
    df = pd.DataFrame({
        'junction_id':      cl_junc.index,
        'chlorine_mg_per_L':cl_junc.values,
        'water_age_h':      age_junc.reindex(cl_junc.index).values,
    })
    df.to_csv(out / "03_water_quality.csv", index=False)

    summary = {
        "chlorine_mean_mg_per_L":     float(cl_junc.mean()),
        "chlorine_min_mg_per_L":      float(cl_junc.min()),
        "chlorine_min_at":            str(cl_junc.idxmin()),
        "chlorine_max_mg_per_L":      float(cl_junc.max()),
        "junctions_below_0p2_mg_per_L": int((cl_junc < 0.2).sum()),
        "water_age_mean_h":           float(age_junc.mean()),
        "water_age_max_h":            float(age_junc.max()),
        "water_age_max_at":           str(age_junc.idxmax()),
        "junctions_above_72h_age":    int((age_junc > 72).sum()),
    }
    (out / "03_water_quality_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"    Chlorine mean/min : {summary['chlorine_mean_mg_per_L']:.3f} / "
          f"{summary['chlorine_min_mg_per_L']:.3f} mg/L (min at "
          f"{summary['chlorine_min_at']})")
    print(f"    Water age mean/max: {summary['water_age_mean_h']:.1f} / "
          f"{summary['water_age_max_h']:.1f} h (max at "
          f"{summary['water_age_max_at']})")
    print(f"    Junctions age > 72 h: {summary['junctions_above_72h_age']}")
    print(f"    Wrote 03_water_quality*.csv/json in {out}")


if __name__ == "__main__":
    import sys
    run(inp_path=sys.argv[1] if len(sys.argv) > 1
        else "../S4_network_topology/rail_nagar.inp",
        out_dir="results", seed=42)
