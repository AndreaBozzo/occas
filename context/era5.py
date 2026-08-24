"""ERA5 retrieval via the Copernicus CDS API, with cache and provenance.

Contract, once written (M4):

- request by (time interval, bounding box) for the variables H1 needs;
- cache on disk, keyed by request, so an analysis re-run does not re-download;
- read ``expver`` (``0001`` final ERA5, ``0005`` ERA5T) into the manifest at retrieval
  time, and **fail loudly if it is absent** rather than recording nothing. Verified on
  2026-08-24 to be present in both formats -- a GRIB header key, a NetCDF scalar
  coordinate -- with identical values, so format is a preference (GRIB is native)
  rather than the control (docs/adr/0008);
- record ``dataset/product ID``, version and ``retrieved_at`` for every retrieval into
  a ``SourceMetadata`` record. **ERA5T is preliminary** and can be replaced by the
  final product, typically within 2-3 months: which one was used must be recoverable
  from the manifest, or the result is not reproducible;
- carry the Copernicus attribution string into every derived artifact.

Not blocked on a CDS account for development: **ARCO-ERA5** (`gcp-public-data-arco-era5`,
Zarr, anonymous) carries hourly `100m_u/v_component_of_wind` at 0.25°, and marks the
preliminary boundary with a store attribute ``valid_time_stop_era5t`` rather than a
per-message ``expver``. A run against the copy records the store and that attribute;
a run against CDS records ``expver``. Both are recordable; CDS NetCDF is not.

Blocked on: a CDS account, for the authoritative CDS-cited retrieval. C6 is answered
from ECMWF's documentation (the ``expver`` header above) and C5 gives the attribution
string; both still need confirming against the first real retrieval, which is what
the account is for.
"""
