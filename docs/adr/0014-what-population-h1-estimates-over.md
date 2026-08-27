# ADR-0014 — What population H1 estimates over, and how the strata are weighted

- **Status:** accepted
- **Date:** 2026-08-26
- **Extends:** [`0006-what-h1-compares.md`](0006-what-h1-compares.md), which fixed *what*
  is compared and left *over which population* unstated.
- **Corrected by:** [`0016-pre-publication-corrections.md`](0016-pre-publication-corrections.md).
  The weight prescribed below, `N_h / n_h` on the realised usable `n_h`, does not match the
  estimand this ADR declares; the design weight is `N_h / n_drawn_h`. The text is left as
  written because it is the contemporaneous record. **Do not apply the formula below
  without reading that correction.**

## Context

ADR-0006 settled the estimand's shape — vector components, circular direction, a declared
vertical reference — before any outcome could be seen. It says nothing about weighting,
and neither does [`04-methodology.md`](../04-methodology.md), whose stratification section
declares the regimes a priori but not how a number over all of them is formed.

That gap is now material, because the draw is not proportional to the frame:

| Retention stratum | Frame | Drawn | Inclusion probability | Design weight `N_h/n_h` |
|---|---:|---:|---:|---:|
| `fixed_wing_or_vtol\|within_window` | 6,185 (37.1%) | 800 | 0.1293 | 7.731 |
| `fixed_wing_or_vtol\|older` | 10,497 (62.9%) | 800 | 0.0762 | 13.121 |
| **Total** | **16,682** | **1,600** | | |

`within_window` is sampled at **1.697×** the rate of `older`. That was a deliberate choice
— equal precision in both cells, and the recent cell is the one the retention policy could
eventually empty — and it is fine as a design. What is not fine is reporting a pooled
statistic computed over the resulting sample as though it described the frame.

The distortion is not marginal, and the usable rates make it worse rather than cancelling
it. On the pilot's fixed-wing rates (18/25 recent, 13/25 older) the expected usable counts
are 576 and 416, so an unweighted pooled estimate would put **58.1% of its mass on a
stratum that is 37.1% of the frame** — over-representing it by **1.57×**. Usability is
higher in exactly the stratum already oversampled, so the two effects compound.

**Two things about this stratum are easy to misread, and both would produce a wrong
sentence in a paper.**

It is defined on `log_date`, which is the **upload** date, not the flight date. Weighting
towards `older` therefore corrects the frame's *upload* composition. It is not a recency
correction, not a seasonal one, and must never be described as either.

And usability is not missing-at-random across strata — 72% against 52% — so reweighting
maps the sample onto the frame *within the usable subpopulation only*. H1's estimand is
agreement among runs that log what H1 needs, which is a subset of the fixed-wing/VTOL
frame and not a random one. The reweighting does not repair that, and nothing can; it is
reported instead.

## Decision

**Stratum-specific results are primary.** Every agreement statistic names the stratum it
was computed on. This is the reporting that needs no weighting argument to be true.

**A frame-level pooled estimate is reported only as a reweighted one, beside the
unweighted sample statistic, never instead of it.** Weights are the design weights
`w_h = N_h / n_h` computed on the **realised usable** `n_h`, not on the drawn 800, because
the runs that drop out are not a random subset of the ones drawn.

**`N_h` comes from the pinned frame** — the `dbinfo` dump hashed on 2026-08-20, the same
file the draw was made from and the same one `ingest/retrieve_h1.py` serves over loopback
(`adr/0013`). The weights, both `N_h` and the realised `n_h`, go into the manifest.

**The bootstrap resamples runs within stratum.** Bootstrap by run is already pinned by the
`validation_artifact.json` schema; stratifying the resample is what keeps the interval
consistent with the design that produced the point estimate.

**The per-stratum usable rate is reported wherever a pooled number is.** A reader who
cannot see that 72% and 52% produced the pooling cannot judge the estimand.

All of this is fixed now, on 2026-08-26, with 628 of 1,548 logs retrieved and **no
agreement statistic computed from any of them** (DPIA §1.1).

## Consequences

- There are two pooled numbers where a reader expects one. The unweighted one describes
  the sample; the reweighted one describes the frame. Labelling them is not optional, and
  the difference between them is itself worth reporting — it is the size of the design
  effect.
- Any published artifact — a Zenodo release, a dataset card, a table in a paper — carries
  `N_h`, realised `n_h`, and the usable rate alongside every pooled statistic. Without
  those three the number cannot be re-derived or checked.
- **Now forbidden:** reporting a pooled unweighted statistic as a property of PX4
  fixed-wing flight. It is a property of this draw.
- Fine stratification interacts with this and with `adr/0009`'s k-threshold in opposite
  directions: more regimes means more cells below 20 runs / 10 vehicles, and reweighting
  within a sparse cell is unstable. Where a regime is too thin to weight, the
  stratum-specific result stands alone and the pooled one is suppressed, with its count.

## Alternatives considered

**Report stratum-specific results only, and no pooled number.** The most defensible
position, and one that fails in practice: readers pool the strata regardless, by
inspection and without weights, and a paper that declines to state the frame-level figure
invites a less accurate one to be inferred from its table.

**Redraw proportionally.** ~594 recent / 1,006 older would need no weighting at all. It
also gives up precision in the smaller stratum for no scientific gain, and the draw is
made and 40% retrieved — redrawing now would spend a day of retrieval to remove one line
of arithmetic.

**Weight by flight date rather than upload date.** Closer to what a reader intuitively
wants, and unavailable: flight time is recoverable only after conversion, so it cannot
define a stratum the frame was drawn on. It remains available as a *regime* under
`04-methodology.md`, which is the right place for it.
