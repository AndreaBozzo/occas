# ADR-0008 — Retrieve ERA5 as GRIB: the release marker does not survive NetCDF

- **Status:** accepted
- **Date:** 2026-08-24

## Context

ADR-0004 requires every analysis to record its retrieval in a manifest at run time.
For ERA5 that means recording *which release* was retrieved, because the two are not
the same data: ERA5T is the initial release, published with about five days' latency,
and it may be revised two to three months later when the final ERA5 replaces it. An
analysis run against ERA5T and rerun after the revision can move without a single line
of our code changing. A manifest that cannot say which release it used cannot explain
that, and audit row C6 was left open at M1 precisely because no identifying field had
been found.

ECMWF's ERA5 documentation answers it, and the answer is format-dependent:

- "For GRIB, ERA5T data can be identified by the key `expver=0005` in the GRIB header.
  ERA5 data is identified by the key `expver=0001`."
- "For netCDF data requests which return just ERA5 or just ERA5T data, there is no
  means of differentiating between ERA5 and ERA5T data in the resulting netCDF files."

NetCDF exposes the origin only when a single response happens to straddle the boundary
and contains both. A request landing entirely inside ERA5T — the normal case for any
recent flight — comes back indistinguishable from final data.

NetCDF is the convenient choice: it is what the CDS examples use and what `xarray`
opens without ceremony. It is also the choice that silently destroys the field the
manifest is required to record.

## Decision

Retrieve ERA5 in **GRIB**, and read `expver` from the message header into the manifest
at retrieval time.

## Consequences

- The manifest can state the release per retrieval instead of per intention. Where a
  request straddles the cutover, the mixture is recorded as a mixture.
- A conversion step and a GRIB reader enter the pipeline. This is a real cost and is
  accepted for one reason: without it, C6 is permanently unanswerable and every ERA5
  number carries an unfalsifiable footnote.
- A rerun after a final-release revision becomes a comparison we can actually make —
  same request, two `expver` values, a measurable difference — rather than an anomaly
  someone notices later.
- This binds *CDS* retrieval. The account-free copy, ARCO-ERA5, is Zarr and marks the
  boundary differently — a store attribute `valid_time_stop_era5t`, plus a documented
  monthly job that revalidates ERA5T against final ERA5 and replaces it where they
  differ. That satisfies the same requirement by another means, and a run against the
  copy records the store and the attribute instead of `expver`. What remains forbidden
  is the combination that records nothing: NetCDF from CDS.
- Provisional until the first real retrieval. The documentation says what the header
  carries; only a retrieval proves what arrives. If the header is absent or the
  behaviour has changed, this ADR is superseded by what was observed, not amended
  quietly.

## Alternatives considered

**Retrieve NetCDF and record the request date as a proxy for the release.** The latency
is documented, so the release is *usually* inferable. "Usually inferable" is exactly the
kind of claim this project refuses elsewhere — a proxy named as though it were the
measurement. It also fails at the boundary, which is where it matters.

**Retrieve NetCDF and accept that the release is unrecorded.** This is the honest
version of the previous option and still loses: it would put a permanent "we do not
know which ERA5 this is" beside every H1 number, on a question that a format choice
answers for free.
