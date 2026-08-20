# Operational Context Corpus for Autonomous Systems

A reproducible corpus linking **real telemetry from autonomous systems** to the
**external operating conditions** under which it was produced — with a queryable
schema, full provenance, and a machine-readable representation of the operational
design domain (ODD).

> Current status: **pre-data**. No log has been downloaded yet. The next artifact
> due is [`docs/01-source-audit.md`](docs/01-source-audit.md), written by looking at
> real files. See [`docs/00-scope.md`](docs/00-scope.md).

## What this is

Observed behaviour of real autonomous systems, turned into **queryable, contextualised
events**, with enough provenance and reproducibility to be used as evidence.

The value of external context is **not predictive** — onboard telemetry already
measures locally and at high rate most of what a reanalysis approximates at tens of
kilometres and hourly steps. The value is:

1. **Stratification** — an anomaly rate is high *relative to what?*
2. **Retrieval and comparability** — find the runs comparable to a given run.
3. **Operational coverage** — which regions of the operating space have been flown.
4. **Evidence** — do declared conditions match encountered ones?

## What this is not

Not an autonomy stack, not a robotics data platform, not a viewer, not a replay
engine, not an edge product, and **not a ULog converter** — conversion is delegated to
[`PX4/flight-review-rs`](https://github.com/PX4/flight-review-rs) (`ulog-convert`).
See [`docs/adr/0001-no-ulog-converter.md`](docs/adr/0001-no-ulog-converter.md).

## First deliverable

> *How well does ERA5 wind agree with onboard PX4 wind estimates across real-world
> flights?*

Neither source is ground truth: ERA5 is a 0.25° hourly reanalysis; PX4 wind is an
EKF2 estimate with published variances. The study is therefore an **agreement
analysis between two uncertain estimates**, stratified by airframe, airspeed sensing,
estimator mechanism and variance, firmware, altitude, topography, season and
geography. A negative result is publishable; a non-reproducible one is not.

## Layout

| Path | Purpose |
|---|---|
| `docs/` | Scope, source audit, data model, ODD representation, methodology, limitations, ADRs |
| `ingest/` | Orchestration of existing tooling. **Contains no parsers.** |
| `context/` | External context sources (ERA5, METAR, DEM) and the spatio-temporal join |
| `events/` | Event extractors and the UAV-SEAD import |
| `analysis/` | One directory per hypothesis; every analysis emits an `AnalysisManifest` |
| `schemas/` | JSON Schema for the data model; ODD taxonomy (only after the M0 prior-art check) |
| `artifacts/` | Manifests and results. **Never raw redistributed logs.** |
| `tests/` | Fixture-based tests, run in CI on every commit |

## Reproducibility contract

No published number or figure without a versioned script and an `AnalysisManifest`
recording input hashes, dependency versions, parameters, seeds and retrieval
timestamps. Pinned environment; no analysis in unversioned notebooks.

## Development

```sh
uv sync --all-extras   # create the pinned environment
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

## Licensing

Code is Apache-2.0 ([`LICENSE`](LICENSE)). Data sources carry their own terms and
attribution requirements — see [`DATA_LICENSES.md`](DATA_LICENSES.md). Derived and
aggregated features are published; raw geolocated trajectories are not.
