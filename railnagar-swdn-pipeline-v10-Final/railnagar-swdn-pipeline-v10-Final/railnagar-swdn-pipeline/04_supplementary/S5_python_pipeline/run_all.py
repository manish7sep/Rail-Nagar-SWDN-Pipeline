"""
run_all.py
==========
Master orchestrator for the Rail Nagar SWDN reproducible analysis pipeline.
Runs all eight analysis stages in sequence and writes outputs to results/.

Usage:
    python run_all.py [--inp path/to/rail_nagar.inp] [--seed 42]

Reference implementation of the methodology described in:
Bol, Nkurunziza, Thummar, Gundlapalli & Pandey (2026).
"A reproducible EPANET-WNTR framework with synthetic IoT leak diagnostics
for smart water networks: Rail Nagar, Rajkot, Gujarat, Bharat".
Submitted to Journal of Hydroinformatics.

Licence: MIT
"""
import argparse
from pathlib import Path
import sys
import importlib
import time

# Analysis stages in execution order
STAGES = [
    ("01_steady_state",              "Steady-state peak-hour hydraulics"),
    ("02_extended_period_simulation","24-h EPS with diurnal pattern"),
    ("03_water_quality",             "Chlorine decay + water age"),
    ("04_leak_simulation",           "Pressure-dependent leak simulation"),
    ("05_iot_leak_detection",        "Synthetic IoT sensors + 3σ residual detection"),
    ("06_resilience_indices",        "Todini I_r, MRI, NRI"),
    ("07_sensor_placement",          "Greedy max-coverage optimal placement"),
    ("08_verification_checks",       "Five physical-consistency checks"),
]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inp", default="../S4_network_topology/rail_nagar.inp",
                    help="Path to EPANET input file")
    ap.add_argument("--out", default="results",
                    help="Output directory for results")
    ap.add_argument("--seed", type=int, default=42,
                    help="Random seed for reproducibility")
    ap.add_argument("--only", nargs="+", default=None,
                    help="Run only specified stages (e.g., --only 01 02)")
    args = ap.parse_args()

    inp_path = Path(args.inp).resolve()
    out_dir  = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not inp_path.exists():
        sys.exit(f"ERROR: EPANET input file not found: {inp_path}")

    print("=" * 74)
    print(" Rail Nagar SWDN — reproducible analysis pipeline")
    print("=" * 74)
    print(f" INP file : {inp_path}")
    print(f" Output   : {out_dir}")
    print(f" Seed     : {args.seed}")
    print("=" * 74)

    for i, (mod_name, desc) in enumerate(STAGES, 1):
        stage_id = mod_name.split("_")[0]
        if args.only and stage_id not in args.only:
            continue
        print(f"\n[{i}/{len(STAGES)}] {desc}")
        print("-" * 74)
        t0 = time.time()
        try:
            mod = importlib.import_module(mod_name)
            mod.run(inp_path=str(inp_path), out_dir=str(out_dir), seed=args.seed)
            print(f"  ✓ completed in {time.time()-t0:.1f} s")
        except Exception as e:
            print(f"  ✗ FAILED: {e}")
            import traceback; traceback.print_exc()

    print("\n" + "=" * 74)
    print(f" Pipeline complete. Results in: {out_dir}")
    print("=" * 74)

if __name__ == "__main__":
    main()
