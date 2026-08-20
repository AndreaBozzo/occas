# ADR-0003 — H1 measures agreement, not calibration

- **Status:** accepted
- **Date:** 2026-08-20

## Context

H1 was originally framed as calibrating external context against reality: how well
does ERA5 describe the wind the drone actually experienced? That framing assumes the
onboard estimate is truth.

It is not. The PX4 wind figure is an EKF2 **estimate**, with published
`variance_north` / `variance_east`, produced by a mechanism that differs by platform:
on fixed-wing typically fusion of airspeed and synthetic sideslip; on multicopter,
inference from drag specific forces, which requires correctly calibrated drag
coefficients. ERA5 is a 0.25° hourly reanalysis. Both are uncertain, in different
ways, for different reasons.

## Decision

Frame H1 as an agreement analysis between two uncertain estimates, stratified by
airframe, airspeed sensing, estimator mechanism and parameters, reported EKF variance,
firmware, altitude, topography, season and geography. Use bias and limits of agreement
between measurement methods. Do not regress one on the other as if one were true.

## Consequences

- The scientific object becomes "under which conditions is a reanalysis a good enough
  proxy for the operating context of a UAS?" — harder to answer and far more
  defensible than "ERA5 describes the drone's wind".
- Estimator configuration and uncertainty become first-class data. `EstimatorConfig`
  and `ValidationArtifact` enter the data model, and `context_uncertainty` becomes a
  regime property pointing at a validation artifact rather than a per-row error.
- The deliverable includes the regimes where the reanalysis is **not** a useful proxy.
  Those are results, not failures — see gate G3, outcome C.
- If estimator configuration turns out not to be reconstructible from the logs (M2),
  the study narrows to fixed-wing with airspeed rather than proceeding on an
  assumption.

## Alternatives considered

Treating EKF2 wind as ground truth would make the statistics simpler, the headline
cleaner, and the conclusion unfalsifiable in the wrong direction: every disagreement
would be attributed to ERA5.
