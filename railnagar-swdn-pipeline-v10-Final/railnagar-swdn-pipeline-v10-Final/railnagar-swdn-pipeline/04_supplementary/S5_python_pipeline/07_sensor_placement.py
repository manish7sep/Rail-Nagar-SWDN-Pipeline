"""
07_sensor_placement.py
======================
Greedy max-coverage optimal sensor placement for leak-detection
localisation. Uses the sensitivity matrix S[i,j] = ∂p_i/∂leak_j:

At each iteration k, add the sensor location j* that maximises the
newly-covered leak-source area (in the ε-sensitivity sense), until the
budget N_sensors is exhausted.

Referenced in Section 4.5 and Table 7 of the manuscript.
"""
import wntr
import numpy as np
import json
from pathlib import Path
from importlib import import_module

_ss = import_module("01_steady_state")
_leak = import_module("04_leak_simulation")

N_SENSORS = 5
SENSITIVITY_EPSILON = 0.1        # m — a leak is "covered" by a sensor if
                                 #     ∂p_sensor/∂leak > ε at that node


def _sensitivity_matrix(inp_path):
    """
    Build S[i,j] = pressure change at node i when a small leak is placed at
    node j (mean-demand baseline, single time-step).
    """
    wn = wntr.network.WaterNetworkModel(inp_path)
    wn = _ss._peak_hour_setup(wn)
    res_base = wntr.sim.EpanetSimulator(wn).run_sim()
    p_base = res_base.node['pressure'].iloc[0].drop('TA1')

    node_ids = list(p_base.index)
    N = len(node_ids)
    S = np.zeros((N, N))

    # Perturb each node with a small emitter and record pressure change everywhere
    for j_idx, j_node in enumerate(node_ids):
        wn2 = wntr.network.WaterNetworkModel(inp_path)
        wn2 = _ss._peak_hour_setup(wn2)
        wn2.get_node(j_node).add_leak(
            wn2, area=_leak.LEAK_AREA_M2,
            discharge_coeff=_leak.CD, start_time=0)
        try:
            res = wntr.sim.WNTRSimulator(wn2).run_sim()
            p_leak = res.node['pressure'].iloc[0].drop('TA1')
            S[:, j_idx] = (p_base - p_leak).reindex(node_ids).fillna(0).values
        except Exception:
            S[:, j_idx] = 0
    return S, node_ids


def _greedy_max_coverage(S, node_ids, N, eps):
    """Pick N sensor locations that maximise the number of covered leak sources."""
    N_nodes = len(node_ids)
    covered = np.zeros(N_nodes, dtype=bool)
    selected = []
    for k in range(N):
        best_i, best_gain = -1, -1
        for i in range(N_nodes):
            if i in selected: continue
            newly_covered = (S[i, :] > eps) & (~covered)
            gain = int(newly_covered.sum())
            if gain > best_gain:
                best_gain, best_i = gain, i
        if best_i == -1: break
        selected.append(best_i)
        covered |= (S[best_i, :] > eps)
    return [node_ids[i] for i in selected], int(covered.sum())


def run(inp_path, out_dir, seed=42):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    print("    Computing sensitivity matrix (this may take ~30 s)...")
    S, node_ids = _sensitivity_matrix(inp_path)
    print(f"    Sensitivity matrix: {S.shape}, max sensitivity {S.max():.2f} m")

    selected, coverage = _greedy_max_coverage(
        S, node_ids, N=N_SENSORS, eps=SENSITIVITY_EPSILON)

    summary = {
        "algorithm":              "greedy_max_coverage",
        "num_sensors_selected":   len(selected),
        "sensor_locations":       selected,
        "sensitivity_threshold_m":SENSITIVITY_EPSILON,
        "coverage_pct":           coverage / len(node_ids) * 100,
        "total_candidate_nodes":  len(node_ids),
    }
    (out / "07_sensor_placement_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"    Recommended sensors : {', '.join(selected)}")
    print(f"    Coverage            : {coverage}/{len(node_ids)} nodes "
          f"({summary['coverage_pct']:.1f} %)")
    print(f"    Wrote 07_sensor_placement_summary.json in {out}")


if __name__ == "__main__":
    import sys
    run(inp_path=sys.argv[1] if len(sys.argv) > 1
        else "../S4_network_topology/rail_nagar.inp",
        out_dir="results", seed=42)
