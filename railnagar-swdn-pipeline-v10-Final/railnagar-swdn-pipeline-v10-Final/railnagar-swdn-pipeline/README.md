# railnagar-swdn-pipeline — Submission Package

**Manuscript:** "A reproducible EPANET-WNTR framework with synthetic IoT leak
diagnostics for smart water networks: Rail Nagar, Rajkot, Gujarat, Bharat"

**Target journal:** Journal of Hydroinformatics (IWA Publishing)

**Corresponding authors:**
- Dr Bhavana Thummar (bhavana.ajudiya@marwadieducation.edu.in)
- Dr Manish Pandey (manish07sep@gmail.com)

**Version:** V10 (revised from V9 with three new field-infrastructure figures
inserted in §2, updated Figure 6 caption for corrected 3-colour Wong-palette
network map, and all downstream figures renumbered).

## Folder layout

| Folder | Contents |
|---|---|
| `01_manuscript/` | V10 clean & tracked DOCX + PDF renders |
| `02_figures/high_res_600dpi/` | All 10 publication figures at 600 DPI PNG |
| `02_figures/300dpi_previews/` | 300 DPI JPEG previews for editorial workflow |
| `02_figures/List_of_Figures.docx` | Standalone captions list |
| `03_tables/List_of_Tables.docx` | Standalone table captions list |
| `04_supplementary/` | Reconstructed EPANET input + Python analysis pipeline |
| `05_cover_letter/` | Editor cover letter |
| `06_data_availability/` | Data & code availability statement |

## Supplementary contents (`04_supplementary/`)

| Path | Purpose |
|---|---|
| `S4_network_topology/rail_nagar.inp` | EPANET 2.2 input file (reconstructed from Table 4.3 + Table 5.1 of the source project report) |
| `S4_network_topology/data/pipes.csv` | 61 pipes: start, end, length, diameter |
| `S4_network_topology/data/junctions_final.csv` | 61 junctions with elevations |
| `S4_network_topology/data/junctions_report_results.csv` | Raw report-derived junction data |
| `S4_network_topology/build_railnagar_inp.py` | Regenerates `rail_nagar.inp` from the CSVs |
| `S5_python_pipeline/run_all.py` | Master orchestrator for the 8-stage analysis |
| `S5_python_pipeline/01_steady_state.py` | Peak-hour hydraulic analysis (Table 3, Figure 7) |
| `S5_python_pipeline/02_extended_period_simulation.py` | 24-h EPS (Table 4, Figure 8) |
| `S5_python_pipeline/03_water_quality.py` | Chlorine + water age (Table 5, Figure 9) |
| `S5_python_pipeline/04_leak_simulation.py` | Pressure-dependent leak model (Table 6) |
| `S5_python_pipeline/05_iot_leak_detection.py` | Synthetic IoT + 3σ residual detection (Figure 10) |
| `S5_python_pipeline/06_resilience_indices.py` | Todini I_r, MRI, NRI (Table 7) |
| `S5_python_pipeline/07_sensor_placement.py` | Greedy max-coverage placement (Table 7) |
| `S5_python_pipeline/08_verification_checks.py` | 5 physical-consistency checks (Table 9) |

To reproduce all analyses:
```
cd 04_supplementary/S5_python_pipeline
python run_all.py
```

Requires Python 3.11+ with `wntr numpy pandas`.

## V9 → V10 change summary

**Structural:**
- Inserted 3 new field-infrastructure figures in §2 as Figures 2, 3, 4:
  - Figure 2: Six parallel pumps at the feeder pumping station
  - Figure 3: Allen-Bradley SCADA "Flow Data – 1" panel (22 Sep 2024, 08:48:30 IST)
  - Figure 4: Allen-Bradley PLC-SCADA overview panel + MAIN/UPS switches
- Renumbered all subsequent figures (2→5, 3→6, 4→7, 5→8, 6→9, 7→10)
- Amended §2 SCADA paragraph with explicit cross-reference to Figures 2–4
  and the panel timestamp

**Figure 6 (was Figure 3, the network map):**
- Replaced with the corrected 3-colour Wong-palette version
  (vermilion for 147.6 mm, blue for 101.6 mm, reddish-purple for 81.4 mm)
- Caption rewritten from "yellow / green" two-colour description

**Value reconciliation:**
- All four SCADA numbers in §2 (10.87 ML, 6.74 ML, 6.61 ML, 1,249 m³/hr)
  verified against Figure 3 panel photograph. No discrepancies.

## Pre-submission checklist

- [ ] Populate the GitHub repository URL in the Data & Code Availability
      Statement (currently a placeholder)
- [ ] Optionally replace `S4_network_topology/rail_nagar.inp` with the
      original field-surveyed file if Bhavana can share it
- [ ] Review the V10 tracked-changes docx
- [ ] Confirm co-author sign-off on the three new field figures

## Licence

Manuscript and figures: authors' copyright (submission to IWA Publishing).
Supplementary code (S5) and reconstructed inputs (S4): MIT Licence.
