# 08 — Article 35 screening: is a DPIA required?

**Answer: yes — and it binds earlier than this project assumed.**

[`07-personal-data.md`](07-personal-data.md) left this open with the instruction not to
assume it either way. This document closes it, from the sources, on 2026-08-25. It is a
*screening*, not the DPIA: it establishes whether the obligation exists. It does.

The finding that matters is not the yes. It is **when**: Article 35(1) requires the
assessment "prior to the processing", and the processing that triggers it is the reading
of positions out of `.ulg` files — not the publication of results. The DPIA is therefore
a precondition of **retrieval**, which is where 07 did not place it.
[ADR-0011](adr/0011-the-dpia-is-a-precondition-of-retrieval.md) records that consequence.

## What Article 35(1) asks

> Where a type of processing in particular using new technologies, and taking into
> account the nature, scope, context and purposes of the processing, is likely to result
> in a high risk to the rights and freedoms of natural persons, the controller shall,
> **prior to the processing**, carry out an assessment of the impact of the envisaged
> processing operations on the protection of personal data.

Three routes can make an assessment mandatory: the enumerated cases in 35(3), the
general high-risk test in 35(1) as elaborated by WP248, and the supervisory authority's
own list under 35(4). They are checked separately below because they fail and succeed
for different reasons, and a screening that reached the right answer by the wrong route
would not survive being questioned.

## Route 1 — Article 35(3): the three enumerated cases. **Not met.**

| | Case | Applies? |
|---|---|---|
| (a) | "a systematic and extensive evaluation of personal aspects ... based on automated processing, including profiling, and on which decisions are based that produce legal effects" | **No.** H1 computes agreement between two wind estimates. Nothing is evaluated about a person and no decision is taken about anyone. |
| (b) | "processing on a large scale of special categories of data referred to in Article 9(1), or of personal data relating to criminal convictions and offences referred to in Article 10" | **No.** Location data is *not* an Article 9 special category. This is the point most often got wrong in the other direction. |
| (c) | "a systematic monitoring of a publicly accessible area on a large scale" | **No.** We analyse logs that were uploaded; we do not observe an area. WP248 glosses "publicly accessible area" as "a piazza, a shopping centre, a street, a market place, a train station or a public library". |

**So the obvious route does not apply**, and a screening that stopped here would conclude
no DPIA is needed. That conclusion would be wrong.

## Route 2 — Article 35(1) via WP248's nine criteria. **Three met; the threshold is two.**

WP248 rev.01, endorsed by the EDPB, sets the operative test:

> In most cases, a data controller can consider that a processing meeting **two criteria**
> would require a DPIA to be carried out. ... However, in some cases, a data controller
> can consider that a processing meeting only one of these criteria requires a DPIA.

| # | Criterion | Met | Why |
|---|---|---|---|
| 1 | Evaluation or scoring | No | No person is scored, profiled or predicted about. |
| 2 | Automated decision-making with legal or similar effect | No | No decisions are taken about data subjects at all. |
| 3 | Systematic monitoring | **No, but arguably** | The retrieval is "pre-arranged, organised or methodical" in WP243's sense, but the criterion is about observing, monitoring or controlling *data subjects*. Historical analysis of logs their authors published is not monitoring. Counted as not met, deliberately conservatively. |
| 4 | Sensitive data or data of a highly personal nature | **Yes** | See below. |
| 5 | Data processed on a large scale | **Yes** | See below. |
| 6 | Matching or combining datasets | **Yes** | See below. |
| 7 | Vulnerable data subjects | No | UAV operators are not a category recital 75 contemplates. |
| 8 | Innovative use or new technological solutions | **No, but arguably** | Nothing here is technologically novel — reanalysis joins and log parsing are ordinary. The *corpus* is new; the technology is not. Counted as not met. |
| 9 | Prevents exercising a right or using a service | No | The processing affects nobody's access to anything. |

**Criterion 4 — data of a highly personal nature.** WP248 names our data type explicitly:

> These personal data are considered as sensitive (as this term is commonly understood)
> because they are linked to household and private activities ... or because they impact
> the exercise of a fundamental right (such as **location data whose collection questions
> the freedom of movement**) ...

And it anticipates this project's strongest counter-argument — that the logs are already
public — and declines to treat it as an exemption:

> In this regard, **whether the data has already been made publicly available** by the data
> subject or by third parties **may be relevant**. The fact that personal data is publicly
> available may be considered as a factor in the assessment **if the data was expected to
> be further used for certain purposes**.

Public availability is a factor, weighed against expected further use. An uploader
submitting a flight report to have a controller problem diagnosed did not expect
population-scale research. The factor runs against us, not for us.

**Criterion 5 — large scale.** WP248 gives four factors and all four point the same way:

| Factor | This project |
|---|---|
| number of data subjects | tens of thousands of distinct uploaders; 450,395 public logs, a frame of 79,477 (28,402 inside the retention window) |
| volume and range of data items | 26 metadata fields per record, plus full telemetry including position, in every retrieved `.ulg` |
| duration or permanence | the corpus spans 2016–2026 and PX4 publishes it in perpetuity |
| geographical extent | worldwide |

**Criterion 6 — matching or combining datasets.** WP248's wording is the project's own
design statement read back:

> Matching or combining datasets, for example originating from two or more data
> processing operations performed for **different purposes** and/or by **different data
> controllers** in a way that would **exceed the reasonable expectations of the data
> subject**.

