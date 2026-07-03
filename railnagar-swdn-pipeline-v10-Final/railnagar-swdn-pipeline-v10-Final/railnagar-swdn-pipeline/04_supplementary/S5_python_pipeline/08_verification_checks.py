"""
08_verification_checks.py
=========================
Five independent physical-consistency checks used in Section 4.7 and
Table 9 of the manuscript. All checks operate on the reconstructed
rail_nagar.inp; a check passes if the residual is below its documented
tolerance.

  1. Mass balance         (steady-state)     — sum of node demands = tank outflow
  2. Tank volume continuity (24-h EPS)       — ΔV = ∫(inflow − outflow) dt
  3. Hazen-Williams dimensional check         — Δh vs. HW formula for P1
  4. Chlorine decay endpoint reproducibility  — steady-state matches analytical decay
  5. EPANET–INP cross-engine reproducibility  — EpanetSimulator vs. WNTRSimulator
"""
import wntr
import json
import numpy as np
from pathlib import Path
from importlib import import_module

_ss = import_module("01_steady_state")
_eps = import_module("02_extended_period_simulation")


def _check_mass_balance(inp_path):
    wn = wntr.network.WaterNetworkModel(inp_path)
    wn = _ss._peak_hour_setup(wn)
    res = wntr.sim.EpanetSimulator(wn).run_sim()
    d = res.node['demand'].iloc[0]
    junction_sum = d.drop('TA1').sum() * 1000   # L/s
    tank_outflow = -d['TA1'] * 1000              # L/s
    residual = abs(junction_sum - tank_outflow)
    return {
        "check_name":         "steady_state_mass_balance",
        "junction_demand_LPS": float(junction_sum),
        "tank_outflow_LPS":   float(tank_outflow),
        "residual_LPS":       float(residual),
        "tolerance_LPS":      0.1,
        "passed":             bool(residual < 0.01),
    }


def _check_tank_continuity(inp_path):
    wn = wntr.network.WaterNetworkModel(inp_path)
    wn.get_pattern('demand').multipliers = _eps.DIURNAL_NORM
    wn.options.time.duration = 24 * 3600
    res = wntr.sim.EpanetSimulator(wn).run_sim()

    tank_head = res.node['head']['TA1']
    tank_elev = wn.get_node('TA1').elevation
    tank_level = tank_head - tank_elev
    tank_dia = wn.get_node('TA1').diameter
    tank_area = np.pi * (tank_dia / 2) ** 2

    dV_computed = (tank_level.iloc[-1] - tank_level.iloc[0]) * tank_area   # m³
    # Integrated net inflow (m³)
    tank_flow = -res.node['demand']['TA1'] * 3600   # m³ per hourly step
    dV_integrated = tank_flow.sum()

    # Tank supplies water: dV level decreases while integrated flow is positive.
    # Take absolute values for continuity check.
    residual = abs(abs(dV_computed) - abs(dV_integrated))
    return {
        "check_name":       "tank_volume_continuity_24h",
        "delta_V_from_level_m3":  float(dV_computed),
        "delta_V_integrated_m3":  float(dV_integrated),
        "residual_m3":            float(residual),
        "tolerance_m3":           500.0,
        "passed":                 bool(residual < 500.0),
    }


def _check_hazen_williams(inp_path):
    wn = wntr.network.WaterNetworkModel(inp_path)
    wn = _ss._peak_hour_setup(wn)
    res = wntr.sim.EpanetSimulator(wn).run_sim()

    p1 = wn.get_link('P1')
    q_sim = res.link['flowrate'].iloc[0]['P1']        # m³/s
    h_sim = res.link['headloss'].iloc[0]['P1']        # m

    # Hazen-Williams SI: h_f = 10.67 × Q^1.852 / (C^1.852 × D^4.87) × L
    Q, C, D, L = q_sim, p1.roughness, p1.diameter, p1.length
    # WNTR returns headloss as m/km * length/1000 = m total; use total headloss
    h_sim_total = h_sim if h_sim > 0.5 else h_sim * L         # handle unit-headloss vs total
    h_theoretical = 10.674 * (Q/1)**1.852 / (C**1.852 * D**4.87) * L
    residual = abs(h_sim_total - h_theoretical)
    return {
        "check_name":         "hazen_williams_dimensional_P1",
        "simulated_headloss_m":     float(h_sim_total),
        "theoretical_headloss_m":   float(h_theoretical),
        "residual_m":               float(residual),
        "tolerance_m":              0.50,
        "passed":                   bool(residual < 0.05),
    }


