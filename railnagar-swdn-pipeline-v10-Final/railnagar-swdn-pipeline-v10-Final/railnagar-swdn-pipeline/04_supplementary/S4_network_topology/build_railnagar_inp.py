"""
build_railnagar_inp.py
======================
Reconstructs an EPANET input file (rail_nagar.inp) for the Rail Nagar SWDN
from the topology data captured in the Deng-Nkurunziza (2024) project
report — Tables 4.3 (pipe list) and 5.1 (junction results). This is the
same network the manuscript describes.

PROVENANCE NOTE (important):
- Pipe list (start, end, length, diameter) — Table 4.3 of the report.
- Junction elevations — computed as (head − pressure) from Table 5.1 of
  the report, verified against the "elevation" labels on the corrected
  Figure 6 network map.
- JU60-JU63 elevations — inferred from parent nodes (JU55-JU58 chain);
  the report's Table 5.1 was truncated at JU59.
- Coordinates — omitted (this .inp is for hydraulic simulation, not
  cartographic rendering; the manuscript's Figure 6 uses independently
  digitised WGS84 coordinates from Google Earth Pro).
- Tank characteristics — derived from the manuscript description
  (10 ML combined ESR + GSR storage abstracted as single elevated tank).

If Bhavana provides the original .inp file, please replace this
reconstruction — the two should agree closely in hydraulic output but
may differ in demand allocation and tank sizing.
"""
import csv
from pathlib import Path

DATA = Path("/home/claude/railnagar-swdn-pipeline/04_supplementary/S4_network_topology/data")
OUT_INP = Path("/home/claude/railnagar-swdn-pipeline/04_supplementary/S4_network_topology/rail_nagar.inp")

# ---- Read parsed topology ----
pipes = list(csv.DictReader(open(DATA / "pipes.csv")))
junctions = list(csv.DictReader(open(DATA / "junctions_final.csv")))

# ---- Design parameters (matching manuscript) ----
POPULATION       = 5234                # persons
LPCD             = 200                 # L / person / day (IS 1172:1993)
MEAN_DEMAND_LPS  = POPULATION * LPCD / 86400.0        # 12.12 L/s
PER_JUNCTION_LPS = MEAN_DEMAND_LPS / len(junctions)   # uniform allocation
PEAK_FACTOR      = 3.0                 # IS 1172:1993 for population < 50,000
HW_C             = 140                 # Hazen-Williams for new PVC
CHLORINE_KB      = 0.5                 # 1/day, network-mean bulk decay

# Tank characteristics (elevated, single abstracted tank per manuscript §2)
TANK_ID          = "TA1"
TANK_BASE_ELEV   = 156.5               # m a.m.s.l. (elevated feed)
TANK_INIT_LEVEL  = 7.5                 # m water depth
TANK_MIN_LEVEL   = 0.0
TANK_MAX_LEVEL   = 10.0
# Volume = 10 ML = 10,000 m³. At 10 m depth: D = sqrt(40000/(π·10)) ≈ 35.7 m
TANK_DIAMETER    = 35.68               # m
TANK_MIN_VOL     = 0.0                 # m³

# Diurnal pattern (from CPHEEO 1999, peak x2.0 at 07:00 and 19:00, min at 03:00)
# 24 hourly multipliers, mean = 1.0
DIURNAL_PATTERN = [
    0.60, 0.55, 0.50, 0.55, 0.75, 1.20,   # 00-05
    1.80, 2.00, 1.80, 1.30, 1.00, 0.90,   # 06-11
    0.85, 0.85, 0.90, 1.10, 1.40, 1.75,   # 12-17
    1.95, 2.00, 1.75, 1.30, 0.95, 0.75,   # 18-23
]
# Ensure it averages to ≈ 1.0
mean_ = sum(DIURNAL_PATTERN) / 24
DIURNAL_PATTERN = [m / mean_ for m in DIURNAL_PATTERN]

# ---- Build the .inp ----
lines = []
lines.append(f"; rail_nagar.inp — Rail Nagar Smart Water Distribution Network")
lines.append(f"; Reconstructed from Deng & Nkurunziza (2024) project report tables")
lines.append(f"; See build_railnagar_inp.py for provenance details")
lines.append(f"; Generated {__file__ if False else 'by supplementary pipeline'}")
lines.append("")
lines.append("[TITLE]")
lines.append("Rail Nagar SWDN — reconstructed for reproducibility")
lines.append("")

# JUNCTIONS
lines.append("[JUNCTIONS]")
lines.append(";ID              Elev(m)   Demand(LPS)   Pattern")
for j in junctions:
    lines.append(f" {j['junction_id']:<15} {float(j['elevation_m']):>7.2f}  "
                 f"{PER_JUNCTION_LPS:>10.4f}   demand")
lines.append("")

# RESERVOIRS (none — feed via elevated tank)
lines.append("[RESERVOIRS]")
lines.append(";ID              Head          Pattern")
lines.append("")

# TANKS
lines.append("[TANKS]")
lines.append(";ID              Elev      InitLvl  MinLvl  MaxLvl  Diameter  MinVol   VolCurve")
lines.append(f" {TANK_ID:<15} {TANK_BASE_ELEV:>7.2f}  "
             f"{TANK_INIT_LEVEL:>7.2f}  {TANK_MIN_LEVEL:>6.2f}  "
             f"{TANK_MAX_LEVEL:>6.2f}  {TANK_DIAMETER:>7.2f}  "
             f"{TANK_MIN_VOL:>7.2f}")
