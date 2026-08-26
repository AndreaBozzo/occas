# ADR-0013 — H1 reads ERA5 from the account-free copy

- **Status:** accepted
- **Date:** 2026-08-26
- **Extends:** [`0008-record-the-era5-release-marker.md`](0008-record-the-era5-release-marker.md),
  which already anticipated this route and said what evidence it would have to produce.

## Context

The pilot joined 42 windows to ERA5 through the Copernicus CDS, one request per distinct
`(date, hour, grid cell)`. H1 proper runs on the 1,600-log draw: roughly 1,000 usable
runs, and on the pilot's rate of about 1.2 windows per usable run, on the order of 1,200
requests. The CDS is a free, queued, account-gated service. Twelve hundred requests is
past what it should be asked for by one unfunded study, and the request count grows with
every future re-run — including the re-retrieval ADR-0008 already commits us to when
ERA5T is replaced.

`context/era5.py` has documented the alternative since it was written: **ARCO-ERA5**, a
curated copy of ERA5 in Google Cloud Public Datasets, Zarr, read anonymously, no quota
and no account (audit row C5). It was deliberately left unwritten because no analysis
needed it. One does now.

The copy is not the authority, and the difference is not cosmetic:

- It marks the ERA5T boundary with **store attributes** — `valid_time_start`,
  `valid_time_stop`, `valid_time_stop_era5t` — not with a per-field `expver`.
- Those attributes **move**, and they move on a different schedule from the CDS's.
- It is on ERA5's native grid: latitude descending 90 → −90, longitude **0 → 359.75**,
  where the CDS route works in −180…180.

That last one is the dangerous one. A position at longitude −122.3 asked of this store
without conversion does not fail: `method="nearest"` clamps to longitude 0.0 and returns
a perfectly plausible wind speed from the Gulf of Guinea. Four of the pilot's 42 windows
are at negative longitudes.

## Decision

**H1 reads ERA5 through ARCO-ERA5; the CDS remains the authoritative route and the
citable identity of the product.** Both live in `context/era5.py`, produce the same
release-marker vocabulary, and record which one produced a given row. The copy's
`valid_time_stop*` attributes are read at run time, never assumed, and travel into the
manifest alongside the marker they produced.

The decision was taken on measurement, not on the copy's reputation. All 42 pilot
windows, already retrieved through the CDS, were re-read through ARCO
(`artifacts/era5-route-comparison.json`, 2026-08-26):

| Check | Result |
|---|---|
| Grid cell selected | **Identical, 42/42** — distance-to-grid-point differs by 0.000e+00 km |
| 100 m u/v, 10 m u/v | Agree to **≤ 6.2e-4 m s⁻¹** (median 1.5e-4) across all 168 values |
| Release marker | **41/42 agree** |
| ERA5T share | **6/42 via the CDS, 7/42 via ARCO** |

The residual on the values is GRIB packing surviving two different conversions to two
different formats. It is four orders of magnitude below the EKF2-versus-ERA5
disagreement H1 exists to measure, and it is recorded rather than dismissed.

## Consequences

**The one disagreement is the finding, not the noise.** Window `2026-05-07T10:00Z` was
final ERA5 to the CDS on 2026-08-25 and is ERA5T here, because this copy's
`valid_time_stop` is still 2026-04-30 — it lags the authority by about a month. So:

- **The ERA5T share is a property of the route and the day, not of the corpus.** Any
  published H1 result states which route produced it and what its boundaries were on the
  day it ran. A share quoted without those is not reproducible.
- The obligation ADR-0008 created — re-retrieve the ERA5T windows or report the share —
  is now *executable*: `analysis/h1_agreement/compare_era5_routes.py` re-reads them and
  says which moved and by how much.

**What becomes easier.** H1 stops depending on a queue, and on an account whose licence
acceptance is per-dataset and revocable. Reruns cost bandwidth instead of goodwill.

**What becomes harder.** One point read pulls one whole global field per variable — the
store is chunked `[1, 721, 1440]`, about 4 MB per variable-hour, so a window costs
roughly 16 MB regardless of how little of the planet it wanted. Around 1,200 windows is
of the order of 20 GB. The route is cheap in requests and expensive in bytes, which is
the right way round for a public bucket and the wrong way round for a laptop tether.

**What is now forbidden.** Reading the store without checking coverage first. Its `time`
axis runs 1900 → 2050 while its data runs 1940 → a few days ago; an hour outside that
range does not raise, it returns a fill value. `OutsideStoreCoverage` is fatal for the
same reason a missing `expver` is.

## Alternatives considered

**Stay on the CDS and accept the queue.** Defensible for 42 windows, not for 1,200, and
it makes every future re-run a fresh imposition. It also leaves the study one licence
re-acceptance away from being unable to reproduce itself.

**Use the copy and drop the CDS.** Cheaper to maintain, and wrong. The DOI, the licence
revision and the `expver` semantics are the authority's; the copy asks to be cited as a
copy. Keeping both means the marker vocabulary has a source of truth, and it is what made
the cross-check above possible at all.

**Trust the store attributes without checking them against the CDS.** That is the
recollection-shaped failure this project keeps finding: the attribute name was known from
documentation, its *semantics* — inclusive of the boundary day, and lagging the
authority — were not, and only reading 42 real windows through both routes established
them.
