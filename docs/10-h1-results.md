# 10 — H1 results: agreement between ERA5 and the onboard wind estimate

Every figure on this page is emitted by `analysis/h1_agreement/agreement.py` into
[`artifacts/h1-agreement.json`](../artifacts/h1-agreement.json) and
[`artifacts/h1-validation-artifacts.jsonl`](../artifacts/h1-validation-artifacts.jsonl),
attested by manifest `artifacts/manifests/97cd29f0-7cb3-42d2-ba6f-1a5c8339bfba.json`. None is computed elsewhere
or transcribed by hand.

> **Status.** These are the numbers after the corrections in
> [`adr/0016`](adr/0016-pre-publication-corrections.md), which were found in review
> *after* H1 had been run and are labelled post-hoc there. The estimators changed; no
> decision threshold did. The time-aligned rerun the ADR called for has since been run
> over all 1,059 windows; it is reported below and changes nothing.

## The question, and what was fixed before it was answered

> "In which vehicle, estimator and operational conditions does ERA5 wind show useful
> agreement with onboard PX4 wind estimates?"

**Neither source is ground truth** ([`adr/0003`](adr/0003-h1-is-agreement-not-calibration.md)).
What follows are limits of agreement between two measurement methods. Differences are
formed as `era5 - onboard`, so a positive bias means ERA5 reads higher.

| Decision | Where | Fixed on |
|---|---|---|
| Vector components primary; direction circular; 100 m the declared vertical reference | [`adr/0006`](adr/0006-what-h1-compares.md) | 2026-08-20 |
| Strata primary; pooled estimates reweighted; bootstrap by run within stratum | [`adr/0014`](adr/0014-what-population-h1-estimates-over.md) | 2026-08-26 |
| Direction undefined below 2.0 m s⁻¹; `useful_proxy` at 3.0 m s⁻¹ | [`adr/0015`](adr/0015-what-makes-the-reanalysis-a-useful-proxy.md) | 2026-08-27, before `build_pairs` finished |
| Aggregate publication only, 20 runs and 10 vehicles per cell | [`adr/0009`](adr/0009-aggregate-only-for-positional-results.md) | 2026-08-24 |
| *Corrections to the estimators, after the result was seen* | [`adr/0016`](adr/0016-pre-publication-corrections.md) | 2026-08-27, **post-hoc** |

## Realised sample

Of 1,600 fixed-wing/VTOL logs drawn 800 per retention stratum, 871 carry the wind topic,
absolute time and global position H1 requires, yielding 1,059 ERA5-hour windows. No window
was lost to an incomplete ERA5 read and no cell fell below the publication floor.

| Stratum | Frame `N_h` | Drawn | Usable | Vehicles | Windows | Weight `N_h/n_drawn` | Implied usable |
|---|---:|---:|---:|---:|---:|---:|---:|
| `older` | 10,497 | 800 | 385 | 384 | 468 | 13.121 | 5,052 |
| `within_window` | 6,185 | 800 | 486 | 484 | 591 | 7.731 | 3,757 |

Implied usable population **8,809** runs, 57.3% `older`.

The weight is the inverse inclusion probability `N_h / n_drawn_h`. A usable run's chance of
having been drawn does not depend on how many other runs turned out usable, so dividing by
the usable count would target the pre-usability frame instead of the population these
statistics describe ([`adr/0016`](adr/0016-pre-publication-corrections.md) correction 1).

## Result

**No evidence of a systematic component-wise offset, and agreement far too imprecise for
ERA5 to substitute for the onboard estimate.** `useful_proxy` is false in every regime, at
both vertical references, at every join tolerance.

| Regime | Runs | Windows | Bias `u` | 95% CI | Bias `v` | 95% CI | \|Δv\| median | \|Δv\| p97.5 | CI on p97.5 | Useful proxy |
|---|---:|---:|---:|---|---:|---|---:|---:|---|:--:|
| `older` | 385 | 468 | +0.151 | [-0.094, +0.403] | +0.021 | [-0.261, +0.299] | 2.33 | 8.76 | [7.19, 11.01] | **no** |
| `within_window` | 486 | 591 | -0.096 | [-0.326, +0.138] | +0.156 | [-0.145, +0.513] | 2.39 | 9.35 | [8.04, 11.78] | **no** |
| pooled, unweighted | 871 | 1059 | +0.013 | [-0.157, +0.192] | +0.096 | [-0.117, +0.329] | 2.37 | 9.19 | [8.05, 10.82] | **no** |
| pooled, reweighted | 871 | 1059 | +0.046 | [-0.132, +0.231] | +0.078 | [-0.132, +0.296] | 2.36 | 9.11 | [7.88, 10.82] | **no** |

