# ADR-0009 — Positional results are published only in aggregate

- **Status:** accepted, pending the controller's sign-off on the assessment behind it
- **Date:** 2026-08-24
- **Tightens:** the standing rule "publish derived and aggregate features with
  generalised coordinates", which was too weak.

## Context

The project has carried a placeholder policy since it started: publish derived and
aggregate features, generalise coordinates, publish the pipeline rather than the data.
It was written before the B rows of the source audit were answered, and it contained an
assumption nobody had checked — that generalising coordinates on a per-run row makes
that row safe to publish.

Reading the sources ([`../07-personal-data.md`](../07-personal-data.md)) shows it does
not, for a reason specific to this corpus.

Recital 26 GDPR asks what means are "reasonably likely to be used, such as singling out,
either by the controller **or by another person**". WP29 Opinion 05/2014 (WP216) applies
that to event-level movement data and gives the escape route: event-level travel patterns
"would still qualify as personal data for any party, as long as the data controller (or
any other party) still has access to the original raw data, even if direct identifiers
have been removed"; only if the controller "would delete the raw data, and only provide
aggregate statistics to third parties on a high level" does the result become anonymous.

**That escape route is closed to us, and not by our choice.** The raw logs are not ours
to delete. PX4 publishes them, permanently, to everyone. Where WP216 worries about a
controller who retains the original, our original is a public download. A per-run row
with rounded coordinates can be matched back to its log on duration, airframe, firmware
and date. Rounding the coordinates does not touch the join that re-identifies the row.

The scale of the underlying risk is not speculative either: WP216 cites the MIT mobility
study finding that four location points single out 95% of a population, and two single
out more than half.

Article 89(1) then converts this from a permission question into an obligation: "where
those purposes can be fulfilled by further processing which does not permit or no longer
permits the identification of data subjects, those purposes shall be fulfilled in that
manner." H1's output is agreement statistics per regime. It never needs to identify
anyone, so it must not.

## Decision

**Nothing positional is published per run.** Published positional results are statistics
aggregated across runs, at a spatial resolution no finer than the analysis grid, with a
minimum population per cell. Per-run positional data exists only inside the pipeline.

Provisional parameters, to be revised against the first real sample: a published cell
draws on at least **20 runs from at least 10 distinct `vehicle_uuid` values**, and cells
below that threshold are reported as suppressed **with their count**.

The threshold now has a floor to cite. The Garante's deontological rules for statistical
and scientific research (delibera 19 December 2018 n. 515, Allegato A5, art. 5) set the
minimum frequency for a result to count as aggregated — "il valore minimo attribuibile
alla soglia è pari a tre" — and require the threshold to rise with "il livello di
riservatezza delle informazioni". Take-off locations are not low-sensitivity, so three is
the floor and not the answer. Those rules do not bind an unaffiliated researcher
([`../07-personal-data.md`](../07-personal-data.md)); we adopt them as the benchmark
because they are the standard the Italian regulator would apply.

## Consequences

- The `context_uncertainty` design already points at a `ValidationArtifact` per *regime*
  rather than carrying per-row error. That was decided for statistical reasons, and it
  turns out to be the shape this rule needs as well. Nothing in the schemas has to change.
- Suppressed cells are part of the result. A coverage matrix with gaps in it, labelled
  as gaps and carrying their counts, is an accurate artifact; one from which sparse cells
  have been silently omitted is a distorted one, and the reader cannot distinguish them.
- `vehicle_uuid` cannot be published, hashed or not — WP216's own table records that
  singling out survives hashing. It stays a grouping key inside the pipeline, including
  for the bootstrap, which is by run and by vehicle.
- The k threshold interacts with stratification: the finer the regimes, the more cells
  fall below it. If H1's interesting regimes turn out to be sparse, that tension is a
  finding to report, not a reason to lower k quietly.
- **Each published table must be checked against the ones already published, not only
  against its own threshold.** Art. 5(e) of the same rules requires results about one
  population to be released "in modo che non siano possibili collegamenti tra loro o con
  altre fonti note di informazione". Two overlapping aggregations of the same runs can be
  differenced to recover the cells each of them suppressed, so a per-table check is not
  sufficient and a release is cumulative. This is a property of the published *set*, and
  the manifest is where that set is recorded.
- This forbids a "just for reproducibility" per-run release of the joined table. The
  pipeline plus the public corpus is the reproducibility path; anyone can re-run it
  against the same logs.

## Alternatives considered

**Keep generalised per-run publication and set the rounding coarse enough.** This treats
rounding as the control when the join is the control. At any rounding that leaves the row
scientifically useful, the run remains matchable against the public corpus, so the
coordinate precision is not what is doing the work.

**Rely on the recipient's perspective** — argue that whoever downloads our derived table
cannot re-identify anyone. The relative approach exists in the case law, and *EDPS v SRB*
(C-413/23 P) confirms identifiability is assessed on the circumstances of each case. It
does not help here: the circumstance is that the re-identification key is public.

**Publish nothing positional at all.** Safer, and it would remove the coverage matrix,
which is H3's entire output and one of the artifacts the SORA evidence map is about.
Aggregation with a declared threshold gets the science and satisfies Article 89(1); total
abstention would be caution bought with results.
