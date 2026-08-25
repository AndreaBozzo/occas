# 07 — Personal data: the B rows answered

**Status: PROVISIONAL.** Drafted from primary sources on 2026-08-24 and awaiting the
controller's decision. This is a documented position, not legal advice, and the
legitimate-interests assessment in B3 needs a signature from the person who is actually
the controller. Gate **G1** turns on it.

Every quotation below was read in the source text, not in a summary of it. Where a
widely-repeated reading of a source turned out to be wrong, that is noted rather than
inherited.

## B1 — Which fields could identify a natural person?

The data subject here is **the uploader-operator**, not a bystander. A ULog contains no
imagery and no audio, so the drone-surveillance framing that dominates the literature
does not apply; what the corpus exposes is the person who flew and published.

| Where | Field | Why it matters |
|---|---|---|
| `dbinfo` (public metadata) | `vehicle_uuid` | A persistent identifier linking every flight of one airframe. Pseudonymisation, not anonymisation |
| `dbinfo` | `vehicle_name`, `description`, `feedback` | Free text. Can carry names, employers, club names, place names — unbounded by schema |
| `dbinfo` | `log_date` | Combined with the above, a behavioural pattern over time |
| Inside the `.ulg` | GPS position and time | Take-off and landing points. The corpus equivalent of WP216's "very likely home or office" |

The uploader's email is collected by the upload form but is **not** among the 26
published fields, so it is PX4's to hold and not ours to process.

Recital 26 GDPR settles the status of `vehicle_uuid`: "personal data which have undergone
pseudonymisation, which could be attributed to a natural person by the use of additional
information should be considered to be information on an identifiable natural person."

## B2 — What are uploaders told about publication and re-use?

Three things, all verified in `flight_review` source rather than inferred:

