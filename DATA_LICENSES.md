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
| UAV-SEAD | 1,396 real PX4 logs, ~52 h, 4 expert-annotated state-estimation anomaly classes | CC-BY-4.0 (HuggingFace dataset card, DOI 10.57967/hf/7772) — verified 2026-08-20 | Not usable for H1 (no wind topic, 8.8% with global position); H2 event vocabulary only |
| ALFA | Fixed-wing UAV faults and anomalies with temporal ground truth | CC-BY-4.0 on the KiltHub record, CC0 in the record's own README — **conflicting, resolve before use** (verified 2026-08-24) | ArduPilot, not PX4, and no ULog: outside the corpus. Complementary to H2 only |
| BASiC | 70 flights, simulated sensor faults in ArduPilot SITL | CC-BY-4.0 on the Zenodo record 10.5281/zenodo.8195068 — verified 2026-08-24 | Simulated *and* ArduPilot. Synthetic baseline only, never merged into the real-flight corpus |
| ERA5 / ERA5T (Copernicus CDS, or the ARCO-ERA5 copy in Google Cloud Public Datasets) | Hourly reanalysis, 0.25°, incl. 100 m u/v wind | *Licence to use Copernicus Products* rev. 12 either way — **not** CC-BY; the copy does not relicense the data, and ARCO additionally asks to be cited (Carver & Merose 2023) | Attribution required; record `dataset/product ID`, version and `retrieved_at`, plus which route was used and its release marker (`expver` from CDS in either format, `valid_time_stop_era5t` from ARCO) |
| Copernicus DEM (WorldDEM-30, GLO-30/GLO-90) | Surface elevation, slope — a **Digital Surface Model**, not bare earth and not an obstacle map | COP-DEM-GLO-30-F "Full, Free & Open" licence — free, but **not** CC-BY: prescribed notices, a liability sentence, and flow-down to subsequent users (verified 2026-08-24) | Phase 2 (H3). Retrievable without credentials from `s3://copernicus-dem-30m` (eu-central-1, COG) |
| METAR / airport stations | 10 m observations over a runway | **Non-U.S. observations cannot be redistributed** — WMO Resolution 40, stated in the NCEI ISD readme and inherited by IEM, which ingests ISD (verified 2026-08-24) | Optional third reference. Retrieve and process locally; publish per-station values for U.S. stations only |

## Attribution

Every published artifact carries the attribution required by its sources. For PX4
logs this means a CC-BY credit to PX4 and a pointer back to the source records; for
Copernicus products it means the Copernicus attribution statement plus the product ID
and version actually retrieved.

### ERA5 — the exact strings

*Licence to use Copernicus Products*, revision 12, clause 5. Anything we publish is an
adaptation, so it carries the second form, with the year of the information used:

> Contains modified Copernicus Climate Change Service information [Year]

Distribution of an unmodified product would instead require "Generated using Copernicus
Climate Change Service information [Year]". Either way clause 5.1.3 requires the
publication to state:

> Neither the European Commission nor ECMWF is responsible for any use that may be made
> of the Copernicus information or data it contains.

Clause 6.2 is a trap worth naming: IPR in items created by modifying Copernicus Products
*through the CDS Toolbox* belongs to the European Union. Deriving anything in the Toolbox
would hand over the IPR in our own outputs. All derivation happens locally.

### Copernicus DEM — the exact strings

The DEM licence prescribes its notices word for word, and prescribes a *different* one
once the data have been adapted. Any artifact derived from the DEM — which is every use
we would make of it — carries the second:

> produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and
> Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all
> rights reserved.

Distributing it unmodified would instead require:

> © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under
> COPERNICUS by the European Union and ESA; all rights reserved.

Either way, the licence or notice covering our distribution must also carry:

> The organisations in charge of the Copernicus programme by law or by delegation do
> not incur any liability for any use of the Copernicus WorldDEM-30.

and must bind subsequent users to the same obligations. This is a flow-down term. It is
why the closing rule of this document — *where an upstream licence imposes stricter
terms, the stricter terms govern* — is not decorative: a DEM-derived artifact cannot be
released under plain CC-BY-4.0 without carrying these terms with it.

## Personal data

Public logs **may contain** geolocated trajectories potentially attributable to
natural persons. The project does not assume every trajectory is personal data; it
assumes some may be. Consequently:

- publish positional results **only in aggregate**, never per run — a generalised
  per-run row is pseudonymised, not anonymous, because the raw log stays public and
  the row joins back to it on duration, airframe, firmware and date;
- keep generalisation anyway: it is a real Article 89(1) safeguard, it is just not the
  one doing the work;
- never publish `vehicle_uuid`, hashed or otherwise, nor free text from `description`,
  `vehicle_name` or `feedback`;
- publish the pipeline so it can be re-run by anyone against the original source;
- carry complete CC-BY attribution in every artifact.

A permissive content licence does not settle the data-protection question. The two are
assessed separately: the assessment is [`docs/07-personal-data.md`](docs/07-personal-data.md)
and the publication rule it produces is
[`docs/adr/0009-aggregate-only-for-positional-results.md`](docs/adr/0009-aggregate-only-for-positional-results.md).
Both are provisional until the controller signs off.

## Derived artifacts

Release terms are decided **per artifact, from the sources that artifact actually
used**, and recorded in its manifest — not declared once for the repository. See
[`docs/adr/0007-licences-travel-with-the-data.md`](docs/adr/0007-licences-travel-with-the-data.md).

CC-BY-4.0 with upstream attribution preserved is the default for an artifact whose
sources allow it. It is not a property of this repository: an artifact touching the
Copernicus DEM or non-U.S. METAR observations cannot carry that label unchanged.