| Regime | Runs | Windows | Bias `u` | 95% CI | Bias `v` | 95% CI | \|Δv\| median | \|Δv\| p97.5 | CI on p97.5 | Useful proxy |
|---|---:|---:|---:|---|---:|---|---:|---:|---|:--:|
| `older` | 385 | 468 | -0.007 | [-0.229, +0.224] | -0.028 | [-0.290, +0.230] | 2.13 | 9.05 | [6.71, 10.46] | **no** |
| `within_window` | 486 | 591 | -0.072 | [-0.286, +0.137] | +0.065 | [-0.222, +0.399] | 2.23 | 8.41 | [6.81, 10.85] | **no** |
| pooled, unweighted | 871 | 1059 | -0.043 | [-0.199, +0.116] | +0.024 | [-0.168, +0.245] | 2.18 | 8.42 | [7.14, 10.19] | **no** |
| pooled, reweighted | 871 | 1059 | -0.035 | [-0.194, +0.132] | +0.012 | [-0.172, +0.220] | 2.17 | 8.43 | [7.13, 10.07] | **no** |

**On the offset.** Every component bias interval includes zero, in every regime and at both
references. This is a failure to reject a zero offset, not a demonstration that the offset
is zero: the intervals are compatible with offsets up to roughly ±0.3–0.5 m s⁻¹, and no
equivalence test was performed.

**On the dispersion.** The typical disagreement is a median vector difference of about
2.4 m s⁻¹, and the 97.5th percentile is 8.8–9.4 m s⁻¹ against the 3.0 m s⁻¹ band declared
in `adr/0015`. The bootstrap interval on that percentile does not approach 3.0 in any
regime.

The magnitude is summarised by empirical quantiles rather than by mean ± 1.96 SD. It is
non-negative, so the classical construction returned a lower limit of −3.043 m s⁻¹ on this
sample, below which not one of the 1,059 windows fell
([`adr/0016`](adr/0016-pre-publication-corrections.md) correction 2). `useful_proxy` is
evaluated against the 97.5th percentile — the same declared band and the same intended 95%
coverage, read off the distribution instead of assumed from it.

## Operational regimes

The axes declared a priori in [`04-methodology.md`](04-methodology.md) that the corpus can
cut. Every cell below carries at least 20 runs from at least 10 distinct vehicles. One cell
falls below that floor and is not shown: the 9 runs whose altitude proxy is undefined,
reported as suppressed with their count in
[`artifacts/h1-agreement.json`](../artifacts/h1-agreement.json) rather than omitted
silently ([`adr/0009`](adr/0009-aggregate-only-for-positional-results.md)).

| Axis | Cell | Runs | Vehicles | Windows | \|Δv\| median | \|Δv\| p97.5 | CI on p97.5 | Useful proxy |
|---|---|---:|---:|---:|---:|---:|---|:--:|
| `airframe` | `fixed_wing` | 419 | 415 | 504 | 2.45 | 10.12 | [7.87, 12.80] | **no** |
| `airframe` | `vtol` | 452 | 452 | 555 | 2.32 | 8.54 | [7.58, 9.96] | **no** |
| `airspeed_topic` | `absent` | 120 | 120 | 135 | 2.71 | 8.04 | [6.54, 12.67] | **no** |
| `airspeed_topic` | `present` | 751 | 747 | 924 | 2.32 | 9.23 | [8.08, 10.72] | **no** |
| `altitude_proxy` | `agl_proxy_50_to_120m` | 376 | 375 | 449 | 2.32 | 7.53 | [6.75, 8.85] | **no** |
| `altitude_proxy` | `agl_proxy_ge_120m` | 143 | 142 | 202 | 1.99 | 7.55 | [5.34, 9.47] | **no** |
| `altitude_proxy` | `agl_proxy_lt_50m` | 343 | 343 | 397 | 2.80 | 12.79 | [9.85, 14.88] | **no** |
| `estimator_sigma` | `sigma_0.5_to_1.0` | 157 | 157 | 169 | 2.96 | 8.89 | [6.97, 11.72] | **no** |
| `estimator_sigma` | `sigma_ge_1.0` | 53 | 53 | 54 | 4.28 | 26.62 | [14.60, 69.04] | **no** |
| `estimator_sigma` | `sigma_lt_0.5` | 693 | 690 | 836 | 2.23 | 8.09 | [7.16, 9.44] | **no** |
| `season` | `DJF` | 169 | 169 | 199 | 2.31 | 11.76 | [7.89, 14.97] | **no** |
| `season` | `JJA` | 277 | 275 | 344 | 2.40 | 8.42 | [7.44, 13.06] | **no** |
| `season` | `MAM` | 213 | 213 | 256 | 2.29 | 9.62 | [6.78, 11.72] | **no** |
| `season` | `SON` | 212 | 212 | 260 | 2.53 | 8.72 | [7.07, 10.04] | **no** |

