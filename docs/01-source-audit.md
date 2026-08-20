# 01 — Source & legal audit (M1)

**Status: NOT STARTED. This file contains questions, not findings.**

Every row below is answered by looking at the source itself — the terms of service,
the licence file on the repository, the response headers of the download endpoint, or
the files on disk. Nothing here may be filled in from recollection or from a project
brief. Each answer records *where it was checked* and *when*.

Gate G1 depends on this file. Until a row is answered, nothing derived from that
source may be published.

## A. PX4 Flight Review — access

| # | Question | Where to check | Answer | Checked on |
|---|---|---|---|---|
| A1 | What are the terms of service for `logs.px4.io`? | The site's ToS / footer; `PX4/flight_review` repository | TBD | — |
| A2 | Is there a documented or de-facto rate limit on the download endpoint? | Response headers; `download_logs.py`; ask on discuss.px4.io | TBD | — |
| A3 | Does `download_logs.py` still work as documented, and which filters does it actually expose? | Run it | TBD | — |
| A4 | Is the CC-BY attribution requirement stated per-log or corpus-wide? | Site metadata; per-log record | TBD | — |
| A5 | Does any log carry a non-default licence or a private/unlisted flag? | Log metadata fields | TBD | — |

## B. Personal data (GDPR)

CC-BY is a copyright licence and says nothing about data protection. These are
separate questions.

| # | Question | Answer | Checked on |
|---|---|---|---|
| B1 | Which fields in a public ULog could identify a natural person, directly or indirectly? (takeoff/landing coordinates, home position, operator-set vehicle name, GCS identifiers, timestamps) | TBD | — |
| B2 | What does the upload flow tell uploaders about publication and re-use? | TBD | — |
| B3 | Which lawful basis, if any, would apply to processing derived features? | TBD | — |
| B4 | What coordinate generalisation is sufficient in published artifacts, and how is it justified? | TBD | — |
| B5 | Does publishing *aggregate* features over these logs change the analysis versus publishing per-run features? | TBD | — |

Standing policy until B1–B5 are answered: publish derived and aggregate features
only, generalise coordinates, publish the pipeline rather than the data.

## C. Other datasets

| # | Question | Answer | Checked on |
|---|---|---|---|
| C1 | UAV-SEAD: what licence is on the HuggingFace repository, and does it permit derived publication? | TBD | — |
| C2 | UAV-SEAD: what exactly do the four anomaly classes annotate, and at what temporal resolution? | TBD | — |
| C3 | ALFA: licence and citation requirement | TBD | — |
| C4 | BASiC: licence; confirm it is SITL-only | TBD | — |
| C5 | ERA5: which Copernicus licence version applies, and what attribution string does it require? | TBD | — |
| C6 | ERA5 vs ERA5T: how is the preliminary product identified in the response, so a manifest can record it? | TBD | — |
| C7 | Copernicus DEM: licence and access route | TBD | — |
| C8 | METAR: which archive, under which terms? | TBD | — |

## D. Standards

| # | Question | Answer | Checked on |
|---|---|---|---|
| D1 | Is BSI PAS 1883:2020 withdrawn? If so, when and superseded by what? | TBD | — |
| D2 | Which ASAM OpenODD version is current, and what are its licence terms for producing a taxonomy expressed in it? | TBD | — |

## E. Conclusion

To be written when A–D are answered. Must state explicitly:

- what may be downloaded, and at what rate;
- what may be processed;
- what may be published, and in what form;
- which G1 fallback applies if any of the above is negative.