PX4 collects logs for flight review and debugging; ECMWF publishes ERA5 for climate
science; this project joins them for a third purpose neither was collected for. Different
purposes, different controllers, and a use no uploader had in view. The join is not an
incidental feature of the design — it *is* the design.

**Three criteria against a threshold of two.** Even discounting 3 and 8 entirely, which
this screening does, the test is met.

## Route 3 — Article 35(4): the Garante's list. **Met, and by direct description.**

The Italian supervisory authority's list under Article 35(4) is Allegato 1 to
provvedimento n. 467 of 11 October 2018 (GU n. 269, 19 November 2018), twelve types of
processing. This is not a rule of thumb; it is the list of processing for which the
authority has determined the obligation exists. Two entries apply, and the first describes
this project almost literally:

> **4.** Trattamenti su larga scala di dati aventi carattere estremamente personale (v. WP
> 248, rev. 01): si fa riferimento, fra gli altri, ai dati connessi alla vita familiare o
> privata ..., o che incidono sull'esercizio di un diritto fondamentale (**quali i dati
> sull'ubicazione, la cui raccolta mette in gioco la libertà di circolazione**) ...

> **9.** Trattamenti di dati personali effettuati mediante **interconnessione,
> combinazione o raffronto di informazioni** ...

Large-scale processing of location data, and processing by combination of datasets. The
controller is established in Italy, so this list is the one that binds.

## What this changes

**1. The DPIA is a precondition of retrieval, not of publication.** Article 35(1) says
"prior to the processing". The processing that meets criterion 4 is reading positions out
of a `.ulg`. Publication controls — ADR-0009's aggregate-only rule, the k thresholds — are
*mitigations the DPIA will describe*; they do not postpone it. 07 listed the DPIA
alongside the publication items, and that placement was wrong.

**2. Nothing done so far required one, and that was not luck.** The corpus audit read
`dbinfo`, which carries **no coordinates**. Criterion 4 is therefore not met by the
metadata layer; only criterion 5 is, and one criterion does not presumptively trigger the
obligation. The Garante's item 4 likewise requires data "aventi carattere estremamente
personale", which the metadata is not. **The work completed to date sits cleanly on the
permitted side of the line**, and it does so because
[ADR-0005](adr/0005-sample-from-metadata-not-bulk-download.md) put the metadata first for
unrelated reasons. The boundary is exact and worth stating: it is the first `.ulg`.

**3. Article 36(1) may follow.** If the DPIA concludes the processing "would result in a
high risk in the absence of measures taken by the controller to mitigate the risk", the
controller "shall consult the supervisory authority **prior to processing**". Whether that
is reached depends on whether the mitigations already designed are judged sufficient. They
are substantial — aggregate-only publication, no raw redistribution, k ≥ 20 runs and 10
vehicles, no `vehicle_uuid`, no free text — and the honest position is that this is
plausibly *not* reached. It is not a question this screening can settle, and assuming the
comfortable answer is exactly the failure mode the project refuses elsewhere.

## What the DPIA must contain, and where the answers already are

Article 35(7) requires four elements. Most of the content exists; the DPIA is assembly
plus the controller's judgement, not fresh research.

| Art. 35(7) element | Where it already is | Still needed |
|---|---|---|
| (a) systematic description of the processing and its purposes | [`00-scope.md`](00-scope.md), [`04-methodology.md`](04-methodology.md), [`02-data-model.md`](02-data-model.md) | the legitimate-interest statement written out as such |
| (b) necessity and proportionality assessment | [`07-personal-data.md`](07-personal-data.md) B3, and the Art. 89(1) data-minimisation argument | a statement of why no less intrusive design achieves H1 |
| (c) assessment of the risks to rights and freedoms | 07 B1/B4/B5 — singling out, linkability, the public-raw-corpus problem | risk *severity and likelihood*, which 07 does not grade |
| (d) the measures envisaged to address the risks | [ADR-0009](adr/0009-aggregate-only-for-positional-results.md), the k thresholds, the exclusion mechanism | the exclusion mechanism must exist, not merely be promised |

Article 35(7) is quoted here in substance rather than verbatim: it was read in summary in
this pass, and the DPIA itself should quote it from EUR-Lex directly.

## Sources

| Source | Read | Used for |
|---|---|---|
| GDPR Art. 35(1), 35(3)(a)–(c) — verbatim | 2026-08-25 | the test, and route 1 |
| GDPR Art. 36(1) — verbatim | 2026-08-25 | prior consultation |
| WP29 WP248 rev.01, *Guidelines on Data Protection Impact Assessment*, endorsed by the EDPB, §III.B criteria 1–9 and the two-criteria rule — verbatim | 2026-08-25 | route 2 |
| Garante, Allegato 1 to provvedimento n. 467 of 11 Oct 2018, doc. web 9058979 (GU 269/2018), items 1–12 — verbatim, read from the PDF | 2026-08-25 | route 3 |

Art. 35(1), 35(3) and 36(1) were read from `gdpr-info.eu`, a mirror rather than the
official text: EUR-Lex returned an empty document on three attempts from here. The
quoted wording should be confirmed against EUR-Lex before the DPIA is signed. The two
sources that carry the decisive reasoning — WP248 and the Garante's list — were read
from the issuing bodies' own PDFs.