**No regime rescues the reanalysis.** The best cell is `altitude_proxy 50–120 m`, at
7.53 — still 2.5× the band.

**Two axes separate, and they are not equally interesting.**

*Altitude is the substantive one.* Disagreement falls monotonically with height — median
2.80, 2.32, 1.99 m s⁻¹ — and the 97.5th percentile for flights below 50 m is **12.79**
against 7.53 between 50 and 120 m, with bootstrap intervals that **do not overlap**
([9.85, 14.88] against [6.75, 8.85]). This is the one result here with a clean physical
reading: a 0.25° reanalysis wind at 100 m describes the free atmosphere far better than it
describes the surface layer a UAS below 50 m is flying in, where roughness, obstacles and
shear dominate. It is also a caution about the vertical reference rather than a rescue —
even the best-agreeing altitude band fails the band.

*Estimator uncertainty separates more strongly and means less.* The 97.5th percentile runs
8.09, 8.89, 26.62 across the three sigma bands and the median runs 2.23, 2.96, 4.28. That
gradient is partly circular by construction: a noisy onboard estimate disagrees more with
*anything*, so it locates where the comparison is least informative rather than where the
reanalysis is worst. It is the same caution
[`adr/0015`](adr/0015-what-makes-the-reanalysis-a-useful-proxy.md) attaches to the
estimator-relative ratio.

**Nothing else separates.** Fixed-wing against VTOL, airspeed topic present against absent,
and the four seasons all have overlapping bootstrap intervals on the 97.5th percentile. The
airspeed comparison runs *opposite* to the mechanism one would expect — logs without an
airspeed topic agree slightly better — which is a further reason to read it as noise rather
than as a finding. An airspeed *topic* is in any case a proxy for airspeed *sensing*, and
is labelled as one.

**The altitude axis is a proxy and is named as one.** `adr/0006` specifies AGL, which this
corpus cannot produce: the downward rangefinder that would give it is valid for a median
0.4% of rows and reads at touchdown. What is cut is height above the takeoff point. Over
flat ground near the launch site the two agree; over a ridge they do not, and nothing here
says which a given run is. Nine runs whose median height falls outside a plausible range —
the extreme is −2,347 m, a reset local origin rather than a flight — are suppressed with
their count rather than banded. See `analysis/h1_agreement/altitude.py`.

**Declared but not cut:** firmware version, which the sampling frame does not carry, and
topography, which has the same DEM dependency as true AGL.

## Direction

Reported only where both sources exceed the declared 2.0 m s⁻¹ cutoff; below it the window
is counted as undefined rather than discarded.

| Stratum | Defined | Undefined | Mean \|error\| | Median | p90 | Circular mean | Resultant `R` |
|---|---:|---:|---:|---:|---:|---:|---:|
| `older` | 259 | 209 | 27.6° | 17.1° | 70.3° | -4.1° | 0.799 |
| `within_window` | 371 | 220 | 31.8° | 18.9° | 79.0° | -3.3° | 0.751 |
| pooled, unweighted | 630 | 429 | 30.1° | 18.0° | 74.7° | -3.7° | 0.770 |

At the primary cutoff, **429 of 1,059 windows — 40.5% — are direction-undefined**, which
`adr/0006` anticipated would be a primary reported quantity in a corpus containing 18,348
uploader-declared *Calm* flights.

Direction is *centred but dispersed*: the circular mean error is about −4°, while the 90th
percentile of absolute error is around 75°. Dispersion is reported as a resultant length
and as quantiles of absolute error, not as a linear limit of agreement over wrapped angles
([`adr/0016`](adr/0016-pre-publication-corrections.md) correction 3).

## Robustness

**Clustering.** The bootstrap resamples runs, so the intervals already account for windows
sharing a flight. This checks whether the point estimates do:

| Statistic | All 1059 windows | One per run (871) |
|---|---:|---:|
| Bias `u` | +0.0131 | -0.0209 |
| Bias `v` | +0.0960 | +0.1352 |
| \|Δv\| p97.5 | 9.188 | 9.226 |

Clustering is shallow — 1.22 windows per run — and the shift is correspondingly small.