- the upload form states publication under CC-BY (PR #302);
- `is_public = 1` is reachable **only** inside the `upload_type == 'flightreport'`
  branch, so publication is an affirmative choice on a form where the uploader is also
  writing a flight report;
- that same branch sets `allow_for_analysis = 1` unconditionally, under the source
  comment "always allow for statistical analysis".

**Provisional position:** this is a copyright licence and a publication choice. It is not
a data-protection notice, and it is not consent under Article 6(1)(a) — a CC-BY statement
does not identify a controller, a purpose, a retention period or a set of rights. What it
*is* is good evidence of the data subject's **reasonable expectations** under Recital 47,
which is a balancing input in B3 and nothing more. The distinction matters because
treating a licence as consent would be the single easiest mistake to make here.

## B3 — Which lawful basis applies to processing derived features?

**Provisional position: Article 6(1)(f), legitimate interests**, assessed in the three
steps the EDPB sets out in Guidelines 1/2024 on Article 6(1)(f) (adopted for public
consultation on 8 October 2024 — whether a final version has since been adopted could not
be checked, as the EDPB site refused the request from here).

**1. The interest.** Scientific research into whether a public reanalysis product agrees
with onboard wind estimation, and under which conditions it does not. Non-commercial at
this stage, and published openly. Article 5(1)(b) is directly in point: "further
processing for archiving purposes in the public interest, scientific or historical
research purposes or statistical purposes shall, in accordance with Article 89(1), not be
considered to be incompatible with the initial purposes."

**2. Necessity.** H1 cannot be answered without real flights flown in real conditions. The
obvious less-intrusive alternative — simulation — is excluded on scientific grounds that
predate this assessment: `PX4_SITL` is a separate control population and is never merged
into the real-flight corpus. Necessity here is a genuine finding, not a convenience.

**3. Balancing.** In favour: the data subject published deliberately, under a licence,
having ticked a public box on a form that says the log is always allowed for statistical
analysis; the processing is research; no decision is taken about any individual; nothing
is inferred about a person's health, beliefs or associations. Against: location data is
sensitive in effect if not in law, take-off sites are frequently homes, and `vehicle_uuid`
makes a longitudinal profile of one operator constructible. Recital 47 asks "whether a
data subject can reasonably expect at the time and in the context of the collection of the
personal data that processing for that purpose may take place" — for *statistical analysis
of flight data*, plainly yes; for *publication of a per-flight positional record*, plainly
not.

The balance therefore does not come out as a yes or a no. It comes out as a constraint on
what may be published, which is B4 and B5.

**Article 89(1) safeguards** are not optional decoration, and one sentence of it is close
to dispositive for this project:

> Where those purposes can be fulfilled by further processing which does not permit or no
> longer permits the identification of data subjects, those purposes shall be fulfilled in
> that manner.

H1's output is agreement statistics per regime. It does not require identifying anyone. So
Article 89(1) does not merely permit the aggregate-only design — it *requires* it.

**Article 14, not Article 13.** The data does not come from the data subject, so the
information duty is Article 14, and complying with it literally would mean contacting tens
of thousands of uploaders. Article 14(5)(b) exempts processing where provision "proves
impossible or would involve a disproportionate effort, in particular for processing for
... scientific or historical research purposes or statistical purposes, subject to the
conditions and safeguards referred to in Article 89(1)", and requires instead that the
controller "take appropriate measures to protect the data subject's rights and freedoms
and legitimate interests, including **making the information publicly available**".

**Action this creates:** a public privacy notice stating controller, purposes, basis,
categories, retention and how to object. That is the price of the exemption, and it is
cheap. It does not exist yet. The Italian rules below say where it should go: not only
in the repository, but in a channel the data subjects actually read.

## B4 — What coordinate generalisation is sufficient, and how justified?

**Provisional position: no rounding of per-run coordinates is sufficient, because rounding
is not the binding constraint.**

Recital 26 sets the test: "account should be taken of all the means reasonably likely to
be used, such as **singling out**, either by the controller **or by another person**".

WP29 Opinion 05/2014 on Anonymisation Techniques (WP216) then applies exactly this to
event-level movement data, and the passage is worth quoting in full because it describes
our situation almost literally:

> if an organisation collects data on individual travel movements, the individual travel
> patterns at event level would still qualify as personal data for any party, as long as
> the data controller (or any other party) still has access to the original raw data, even
> if direct identifiers have been removed from the set provided to third parties. But if
> the data controller would delete the raw data, and only provide aggregate statistics to
> third parties on a high level ... that would qualify as anonymous data.

The escape route in that passage is deleting the raw data. **It is not available to us.**
The raw logs are not ours to delete: PX4 publishes them, in perpetuity, to everyone. The
re-identification key is not merely retained somewhere — it is a public download. A
recipient of a per-run row with rounded coordinates can match it back against the public
corpus on duration, airframe, firmware and date, and recover the exact log.

On how little it takes, WP216 cites the MIT mobility study directly:

> 95% of the population could be singled-out with four location points, and ... just two
> points were enough to single-out more than 50% of the data subjects.

And WP216's own summary table (Table 6) records that pseudonymisation defeats none of the
three risks — singling out, linkability, inference — while aggregation and k-anonymity
defeat only singling out.

So generalising coordinates on a per-run row is **pseudonymisation**. It is a genuine
safeguard under Article 89(1) and it is worth doing. It is not anonymisation, and the
output stays personal data.

## B5 — Does aggregate publication differ from per-run publication?

**Yes — and it is the only route WP216 endorses.** The same passage that closes off
per-run publication opens this one: aggregate statistics "on a high level", where the
individual events are no longer identifiable, "would qualify as anonymous data".

A note on a case that is often cited for the opposite conclusion. In **EDPS v SRB**
(C-413/23 P, 4 September 2025) the CJEU addressed whether pseudonymised data transferred
to a third party is personal data from the recipient's perspective. It is widely
summarised as holding that it is not. That is not what the Court decided here: it **set
aside** the General Court's judgment, held that "the relevant perspective ... depends, in
essence, on the circumstances of the processing of the data in each individual case", and
that for the information duty "the identifiable nature of the data subject must be
assessed at the time of collection of the data and from the point of view of the
controller". The case was referred back to the General Court.

Even on the most recipient-friendly reading, it would not help here. The relative approach
turns on whether the recipient can reasonably re-identify. Our recipient can: the raw
corpus is public.

## What this permits and forbids

Provisional, and the thresholds in particular are judgement calls that WP216 explicitly
declines to set in general ("in most cases it is not possible to give minimum
recommendations for parameters to use as each dataset needs to be considered on a
case-by-case basis").

**Permitted to publish**

- Agreement statistics per regime, aggregated across runs.
- Spatial resolution no finer than the analysis grid itself — ERA5's 0.25°, about 25 km.
  The grid is chosen for scientific reasons and happens to be coarse; the privacy
  constraint is the count in the cell, not the rounding.
- **Provisional k:** no published cell may draw on fewer than **20 runs from at least 10
  distinct `vehicle_uuid` values**. Cells below that are reported as suppressed, with their
  count, because suppression that hides its own existence is its own distortion.

**Forbidden to publish**

- Any per-run row carrying a positional attribute, however generalised.
- `vehicle_uuid`, raw or hashed — hashing is pseudonymisation and Table 6 is explicit that
  singling out survives it.
- Free text from `description`, `vehicle_name` or `feedback`, verbatim or excerpted.

**Internal processing** may use the full data, minimised to what H1 needs, with the
manifest recording what was read.

## Italian provisions — the Garante's deontological rules

Read on 2026-08-24. **Which text is current matters and is not obvious:** the Garante's
provvedimento n. 298 of 9 May 2024 (GU Serie Generale n. 130, 5 June 2024) is about
Article 110 of the Codice — medical, biomedical and epidemiological research — and it
promotes *new* rules while expressly preserving the old ones, "nelle more
dell'approvazione delle nuove Regole deontologiche e ferma la vigenza di quelle di cui
all'allegato A5". So the operative text is still the **Regole deontologiche per
trattamenti a fini statistici o di ricerca scientifica**, delibera 19 December 2018
n. 515, Allegato A5 to the Codice.

**They probably do not bind this project, and that is not entirely good news.** Article 2
limits their scope to processing whose controllers are "università, altri enti o istituti
di ricerca e società scientifiche, nonché ricercatori che operano nell'ambito di dette
università, enti, istituti di ricerca e soci di dette società scientifiche" — and Article
1(d) defines a research body as one whose research purpose "risulta dagli scopi
dell'istituzione e la cui attività scientifica è documentabile". An unaffiliated
individual is outside that list. Two consequences:

- Article 2-quater(4) of the Codice makes compliance with deontological rules "condizione
  essenziale per la liceità" of processing **for those they apply to**. That condition
  does not attach here, so nothing in them is a precondition for us.
- Neither do their accommodations. We cannot invoke their simplified regime and then
  disclaim their obligations.
- **If the work is ever done under a university** — a collaboration, a hosted project, a
  co-author's affiliation — they become binding, and Article 3 then requires a documented
  research project specifying the measures adopted. The repository already is that
  document in all but name.

They remain the sharpest available statement of what the Italian regulator considers
identifiable, so this project adopts them voluntarily as a benchmark, which costs nothing
and is the standard we would be measured against anyway.

**Article 4 — identifiability.** A data subject is identifiable when, using reasonable
means, one can establish "un'associazione significativamente probabile" between the
combination of variables for a statistical unit and identifying data. The enumerated
"reasonable means" include:

> archivi, anche non nominativi, che forniscano ulteriori informazioni oltre quelle
> oggetto di comunicazione o diffusione

That is the public PX4 corpus, named as a category. The Italian rules reach B4's
conclusion by an explicit route rather than by analogy.

**Article 5 — the threshold, and a constraint we had missed.** Results count as aggregated
when the combination of values carries a frequency at or above a pre-set threshold, and
"il valore minimo attribuibile alla soglia è pari a tre". Three is a floor, not a target:
5(b) requires the threshold to rise with "il livello di riservatezza delle informazioni",
and take-off locations are not low-sensitivity. Our provisional 20 runs / 10 vehicles sits
well above the floor and can now cite one.

Article 5(e) adds a constraint that was not in the earlier draft: results about the same
population must be published "in modo che non siano possibili collegamenti tra loro o con
altre fonti note di informazione, che rendano possibili eventuali identificazioni". Publish
two overlapping aggregations of the same runs and the difference between them can isolate
the cells that were suppressed. **Every published table must be checked against the others
already published, not only against its own threshold.**

**Article 6(3) — how the notice is published.** Where data come from third parties or were
collected for other purposes and an individual informativa "comporta uno sforzo
sproporzionato rispetto al diritto tutelato", the controller adopts "idonee forme di
pubblicità", and the examples are concrete: a national newspaper, a broadcast announcement,
or "inserzione in strumenti informativi di cui gli interessati sono normalmente
destinatari". This is the Italian gloss on Article 14(5)(b)'s "making the information
publicly available", and it is more demanding: publish where the data subjects actually
are. For this population that is not a file in a git repository — it is the PX4 forum,
where a thread already exists.

## Still open

- **A DPIA under Article 35 — the screening is done and the answer is yes.**
  [`08-dpia-screening.md`](08-dpia-screening.md), 2026-08-25. Not by Art. 35(3), whose
  three cases are all absent, but by three of WP248's nine criteria against a threshold
  of two, and by items 4 and 9 of the Garante's Art. 35(4) list — item 4 names
  large-scale location data outright. **Art. 35(1) says "prior to the processing"**, so
  the DPIA precedes the first `.ulg`, not the first publication; listing it here among
  the publication tasks was the wrong placement
  ([ADR-0011](adr/0011-the-dpia-is-a-precondition-of-retrieval.md)). Nothing done so far
  required one: `dbinfo` carries no coordinates, so the metadata layer meets one
  criterion, not three. Art. 36(1) prior consultation stays open until the DPIA grades
  its own residual risk.
- **Whether affiliation changes the answer.** The deontological rules are out of scope for
  an unaffiliated individual today. Any university involvement makes them binding and adds
  Article 3's documented-project requirement.
- **Publishing the privacy notice.** Drafted at [`../PRIVACY.md`](../PRIVACY.md), with a
  forum version at [`outreach/privacy-notice-post.md`](outreach/privacy-notice-post.md).
  It needs a contact address and a stable URL, and it is not a notice until it is
  actually published — in a channel the data subjects read, per art. 6(3) of the
  deontological rules.
- **The exclusion list the notice promises.** Article 21 objections have to be honoured
  by something, and a promise with no mechanism behind it is worse than no promise. It
  is deliberately unbuilt until retrieval starts — but it must exist before the first
  published result, and the manifest should record which exclusions were in force for
  a run.
- **B2's remaining half**: whether PX4's own notice at upload is adequate is a question
  about *their* controller obligations, not ours. It was asked on the M0 thread and has had
  no reply.

## Sources

| Source | Used for |
|---|---|
| GDPR Recital 26, Art. 5(1)(b), 6(1)(f), 14(5)(b), 89(1)–(2), Recital 47 (EUR-Lex, CELEX 32016R0679) | B1, B3, B4 |
| WP29 Opinion 05/2014 on Anonymisation Techniques (WP216), pp. 9, 23, 24 | B4, B5 |
| EDPB Guidelines 1/2024 on Art. 6(1)(f) | B3 three-step structure |
| CJEU, *EDPS v SRB*, C-413/23 P, 4 Sept 2025 (Court press release 107/25) | B5 |
| `PX4/flight_review` — `app/tornado_handlers/upload.py`, `app/plot_app/db_entry.py` | B1, B2 |
| Garante, Regole deontologiche 19 Dec 2018 n. 515 (Allegato A5), artt. 1–6 | Italian benchmark |
| Garante, provvedimento n. 298 of 9 May 2024 (GU 130/2024) | Confirms A5 still in force |
| D.lgs. 196/2003 art. 2-quater(4) | Status of the deontological rules |
