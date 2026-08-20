# Artifacts

Manifests and results. **Never raw redistributed logs, never raw geolocated
trajectories.**

- `manifests/` — one `AnalysisManifest` per analysis run, committed. Every published
  number traces back to one of these. See
  [`../docs/adr/0004-no-result-without-a-manifest.md`](../docs/adr/0004-no-result-without-a-manifest.md).
- Bulk outputs (`*.parquet`, `*.csv`) are gitignored: they are regenerated from the
  pipeline, and the manifest is what makes that possible.

Published artifacts carry the attribution required by their sources — see
[`../DATA_LICENSES.md`](../DATA_LICENSES.md) — and generalised coordinates.
