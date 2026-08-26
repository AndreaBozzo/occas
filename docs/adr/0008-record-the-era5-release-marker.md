# ADR-0008 — Record the ERA5 release marker; do not trust a format to carry it

- **Status:** accepted
- **Date:** 2026-08-24
- **Supersedes:** the first version of this ADR, taken earlier the same day, which
  required GRIB on documentation that the first real retrieval disproved.

## Context

ADR-0004 requires every analysis to record its retrieval in a manifest at run time. For
ERA5 that means recording *which release* was retrieved: ERA5T is the initial release,
published with about five days' latency, and it may be revised two to three months
later when the final ERA5 replaces it. An analysis run against ERA5T and rerun after
the revision can move without a line of our code changing.

**What ECMWF's documentation says.** The ERA5 data documentation states that "for GRIB,
ERA5T data can be identified by the key `expver=0005` in the GRIB header. ERA5 data is
identified by the key `expver=0001`", and that "for netCDF data requests which return
just ERA5 or just ERA5T data, there is no means of differentiating between ERA5 and
ERA5T data in the resulting netCDF files". On that basis this ADR originally fixed the
retrieval format to GRIB.

**What the service actually returns.** Two pairs of retrievals on 2026-08-24, the same
tiny request in both formats (`reanalysis-era5-single-levels`, 100 m u/v, 12:00,
area 45.6/9.0/45.4/9.3):

| date | GRIB | NetCDF |
|---|---|---|
| 2026-08-16 | `expver=0005` in the header | `expver` scalar coordinate = `0005` |
| 2026-01-15 | `expver=0001` in the header | `expver` scalar coordinate = `0001` |

The NetCDF values are identical to the GRIB ones, and the marker discriminates in both
formats. The CDS builds its NetCDF by converting the GRIB — the file's own `history`
attribute records "GRIB to CDM+CF via cfgrib-0.9.15.1/ecCodes-2.48.0" — and that
conversion now preserves `expver`. The documentation has not caught up.

So the premise was wrong, and a decision resting on it cannot stand just because it was
convenient to have made. But the lesson is not simply "NetCDF is fine". The marker
survives NetCDF today because of a conversion step with a version number in it; the
documentation describing that step is already wrong in the safe direction. What must not
happen is a retrieval that silently produces no marker at all.

## Decision

**The retrieval records the release marker, and fails loudly if it is absent.** The
manifest carries `expver` as retrieved; a retrieval that cannot produce one is an error,
not a warning, and not a field left null. Format is a preference, not the control:
prefer GRIB, where the marker is native and no conversion sits between us and it.

## Consequences

- The invariant is now about the *marker*, which is what the manifest needs, rather than
  about a format that happens to carry it. If a future CDS release drops `expver` from
  NetCDF again, the pipeline stops instead of quietly recording nothing.
- NetCDF is permitted, so `xarray` can be used directly without a GRIB reader in the
  dependency set. `eccodes` stays out of `pyproject.toml` until something needs it.
- The check is cheap and belongs in the retrieval path, not in a later validation step:
  by the time an analysis reads the file, the failure would have to be attributed
  backwards.
- ARCO-ERA5, the account-free copy, marks the boundary differently — a store attribute
  `valid_time_stop_era5t`, plus a documented monthly job that revalidates ERA5T against
  final ERA5. A run against the copy records the store and that attribute. Same
  requirement, different evidence, both recordable. **Built and measured on 2026-08-26**
  ([`0013`](0013-h1-reads-era5-from-the-account-free-copy.md)), which turned up something
  this bullet did not anticipate: the copy's boundary *lags* the authority's by about a
  month, so the two routes assign different markers to the same window and the ERA5T
  share depends on which one produced it. The requirement stands; what it identifies is
  the release *as served by a named route on a named day*, not a property of the window.
- Audit row C6 is closed by observation rather than by documentation, and says so.

## Alternatives considered

**Keep the GRIB requirement anyway** — it is still the native carrier, and the rule was
already written. Making the pipeline harder to work with, on a premise now known to be
false, to avoid revising a decision taken hours earlier is sunk cost dressed as rigour.

**Trust NetCDF and drop the check** — the marker is there today, so assert nothing. This
fails the way that costs most: silently, months later, when a rerun disagrees with a
published number and nothing in the manifest can say whether the data changed underneath
it.

**Record the request date and infer the release from the documented latency.** A proxy
named as though it were the measurement, which this project refuses elsewhere. It also
fails precisely at the cutover, which is the only place it matters.
