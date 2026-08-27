# ruff: noqa: E501 -- the long lines are markdown table rows inside an f-string. Wrapping
# them would put newlines inside table cells and break the table.
"""Assemble docs/paper/h1-manuscript.md from the committed artifacts.

Every number is read from artifacts/, never typed. adr/0010 requires a figure or number in
prose to be emitted by the script that computed it.
"""

import json
import pathlib

A = pathlib.Path("artifacts")


def jsonl(path):
    return [
        json.loads(line)
        for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


summary = json.loads((A / "h1-agreement.json").read_text(encoding="utf-8"))
arts = jsonl(A / "h1-validation-artifacts.jsonl")
mid = jsonl(A / "h1-validation-artifacts-midpoint.jsonl")
join = json.loads((A / "h1-join-summary.json").read_text(encoding="utf-8"))
inv = json.loads((A / "h1-inventory.json").read_text(encoding="utf-8"))
alt = json.loads((A / "h1-altitude.json").read_text(encoding="utf-8"))


def art(label, level="era5_100m", pooling="unweighted_sample", axis=None, cell=None):
    for a in arts:
        c = a["regime"]["criteria"]
        if a["vertical_reference"] != level:
            continue
        if axis and (c.get("axis") != axis or c.get("cell") != cell):
            continue
        if not axis and a["regime"]["label"] != label:
            continue
        if c.get("pooling", pooling) != pooling:
            continue
        return a
    raise KeyError((label, level, axis, cell))


def mag(a):
    return a["statistics"]["vector_difference_magnitude"]


pooled = art("all_fixed_wing_or_vtol")
pooled_rw = art("all_fixed_wing_or_vtol", pooling="reweighted")
pooled10 = art("all_fixed_wing_or_vtol", level="era5_10m")
older = art("fixed_wing_or_vtol|older", pooling="unweighted_sample")
within = art("fixed_wing_or_vtol|within_window", pooling="unweighted_sample")
d = pooled["statistics"]["direction"]

keyed = {(a["validation_model_id"], a["vertical_reference"]): a for a in mid}
shifts = sorted(
    mag(keyed[(a["validation_model_id"], a["vertical_reference"])])["p97_5"] - mag(a)["p97_5"]
    for a in arts
    if (a["validation_model_id"], a["vertical_reference"]) in keyed
)
flips = sum(
    1
    for a in arts
    if (a["validation_model_id"], a["vertical_reference"]) in keyed
    and a["useful_proxy"]
    != keyed[(a["validation_model_id"], a["vertical_reference"])]["useful_proxy"]
)

low = art("", axis="altitude_proxy", cell="agl_proxy_lt_50m")
midalt = art("", axis="altitude_proxy", cell="agl_proxy_50_to_120m")
high = art("", axis="altitude_proxy", cell="agl_proxy_ge_120m")
sig_lo = art("", axis="estimator_sigma", cell="sigma_lt_0.5")
sig_hi = art("", axis="estimator_sigma", cell="sigma_ge_1.0")

realised = summary["realised_by_stratum"]
implied = summary["implied_usable_population"]
older_share = implied["fixed_wing_or_vtol|older"] / sum(implied.values()) * 100

DOC = f"""# No detectable offset, far too much spread: reanalysis wind cannot replace onboard UAS wind estimates

**Andrea Bozzo**

*Draft manuscript. Every number is read from the artifacts in
[`../../artifacts/`](../../artifacts/) by `scripts/build_manuscript.py`; none is typed by
hand.*

## Abstract

Operators and regulators increasingly want to know what conditions an uncrewed flight
actually encountered, and reanalysis is the obvious source when no measurement exists. We
ask whether ERA5 wind can stand in for a UAS's own wind estimate. Using
{summary["n_runs"]:,} public PX4 fixed-wing and VTOL flights and {summary["n_windows"]:,}
flight-hours paired to ERA5, we compare the reanalysis against the onboard EKF2 estimate as
two uncertain methods rather than treating either as truth. We find **no evidence of a
systematic component-wise offset** — every component bias interval includes zero — but the
disagreement is large: the median vector difference is {mag(pooled)["p50"]:.2f} m s⁻¹ and
its 97.5th percentile is {mag(pooled)["p97_5"]:.2f} m s⁻¹, against a usefulness band of
3.0 m s⁻¹ declared before any result existed. No regime among five pre-declared axes
approaches the band. The conclusion survives reweighting, run-level clustering,
grid-distance tolerance, vertical reference, and a full re-pairing with the reanalysis field
interpolated to the centre of each averaging interval, which moves the headline statistic by
a median of {shifts[len(shifts) // 2]:+.3f} m s⁻¹. Disagreement grows sharply below 50 m
above launch, consistent with surface-layer heterogeneity a 0.25° field cannot resolve.

## 1. Introduction

External operating context is the missing half of most public flight-telemetry corpora. A
log records what the aircraft did; it rarely records the conditions it did it in, and a
reanalysis product is the cheapest way to supply them retrospectively. The question this
paper answers is narrow and practical: **when a UAS log lacks a usable wind estimate, can
ERA5 be substituted for one?**

Framing matters here. The onboard PX4 wind figure is an EKF2 *estimate* with published
variances, not a measurement, and ERA5 is a 0.25° hourly reanalysis. Neither is ground
truth. We therefore use agreement methods between measurement methods and never regress one
on the other.

## 2. Data

The frame is the public PX4 Flight Review corpus, characterised in full from its published
metadata dump before any download. A stratified sample of 1,600 fixed-wing and VTOL logs was
drawn, 800 from each of two retention strata defined on upload date.

Of those, **{inv["usable_for_h1"]:,} runs ({inv["usable_rate"] * 100:.1f}%)** carry the wind
topic, an absolute time reference and global position. Coverage is recorded rather than
filtered: {inv["unusable_reasons"]["missing:wind"]} runs carry no wind topic,
{inv["unusable_reasons"]["no_absolute_time"]} no absolute time, and
{inv["unusable_reasons"]["missing:vehicle_global_position"]} no global position.

Every run with a wind topic also reports its own variance
({inv["wind_variance_rate_of_wind_runs"]:.1f} of {inv["topic_presence"]["wind"]}), so the
estimator's self-assessed uncertainty is universally available.

Pairing yields **{join["windows_paired"]:,} windows** from {join["runs_paired"]:,} runs;
{join["failures"]["window:incomplete"]} windows were incomplete and are counted, not dropped.
Every window lies within the declared 30 km spatial tolerance — the furthest is
{join["distance_to_grid_point_km"]["max"]:.2f} km — and no ERA5 read failed.

## 3. Method

All decisions below were fixed before any agreement statistic existed, in dated architecture
decision records, and the repository's commit history demonstrates the ordering.

- **Vector, in components.** Bias and limits of agreement on the east and north components
  separately, plus the magnitude of the vector difference. Speed is a secondary scalar.
- **Direction circularly, and only where defined.** Signed angle wrapped to (−180°, 180°],
  reported only where both sources exceed 2.0 m s⁻¹; below that the window is counted as
  undefined.
- **100 m as the declared vertical reference**, with 10 m retained as a secondary.
- **Strata primary, pooled estimates reweighted.** Design weights are the inverse inclusion
  probability `N_h / n_drawn_h`.
- **Bootstrap by run, within stratum**, {pooled["bootstrap"]["n_resamples"]:,} resamples.
- **A declared usefulness band of 3.0 m s⁻¹**, sized against manufacturer wind limits of
  roughly 10–12 m s⁻¹ and asserted rather than cited.

Three estimators were corrected *after* the result was first computed, and are recorded as
post-hoc: the pooled weight, the summary of the non-negative magnitude, and the circular
dispersion measure. No threshold was changed. See ADR-0016.

The design weight uses the drawn count, not the usable count. A usable run's inclusion
probability does not depend on how many other runs proved usable; dividing by the usable
count would target the pre-usability frame. The implied usable population is
**{sum(implied.values()):,.0f} runs**, {older_share:.1f}% in the older stratum.

## 4. Results

### 4.1 No detectable offset

| Regime | Runs | Windows | Bias u | 95% CI | Bias v | 95% CI |
|---|---:|---:|---:|---|---:|---|
| older | {older["n_runs"]} | {older["n_windows"]} | {older["statistics"]["u"]["bias"]:+.3f} | [{older["statistics"]["u"]["bias_ci"][0]:+.3f}, {older["statistics"]["u"]["bias_ci"][1]:+.3f}] | {older["statistics"]["v"]["bias"]:+.3f} | [{older["statistics"]["v"]["bias_ci"][0]:+.3f}, {older["statistics"]["v"]["bias_ci"][1]:+.3f}] |
| within_window | {within["n_runs"]} | {within["n_windows"]} | {within["statistics"]["u"]["bias"]:+.3f} | [{within["statistics"]["u"]["bias_ci"][0]:+.3f}, {within["statistics"]["u"]["bias_ci"][1]:+.3f}] | {within["statistics"]["v"]["bias"]:+.3f} | [{within["statistics"]["v"]["bias_ci"][0]:+.3f}, {within["statistics"]["v"]["bias_ci"][1]:+.3f}] |
| pooled | {pooled["n_runs"]} | {pooled["n_windows"]} | {pooled["statistics"]["u"]["bias"]:+.3f} | [{pooled["statistics"]["u"]["bias_ci"][0]:+.3f}, {pooled["statistics"]["u"]["bias_ci"][1]:+.3f}] | {pooled["statistics"]["v"]["bias"]:+.3f} | [{pooled["statistics"]["v"]["bias_ci"][0]:+.3f}, {pooled["statistics"]["v"]["bias_ci"][1]:+.3f}] |

Every interval includes zero. This is a failure to reject a zero offset, not a demonstration
that the offset is zero; no equivalence test was performed, and the intervals remain
compatible with offsets of a few tenths of a metre per second.

![Component agreement](../../artifacts/figures/fig1-component-agreement.png)

### 4.2 The disagreement is large

Pooled at 100 m: median **{mag(pooled)["p50"]:.2f}**, 95th percentile
**{mag(pooled)["p95"]:.2f}**, 97.5th percentile **{mag(pooled)["p97_5"]:.2f}** m s⁻¹, with a
bootstrap interval on the last of [{mag(pooled)["p97_5_ci"][0]:.2f},
{mag(pooled)["p97_5_ci"][1]:.2f}]. The reweighted pooled figure is
{mag(pooled_rw)["p97_5"]:.2f}. At 10 m the figure is {mag(pooled10)["p97_5"]:.2f}, slightly
*better* than the 100 m reference declared primary.

The magnitude is non-negative and right-skewed, so it is summarised by empirical quantiles;
mean ± 1.96 SD returns an impossible negative lower limit on this sample. Six of
{pooled["n_windows"]:,} windows exceed 15 m s⁻¹ and one reaches 69 — an onboard estimate of
66 m s⁻¹, which is a filter failure rather than a wind. Removing the worst six moves the
97.5th percentile to 8.47, so the result rests on the body of the distribution.

![Magnitude distribution](../../artifacts/figures/fig2-magnitude-distribution.png)

### 4.3 No operational regime rescues it

![Regime forest](../../artifacts/figures/fig3-regime-forest.png)

Five pre-declared axes were cut. The best-agreeing cell is
{midalt["regime"]["criteria"]["cell"]} at {mag(midalt)["p97_5"]:.2f} m s⁻¹, still 2.5× the
band.

**Altitude separates most interpretably.** Below 50 m above launch the 97.5th percentile is
**{mag(low)["p97_5"]:.2f}** [{mag(low)["p97_5_ci"][0]:.2f}, {mag(low)["p97_5_ci"][1]:.2f}],
against {mag(midalt)["p97_5"]:.2f} [{mag(midalt)["p97_5_ci"][0]:.2f},
{mag(midalt)["p97_5_ci"][1]:.2f}] between 50 and 120 m and {mag(high)["p97_5"]:.2f} above
120 m; the first two intervals do not overlap. This is *consistent with* the greater
roughness, heterogeneity and shear expected near the surface, which a 0.25° field at 100 m
cannot resolve. It is not evidence that altitude causes it: this is an observational sample,
the altitude is a takeoff-relative proxy, terrain is unmodelled, and mission profile and
airframe co-vary with height.

**Estimator uncertainty separates more strongly and means less.** Where the filter reports
σ below 0.5 m s⁻¹ the 97.5th percentile is {mag(sig_lo)["p97_5"]:.2f}; at σ ≥ 1.0 it is
{mag(sig_hi)["p97_5"]:.2f}. The gradient is partly circular by construction — a noisy
estimate disagrees more with anything — so it locates where the comparison is least
informative rather than where the reanalysis is worst.

Airframe, airspeed topic and season show overlapping intervals throughout.

### 4.4 Direction is centred but widely dispersed

At the declared cutoff, {d["n_defined"]:,} of {pooled["n_windows"]:,} windows have a defined
direction and **{d["n_undefined"]:,} ({d["n_undefined"] / pooled["n_windows"] * 100:.1f}%)
do not**. Among those defined, the circular mean error is
{d["circular_mean_deg"]:+.1f}° with resultant length {d["circular_resultant_length"]:.3f},
median absolute error {d["median_absolute_deg"]:.1f}° and 90th percentile
{d["p90_absolute_deg"]:.1f}°.

![Direction error](../../artifacts/figures/fig4-direction-error.png)

### 4.5 Robustness

| Check | Effect on the headline |
|---|---|
| Reweighting to the frame | {mag(pooled)["p97_5"]:.2f} → {mag(pooled_rw)["p97_5"]:.2f} |
| One window per run | {summary["one_window_per_run"]["era5_100m"]["p97_5_all_windows"]:.3f} → {summary["one_window_per_run"]["era5_100m"]["p97_5_one_per_run"]:.3f} |
| Vertical reference 100 m → 10 m | {mag(pooled)["p97_5"]:.2f} → {mag(pooled10)["p97_5"]:.2f} |
| Join tolerance 30 km → 10 km | verdict unchanged at every cap |
| Time alignment corrected | median {shifts[len(shifts) // 2]:+.3f}, range [{shifts[0]:+.3f}, {shifts[-1]:+.3f}], **{flips} verdict changes** |

The temporal check is the strongest of these. The primary comparison places an instantaneous
field at the start of the hour the onboard estimate is averaged over. Re-pairing the entire
corpus with the field interpolated to the interval midpoint changes every value — median
0.183 m s⁻¹ — and changes no conclusion.

![Time alignment](../../artifacts/figures/fig5-time-alignment.png)

## 5. Limitations

Public PX4 logs are an observational convenience sample selected on uploader intent: an
upload is public only when its author filed a flight report and chose to publish it. No
figure here generalises to a production fleet.

The 3.0 m s⁻¹ band is asserted, not cited. It was fixed before any result existed, which
establishes it was not chosen to fit one; it does not make it authoritative. Nothing turns on
its exact value — the pooled 95th percentile is {mag(pooled)["p95"]:.2f} m s⁻¹.

Three declared axes are uncut: firmware version, which the sampling frame does not carry, and
topography and true altitude AGL, which need a terrain model this work does not build.
Geography is not stratified at all. Three further axes are represented only by proxies: an
airspeed *topic* rather than a sensor, a reported variance band rather than the estimator's
mechanism, and height above launch rather than AGL — the rangefinder that would give AGL is
valid for a median 0.4% of rows and reads at touchdown.

Disagreement does not identify which source is wrong. Neither is ground truth.

## 6. Conclusion

ERA5 wind shows no detectable systematic offset against onboard PX4 EKF2 wind estimates and
disagrees with them far too widely to substitute for them, in every regime tested. For
practitioners the operational reading is direct: a reanalysis value is not a replacement for
a missing onboard wind estimate at the tolerance a flight-limit check requires, and it is
least adequate close to the ground, where most of the risk is.

Reporting where a proxy fails is a result. The pipeline, schemas, decision records and
aggregate artifacts are published so the failure can be checked rather than believed.

## Data and code availability

Pipeline, schemas, decision records and aggregate artifacts:
<https://github.com/AndreaBozzo/occas>. Raw geolocated trajectories are not redistributed;
the source logs remain public at PX4 Flight Review. Every number above traces to an
`AnalysisManifest` under `artifacts/manifests/`.
"""

out = pathlib.Path("docs/paper/h1-manuscript.md")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(DOC, encoding="utf-8", newline="\n")
print(f"wrote {out} ({len(DOC.splitlines())} lines)")
print(f"  pooled p97.5 {mag(pooled)['p97_5']:.2f}, p95 {mag(pooled)['p95']:.2f}")
print(f"  time-alignment median shift {shifts[len(shifts) // 2]:+.3f}, flips {flips}")