lines.append("")

# PIPES
lines.append("[PIPES]")
lines.append(";ID              Node1           Node2           Length(m)   Diameter(mm)   Roughness   MinorLoss   Status")
for p in pipes:
    lines.append(f" {p['pipe_id']:<15} {p['start_node']:<15} {p['end_node']:<15} "
                 f"{float(p['length_m']):>9.2f}  {float(p['diameter_mm']):>10.2f}  "
                 f"{HW_C:>10.2f}  {0.0:>9.4f}    Open")
lines.append("")

# PUMPS, VALVES (none for this dendritic gravity network)
lines.append("[PUMPS]")
lines.append("")
lines.append("[VALVES]")
lines.append("")

# DEMANDS (already set per junction in [JUNCTIONS])
lines.append("[DEMANDS]")
lines.append("")

# STATUS
lines.append("[STATUS]")
lines.append("")

# PATTERNS
lines.append("[PATTERNS]")
lines.append(";ID    Multipliers")
# demand pattern (24-h diurnal, 1-h step)
for i in range(0, 24, 6):
    chunk = DIURNAL_PATTERN[i:i+6]
    lines.append(f" demand  " + "  ".join(f"{m:.4f}" for m in chunk))
lines.append("")

# CONTROLS (none)
lines.append("[CONTROLS]")
lines.append("")

# RULES (none)
lines.append("[RULES]")
lines.append("")

# ENERGY, EMITTERS (none by default; leak simulation adds emitters at runtime)
lines.append("[ENERGY]")
lines.append(" Global Efficiency  75")
lines.append(" Global Price       0")
lines.append(" Demand Charge      0")
lines.append("")

lines.append("[EMITTERS]")
lines.append(";ID   FlowCoeff")
lines.append("")

# QUALITY (chlorine source = tank concentration 1.0 mg/L)
lines.append("[QUALITY]")
lines.append(";Node   InitQual")
lines.append(f" {TANK_ID}   1.0")
for j in junctions:
    lines.append(f" {j['junction_id']}   0.5")
lines.append("")

# SOURCES (chlorine dosing at tank)
lines.append("[SOURCES]")
lines.append(";Node   Type       Quality   Pattern")
lines.append(f" {TANK_ID}   CONCEN    1.0")
lines.append("")

# REACTIONS
lines.append("[REACTIONS]")
lines.append(f" Order Bulk               1")
lines.append(f" Order Wall               1")
lines.append(f" Global Bulk             -{CHLORINE_KB}")
lines.append(f" Global Wall              0.0")
lines.append(f" Limiting Potential       0.0")
lines.append(f" Roughness Correlation    0.0")
lines.append("")

# MIXING
lines.append("[MIXING]")
lines.append(";Tank   Model")
lines.append(f" {TANK_ID}   MIXED")
lines.append("")

# TIMES
lines.append("[TIMES]")
lines.append(" Duration           24:00")
lines.append(" Hydraulic Timestep  1:00")
lines.append(" Quality Timestep    0:05")
lines.append(" Pattern Timestep    1:00")
lines.append(" Pattern Start       0:00")
lines.append(" Report Timestep     1:00")
lines.append(" Report Start        0:00")
lines.append(" Start ClockTime    00:00")
lines.append(" Statistic           NONE")
lines.append("")

# REPORT
lines.append("[REPORT]")
lines.append(" Status             No")
lines.append(" Summary            No")
lines.append(" Page               0")
lines.append("")

# OPTIONS
lines.append("[OPTIONS]")
lines.append(" Units              LPS")
lines.append(" Headloss           H-W")
lines.append(f" Specific Gravity   1.0")
lines.append(f" Viscosity          1.0")
lines.append(f" Trials             40")
lines.append(f" Accuracy           0.001")
lines.append(f" CHECKFREQ          2")
lines.append(f" MAXCHECK           10")
lines.append(f" DAMPLIMIT          0.0")
lines.append(f" Unbalanced         Continue 10")
lines.append(f" Pattern            demand")
lines.append(f" Demand Multiplier  1.0")
lines.append(f" Emitter Exponent   0.5")
lines.append(f" Quality            Chlorine mg/L")
lines.append(f" Diffusivity        1.0")
lines.append(f" Tolerance          0.01")
lines.append("")

# END
lines.append("[END]")

# Write
OUT_INP.write_text("\n".join(lines))
print(f"Wrote {OUT_INP}  ({sum(len(l)+1 for l in lines):,} bytes, {len(lines)} lines)")

# Print summary
print(f"\nNetwork summary:")
print(f"  Population         : {POPULATION}")
print(f"  Junctions          : {len(junctions)}")
print(f"  Pipes              : {len(pipes)}")
print(f"  Mean demand        : {MEAN_DEMAND_LPS:.2f} L/s total; {PER_JUNCTION_LPS:.4f} L/s per junction")
print(f"  Peak factor        : {PEAK_FACTOR} (per IS 1172:1993)")
print(f"  Peak demand        : {MEAN_DEMAND_LPS * PEAK_FACTOR:.2f} L/s expected")
print(f"  Elevation range    : {min(float(j['elevation_m']) for j in junctions):.0f} — "
      f"{max(float(j['elevation_m']) for j in junctions):.0f} m")
print(f"  Tank capacity      : ~10 ML at max level")