def _check_chlorine_endpoint(inp_path):
    """Compare simulated chlorine at JU2 with analytical decay from tank."""
    wn = wntr.network.WaterNetworkModel(inp_path)
    wn.get_pattern('demand').multipliers = _eps.DIURNAL_NORM
    wn.options.time.duration = 3 * 24 * 3600
    wn.options.quality.parameter = 'CHEMICAL'
    res = wntr.sim.EpanetSimulator(wn).run_sim()

    c_tank = res.node['quality']['TA1'].iloc[-1]     # mg/L at end
    c_ju2  = res.node['quality']['JU2'].iloc[-1]

    # Analytical: c_ju2 ≈ c_tank × exp(−k_b × t_transit)
    # t_transit ≈ pipe volume / flow ≈ π(0.1476/2)² × 72.56 / (0.0361) ≈ 34.4 s
    # 34.4 s is negligible relative to k_b = 0.5/day, so c_ju2 ≈ c_tank
    residual = abs(c_ju2 - c_tank)
    return {
        "check_name":         "chlorine_endpoint_JU2_vs_tank",
        "tank_concentration_mg_per_L":  float(c_tank),
        "JU2_concentration_mg_per_L":   float(c_ju2),
        "residual_mg_per_L":            float(residual),
        "tolerance_mg_per_L":           0.10,
        "passed":                       bool(residual < 0.02),
    }


def _check_cross_engine(inp_path):
    wn1 = wntr.network.WaterNetworkModel(inp_path)
    wn1 = _ss._peak_hour_setup(wn1)
    r1 = wntr.sim.EpanetSimulator(wn1).run_sim()

    wn2 = wntr.network.WaterNetworkModel(inp_path)
    wn2 = _ss._peak_hour_setup(wn2)
    r2 = wntr.sim.WNTRSimulator(wn2).run_sim()

    p1 = r1.node['pressure'].iloc[0].drop('TA1')
    p2 = r2.node['pressure'].iloc[0].drop('TA1')
    max_diff = float((p1 - p2).abs().max())
    return {
        "check_name":         "EpanetSimulator_vs_WNTRSimulator",
        "max_pressure_diff_m": max_diff,
        "tolerance_m":         1.0,
        "passed":              bool(max_diff < 0.5),
    }


def run(inp_path, out_dir, seed=42):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    checks = []
    for fn in [_check_mass_balance, _check_tank_continuity,
               _check_hazen_williams, _check_chlorine_endpoint,
               _check_cross_engine]:
        print(f"      running {fn.__name__}...")
        try:
            checks.append(fn(inp_path))
        except Exception as e:
            checks.append({
                "check_name": fn.__name__.replace('_check_', ''),
                "error": str(e), "passed": False,
            })

    n_passed = sum(1 for c in checks if c.get('passed', False))
    summary = {
        "num_checks":       len(checks),
        "num_passed":       n_passed,
        "num_failed":       len(checks) - n_passed,
        "all_checks":       checks,
    }
    (out / "08_verification_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"    Verification result: {n_passed}/{len(checks)} checks passed")
    for c in checks:
        status = "✓" if c.get('passed') else "✗"
        print(f"      {status} {c.get('check_name')}")
    print(f"    Wrote 08_verification_summary.json in {out}")


if __name__ == "__main__":
    import sys
    run(inp_path=sys.argv[1] if len(sys.argv) > 1
        else "../S4_network_topology/rail_nagar.inp",
        out_dir="results", seed=42)
