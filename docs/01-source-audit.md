# 01 — Source & legal audit (M1)

**Status: IN PROGRESS.** Access questions (section A) are answered. Personal-data
questions (section B) are **UNRESOLVED** and still block publication of anything
derived from per-run positions — gate G1.

Answers record where they were checked and when. Nothing here is filled in from
recollection.

**Open questions are pending on the M0 forum thread**, posted 2026-08-20:
<https://discuss.px4.io/t/characterising-the-public-log-corpus-450k-logs-and-a-question-about-acceptable-retrieval/49391> — see [`outreach/m0-px4-forum-post.md`](outreach/m0-px4-forum-post.md).
**Two of the four no longer depend on a reply.** The `wind_speed` encoding is verified
in `flight_review` source and against the dump itself ([`02b-dbinfo-inventory.md`](02b-dbinfo-inventory.md)),
and C6 is answered from ECMWF's documentation. What genuinely needs a maintainer is
A2 (acceptable retrieval volume) and A6 (is `dbinfo` supportable) — both are opinions
about their service, which no amount of reading can supply.

**No reply as of 2026-08-24** (4 days, 21 views, 0 replies — checked against the
topic JSON, not the rendered page). Nothing below depends on those answers.

A2 (acceptable retrieval), A6 (is `dbinfo` a supportable interface), B2/B3
(personal data) and the `wind_speed` reading are all asked there. Answers get
recorded here with the reply's date and author.

