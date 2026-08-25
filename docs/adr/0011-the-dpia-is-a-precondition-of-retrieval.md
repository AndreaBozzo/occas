# ADR-0011 — The DPIA is a precondition of retrieval, not of publication

- **Status:** accepted
- **Date:** 2026-08-25
- **Follows from:** [`../08-dpia-screening.md`](../08-dpia-screening.md)
- **Tightens:** [ADR-0009](0009-aggregate-only-for-positional-results.md), which settled
  what may be published and left when the assessment must happen unstated.

## Context

[`../07-personal-data.md`](../07-personal-data.md) listed "a DPIA screening under Article
35" under *Still open*, in a list otherwise made of publication tasks — the privacy
notice, the exclusion mechanism, the contact address. The placement carried an implicit
assumption: that the assessment belonged to the publication step, alongside the controls
that make publication lawful.

The screening was done on 2026-08-25 and the assumption is wrong.

A DPIA is required. Not by Article 35(3), whose three enumerated cases are all absent —
there is no profiling with legal effects, location is not an Article 9 special category,
and nothing here monitors a publicly accessible area. It is required by two independent
routes that do apply: three of WP248's nine criteria against a threshold of two (data of
a highly personal nature, large scale, matching or combining datasets), and items 4 and 9
of the Garante's Article 35(4) list, the first of which names large-scale location data
in terms that describe this project almost literally.

And Article 35(1) fixes the timing: the controller shall, **prior to the processing**,
carry out the assessment. The processing that meets the criteria is reading positions out
of a `.ulg`. Aggregate-only publication, the k thresholds and the suppression rules are
*mitigations the DPIA will describe*. Mitigations do not postpone the assessment that
evaluates them.

There is a second finding, and it is the more useful one. The corpus audit already run
reads `dbinfo`, which carries no coordinates. It meets one criterion, not three, and the
Garante's item 4 requires data of an extremely personal character that the metadata is
not. **Everything done so far is on the permitted side, and the line is exact:** it is the
first `.ulg`. [ADR-0005](0005-sample-from-metadata-not-bulk-download.md) put the metadata
first to avoid loading someone else's service. It turns out to have kept the project
lawful as well, which was not the reason it was written.

## Decision

**Gate G1 is not cleared until the DPIA exists, and the DPIA precedes the first `.ulg`
retrieval.** The G1 checklist gains it as an item in its own right rather than inheriting
it from the publication tasks.

## Consequences

- The order of work is fixed and is not the intuitive one: DPIA, then retrieval, then
  analysis, then the publication controls. Writing the stratified sampler does not become
  more urgent; running it becomes conditional on a document.
- `ingest/px4_download.py` already fails closed on a dedicated `G1-status` flag, so no
  code change is needed to enforce this — but its docstring named "a DPIA screening" among
  the things G1 waits on, which was accurate and is now stale in the other direction: the
  screening is done, and what remains is the DPIA itself.
- `--acknowledge-unaudited` was flagged here for the controller's eye and **removed on
  2026-08-25 at their instruction**. It existed so a deliberate small sample could be
  taken with the block recorded rather than bypassed, and the retrieval record did stamp
  `publication_eligibility=blocked`. But an acknowledgement is a record of a decision,
  not a legal basis: Article 35(1) requires the assessment prior to the processing, and a
  small sample of geolocated logs is still processing. A gate with a documented way
  around it is a suggestion. `tests/test_ingest_gate.py` now asserts it has not returned.
- Article 36(1) prior consultation with the Garante becomes a live question, answerable
  only once the DPIA grades its own residual risk. The mitigations already designed are
  substantial and it is plausibly not reached. "Plausibly not" is not a finding.
- Most of Article 35(7)'s content already exists across `00-scope`, `04-methodology` and
  `07-personal-data`. What is missing is specific and short: a written legitimate-interest
  statement, a why-no-less-intrusive-design argument, risk severity and likelihood
  grading, and the exclusion mechanism actually built. The screening maps them.

## Alternatives considered

**Treat the screening as the DPIA.** It is not, and calling it one would be the exact
species of overclaim this project polices elsewhere. A screening asks whether the
obligation exists; Article 35(7) prescribes what discharges it.

**Conclude no DPIA is needed, on the grounds that the logs are already public.** The
tempting reading, and WP248 addresses it directly: public availability "may be considered
as a factor in the assessment if the data was expected to be further used for certain
purposes". It is a factor, weighed against expected use — and an uploader submitting a
flight report for debugging did not expect population-scale research. The factor runs
against us. Reaching the convenient answer through the one passage that explicitly
qualifies it would not survive being asked about.

**Defer the DPIA to just before publication, since only publication can harm anyone.**
Sympathetic, and wrong on the text. Article 35(1) says prior to the processing, and the
risk it contemplates is not only disclosure: holding a corpus of geolocated trajectories
is itself the exposure, whatever is eventually published from it.
