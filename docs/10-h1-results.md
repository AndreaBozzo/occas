# 10 — H1 results: agreement between ERA5 and the onboard wind estimate

Every figure on this page is emitted by `analysis/h1_agreement/agreement.py` into
[`artifacts/h1-agreement.json`](../artifacts/h1-agreement.json) and
[`artifacts/h1-validation-artifacts.jsonl`](../artifacts/h1-validation-artifacts.jsonl),
attested by manifest `artifacts/manifests/6126a705-a271-4f69-9886-ef143981bd42.json`.
None is computed elsewhere or transcribed by hand.

## The question, and what was fixed before it was answered

> In which vehicle, estimator and operational conditions does ERA5 wind show useful
> agreement with onboard PX4 wind estimates?

**Neither source is ground truth** ([`adr/0003`](adr/0003-h1-is-agreement-not-calibration.md)).
What follows are limits of agreement between two measurement methods. Differences are
formed as `era5 - onboard`, so a positive bias indicates that ERA5 reads higher.

Four decisions were recorded before any of these numbers existed, and each is the kind
that could otherwise have been selected to suit the result:

| Decision | Where | Fixed on |
|---|---|---|
| Vector components primary; direction circular; 100 m the declared vertical reference | [`adr/0006`](adr/0006-what-h1-compares.md) | 2026-08-20 |
| Strata primary; pooled estimates reweighted; bootstrap by run within stratum | [`adr/0014`](adr/0014-what-population-h1-estimates-over.md) | 2026-08-26 |
| Direction undefined below 2.0 m s⁻¹; `useful_proxy` at 3.0 m s⁻¹ on the upper limit | [`adr/0015`](adr/0015-what-makes-the-reanalysis-a-useful-proxy.md) | 2026-08-27 |
| Aggregate publication only, 20 runs and 10 vehicles per cell | [`adr/0009`](adr/0009-aggregate-only-for-positional-results.md) | 2026-08-24 |

## Realised sample

Of a stratified draw of 1,600 fixed-wing/VTOL logs, 871 carry the wind topic, absolute
time and global position that H1 requires. Those runs yield 1,059 ERA5-hour windows.
No window was lost to an incomplete ERA5 read, and no stratum fell below the
publication threshold.

| Stratum | Runs | Vehicles | Windows | Frame `N_h` | Design weight |
|---|---:|---:|---:|---:|---:|
| `older` | 385 | 384 | 468 | 10,497 | 27.26 |
| `within_window` | 486 | 484 | 591 | 6,185 | 12.73 |

Design weights are `N_h / n_h` on the **realised** usable runs rather than the 800 drawn
per stratum, because usability differs by stratum and the runs that drop out are not a
random subset ([`adr/0014`](adr/0014-what-population-h1-estimates-over.md)).

## Result

**ERA5 is unbiased against the onboard EKF2 estimate, and too imprecise to substitute
for it.** `useful_proxy` is false in every regime, at both vertical references.

| Regime | Runs | Windows | Bias `u` | 95% CI | Bias `v` | 95% CI | \|Δ\| upper LoA | CI on that limit | Useful proxy |
|---|---:|---:|---:|---|---:|---|---:|---|:--:|
| `older` | 385 | 468 | +0.151 | [-0.094, +0.403] | +0.021 | [-0.261, +0.299] | 7.74 | [6.80, 8.74] | **no** |
| `within_window` | 486 | 591 | -0.096 | [-0.326, +0.138] | +0.156 | [-0.145, +0.513] | 10.01 | [6.84, 13.73] | **no** |
| pooled, unweighted | 871 | 1059 | +0.013 | [-0.157, +0.192] | +0.096 | [-0.117, +0.329] | 9.10 | [7.10, 11.79] | **no** |
| pooled, reweighted | 871 | 1059 | +0.060 | [-0.123, +0.248] | +0.071 | [-0.138, +0.286] | 8.68 | [7.12, 10.78] | **no** |

