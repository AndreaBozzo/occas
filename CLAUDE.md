# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```sh
uv sync --all-extras --group dev   # pinned environment
uv run pytest                      # full suite
uv run pytest tests/test_schema.py -k invalid   # one file / one selection
uv run ruff check . && uv run ruff format .
bash -n ingest/convert.sh          # the shell wrapper is syntax-checked in CI
```

CI (`.github/workflows/ci.yml`) runs lint, format check, shell syntax, the test suite,
and a CRLF check over tracked text files.

## What this project is

A **corpus**, not a platform. It links real PX4 flight telemetry to the external
operating conditions under which it was produced, with provenance and reproducibility
sufficient to be used as evidence. [`docs/00-scope.md`](docs/00-scope.md) is the
operative scope contract and lists the out-of-scope items explicitly.

**H1 is answered.** 1,600 fixed-wing/VTOL logs retrieved and converted, 871 usable,
1,059 windows paired with ERA5: the reanalysis is unbiased against the onboard EKF2
estimate and too imprecise to substitute for it, in every regime tested
([`artifacts/h1-agreement.json`](artifacts/h1-agreement.json), `adr/0015`).

H2 and H3 remain **pre-data**. Their modules are deliberately unwritten and carry a
docstring stating their contract and what blocks them. That is the current state, not
an omission — do not fill them in speculatively. Anything written by looking at real
sources must be written that way, never from recollection.

## Invariants

These are decisions, recorded in [`docs/adr/`](docs/adr/), not preferences. Changing
one means writing an ADR, not editing code.

- **No ULog parser lives here.** Conversion is delegated to `ulog-convert` from
  `PX4/flight-review-rs`; `ingest/` orchestrates external tooling and contains no
  parsing logic. A missing capability becomes an upstream contribution (ADR-0001).
- **Neither wind source is ground truth.** H1 compares ERA5 reanalysis against an EKF2
  *estimate*. Use bias and limits of agreement between measurement methods; never
  regress one on the other, and never treat the onboard estimate as truth (ADR-0003).
- **The ARCO copy is not the authority.** H1 reads ERA5 from ARCO-ERA5 because ~1,200
  windows is more than the free CDS queue should be asked for; the CDS stays the citable
  identity and the marker vocabulary. The copy is on ERA5's native 0-360 longitude grid
  and its release boundary lags the CDS's by about a month, so the recorded ERA5T share
  is a property of the route and the day it ran (ADR-0013).
- **No result without a manifest.** Every analysis emits an `AnalysisManifest` through
  `analysis/common/manifest.py` before it may emit a number. Retrieval and environment
  metadata are captured *at run time* — a manifest written afterwards is wrong
  (ADR-0004).
- **OpenODD is the representation model, not a taxonomy.** Never claim alignment or
  conformance to ISO 34503 for a UAS domain. `schemas/odd_taxonomy.yaml` stays unwritten
  until the M0 prior-art check is recorded in `docs/03-odd-representation.md` — a test
  enforces this (ADR-0002).
- **`PX4_SITL` is a separate control population.** Never merged into the real-flight
  corpus, under any label.
- **Positional results are published only in aggregate.** Raw geolocated trajectories
  are never redistributed, and neither are generalised per-run rows: rounding is
  pseudonymisation, not anonymisation, because the raw log stays public and the row
  joins back to it. Publish statistics over runs — provisionally at least 20 runs and
  10 vehicles per cell, suppressed cells reported with their counts — and publish the
  pipeline instead of the data (ADR-0009,
  [`docs/07-personal-data.md`](docs/07-personal-data.md), [`DATA_LICENSES.md`](DATA_LICENSES.md)).
- **A pooled H1 number is a reweighted one.** The draw is 800/800 across retention
  strata that are 37.1%/62.9% of the frame, and usability differs by stratum (72% vs
  52%), so an unweighted pool puts 58% of its mass on 37% of the population. Strata
  results are primary; pooled ones carry `N_h`, realised `n_h` and the usable rate
  (ADR-0014).
- **Bootstrap by run, never by window.** Windows within a run are not independent.
  The `validation_artifact.json` schema pins `bootstrap.unit` to `run`.

## Architecture

The schemas in [`schemas/`](schemas/) are the real design; the Python is thin.
[`docs/02-data-model.md`](docs/02-data-model.md) explains them.

Two entities exist because of how H1 is framed. `EstimatorConfig` records the onboard
estimator's mechanism, parameters and reported variance — including
`reconstructible: false` when it cannot be recovered, which is itself a finding.
`ValidationArtifact` holds agreement statistics **per regime**. Consequently
`context_uncertainty` on a context feature is a *regime property*: it points at a
`ValidationArtifact` by id and declares which population it applies to, rather than
carrying a per-row error, because there is no ground truth to subtract.

Schemas cross-reference by relative filename and each carries an absolute `$id`;
`analysis/common/schema.py` registers every schema under its `$id`, which is what makes
those references resolve.

Join key: `(run_id, time_interval, geospatial_extent) → external_context(time, location)`.
Every joined row records the join and interpolation method, the declared tolerances
*and* the actual distance-to-grid-point and time mismatch, plus quality flags.

## Working conventions

- Field coverage is recorded, not filtered: a missing field is recorded as missing,
  never a silently dropped run.
- Proxies are named as proxies in code and prose: GNSS geometry is not received
  quality, a DEM is not an obstacle map, an EKF estimate is not a measurement.
- Write an ADR for every non-obvious decision, at the moment it is taken.
  `docs/adr/0000-template.md` is the shape. ADRs are the raw material for public posts.
- Build no tool that does not serve an analysis in progress.
- Negative tests declare where they expect to break (`_error_path` in the invalid
  fixtures) and assert the error lands there — a fixture rejected for an unrelated
  reason would look like coverage it does not provide.
- Fixtures are synthetic and describe no real flight or person, because the licence
  and personal-data questions for real logs are still open.
- A time-box overrun forces a scope reduction or a partial publication, never an
  extension justified by sunk cost.
