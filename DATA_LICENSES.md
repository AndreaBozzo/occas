# Data sources, licences and attribution

This repository publishes **code, schemas, manifests and derived aggregate features**.
It does not redistribute raw flight logs, and it does not redistribute raw geolocated
trajectories. Every source below is retrieved by the pipeline from its origin, so that
anyone can re-run the pipeline against the original data.

Rows marked **VERIFY (M1)** are unresolved and are the subject of
[`docs/01-source-audit.md`](docs/01-source-audit.md). Nothing derived from an
unverified row may be published.

| Source | What it provides | Licence / terms | Status |
|---|---|---|---|
| PX4 Flight Review (`logs.px4.io`) | Public ULog flight logs, real and SITL | CC-BY (PX4) | Attribution required in every artifact. Rate limits and ToS: **VERIFY (M1)** |
| PX4 log coordinates | Geolocated trajectories | CC-BY does not address the GDPR | Personal-data assessment: **VERIFY (M1)** — see §"Personal data" |
| UAV-SEAD | 1,396 real PX4 logs, ~52 h, 4 expert-annotated state-estimation anomaly classes | **VERIFY (M1)** — read the licence on the source repository | Not used until confirmed |
| ALFA | Fixed-wing UAV faults and anomalies with temporal ground truth | **VERIFY** before use | Complementary, not in the first deliverable |
| BASiC | 70 flights, simulated sensor faults in ArduPilot SITL | **VERIFY** before use | Synthetic baseline only |
| ERA5 / ERA5T (Copernicus CDS) | Hourly reanalysis, 0.25° | Copernicus Licence | Attribution required; record `dataset/product ID`, version and `retrieved_at` |
| Copernicus DEM | Elevation, slope | Copernicus Licence | Phase 2 (H3) |
| METAR / airport stations | 10 m observations over a runway | Source-dependent | Optional third reference, restricted subset only |

## Attribution

Every published artifact carries the attribution required by its sources. For PX4
logs this means a CC-BY credit to PX4 and a pointer back to the source records; for
Copernicus products it means the Copernicus attribution statement plus the product ID
and version actually retrieved.

## Personal data

Public logs **may contain** geolocated trajectories potentially attributable to
natural persons. The project does not assume every trajectory is personal data; it
assumes some may be. Consequently:

- publish derived and aggregate features, never raw trajectories;
- generalise or round coordinates in public artifacts;
- publish the pipeline so it can be re-run by anyone against the original source;
- carry complete CC-BY attribution in every artifact.

A permissive content licence does not settle the data-protection question. The two
are assessed separately in M1.

## Derived artifacts

Unless a specific artifact states otherwise, derived artifacts published by this
project are released under CC-BY-4.0, with upstream attribution preserved. Where an
upstream licence imposes stricter terms, the stricter terms govern.
