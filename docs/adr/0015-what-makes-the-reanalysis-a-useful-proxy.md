# ADR-0015 — What makes the reanalysis a useful proxy, and where direction is undefined

- **Status:** accepted
- **Date:** 2026-08-27
- **Extends:** [`0003-h1-is-agreement-not-calibration.md`](0003-h1-is-agreement-not-calibration.md)
  and [`0006-what-h1-compares.md`](0006-what-h1-compares.md), which together made these
  two parameters mandatory without assigning values to either.

## Context

ADR-0006 fixed the shape of the estimand before any outcome could be inspected, and left
two quantities inside it unspecified. Both are of the kind that ADR was written to
constrain: they can be selected after the fact in whichever direction produces a more
favourable result.

**The direction cutoff was required but not chosen.** ADR-0006 states that directional
difference is reported "only for windows where **both** sources report speed above a
declared threshold", and that "the threshold is a manifest parameter, not a constant
buried in code". It assigns no value, and neither does
[`04-methodology.md`](../04-methodology.md). A parameter without a declared value is a
free choice deferred to whoever first executes the analysis, and its selection changes the
directional result.

**No definition of "useful proxy" exists.** `validation_artifact.json` carries a
`useful_proxy` boolean documented as being evaluated "against a threshold stated in the
manifest", and ADR-0003 identifies "the regimes where the reanalysis is **not** a useful
proxy" as the deliverable rather than as a caveat. No document in this repository states
that threshold. The deliverable is therefore a boolean whose predicate is undefined.

Both are fixed here, on 2026-08-27, while `build_pairs` is executing over the 871 usable
runs and **no agreement statistic has been computed from any of them** — the same
condition under which ADR-0014 was written, and for the same reason.

A third issue was identified while recording this decision, which is why it is documented
here rather than only in a commit message. `context/align.py` averaged the estimator's
`variance_north` and `variance_east` into a single scalar per window. The criterion below
compares a component-wise limit of agreement against the estimator's own standard
deviation, and an isotropic value cannot address a component-wise question. It is also the
same category of error ADR-0006 identifies at the level of the estimand: a vector quantity
collapsed to a scalar, then used to support the stronger claim. The two variances are now
carried separately. The first run measured after the change reports 0.048 against
0.087 m²s⁻², an anisotropy of 1.8×, indicating that the average was discarding signal
rather than noise.

## Decision

**Direction is undefined below 2.0 m s⁻¹, and the cutoff is swept.**
`speed_threshold_ms` is **2.0** in the manifest and defines the primary result. The
directional statistic is additionally computed at **1.0** and **3.0** and reported as a
sensitivity table, on the principle [`04-methodology.md`](../04-methodology.md) already
applies to the join tolerances: if a result moves under plausible choices of the cutoff,
that movement is itself a finding. `n_defined` and `n_undefined` are reported at every
threshold, not only at the primary one.

**The reanalysis is a useful proxy in a regime when the upper 95% limit of agreement on
the vector difference magnitude is at most 3.0 m s⁻¹.** This defines the `useful_proxy`
boolean, and `3.0` is a manifest parameter.

The band is **asserted rather than cited.** Manufacturer-declared wind limits for small
uncrewed aircraft commonly fall near 10–12 m s⁻¹. A proxy carrying 3 m s⁻¹ of disagreement
retains a usable margin when a flight is checked against a 10 m s⁻¹ limit; one carrying
5 m s⁻¹ does not. That reasoning determines the magnitude of the threshold. It is not a
regulatory value, no standard specifies it, and it is to be identified as an assertion
wherever it is published.

**The estimator-relative ratio is reported alongside the boolean, and not in place of
it**, per component: the limit-of-agreement half-width on `u` and on `v` divided by the
mean onboard standard deviation for the same component. This treats neither source as
ground truth, consistent with ADR-0003, and uses a quantity the 871-run inventory
established is universally available — every run carrying a wind topic also reports its
variance, at a rate of 1.0.

A regime may satisfy one criterion and fail the other. **That disagreement is reported as
a result**, in the same way ADR-0014 treats the difference between the pooled and
reweighted estimates: a regime within 3 m s⁻¹ but well outside the estimator's stated
uncertainty indicates that the two sources disagree by more than either reports, while a
regime outside 3 m s⁻¹ but within the estimator's standard deviation indicates that the
onboard estimate is too uncertain for the comparison to be informative.

## Consequences

- H1 reports three quantities per regime where a reader may expect one boolean: the
  absolute verdict, the estimator-relative ratio per component, and whether the two agree.
- The 3.0 m s⁻¹ band must accompany every published verdict as an assertion with its
  reasoning, rather than as a bare figure. [`06-limitations.md`](../06-limitations.md)
  records it.
- The direction sweep triples the number of directional rows and makes `n_undefined` a
  primary reported quantity rather than a footnote, which ADR-0006 anticipated for a
  corpus containing 18,348 uploader-declared *Calm* flights.
- The estimator-relative ratio is bounded by the quality of EKF2's own variance reporting,
  which is a filter's self-assessment rather than an independent measurement. It
  constitutes a second view of the disagreement, not a second reference.
- **Now forbidden:** altering `3.0` or `2.0` after an agreement statistic has been
  inspected, without a superseding ADR recording the prior value; reporting `useful_proxy`
  without both thresholds in the manifest; reporting the boolean without the accompanying
  ratio.
- The pairs row changes shape. `onboard_variance` is replaced by `onboard_variance_u` and
  `onboard_variance_v`. `data/pilot-pairs.jsonl` predates the change and does not carry
  them.

## Alternatives considered

**A purely statistical criterion with no operational anchor**, for example limits of
agreement within twice the estimator's standard deviation and nothing further. This is
simpler to defend, and it is satisfied most easily in precisely those regimes where EKF2
is least certain — the regimes for which a reader most needs a verdict. Retained as the
secondary ratio rather than as the verdict.

**No boolean at all**, publishing limits of agreement and leaving readers to apply their
own threshold. This is the most defensible position available, and ADR-0014 rejected its
equivalent in another form: readers infer an unstated figure regardless, and a deliverable
that ADR-0003 defines as "the regimes where it is not a useful proxy" cannot be delivered
as `null` throughout.

**A lower directional cutoff of 1.5 m s⁻¹, corresponding to METAR's three-knot calm
reporting threshold.** This is citable rather than asserted, which is preferable in
principle, but it imports a threshold established for reporting surface observations to
pilots — a different purpose at a different height. Retained within the sweep, where its
effect on the result is visible.
