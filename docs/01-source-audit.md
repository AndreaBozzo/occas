# 01 — Source & legal audit (M1)

**Status: IN PROGRESS.** Access questions (section A) are answered. Personal-data
questions (section B) are **UNRESOLVED** and still block publication of anything
derived from per-run positions — gate G1.

Answers record where they were checked and when. Nothing here is filled in from
recollection.

**B-status: UNRESOLVED**

## A. PX4 Flight Review — access

| # | Question | Answer | Checked on |
|---|---|---|---|
| A1 | Terms of service for the log service? | No separate ToS document found. The licence is stated in-page on the browse and upload templates (PX4/flight_review PR #302, Jan 2025) as CC-BY 4.0. Uploaders are told at upload time that logs are published under "CC-BY PX4". | 2026-08-20 |
| A2 | Rate limit on the download endpoint? | **Yes, and documented in the client.** `app/download_logs.py` defaults to a 6 s delay (10 req/min), `--max-num 10`, warns above 100 files and requires confirmation. It handles `503` with exponential backoff honouring `Retry-After`, and treats `403`/`444` as "your IP has been blocked". The script also states that network and storage costs are funded by the Dronecode Foundation. | 2026-08-20 |
| A2b | `robots.txt` on `logs.px4.io`? | `User-agent: *` / `Allow: /` / `Disallow: /*` — the wildcard disallow covers every path. Automated crawling is discouraged by the site's own policy, whatever the content licence permits. **Consequence: ask the maintainers on the record before any bulk retrieval.** | 2026-08-20 |
| A3 | Does `download_logs.py` work as documented, and what filters does it expose? | It lives at `app/download_logs.py` (not the repo root). Filters: `--mav-type`, `--flight-modes`, `--error-labels`, `--rating`, `--uuid`, `--log-id`, `--vehicle-name`, `--airframe-name`, `--airframe-type`, `--latest-per-vehicle`, `--source`, `--git-hash`. Not yet executed. | 2026-08-20 |
| A4 | Is CC-BY attribution stated per-log or corpus-wide? | Corpus-wide, in the page templates. There is no per-log licence field in the metadata. | 2026-08-20 |
| A5 | Does any log carry a non-default licence or a private flag? | The public metadata dump contains only public logs; no per-record licence or visibility field exists. Private logs are simply absent. | 2026-08-20 |
| A6 | Is there a metadata API that avoids downloading logs? | **Yes — this changes the plan.** `https://review.px4.io/dbinfo` redirects (302) to `https://cdn.logs.px4.io/dbinfo.json`: a gzipped 30.7 MB / 356 MB JSON array of **every** public log's metadata, regenerated daily, served from a CDN rather than the origin. Retrieved once and cached. See [`02b-dbinfo-inventory.md`](02b-dbinfo-inventory.md). | 2026-08-20 |
| A7 | Is a database dump available? | No. A maintainer declined this explicitly on the forum (Jan 2025), directing users to extract metadata themselves. A6 supersedes the need. | 2026-08-20 |

## B. Personal data (GDPR) — UNRESOLVED

CC-BY is a copyright licence and says nothing about data protection. Still open, and
still blocking.

| # | Question | Answer | Checked on |
|---|---|---|---|
| B1 | Which fields could identify a natural person? | Partially narrowed: **`dbinfo` carries no coordinates**, so the metadata layer is comparatively low-risk. It does carry `vehicle_uuid`, `vehicle_name`, free-text `description` and `feedback`. Positions live only inside the `.ulg`. Full assessment TBD. | 2026-08-20 |
| B2 | What are uploaders told about publication and re-use? | The upload form states publication under CC-BY (PR #302). Whether that constitutes adequate notice for data-protection purposes: TBD. | 2026-08-20 |
| B3 | Which lawful basis applies to processing derived features? | TBD | — |
| B4 | What coordinate generalisation is sufficient, and how justified? | TBD | — |
| B5 | Does aggregate publication differ from per-run publication? | TBD | — |

Standing policy until B1–B5 are answered: derived and aggregate features only,
generalised coordinates, publish the pipeline rather than the data.

## C. Other datasets

| # | Question | Answer | Checked on |
|---|---|---|---|
| C1 | UAV-SEAD licence | TBD | — |
| C2 | UAV-SEAD anomaly classes and resolution | TBD | — |
| C3 | ALFA licence and citation | TBD | — |
| C4 | BASiC licence; confirm SITL-only | TBD | — |
| C5 | ERA5 Copernicus licence version and attribution string | TBD | — |
| C6 | How is ERA5T identified in the response? | TBD | — |
| C7 | Copernicus DEM licence and access | TBD | — |
| C8 | METAR archive and terms | TBD | — |

## D. Standards

| # | Question | Answer | Checked on |
|---|---|---|---|
| D1 | Is BSI PAS 1883:2020 withdrawn? | **Superseded, then re-issued.** BS ISO 34503:2023 supersedes PAS 1883:2020; **PAS 1883:2025** now exists as an *implementation guide* for BS ISO 34503, not a competing taxonomy. The brief's "appears withdrawn" is wrong and is corrected here. | 2026-08-20 |
| D2 | Current ASAM OpenODD version and terms? | **1.0.0, released 2025-04-03**, free of charge. A released standard, no longer a concept paper. Export to YAML, tabular formats and OpenSCENARIO DSL. | 2026-08-20 |

## E. Conclusion

Not final — B is unresolved. Provisional position:

- **May download:** yes, within the client's own documented limits (10 req/min, and a
  deliberate, small, stratified sample rather than a bulk pull). The `robots.txt`
  wildcard disallow means this should be raised with the maintainers first.
- **May process:** metadata, yes, freely — it is published as a CDN artifact and
  carries no coordinates.
- **May publish:** derived and aggregate features with attribution. Anything keyed to
  per-run position stays blocked until B1–B5 are answered.
