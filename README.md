# Operational Context Corpus for Autonomous Systems

A reproducible corpus linking **real telemetry from autonomous systems** to the
**external operating conditions** under which it was produced — with a queryable schema
and full provenance.

A machine-readable representation of the operational design domain is *in scope and not
yet built*: `schemas/odd_taxonomy.yaml` and `ODDAnnotation` do not exist, and
[`adr/0002`](docs/adr/0002-openodd-as-metamodel.md) blocks them until the M0 prior-art
check is recorded in [`docs/03-odd-representation.md`](docs/03-odd-representation.md).

> Current status: **analysis complete, pending release**. A
> stratified draw of 1,600 fixed-wing/VTOL logs has been retrieved and converted, 871 of
> which carry what H1 requires; 1,059 run-hours are paired with ERA5. The finding is
> that **there is no evidence of a systematic component-wise offset between ERA5 and the
> onboard EKF2 wind estimate, and agreement is far too imprecise for ERA5 to substitute
> for it** — limits of agreement near ±5 m s⁻¹ per component against a pre-declared
> 3.0 m s⁻¹ usefulness band, in every regime and at both vertical references. The
> result and what it does not establish are set out in
> [`docs/10-h1-results.md`](docs/10-h1-results.md); the method is
> [`docs/04-methodology.md`](docs/04-methodology.md).
>
> A pre-publication review on 2026-08-27 identified corrections to the pooled weighting
> and to two statistical summaries. All were applied and the analysis regenerated; the
> corrections are recorded as post-hoc in
> [`adr/0016`](docs/adr/0016-pre-publication-corrections.md), which deliberately leaves the
> original pre-specification untouched. No decision threshold moved. The result survives
> reweighting, clustering, grid-distance tolerance, vertical reference and a full
> time-aligned rerun.
>
> Public metadata for all 450,395 logs was characterised before any download — see
> [`docs/02b-dbinfo-inventory.md`](docs/02b-dbinfo-inventory.md). Aggregate publication
> of results is governed by [`docs/09-dpia.md`](docs/09-dpia.md) and
> [`docs/adr/0009-aggregate-only-for-positional-results.md`](docs/adr/0009-aggregate-only-for-positional-results.md);
> raw geolocated trajectories are never redistributed. Scope is fixed in
> [`docs/00-scope.md`](docs/00-scope.md).

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

## First deliverable — answered

> *How well does ERA5 wind agree with onboard PX4 wind estimates across real-world
> flights?*

Neither source is ground truth: ERA5 is a 0.25° hourly reanalysis; PX4 wind is an
EKF2 estimate with published variances. The study is therefore an **agreement
analysis between two uncertain estimates**, stratified by airframe, airspeed sensing,
estimator mechanism and variance, firmware, altitude, topography, season and
geography. A negative result is publishable; a non-reproducible one is not.

**The answer, over 871 runs and 1,059 run-hours:** we find **no evidence of a systematic
component-wise offset** between the reanalysis and the onboard estimate — every component
bias interval includes zero — and agreement is far too imprecise for ERA5 to substitute
for the onboard estimate, with limits of agreement near ±5 m s⁻¹ per component. It is not
a useful proxy in any regime tested, under a criterion fixed before the result existed.

Failing to reject a zero offset is not the same as establishing one, and this result does
not claim equivalence. Five feasible axes or proxies were evaluated — airframe, airspeed
topic, estimator variance band, season and an altitude proxy; firmware, topography and
geography remain uncut, and airspeed sensing, estimator mechanism and altitude AGL are
represented only by the proxies available. Full write-up, sensitivity analyses and limits:
[`docs/10-h1-results.md`](docs/10-h1-results.md).

## Layout

| Path | Purpose |
|---|---|
| `docs/` | Scope, source audit, corpus inventory, data model, ODD representation, methodology, limitations, ADRs |
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

## Contributing, privacy and reporting

[`CONTRIBUTING.md`](CONTRIBUTING.md) states the invariants a change must not break and
how to run what CI runs. [`PRIVACY.md`](PRIVACY.md) sets out the lawful basis, your
rights and how to object to the use of your flight data — objecting is enough, and no
reason is required. [`SECURITY.md`](SECURITY.md) is the private channel for anything
that should not be reported in a public issue.

## Citation

[`CITATION.cff`](CITATION.cff). Every published number carries an `AnalysisManifest` in
[`artifacts/manifests/`](artifacts/manifests/); cite the manifest id alongside the
figure so the claim can be checked against the state that produced it.
