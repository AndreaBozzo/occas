# Contributing

This is a **corpus**, not a platform. [`docs/00-scope.md`](docs/00-scope.md) is the
operative scope contract and lists the out-of-scope items explicitly. A contribution
that widens the scope needs the scope document changed first.

## Before opening a pull request

Run what CI runs:

```sh
uv sync --all-extras --group dev
uv run ruff check . && uv run ruff format --check .
bash -n ingest/convert.sh
uv run pytest
```

CI additionally rejects CRLF in tracked text files. The repository is `* text=auto
eol=lf`; on Windows, write files with `newline="\n"` explicitly, because
`Path.write_text` translates and a hash recorded over the translated bytes reproduces
for nobody.

## Invariants

These are decisions recorded in [`docs/adr/`](docs/adr/), not preferences. Changing one
means writing an ADR, not editing code around it.

- **No ULog parser lives here.** Conversion is delegated to `ulog-convert` from
  `PX4/flight-review-rs`. A missing capability becomes an upstream contribution
  ([ADR-0001](docs/adr/0001-no-ulog-converter.md)).
- **No result without a manifest.** Every analysis emits an `AnalysisManifest` through
  `analysis/common/manifest.py` before it may emit a number, and it is built *before*
  the outputs it describes ([ADR-0004](docs/adr/0004-no-result-without-a-manifest.md),
  [ADR-0010](docs/adr/0010-manifests-are-verified-against-the-repository.md)).
- **Neither wind source is ground truth.** H1 compares a reanalysis against an onboard
  *estimate*. Do not regress one on the other
  ([ADR-0003](docs/adr/0003-h1-is-agreement-not-calibration.md)).
- **Positional results are published only in aggregate**, at no fewer than 20 runs and
  10 distinct vehicles per cell, with suppressed cells reported alongside their counts
  ([ADR-0009](docs/adr/0009-aggregate-only-for-positional-results.md)).
- **Proxies are named as proxies**, in code and in prose. GNSS geometry is not received
  signal quality; a DEM is not an obstacle map; an EKF estimate is not a measurement.

## Analysis parameters

Any threshold that could be chosen to suit a result — a cutoff, a band, a tolerance —
belongs in an ADR and in the manifest, fixed before the result exists. See
[ADR-0015](docs/adr/0015-what-makes-the-reanalysis-a-useful-proxy.md) for the shape this
takes. A parameter moved after a number has been seen requires a superseding ADR
recording the previous value.

## Tests

A test that has never failed against the unfixed code is not a regression test. Revert
the fix, confirm the test fails, then restore it. Negative fixtures declare where they
expect to break (`_error_path`) and the test asserts the error lands there, so that a
fixture rejected for an unrelated reason is not mistaken for coverage.

Fixtures are synthetic and describe no real flight or person.

## Data and privacy

Do not attach log files, coordinates, `vehicle_uuid` values or any other operator data
to an issue or a pull request.

If you are an uploader and would rather your flights were not used, this is not an issue
to open — write to the address in [`PRIVACY.md`](PRIVACY.md). Objecting is enough and no
reason is required; the logs are removed and added to a permanent exclusion list so that
later runs do not re-include them.

## Reporting a problem with a published number

Provide the `manifest_id` from `artifacts/manifests/` alongside the figure. Every
published number traces to one, and without it the claim cannot be checked against the
state that produced it.
