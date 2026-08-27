# 04 — Methodology

## H1 as an agreement problem

> In which vehicle, estimator and operational conditions does ERA5 wind show useful
> agreement with onboard PX4 wind estimates?

**Neither source is ground truth.**

- ERA5 is a 0.25° hourly reanalysis — tens of kilometres, hourly steps.
- PX4 wind is an EKF2 estimate with published `variance_north` / `variance_east`. The
  mechanism depends on the platform: on fixed-wing typically fusion of airspeed and
  synthetic sideslip; on multicopter, inference from drag specific forces, which
  requires correctly calibrated drag coefficients.

Therefore: **methods for agreement between measurement methods** — bias and limits of
agreement — and **not** regression of one on the other as if one were the true value.
An R-squared between two uncertain estimates answers no question anyone asked.

### What exactly is compared

Specified in [`adr/0006-what-h1-compares.md`](adr/0006-what-h1-compares.md), fixed
before any outcome is inspected:

- **Vector, in components.** Bias and limits of agreement on the north and east
  components separately, plus the magnitude of the vector difference. Wind-*speed*
  bias is a secondary scalar summary and is labelled as one — speed can agree while
  direction disagrees by ninety degrees.
- **Direction wrapped, and only where defined.** Signed angle wrapped to
  (−180°, 180°], so 359° against 1° is a 2° difference. Reported only where both
  sources exceed a declared speed threshold; below it the window is counted as
  *direction undefined* rather than dropped. That count is part of the result.
  The threshold is **2.0 m s⁻¹**, swept at 1.0 and 3.0 as a sensitivity table, fixed
  in [`adr/0015`](adr/0015-what-makes-the-reanalysis-a-useful-proxy.md) before any
  agreement statistic existed.
- **Vertical reference declared: 100 m primary.** ERA5 single levels publishes
  `100m_u/v_component_of_wind` as well as 10 m. Most of the corpus flies nearer 100 m.
  The 10 m comparison is kept as a secondary, and the gap between the two is reported
  as a stratifier — it separates vertical shear from source disagreement.

## Stratification

Declared a priori, before looking at outcomes:

```text
airframe type (fixed-wing / multicopter)
presence of an airspeed sensor
wind-estimation mechanism and parameters
reported EKF variance
firmware version
altitude
topography
season and geography
```

The output of H1 is not a single number. It is a set of **regimes**, each with its own
agreement statistics, including the regimes in which the reanalysis is **not** a useful
proxy. Reporting where it fails is a result, not a caveat.

*Useful* is a declared predicate, not a judgement made on the day: the upper 95% limit
of agreement on the vector difference magnitude at or below **3.0 m s⁻¹**, reported
beside the estimator-relative ratio per component, both fixed in
[`adr/0015`](adr/0015-what-makes-the-reanalysis-a-useful-proxy.md). The band is asserted
rather than cited, and says so wherever it is published.

Where a number over all of them is wanted, it is a *reweighted* one and it says so:
the H1 draw is 800/800 across retention strata that are 37.1%/62.9% of the frame, so a
pooled sample statistic would describe the design rather than the population. Weights,
the estimand, and what reweighting cannot repair are fixed in
[`adr/0014`](adr/0014-what-population-h1-estimates-over.md).

## Alignment and tolerances

Every join declares, and every joined row records:

- spatial tolerance and distance to the grid point actually used;
- temporal tolerance and the actual time mismatch;
- interpolation method;
- quality flags.

Sensitivity analysis on distance-to-grid-point and temporal mismatch is mandatory, not
optional: if the result moves under plausible tolerance choices, that is the finding.

## Statistics

- **Splits by run, source, vehicle and firmware.** Never adjacent windows of the same
  run in both train and test.
- **Confounders declared a priori:** airframe, autopilot version, sensing, hardware
  quality, mission profile, operator experience, geography, season, duration, logging
  configuration, wind-estimation mechanism.
- **Selection bias declared:** public logs are an *observational convenience sample*.
  They over-represent test flights and users seeking support. They do not generalise
  to a production fleet, and no result may be stated as if they did.
  More precisely than "convenience": `flight_review` can only make an upload public
  when its type is `flightreport`, and the dump confirms all 450,395 records are of
  that type. The population is *uploads whose author chose to file a flight report and
  tick public* — a selection on the uploader's intent, made before we ever see the
  log. See [`02b-dbinfo-inventory.md`](02b-dbinfo-inventory.md).
- **Confidence intervals always. Bootstrap by run, never by window** — windows within a
  run are not independent and treating them as such inflates precision.
- **Language:** agreement, association, conditional risk, coverage. Never causality
  without a design that supports it.

## Data quality

- Field-level coverage published.
- Quality flag on every join; explicit spatio-temporal tolerances.
- Proxies always called proxies: GNSS geometry is not received quality; a DEM is not
  an obstacle map; an EKF estimate is not a measurement.

## Third source (optional, inside the M4 budget)

On the subset of flights close enough to a METAR station, add an independent third
reference. METAR is measured at 10 m over a runway, in terrain that is open and flat
by construction. It is comparable only under restricted conditions, and those
conditions must be stated.

**Scope constraint:** this lives inside the M4 budget. If it does not fit, it is cut.
It does not become its own milestone.

## Reproducibility

Every figure and every published number derives from a versioned script and an
`AnalysisManifest` recording input hashes, dependency versions, parameters, seeds and
retrieval timestamps. Pinned environment. No analysis in unversioned notebooks.

For ERA5, record `dataset/product ID`, version and `retrieved_at`: the preliminary
**ERA5T** product can be replaced by the final version, typically within 2-3 months.
It is not the case that the whole archive is continuously rewritten.

**A negative result is publishable. A non-reproducible result is not.**
