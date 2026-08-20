# 01 — Source & legal audit (M1)

**Status: IN PROGRESS.** Access questions (section A) are answered. Personal-data
questions (section B) are **UNRESOLVED** and still block publication of anything
derived from per-run positions — gate G1.

Answers record where they were checked and when. Nothing here is filled in from
recollection.

**Open questions are pending on the M0 forum thread**, posted 2026-08-20:
<https://discuss.px4.io/t/characterising-the-public-log-corpus-450k-logs-and-a-question-about-acceptable-retrieval/49391> — see [`outreach/m0-px4-forum-post.md`](outreach/m0-px4-forum-post.md).
A2 (acceptable retrieval), A6 (is `dbinfo` a supportable interface), B2/B3
(personal data) and the `wind_speed` reading are all asked there. Answers get
recorded here with the reply's date and author.

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
| C0 | Does prior work already join public flight logs to reanalysis per flight? | **Partly — the §1.5 gap claim needs narrowing.** Somanagoudar & Mérida, *Weather-aware energy management for unmanned aerial vehicles*, Eng. Appl. Artif. Intell., DOI 10.1016/j.engappai.2024.109596 (UBC, online 2024-11-12), uses publicly available UAV logs plus ERA5. From abstract-level sources the target is **energy prediction**, with ERA5 as an input feature; there is no indication they validate ERA5 against onboard wind. **Full text not read** — paywalled, and the open UBC copy is IP-blocked. Verify before any novelty claim. | 2026-08-20, partial |
| C1 | UAV-SEAD licence | **CC-BY-4.0.** `aykutkabaoglu/uav-flight-anomaly-dataset` on HuggingFace, DOI 10.57967/hf/7772, curated by Aykut Kabaoglu (with Sanem Sariel), created 2025-09-28, updated 2026-05-19. Compatible with our publication policy. Tooling: `github.com/aykutkabaoglu/ulog_annotation_tool`. | 2026-08-20 |
| C2 | UAV-SEAD anomaly classes and resolution | **Four anomaly classes plus Normal and Uncategorized**, annotated with anomaly *durations*, so labels are time-bounded rather than per-flight: Normal 900 flights (38:24:19) · External Position 197 (05:12:25, of which 01:17:02 anomalous) · Altitude 78 (02:41:21 / 00:25:57) · Mechanical and Electrical 47 (02:12:38 / 00:12:43) · Global Position 41 (01:40:42 / 00:36:23) · Uncategorized 141. 1,396 annotated flights, 52:20:05 total; 3,196 raw. Annotation is "Physically-Constrained Expert Evaluation". | 2026-08-20 |
| C2b | **Is UAV-SEAD usable for H1?** | **No.** Three independent blockers, all from the dataset card: (a) only **04:35:24 of 52:20:05 (8.8%) has global position data** — the rest is indoor, on external/vision position, so there is nothing to join ERA5 *to*; (b) the 81-topic superset schema contains **no wind or airspeed topic at all**, so there is no onboard wind estimate to compare against; (c) the stated limitation is "limited to multi-rotor dynamics, limited outdoor flights with GPS availability". It remains relevant to H2 as an event vocabulary, on a different population. | 2026-08-20 |
| C3 | ALFA licence and citation | TBD | — |
| C4 | BASiC licence; confirm SITL-only | TBD | — |
| C5 | ERA5 Copernicus licence version and attribution string | CC-BY, cited by DOI **10.24381/cds.adbb2d47** for ERA5 single levels. Copernicus attribution required in derived artifacts. Registration and an API key are needed for CDS access — not yet obtained. | 2026-08-20 |
| C6 | How is ERA5T identified in the response? | **Partially.** CDS documents that ERA5 updates daily with ~5 days latency, that the early release is called **ERA5T**, that it may differ from the final release 2–3 months later, and that users are notified if it does. It does **not** document a field that identifies which you received. Must be determined from an actual retrieval before any manifest can claim to record it. | 2026-08-20, partial |
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
