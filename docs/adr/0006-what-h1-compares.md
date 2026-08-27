# ADR-0006 — What H1 compares: vector wind, circular direction, and a declared vertical reference

- **Status:** accepted
- **Date:** 2026-08-20

## Context

[`04-methodology.md`](../04-methodology.md) said "bias and limits of agreement between
measurement methods" and rejected regression. That is the right family of method and
it is not yet a specification. Three things were left undefined, and each of them can
be settled after the fact in whichever way produces the more favourable number:

**1. Wind is a vector; agreement statistics on a scalar are not the same claim.**
Bland–Altman on wind *speed* alone can show excellent agreement while the two sources
disagree about direction by ninety degrees. Speed agreement is a weaker statement than
vector agreement and must not be reported as though it were the stronger one.

**2. Direction is circular.** The difference between 359° and 1° is 2°, not 358°. Any
statistic that treats bearing as a real number is wrong at the wrap point, and the
wrap point is not rare. Worse, when wind speed approaches zero the direction is not
merely noisy — it is undefined, and a directional error computed there is
meaningless rather than large.

**3. The vertical reference was never chosen.** ERA5 single levels publishes 10 m
wind. A multirotor at 80 m AGL is not in that layer. Comparing the two conflates the
vertical wind profile with the disagreement being measured — some of the "error"
would simply be shear, attributable to neither source.

On that third point the situation is better than assumed: ERA5 single levels also
publishes **`100m_u_component_of_wind` / `100m_v_component_of_wind`**, alongside 10 m
neutral-wind variants and `10m_wind_gust_since_previous_post_processing`. Pressure
levels (850, 800, 700 hPa) are available separately. The vertical reference is
therefore a decision, not a constraint.

## Decision

Fix all three **before looking at any H1 outcome**, and record them here so the choice
cannot be made retrospectively.

**Compare vectors, in components.** The primary statistics are agreement on the
north and east components separately — bias and limits of agreement on `u` and on
`v` — plus the magnitude of the vector difference. Wind-speed bias is reported as a
secondary, clearly-labelled scalar summary, never as the headline.

**Treat direction circularly, and only where it is defined.** Directional difference
is computed as the signed angle wrapped to (−180°, 180°]. It is reported only for
windows where **both** sources report speed above a declared threshold; below it, the
window is recorded as *direction undefined* and counted, not silently dropped. The
threshold is a manifest parameter, not a constant buried in code, and the count of
undefined windows is part of the result.

**Declare the vertical reference: 100 m is primary.** Most of the corpus flies closer
to 100 m than to 10 m. The 10 m comparison is retained as a secondary, and **the
difference between the 10 m and 100 m results is itself reported as a stratifier** —
it measures how much of the disagreement is shear rather than source error. Vehicle
altitude used for the comparison is AGL, and the conversion from the log's altitude
reference is recorded per run.

## Consequences

- The H1 deliverable grows a table it would not otherwise have had: agreement per
  regime × per vertical reference. That is more work and a considerably more
  interesting result.
- "Where does the reanalysis stop being a useful proxy" gains a second axis. Height
  may turn out to matter more than airframe, which would be a finding.
- Windows where direction is undefined become a reported quantity. In a corpus with
  18,348 uploader-declared *Calm* flights, that count is not a footnote.
- `ValidationArtifact` must carry component-wise statistics, not one scalar pair. The
  schema's `statistics` block needs `u` and `v` entries and a `direction` entry with
  its own `n_defined`. **This is a schema change and it is the last one before data.**
- None of these may be chosen after results have been seen, which is the reason for
  recording them here.

## Alternatives considered

Scalar speed agreement alone: simpler, publishable, and quietly overstates what was
shown. Comparing to 10 m only because it is the variable everyone uses: would have
loaded the vertical profile into the error term and invited the conclusion that ERA5
is worse than it is. Dropping low-wind windows silently: would bias the direction
statistics toward exactly the conditions where direction is well determined.
