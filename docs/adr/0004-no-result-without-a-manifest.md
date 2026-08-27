# ADR-0004 — No result without a manifest

- **Status:** accepted
- **Date:** 2026-08-20

## Context

The project's only durable claim is reproducibility. A number that cannot be
regenerated is of less value than no number at all, because publishing it invites a
reproduction attempt that will fail. The corpus also depends on sources that move underneath it: ERA5T is superseded
by the final ERA5 product, typically within 2-3 months; `ulog-convert` and PX4 log
schemas change across firmware versions.

## Decision

Every analysis emits an `AnalysisManifest` before it is allowed to emit a result:
input hashes, dependency and external-tool versions, parameters, seeds, source product
IDs and versions, and `retrieved_at` timestamps. A figure or number without a manifest
is not publishable.

## Consequences

- `artifacts/manifests/` is committed; bulk outputs are not.
- CI re-runs the pipeline over fixtures on every commit, so the reproducibility claim
  is tested rather than asserted.
- Exploratory work is still allowed, but nothing exploratory reaches a published
  artifact without being re-run through a manifested script. In practice this means no
  unversioned notebooks.
- Retrieval metadata must be captured at retrieval time. It cannot be reconstructed
  afterwards, and a manifest written later is a manifest that is wrong.

## Alternatives considered

Recording provenance at publication time. It does not work: by then ERA5T may have
been replaced and the tool version is whatever is installed today, not what produced
the numbers.