**B-status: UNRESOLVED.** Section C is closed except C0, C5 and C6: C0 needs the paywalled
full text, and C5/C6 need a CDS account and one real retrieval.

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
| C0 | Does prior work already join public flight logs to reanalysis per flight? | **Partly — the §1.5 gap claim needs narrowing.** Somanagoudar & Mérida, *Weather-aware energy management for unmanned aerial vehicles*, Eng. Appl. Artif. Intell., DOI 10.1016/j.engappai.2024.109596 (UBC, online 2024-11-12), uses publicly available UAV logs plus ERA5. From abstract-level sources the target is **energy prediction**, with ERA5 as an input feature; there is no indication they validate ERA5 against onboard wind. **Full text not read** — paywalled, and the open UBC copy is IP-blocked. **No open-access copy is indexed:** OpenAlex reports `oa_status: closed` with no repository full text, and Semantic Scholar returns an empty `openAccessPdf`; the only location either index knows is the publisher's, licensed CC-BY-NC-ND. That is not proof no copy exists, but it is the end of what searching will find. **The author's UBC thesis covers the same work at length** — Somanagoudar, *Weather-aware energy requirements prediction for UAVs: a machine learning approach with global data integration*, UBC, 2025, DOI 10.14288/1.0445044 — and its abstract, read from the DataCite record because `open.library.ubc.ca` refuses connections from here, describes the same target: predicting UAV energy consumption from operational logs and meteorological data, validated against **measured energy** on a test flight (0.005 Wh discrepancy). Two independent abstracts by the same author, and neither describes comparing reanalysis wind against an onboard estimate. The gap claim survives; the full text still closes the row, through institutional access or by asking the authors (already an open row in [`outreach/README.md`](outreach/README.md)). Verify before any novelty claim. | 2026-08-20, partial; re-checked 2026-08-24 |
| C1 | UAV-SEAD licence | **CC-BY-4.0.** `aykutkabaoglu/uav-flight-anomaly-dataset` on HuggingFace, DOI 10.57967/hf/7772, curated by Aykut Kabaoglu (with Sanem Sariel), created 2025-09-28, updated 2026-05-19. Compatible with our publication policy. Tooling: `github.com/aykutkabaoglu/ulog_annotation_tool`. | 2026-08-20 |
| C2 | UAV-SEAD anomaly classes and resolution | **Four anomaly classes plus Normal and Uncategorized**, annotated with anomaly *durations*, so labels are time-bounded rather than per-flight: Normal 900 flights (38:24:19) · External Position 197 (05:12:25, of which 01:17:02 anomalous) · Altitude 78 (02:41:21 / 00:25:57) · Mechanical and Electrical 47 (02:12:38 / 00:12:43) · Global Position 41 (01:40:42 / 00:36:23) · Uncategorized 141. 1,396 annotated flights, 52:20:05 total; 3,196 raw. Annotation is "Physically-Constrained Expert Evaluation". | 2026-08-20 |
| C2b | **Is UAV-SEAD usable for H1?** | **No.** Three independent blockers, all from the dataset card: (a) only **04:35:24 of 52:20:05 (8.8%) has global position data** — the rest is indoor, on external/vision position, so there is nothing to join ERA5 *to*; (b) the 81-topic superset schema contains **no wind or airspeed topic at all**, so there is no onboard wind estimate to compare against; (c) the stated limitation is "limited to multi-rotor dynamics, limited outdoor flights with GPS availability". It remains relevant to H2 as an event vocabulary, on a different population. | 2026-08-20 |
| C3 | ALFA licence and citation | **CC-BY-4.0 per the record, CC0 per the data — the two disagree.** The KiltHub/figshare record (CMU, DOI 10.1184/R1/12707963.v1, posted 2020-07-31) carries `license: CC BY 4.0`; the `README.txt` *inside* that record states "Licenses/restrictions placed on the data: CC0". Treat as CC-BY — attribute, and resolve with the authors before relying on the CC0 reading. Citation: Keipour, Mousaei & Scherer, *ALFA: A dataset for UAV fault and anomaly detection*, IJRR, 2020 (dataset citation: Keipour et al. 2020, Carnegie Mellon University, DOI above). | 2026-08-24 |
| C3b | **Is ALFA usable for H1?** | **No — different autopilot, and no ULog.** From the record's own README and the dataset site: a fixed-wing *carbonZ* with a Pixhawk running **ArduPilot 3.9.0beta1**, flown at Pittsburgh, PA, 2018-07-18 to 2018-10-18; 47 processed sequences (66 min nominal, 13 min post-fault) distributed as ROS `.bag`, `.mat` and `.csv`, plus separate dataflash and ground-station telemetry archives. No `.ulg`, and the estimator is ArduPilot's, not PX4 EKF2 — so it cannot enter the corpus and cannot be pooled into an H1 regime. Whether its dataflash carries an EKF wind estimate at all (`NKF2`/`XKF2` `VWN`/`VWE`) is **not established**: it would take reading the 541 MB dataflash archive, which nothing currently justifies. Relevant to H2 as fixed-wing fault vocabulary, on a different population. | 2026-08-24 |
| C4 | BASiC licence; confirm SITL-only | **CC-BY-4.0, and SITL-only confirmed.** The licence is read from the **dataset record itself** — Zenodo 10.5281/zenodo.8195068 (Ahmad & Akram, published 2023-07-30), `license: cc-by-4.0` — not from the Data in Brief article, whose "open access article under the CC BY license" line covers the *paper*. SITL confirmed in the authors' own words: "exclusively derived from simulations conducted in a SITL environment", and "the dataset relies on the ArduPilot platform only". 70 flights, ~7 h, six sensor-failure classes (GPS, RC, accelerometer, gyroscope, compass, barometer). **Consequence:** simulated *and* ArduPilot — it is two steps from the real-flight corpus, and the `PX4_SITL` separation rule applies a fortiori. Never merged, under any label. | 2026-08-24 |
| C5 | ERA5 Copernicus licence version and attribution string | CC-BY, cited by DOI **10.24381/cds.adbb2d47** for ERA5 single levels. Copernicus attribution required in derived artifacts. Registration and an API key are needed for CDS access — not yet obtained. **But ERA5 itself does not require an account:** ARCO-ERA5, a curated copy in Google Cloud Public Datasets (`gcp-public-data-arco-era5`, Zarr, anonymous access), publishes `100m_u_component_of_wind` and `100m_v_component_of_wind` hourly at 0.25° — the primary vertical reference ADR-0006 declares. The data stays under the Copernicus licence (the Apache-2.0 in that repository covers the code); the copy asks to be cited as Carver & Merose, *ARCO-ERA5*, 22nd Conf. on AI for Env. Science, AMS, 2023. The AWS `era5-pds` bucket is **deprecated** — its maintainer redirects to an NSF NCAR rehost — so it is not a route to plan on. | 2026-08-20; access route 2026-08-24 |
| C6 | How is ERA5T identified in the response? | **Yes — in GRIB only.** CDS documents that ERA5 updates daily with ~5 days latency, that the early release is called **ERA5T**, and that it may differ from the final release 2–3 months later. The ERA5 data documentation (ECMWF Confluence, `CKB/ERA5: data documentation`) states that "for GRIB, ERA5T data can be identified by the key expver=0005 in the GRIB header. ERA5 data is identified by the key expver=0001", and that "for netCDF data requests which return just ERA5 or just ERA5T data, there is no means of differentiating between ERA5 and ERA5T data in the resulting netCDF files" — the origin is visible in netCDF *only* when a single response mixes both. **Consequence:** the convenient format cannot support the manifest field, so we retrieve GRIB ([`adr/0008-retrieve-era5-as-grib.md`](adr/0008-retrieve-era5-as-grib.md)). Still to be confirmed against the first real retrieval, which needs the CDS account — but the format decision no longer waits on it. | 2026-08-20, partial; documented 2026-08-24 |
| C7 | Copernicus DEM licence and access | **Free and open, but it is not CC-BY, and it flows down.** Licence read in full: *Licence for Copernicus DEM instance COP-DEM-GLO-30-F Global 30m Full, Free & Open* (PDF, Copernicus Data Space documentation). Art. 4 grants reproduction, distribution, communication to the public and adaptation/combination; Art. 5 free of charge; worldwide and unlimited in time. IPR stays with Airbus DS / DLR — the User receives no IPR title (Art. 9). **Obligations that CC-BY does not impose (Art. 6):** the exact source notice, a *different* notice once the data are adapted, the liability sentence quoted verbatim to subsequent users, a no-endorsement duty, and a duty to bind subsequent users to the same terms. Breach terminates the licence. Exact strings in [`DATA_LICENSES.md`](../DATA_LICENSES.md). **Access needs no credentials:** AWS Open Data, `s3://copernicus-dem-30m` and `s3://copernicus-dem-90m` (eu-central-1, Cloud-Optimized GeoTIFF, `--no-sign-request`); the Copernicus Data Space S3/OData route needs an account. **Note the product is a Digital Surface Model**, 30 m sampling — canopy and buildings included, bare earth not separated. It is not a terrain model and it is not an obstacle map. | 2026-08-24 |
| C8 | METAR archive and terms | **Retrievable; largely not redistributable.** Two archives checked. *IEM* (Iowa State) serves ASOS/AWOS/METAR worldwide, 1900-present, with a documented backend: a **1 s per-IP throttle** (stated 2026-04-21), a **1,000 station-year cap per request** (HTTP 422 above it), 503 under load, and the maintainer's instruction to "make an hourly request for all stations" rather than hammer it. The page states no licence — only "Copyright © 2001-2026 Iowa State University" — and points upstream to NCEI ISD as the authoritative source. *NCEI ISD*'s own readme is explicit: "The non-U.S. data in ISD are subject to WMO Resolution 40 restrictions, and cannot be redistributed to other users or customers." IEM ingests ISD, so the restriction flows through. **Consequence:** METAR may be retrieved and processed locally as a third reference, but per-station observations may be published only for U.S. stations. Whether a derived aggregate over non-U.S. stations counts as redistribution is the same question as B5 and is answered with it — not before. | 2026-08-24 |

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
- **Other sources do not share PX4's terms.** C3–C8 are now answered and two of them
  carry obligations that travel to whoever takes our artifact: the Copernicus DEM's
  prescribed notices and flow-down clause, and WMO Resolution 40 on non-U.S. METAR.
  Release terms are therefore decided per artifact from the sources it used —
  [`adr/0007-licences-travel-with-the-data.md`](adr/0007-licences-travel-with-the-data.md).
