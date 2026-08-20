# ADR-0001 — Do not write a ULog converter

- **Status:** accepted
- **Date:** 2026-08-20

## Context

The project needs ULog files in a columnar format to do anything at all. Writing a
converter is the obvious first instinct and the most enjoyable part of the work.

It is also already done. `PX4/flight-review-rs` is official PX4 tooling: a Rust
ULog-to-Parquet converter (ZSTD) built on Auterion's `px4-ulog-rs` with Arrow/Parquet,
covering metadata for all 13 ULog message types, flight analysis (modes, battery, GPS
quality, vibration, parameter diff, GPS track), diagnostic analysers (motor failure,
GPS interference, battery brownout, EKF failure, RC loss), and browser-side querying
via DuckDB-WASM. It ships `ulog-convert`, a standalone CLI for batch conversion over
whole datasets.

## Decision

Use `ulog-convert` for batch conversion. Contribute upstream where extensions are
needed. Write no parser in this repository.

## Consequences

- `ingest/` orchestrates external tooling and contains no parsing logic. This is an
  invariant, checked in review.
- A missing capability becomes an upstream contribution, not a local workaround. This
  is slower per feature and is accepted: it is also the cheapest available route to
  credibility in the PX4 ecosystem, and one of the five V0 success criteria.
- The project takes a dependency on an external tool's release cadence and schema
  stability. Mitigated by pinning the tool version in every `AnalysisManifest`.
- `pyulog` is kept as a parity reference for spot-checking, not as a pipeline
  component.

## Alternatives considered

A Python converter via `pyulog` would be trivially embeddable and hopelessly slow over
10^5 logs. A fork of `flight-review-rs` would remove the upstream coordination cost and
also remove the reason anyone in the ecosystem would care about this project.