| Regime | Runs | Windows | Bias `u` | 95% CI | Bias `v` | 95% CI | \|Δ\| upper LoA | CI on that limit | Useful proxy |
|---|---:|---:|---:|---|---:|---|---:|---|:--:|
| `older` | 385 | 468 | -0.007 | [-0.229, +0.224] | -0.028 | [-0.290, +0.230] | 7.02 | [6.04, 8.04] | **no** |
| `within_window` | 486 | 591 | -0.072 | [-0.286, +0.137] | +0.065 | [-0.222, +0.399] | 9.47 | [6.23, 13.24] | **no** |
| pooled, unweighted | 871 | 1059 | -0.043 | [-0.199, +0.116] | +0.024 | [-0.168, +0.245] | 8.50 | [6.43, 11.27] | **no** |
| pooled, reweighted | 871 | 1059 | -0.031 | [-0.200, +0.141] | +0.007 | [-0.182, +0.214] | 8.05 | [6.40, 10.25] | **no** |

Two statements, and they are separate.

**The bias is indistinguishable from zero.** Every component bias interval includes
zero, in every regime and at both references. There is no systematic offset between the
reanalysis and the onboard estimate in this corpus. That is a finding rather than an
absence of one: it means the disagreement below is dispersion and not calibration.

**The dispersion is large.** Limits of agreement are approximately ±5 m s⁻¹ per
component. The upper limit on the vector difference magnitude ranges from 7.02 to
10.01 m s⁻¹ against the 3.0 m s⁻¹ band declared in
[`adr/0015`](adr/0015-what-makes-the-reanalysis-a-useful-proxy.md), and the bootstrap
interval on that limit does not approach 3.0 in any regime. The verdict is not marginal.

The mean vector difference is 2.99 to 3.06 m s⁻¹ at 100 m — that is, approximately equal
to the band itself. Had the criterion been defined on the mean rather than on the upper
limit of agreement, the result would read as borderline. The criterion was fixed on the
upper limit before these numbers were computed, which is the reason that observation can
be reported rather than debated.

## Direction

Directional difference is computed only where both sources report speed above the
declared cutoff. Below it the window is counted as undefined rather than discarded.

| Stratum | Cutoff | Defined | Undefined | Mean absolute difference |
|---|---:|---:|---:|---:|
| `older` | 1.0 m s⁻¹ | 362 | 106 | 37.5° |
| `older` *(primary)* | 2.0 m s⁻¹ | 259 | 209 | 27.6° |
| `older` | 3.0 m s⁻¹ | 176 | 292 | 23.0° |
| `within_window` | 1.0 m s⁻¹ | 488 | 103 | 35.4° |
| `within_window` *(primary)* | 2.0 m s⁻¹ | 371 | 220 | 31.8° |
| `within_window` | 3.0 m s⁻¹ | 244 | 347 | 28.3° |

At the primary cutoff of 2.0 m s⁻¹ and the 100 m reference, 429 of 1,059 windows —
**40.5%** — are direction-undefined. [`adr/0006`](adr/0006-what-h1-compares.md)
anticipated that this count would be a primary reported quantity rather than a footnote,
in a corpus containing 18,348 uploader-declared *Calm* flights.

The mean absolute difference falls monotonically as the cutoff rises, from 37.5° at
1.0 m s⁻¹ to 23.0° at 3.0 m s⁻¹ in the `older` stratum. The highest cutoff therefore
produces the most favourable figure. The primary value was fixed at 2.0 m s⁻¹ in advance,
and the sweep is published so that the dependence is visible rather than concealed.

## The estimator's own uncertainty

[`adr/0015`](adr/0015-what-makes-the-reanalysis-a-useful-proxy.md) requires a second view
reported alongside the absolute verdict: the limit-of-agreement half-width divided by the
mean standard deviation the onboard filter reports for the same component.

| Stratum | Component | LoA half-width | Mean onboard σ | Ratio |
|---|:--:|---:|---:|---:|
| `older` | `u` | 5.045 | 0.465 | 10.85× |
| `older` | `v` | 5.610 | 0.539 | 10.40× |
| `within_window` | `u` | 5.006 | 1.016 | 4.92× |
| `within_window` | `v` | 7.692 | 1.013 | 7.60× |

