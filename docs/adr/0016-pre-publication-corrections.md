# ADR-0016 — Corrections found after H1 was run, and recorded as such

- **Status:** accepted
- **Date:** 2026-08-27
- **Corrects:** [`0014-what-population-h1-estimates-over.md`](0014-what-population-h1-estimates-over.md)
  on one point of arithmetic, and the statistical summaries specified in
  [`0006-what-h1-compares.md`](0006-what-h1-compares.md) on two. It does **not** alter any
  threshold fixed in [`0015`](0015-what-makes-the-reanalysis-a-useful-proxy.md).

## Context

H1 ran on 2026-08-27. A pre-publication review of the result identified defects that the
pre-specification did not catch, because they are defects in the *estimators and the
wording*, not in the decisions those ADRs recorded.

**These were found after the result was visible. That is the whole reason this ADR
exists as a separate record rather than as an edit to the earlier ones.** ADR-0006,
ADR-0014 and ADR-0015 were written before any agreement statistic existed, and the commit
history demonstrates it. That ordering is an asset and it is not retrospectively
improved: those documents keep their dates and their original text, and every correction
below is dated 2026-08-27 and is post-hoc.

### 1. The pooled weight does not match the estimand ADR-0014 declares

ADR-0014 states that reweighting "maps the sample onto the frame *within the usable
subpopulation only*", and then prescribes `w_h = N_h / n_h` on the **realised usable**
`n_h`. Those are inconsistent. Dividing by the usable count forces each stratum's total
weight back to its full frame size `N_h`, so the pooled statistic is weighted by the
composition of the pre-usability frame — which is the very quantity the ADR says the
estimand is not.

The inclusion probability of a usable run is unchanged by whether other runs turned out
usable: it is `n_drawn_h / N_h` = 800/`N_h`, so the design weight is `N_h / 800`. The
implied usable population is then `N_h · n_usable_h / 800`.

| Stratum | `N_h` | usable | share under `N_h/n_usable` | share under `N_h/800` |
|---|---:|---:|---:|---:|
| `fixed_wing_or_vtol\|older` | 10,497 | 385 | 62.9% | 57.3% |
| `fixed_wing_or_vtol\|within_window` | 6,185 | 486 | 37.1% | 42.7% |

The estimated usable population is ≈ 8,809 runs. The pooled upper limit of agreement on
the vector difference magnitude moves from **8.679 to 8.808 m s⁻¹** at the 100 m
reference. ADR-0014's own stated reason — that the runs which drop out are not a random
subset — argues *for* the domain estimator, since inflating to `N_h` is exactly the
nonresponse adjustment that assumes they are.

### 2. A limit of agreement on a non-negative magnitude is not a limit of agreement

`vector_difference_magnitude` is `hypot(du, dv)`, bounded below by zero. Applying
mean ± 1.96 SD to it produced a lower limit of **−3.043 m s⁻¹** for a quantity whose
observed minimum is 0.034, and **0.0% of the 1,059 windows fall below that limit**. The
lower half of the interval is vacuous and the distribution is right-skewed (Pearson skew
0.639). The upper limit happens to be close to the empirical 97.5th percentile — 9.104
against 9.117 — but the agreement is a coincidence of this sample, not a property of the
construction.

### 3. Circular data, linear dispersion

Directional differences are correctly wrapped to (−180°, 180°], and then
`limits_of_agreement_deg` applies an ordinary mean and standard deviation to the wrapped
values. `mean_absolute_deg` is unaffected: it is a mean of |angle| on [0, 180] and remains
a valid summary.

### 4. "Unbiased" asserted equivalence from a failure to reject

Every component bias interval includes zero. That does not establish that the offset is
zero, and no equivalence test was performed. The claim appeared in the README, the results
document and the repository metadata.

### 5. The temporal offset is a testable design choice, not only a limitation

[`../06-limitations.md`](../06-limitations.md) recorded that `temporal_mismatch_s` is
−1800 s for every window by construction and therefore cannot be swept. That is true of
the recorded column and false of the underlying choice: ERA5 single-level winds are
instantaneous hourly fields, so the field can be interpolated to the midpoint of the
averaging interval and the comparison rerun. Describing it only as an unavoidable
limitation understated what could be checked.

### 6. "H1 answered" overstates what was cut

`04-methodology.md` declares airframe, airspeed sensing, estimator mechanism and variance,
firmware, altitude, topography, season and geography as strata. Only the two retention
strata were evaluated. The overall agreement question is answered; the "under which
operational conditions" question is not.

### 7. Public metadata advertised an ODD representation that does not exist

`schemas/` contains no `odd_taxonomy.yaml` and no `ODDAnnotation`, and
[`../03-odd-representation.md`](../03-odd-representation.md) blocks both until the M0
prior-art check is recorded. The README, `CITATION.cff` and the repository description
described it as delivered.

## Decision

**Correct all seven, and label every correction post-hoc.** The earlier ADRs are not
edited beyond a pointer to this one. A reader must be able to see which choices were fixed
before the result and which were made after it, and no wording here may blur that.

**No threshold moves.** The 3.0 m s⁻¹ usefulness band, the 2.0 m s⁻¹ direction cutoff, the
20-run and 10-vehicle publication floor and the 30 km spatial tolerance are unchanged.
Corrections 1–3 change estimators; 4, 6 and 7 change wording. Altering a decision
threshold after seeing the result is what `adr/0015` forbids, and none of this does it.

**Specifically:**

- The pooled estimate is reweighted with `w_h = N_h / n_drawn_h` and reported as
  secondary to the stratum-specific results, which need no weighting argument.
- The vector-difference magnitude is summarised by its empirical 95th and 97.5th
  percentiles with the run-clustered bootstrap, not by mean ± 1.96 SD. `useful_proxy` is
  evaluated against the same declared 3.0 m s⁻¹ band, applied to the 97.5th percentile.
- Directional dispersion is reported as quantiles of absolute angular error rather than as
  a linear limit of agreement.
- "No evidence of a systematic component-wise offset" replaces "unbiased" wherever it
  appeared.
- A one-window-per-run sensitivity is reported alongside the main estimate.
- A time-aligned rerun, interpolating the ERA5 field to the midpoint of each averaging
  interval, is reported as a robustness analysis.

## Consequences

- The artifacts and manifests produced on 2026-08-27 before this ADR are superseded, not
  deleted. `adr/0010` keeps a superseded manifest as the attestation of an earlier version
  of the same path, and the results document names which figures changed.
- **The central finding is unaffected.** The corrected pooled upper limit is 8.808 m s⁻¹
  and the empirical 97.5th percentile is 9.117, against a band of 3.0. The conclusion did
  not depend on any of the defects above, which is the position a project wants to be in
  when a review arrives.
- **Now forbidden:** presenting any correction in this document as though it had been
  pre-specified, and citing `adr/0014`'s weight formula without this correction.

## Alternatives considered

**Amend ADR-0014 in place so the record reads consistently.** Rejected. The value of the
pre-specification record is that it is contemporaneous, and an ADR edited after the result
to look correct is worth less than one that is visibly wrong and visibly corrected.

**Drop the pooled estimate rather than fix it**, leaving only the stratum-specific
results. Defensible, and ADR-0014 already rejected its equivalent: readers pool the strata
regardless, and declining to state the figure invites a less accurate one to be inferred.
The pooled estimate stays, corrected, and secondary.

**Move the 3.0 m s⁻¹ band now that better summaries are available.** Rejected outright.
The band was fixed before the result existed and that is its entire value. It is applied
to a better statistic; it is not itself revised.
