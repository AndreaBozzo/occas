# H1 — ERA5 ↔ PX4 EKF2 wind agreement

The first deliverable. See [`../../docs/04-methodology.md`](../../docs/04-methodology.md)
for the method and [`../../docs/adr/0003-h1-is-agreement-not-calibration.md`](../../docs/adr/0003-h1-is-agreement-not-calibration.md)
for why it is framed this way.

**Neither source is ground truth.** Bias and limits of agreement between measurement
methods; no regression of one on the other. Bootstrap by run, never by window.

Output is a set of `ValidationArtifact` records, one per regime — including the regimes
where the reanalysis is *not* a useful proxy, which are results and not caveats.

Every script here emits an `AnalysisManifest` via `analysis.common.manifest`.
Empty until M3 produces converted data.
