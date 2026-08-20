# ADR-0005 — Sample from the metadata dump; never bulk-download the corpus

- **Status:** accepted
- **Date:** 2026-08-20

## Context

The plan assumed the corpus had to be downloaded before it could be characterised, and
budgeted M2 for an inventory over ~10² logs.

Three things were then observed (recorded in
[`01-source-audit.md`](../01-source-audit.md) and
[`02b-dbinfo-inventory.md`](../02b-dbinfo-inventory.md)):

1. `https://review.px4.io/dbinfo` redirects to a **CDN-hosted, daily-regenerated JSON
   dump of every public log's metadata** — 450,395 records, 26 fields, no downloads
   and no origin traffic.
2. The upstream client documents its own limits: 6 s between requests, a default cap
   of 10 files, a confirmation prompt above 100, and `403`/`444` meaning the IP has
   been blocked. It also notes that bandwidth and storage are funded by the Dronecode
   Foundation.
3. `logs.px4.io/robots.txt` is `Allow: /` followed by `Disallow: /*` — the site asks
   automated clients not to crawl it, whatever the CC-BY licence permits.

At 10 requests/minute, pulling the real-hardware population would take roughly nine
days of continuous requests against a service someone else pays for.

## Decision

Treat the metadata dump as the **sampling frame**, not as a preliminary. Characterise
the population from it, then download only a stratified sample drawn from the ≥ 300 s,
non-SITL tier. Raise bulk retrieval with the maintainers on the record before doing it,
rather than inferring permission from a licence.

## Consequences

- M2's population-level questions are already answered, over the whole corpus rather
  than 10² logs. What remains needs the `.ulg`: field coverage, estimator
  configuration, geography.
- The `.ulg` download budget becomes a deliberate design choice with a stated stratum,
  which is also better statistics than a convenience pull would have been.
- The sampling frame is versioned by retrieval date, since the dump is regenerated
  daily. Each analysis manifest records which day's frame it drew from.
- `robots.txt` is honoured. If the maintainers say bulk retrieval is fine, that
  exchange is cited in the audit and this ADR is superseded.

## Alternatives considered

Downloading first and asking later. It would have been faster to start, would have
imposed real cost on a nonprofit, risks an IP block that ends the project's access
entirely, and would have made the first contact with the PX4 maintainers a complaint.
