# ADR-0015 — What makes the reanalysis a useful proxy, and where direction is undefined

- **Status:** accepted
- **Date:** 2026-08-27
- **Extends:** [`0003-h1-is-agreement-not-calibration.md`](0003-h1-is-agreement-not-calibration.md)
  and [`0006-what-h1-compares.md`](0006-what-h1-compares.md), which between them made
  these two parameters mandatory and named neither.

## Context

ADR-0006 fixed the estimand's shape before any outcome could be seen, and left two
numbers inside it unset. Both are of exactly the kind that ADR was written to close.

**The direction cutoff was promised, not chosen.** ADR-0006 requires directional
difference to be reported "only for windows where **both** sources report speed above a
declared threshold" and specifies that "the threshold is a manifest parameter, not a
constant buried in code". It then names no value, and neither does
[`04-methodology.md`](../04-methodology.md). A parameter with no declared value is not a
parameter; it is a free choice deferred to whoever first runs the analysis, and it moves
the direction result.

**"Useful proxy" was never defined at all.** `validation_artifact.json` carries a
`useful_proxy` boolean documented as "against a threshold stated in the manifest", and
ADR-0003 makes "the regimes where the reanalysis is **not** a useful proxy" the
deliverable rather than a caveat. No document in this repository states the threshold.
The deliverable is a boolean whose predicate does not exist.

Both are fixed here, on 2026-08-27, while `build_pairs` is being run over the 871 usable
runs and **no agreement statistic has been computed from any of them** — the same
condition ADR-0014 was written under, and for the same reason.

A third thing was found while writing this down, which is why it is recorded here rather
than only in a commit message. `context/align.py` averaged the estimator's
`variance_north` and `variance_east` into one scalar per window. The criterion below
compares a component-wise limit of agreement against the estimator's own sigma, and an
isotropic sigma cannot answer a component-wise question. It is also ADR-0006's own error
one level down: collapsing a vector quantity into a scalar and then making the stronger
claim. The two are now carried separately, and the first run measured after the change
reports 0.048 against 0.087 m²s⁻² — anisotropic by 1.8×, so the average was discarding
signal, not noise.

## Decision

**Direction is undefined below 2.0 m s⁻¹, and the cutoff is swept.** `speed_threshold_ms`
is **2.0** in the manifest and is the primary result. The direction statistic is also
computed at **1.0** and **3.0** and reported as a sensitivity table, on the same principle
[`04-methodology.md`](../04-methodology.md) already applies to the join tolerances: if the
result moves under plausible choices of the cutoff, that movement is the finding. `n_defined`
and `n_undefined` are reported at every threshold, never only at the primary one.

**The reanalysis is a useful proxy in a regime when the upper 95% limit of agreement on
the vector difference magnitude is at most 3.0 m s⁻¹.** This is the `useful_proxy`
boolean, and `3.0` is a manifest parameter.

The band is **asserted, not cited.** Manufacturer-declared wind limits for small UAS
commonly sit around 10–12 m s⁻¹; a proxy carrying 3 m s⁻¹ of disagreement still leaves a
usable margin when checking a flight against a 10 m s⁻¹ limit, and one carrying 5 m s⁻¹
does not. That reasoning sizes the number. It is not a regulatory threshold, no standard
states it, and it must be labelled an assertion wherever it is published.

**Beside the boolean, and never instead of it, the estimator-relative ratio is reported
per component:** the limit-of-agreement half-width on `u` and on `v` divided by the mean
onboard sigma on the same component. This makes neither source ground truth, which is
ADR-0003's commitment, and it uses a quantity the 871-run inventory showed is universally
available — every run carrying a wind topic also reports its variance, at a rate of 1.0.

A regime can pass one and fail the other. **That disagreement is a reported result**, in
the same way ADR-0014 makes the gap between the pooled and reweighted numbers a result:
a regime inside 3 m s⁻¹ but far outside the estimator's own stated uncertainty means the
two sources disagree by more than either admits to, and a regime outside 3 m s⁻¹ but
inside the estimator's sigma means the onboard estimate is too uncertain for the
comparison to bite.

## Consequences

- H1 reports three things per regime where a reader expects one boolean: the absolute
  verdict, the estimator-relative ratio per component, and whether they agree.
- The 3.0 m s⁻¹ band has to travel with every published verdict as an assertion with its
  reasoning, not as a bare number. [`06-limitations.md`](../06-limitations.md) carries it.
- The direction sweep triples the direction rows and makes `n_undefined` a headline
  quantity rather than a footnote — which ADR-0006 already anticipated for a corpus with
  18,348 uploader-declared *Calm* flights.
- The estimator-relative ratio is only as good as EKF2's own variance reporting, which is
  a filter's self-assessment and not an independent one. It is a second view, not a
  second truth.
- **Now forbidden:** moving `3.0` or `2.0` after seeing an agreement statistic without a
  superseding ADR that says what the number was before; reporting `useful_proxy` without
  both thresholds in the manifest; reporting the boolean without the ratio beside it.
- The pairs row changed shape. `onboard_variance` is replaced by `onboard_variance_u` and
  `onboard_variance_v`; `data/pilot-pairs.jsonl` predates the change and does not carry
  them.

## Alternatives considered

**A purely statistical criterion, with no operational anchor** — for instance limits of
agreement within twice the estimator's sigma and nothing else. Cleaner to defend, and it
passes trivially in exactly the regimes where EKF2 is least certain, which are the regimes
a reader most wants a verdict on. Retained as the secondary ratio rather than as the
verdict.

**No boolean at all**, publishing limits of agreement and letting readers apply their own
threshold. The most defensible position available and the one ADR-0014 already rejected in
another guise: readers infer the missing figure anyway, and a deliverable that ADR-0003
defines as "the regimes where it is not a useful proxy" cannot be delivered as `null`
everywhere.

**A lower cutoff for direction, 1.5 m s⁻¹, tied to METAR's 3-knot calm reporting.**
Citable rather than chosen, which is genuinely better, and it buys the citation by
importing a threshold set for reporting surface observations to pilots — a different
purpose at a different height. Kept in the sweep instead, where its effect is visible.
