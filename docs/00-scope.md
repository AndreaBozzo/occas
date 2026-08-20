# 00 — Scope

Derived from project brief v0.3.1 (August 2026). This file is the operative scope
contract; where it and the brief disagree, this file wins and the brief is patched
with a date and a reason.

## Thesis

Turn observed behaviour of real autonomous systems into **queryable, contextualised
events**, with provenance and reproducibility sufficient to be used as evidence.

## In scope

- A reproducible pipeline from public PX4 ULog files to contextualised features.
- Spatio-temporal joins between flight logs and external context (ERA5 first, DEM and
  METAR later), with explicit tolerances and quality flags.
- A machine-readable representation of the operating space, expressed in the ASAM
  OpenODD model.
- Agreement statistics between external context and onboard estimates, stratified by
  regime.
- Manifests, schemas and published coverage.

## Out of scope

- An autonomy stack, a robotics data platform, a viewer, a replay engine, an edge
  product.
- **A ULog converter** — see [`adr/0001-no-ulog-converter.md`](adr/0001-no-ulog-converter.md).
- Event search and curation as a product surface (occupied territory).
- An event ontology built from scratch (start from UAV-SEAD and the diagnostic
  analysers already in `flight-review-rs`).
- A new data format.
- Claims of conformance or alignment to ISO 34503 for a UAS domain.
- LLM agents that "explain the logs" before deterministic evidence exists.

## Hypotheses

| ID | Statement | Status |
|---|---|---|
| **H1** *(primary)* | Under which vehicle, estimator and operational conditions does ERA5 wind show useful agreement with onboard PX4 wind estimates? | Active — first deliverable |
| **H2** | Conditioning on context makes event rates across populations more comparable. Metric: between-group variance reduction, not AUC. | After M5 |
| **H3** | The corpus can measure which regions of the operating space are covered, and how densely. Deliverable: a coverage matrix, not a model. | After M5 |
| **H4** | Robust condition–event associations can inform data-retention policy. | Deferred; only after H1–H3 and only with a demonstrated advantage |

**Neither wind source is ground truth.** H1 is an agreement analysis between two
uncertain estimates. See [`04-methodology.md`](04-methodology.md).

## Milestones and time-boxes

| # | Milestone | Budget | Output |
|---|---|---|---|
| M0 | Practitioner check | 3 days | discuss.px4.io thread; contact UAV-SEAD authors; UAS ODD prior art (JARUS/ASTM/EASA); informal survey on the usefulness of ODD evidence for SORA |
| M1 | Source & legal audit | 1 week | [`01-source-audit.md`](01-source-audit.md) |
| M2 | Sample audit | 1 week | Inventory over ~10² logs: coverage, firmware, geography, SITL ratio, estimator configuration and uncertainty |
| M3 | Conversion pipeline | 1 week | Batch via `ulog-convert`, stable schema, manifests |
| M4 | ERA5 join + agreement (H1) | 3 weeks | Stratified study; METAR third source if the budget allows |
| M5 | Publication | 1 week | Post + repo + artifacts |
| M6 | Decision | — | Gates below |

Then, and only then: DEM → coverage (H3) → stratification (H2) → upstream
contribution to `flight-review-rs` → GNSS.

### Time-box rule

Overrunning a time-box forces a **scope reduction or a partial publication**. An
extension must be justified by new evidence, never by sunk cost.

**Outer limit:** if M4 is not complete by week 10, publish whatever exists — even just
M1–M3 as a source audit of the public PX4 corpus. That alone is a useful contribution.

## Decision gates

| Gate | GO condition | If NO |
|---|---|---|
| G0 — Relevance | The community confirms the question is open | Reformulate or stop; cost is 3 days |
| G1 — Legal | Access, processing and publication of derivatives are compatible | Fallback: pipeline + analysis, no dataset |
| G2 — Feasibility | Usable-run rate is sufficient, with readable estimator configuration | Change source or narrow scope |
| G3 — Agreement (H1) | Agreement and disagreement regimes identified and interpretable | Publish anyway: knowing *where* the reanalysis is useless is a result |
| G4 — Coverage (H3) | The coverage matrix is informative | Narrow to a single operational domain |
| G5 — Perceived value | Practitioners or operators confirm the artifact is useful | Stop the product trajectory, keep the OSS |

Three legitimate outcomes at G3: good agreement over wide regimes (extend context,
proceed to H3); conditional agreement (narrow to the regimes where it holds); poor
agreement everywhere (publish — the field needs to know).

## Definition of success for V0

1. A public **source audit** of the public PX4 corpus, with licences and coverage.
2. A **reproducible pipeline** from raw log to contextualised features.
3. A **representation of the operating space** reusable by others.
4. A **quantitative agreement result**, positive or negative.
5. At least one **substantial upstream contribution proposed** to the PX4 ecosystem,
   with maintainer feedback. A merge is preferable but is not under our control.

None of the five requires hardware, a fleet, or a permission.

## Closing rule

No further revision of the brief before data exists. The next project artifact is
[`01-source-audit.md`](01-source-audit.md), written by looking at real files.
