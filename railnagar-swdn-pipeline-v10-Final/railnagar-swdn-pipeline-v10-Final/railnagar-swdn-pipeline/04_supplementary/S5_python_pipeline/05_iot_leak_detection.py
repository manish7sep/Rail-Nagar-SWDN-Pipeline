"""
05_iot_leak_detection.py
========================
Synthetic IoT pressure-sensor layer with residual-based leak detection.
Ten sensors at 5-minute sampling with 2.5 % Gaussian noise. A 3σ residual
rule is trained on the leak-free first 6 hours and then applied to the
whole 24-h window.

Produces the true-positive / false-positive detection metrics reported in
Table 6 and Figures 10a–d.
"""
import wntr
import pandas as pd
import numpy as np
import json
from pathlib import Path
from importlib import import_module

_eps = import_module("02_extended_period_simulation")
_leak = import_module("04_leak_simulation")

# Ten sensor locations: mix of leak nodes (for TP) and control nodes (for FP)
SENSOR_LEAK_NODES = ['JU8', 'JU22', 'JU45', 'JU59']              # 4 leak-adjacent
SENSOR_CTRL_NODES = ['JU2', 'JU19', 'JU27', 'JU30', 'JU63', 'JU13']  # 6 controls
SENSORS           = SENSOR_LEAK_NODES + SENSOR_CTRL_NODES

NOISE_SD_FRAC = 0.025            # 2.5 % Gaussian noise (of local pressure)
SAMPLING_MIN  = 5                # min between samples
DETECT_SIGMA  = 3.0              # threshold multiplier
BASELINE_H    = 6                # baseline window (leak-free) in hours


def _resample_1h_to_5min(ts_1h):
    """Upsample hourly-resolution WNTR output to 5-min resolution via linear interp."""
    idx_h = np.arange(len(ts_1h))
    idx_5min = np.arange(0, len(ts_1h) - 1, SAMPLING_MIN / 60)
    return np.interp(idx_5min, idx_h, ts_1h.values)


def run(inp_path, out_dir, seed=42):
    rng = np.random.default_rng(seed)
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)

    # --- Modelled (baseline) pressures at sensor nodes ---
    wn_base = wntr.network.WaterNetworkModel(inp_path)
    wn_base.get_pattern('demand').multipliers = _eps.DIURNAL_NORM
    wn_base.options.time.duration = 24 * 3600
    res_base = wntr.sim.EpanetSimulator(wn_base).run_sim()

    # --- Observed (with leaks) pressures ---
    wn_leak = wntr.network.WaterNetworkModel(inp_path)
    wn_leak.get_pattern('demand').multipliers = _eps.DIURNAL_NORM
    wn_leak.options.time.duration = 24 * 3600
    for nid in _leak.LEAK_NODES:
        wn_leak.get_node(nid).add_leak(
            wn_leak, area=_leak.LEAK_AREA_M2,
            discharge_coeff=_leak.CD, start_time=12*3600)     # leak at hour 12
    res_leak = wntr.sim.WNTRSimulator(wn_leak).run_sim()

    # Sensor time series at 5-min resolution
    detections = []
    for nid in SENSORS:
        p_mod = _resample_1h_to_5min(res_base.node['pressure'][nid])
        p_obs = _resample_1h_to_5min(res_leak.node['pressure'][nid])
        noise = rng.normal(0, NOISE_SD_FRAC * np.abs(p_obs))
        p_obs_noisy = p_obs + noise

        residual = p_obs_noisy - p_mod
        # Baseline window: first BASELINE_H hours × 12 samples/h
        n_baseline = BASELINE_H * 60 // SAMPLING_MIN
        sigma = residual[:n_baseline].std()
        threshold = DETECT_SIGMA * sigma

        # Post-leak flags (after hour 12)
        n_pre_leak = 12 * 60 // SAMPLING_MIN
        alerts_pre = np.sum(np.abs(residual[:n_pre_leak]) > threshold)
        alerts_post = np.sum(np.abs(residual[n_pre_leak:]) > threshold)

        detections.append({
            'sensor_node':      nid,
            'sensor_type':      'leak' if nid in SENSOR_LEAK_NODES else 'control',
            'baseline_sigma_m': float(sigma),
            'threshold_m':      float(threshold),
            'pre_leak_alerts':  int(alerts_pre),
            'post_leak_alerts': int(alerts_post),
            'detected':         bool(alerts_post > n_pre_leak / 4),
        })

    df = pd.DataFrame(detections)
    df.to_csv(out / "05_iot_detection.csv", index=False)

    # --- Confusion metrics ---
    leak_sensors = df[df.sensor_type == 'leak']
    ctrl_sensors = df[df.sensor_type == 'control']
    tp = int(leak_sensors.detected.sum())
    fn = int((~leak_sensors.detected).sum())
    fp = int(ctrl_sensors.detected.sum())
    tn = int((~ctrl_sensors.detected).sum())

    summary = {
        "num_sensors":            len(SENSORS),
        "sampling_interval_min":  SAMPLING_MIN,
        "noise_sd_fraction":      NOISE_SD_FRAC,
        "detection_sigma":        DETECT_SIGMA,
        "baseline_hours":         BASELINE_H,
        "leak_sensors":           SENSOR_LEAK_NODES,
        "control_sensors":        SENSOR_CTRL_NODES,
        "true_positives":         tp,
        "false_negatives":        fn,
        "false_positives":        fp,
        "true_negatives":         tn,
        "true_positive_rate_pct": tp / (tp + fn) * 100 if tp + fn else 0.0,
        "false_positive_rate_pct":fp / (fp + tn) * 100 if fp + tn else 0.0,
        "random_seed":            seed,
    }
    (out / "05_iot_detection_summary.json").write_text(json.dumps(summary, indent=2))

    print(f"    Sensor count      : {len(SENSORS)} ({len(SENSOR_LEAK_NODES)} leak + "
          f"{len(SENSOR_CTRL_NODES)} control)")
    print(f"    True-positive rate: {summary['true_positive_rate_pct']:.1f} % "
          f"({tp}/{tp+fn})")
    print(f"    False-positive rate: {summary['false_positive_rate_pct']:.1f} % "
          f"({fp}/{fp+tn})")
    print(f"    Wrote 05_iot_detection*.csv/json in {out}")


if __name__ == "__main__":
    import sys
    run(inp_path=sys.argv[1] if len(sys.argv) > 1
        else "../S4_network_topology/rail_nagar.inp",
        out_dir="results", seed=42)