The two sources disagree by between 4.9 and 10.9 times the onboard filter's own stated
uncertainty. The ADR provided for the case in which the two criteria disagree, and
required that disagreement to be reported; it does not arise here, as both indicate the
same conclusion.

The onboard standard deviation is roughly twice as large in `within_window`
(1.016 and 1.013 m s⁻¹ for `u` and `v`) as in `older` (0.465 and 0.539), which is why the
ratios differ between strata while the limits of agreement are comparable. EKF2's variance is a filter's
self-assessment and not an independent measurement; see
[`06-limitations.md`](06-limitations.md).

## Sensitivity to the join tolerance

[`04-methodology.md`](04-methodology.md) requires this analysis. The `useful_proxy`
verdict is recomputed at each cap, and the publication threshold is re-applied, since a
tighter cap removes windows and removes runs and vehicles with them.

| Cap | Stratum | Windows | Runs | Vehicles | \|Δ\| upper LoA | Useful proxy |
|---:|---|---:|---:|---:|---:|:--:|
| 10 km | `older` | 192 | 163 | 162 | 8.14 | **no** |
| 10 km | `within_window` | 287 | 242 | 242 | 7.08 | **no** |
| 15 km | `older` | 436 | 360 | 359 | 7.74 | **no** |
| 15 km | `within_window` | 563 | 462 | 460 | 10.15 | **no** |
| 20 km | `older` | 468 | 385 | 384 | 7.74 | **no** |
| 20 km | `within_window` | 591 | 486 | 484 | 10.01 | **no** |
| 30 km | `older` | 468 | 385 | 384 | 7.74 | **no** |
| 30 km | `within_window` | 591 | 486 | 484 | 10.01 | **no** |

**The verdict does not change at any cap**, which is what makes it robust. Two further
observations:

- The declared 30 km spatial tolerance was never binding. The furthest window in the
  corpus is 17.82 km from its grid point, so the 30 km and 20 km rows are identical by
  construction.
- The two strata move in **opposite** directions as the cap tightens: restricting to
  10 km makes `older` worse (7.74 to 8.14) and `within_window` better (10.01 to 7.08).
  Distance to grid point is therefore not driving the disagreement in any simple way.

The temporal half of this analysis cannot be performed. The mismatch is −1800 s for every
window in the corpus by construction, so there is no variation to examine; the
consequence, that the reanalysis value is located at the start of the averaging interval
rather than its centre, is recorded in [`06-limitations.md`](06-limitations.md).

## Two points on which the a priori framing was wrong

Both are reportable, and neither could have been known when the framing was fixed.

**The 10 m reference agrees marginally better than 100 m.**
[`adr/0006`](adr/0006-what-h1-compares.md) declared 100 m primary on the reasoning that
most of the corpus flies nearer to it than to 10 m. The upper limit of agreement is
nevertheless lower at 10 m in every regime — 7.02 against 7.74 in `older`. That
difference is the shear stratifier the ADR asked for, and it points against the ADR's own
expectation. Both references fail the band, so this does not change the conclusion.

**The strata are not interchangeable.** `within_window` shows a materially wider upper
limit than `older` (10.01 against 7.74 at 100 m) on a larger sample. Reporting a single
pooled figure would have concealed this, which is the reason
[`adr/0014`](adr/0014-what-population-h1-estimates-over.md) makes stratum-specific results
primary. The reweighted pooled estimate sits below the unweighted one (8.68 against 9.10),
because `older` is 62.9% of the frame but 44.2% of the usable sample; that gap is the size
of the design effect.

## What this does not establish

- Public PX4 logs are an observational convenience sample selected on uploader intent.
  No figure here generalises to a production fleet.
- The 3.0 m s⁻¹ band is asserted rather than cited. It was fixed before any result
  existed, which establishes that it was not chosen to fit one; it does not make it
  authoritative.
- Disagreement does not identify which source is in error. Neither is ground truth.
- The regimes reported here are the retention strata. The remaining axes declared a
  priori in [`04-methodology.md`](04-methodology.md) — airframe, airspeed sensor,
  altitude, terrain, season — have not been cut.

Full limitations: [`06-limitations.md`](06-limitations.md).