**Join tolerance.** The verdict does not change at any distance cap between 10 km and the
declared 30 km, and the 30 km tolerance was never binding: the furthest window is 17.82 km
from its grid point. The two strata move in *opposite* directions as the cap tightens, so
distance to grid point is not driving the disagreement in any simple way. Full table in
[`artifacts/h1-agreement.json`](../artifacts/h1-agreement.json) under
`tolerance_sensitivity`.

**Vertical reference.** The 10 m reference agrees slightly *better* than the 100 m one
`adr/0006` declared primary — 8.42 against 9.19 pooled. That gap is the shear stratifier
the ADR asked for, pointing against its own expectation. Both fail the band.

**Time alignment.** The primary comparison places the instantaneous ERA5 field at the
*start* of the hour the onboard estimate is averaged over, a systematic −1800 s offset
([`06-limitations.md`](06-limitations.md)). The whole corpus was re-paired with the field
interpolated to the midpoint of each averaging interval — `build_pairs --alignment
interval_midpoint`, 1,059 windows, two ERA5 reads each — and re-analysed. Coverage is
identical and every ERA5 value changes, by a median of 0.183 m s⁻¹ and at most 1.802.

| Regime | \|Δv\| median | | \|Δv\| p97.5 | | Bias `u` | | Useful proxy |
| | start | midpoint | start | midpoint | start | midpoint | either |
|---|---:|---:|---:|---:|---:|---:|:--:|
| `older` | 2.33 | 2.26 | 8.76 | 8.74 | +0.151 | +0.137 | **no** |
| `within_window` | 2.39 | 2.39 | 9.35 | 9.50 | -0.096 | -0.072 | **no** |
| pooled | 2.37 | 2.34 | 9.19 | 9.04 | +0.013 | +0.020 | **no** |

| Axis | Cell | \|Δv\| p97.5 start | midpoint | change |
|---|---|---:|---:|---:|
| `airframe` | `fixed_wing` | 10.12 | 10.24 | +0.13 |
| `airframe` | `vtol` | 8.54 | 8.56 | +0.02 |
| `airspeed_topic` | `absent` | 8.04 | 7.97 | -0.07 |
| `airspeed_topic` | `present` | 9.23 | 9.14 | -0.09 |
| `altitude_proxy` | `agl_proxy_50_to_120m` | 7.53 | 7.30 | -0.24 |
| `altitude_proxy` | `agl_proxy_ge_120m` | 7.55 | 7.42 | -0.14 |
| `altitude_proxy` | `agl_proxy_lt_50m` | 12.79 | 12.64 | -0.16 |
| `estimator_sigma` | `sigma_0.5_to_1.0` | 8.89 | 9.14 | +0.25 |
| `estimator_sigma` | `sigma_ge_1.0` | 26.62 | 26.98 | +0.35 |
| `estimator_sigma` | `sigma_lt_0.5` | 8.09 | 8.05 | -0.04 |
| `season` | `DJF` | 11.76 | 11.79 | +0.03 |
| `season` | `JJA` | 8.42 | 8.19 | -0.23 |
| `season` | `MAM` | 9.62 | 9.32 | -0.30 |
| `season` | `SON` | 8.72 | 8.87 | +0.15 |

Across all 64 paired artifacts the 97.5th percentile moves by a **median of −0.032 m s⁻¹**,
between −0.371 and +0.479. **No verdict flips**, and no regime becomes a useful proxy. The
altitude gradient survives intact — 12.64 below 50 m against 7.30 between 50 and 120 — so
it is a property of the surface layer rather than an artifact of comparing an instantaneous
field against an hour mean.

The offset was a real design choice and `adr/0016` was right that calling it only an
unavoidable limitation understated what could be tested. Testing it removes the objection
instead of answering it: a median shift of 0.03 m s⁻¹ against a 6 m s⁻¹ gap to the
criterion. Artifacts:
[`h1-agreement-midpoint.json`](../artifacts/h1-agreement-midpoint.json), manifest
`artifacts/manifests/d8f91079-8f0d-4aa2-84cd-63241f8e48ba.json`.

## What this does not establish

- Public PX4 logs are an observational convenience sample selected on uploader intent. No
  figure here generalises to a production fleet.
- The 3.0 m s⁻¹ band is asserted, not cited. It was fixed before any result existed, which
  establishes it was not chosen to fit one; it does not make it authoritative.
- Disagreement does not identify which source is in error. Neither is ground truth.
- The estimator-sigma gradient is partly circular by construction, as above.
- Two declared axes remain uncut — firmware and topography — so the "under which
  operational conditions" question is answered for five axes and open for two. The
  altitude answer rests on a proxy for AGL, not on AGL.

Full limitations: [`06-limitations.md`](06-limitations.md).
