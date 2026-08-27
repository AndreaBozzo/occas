# 09 — Data Protection Impact Assessment (Article 35 GDPR)

> **STATUS: ADOPTED — version 1, 2026-08-25.** Adopted by the controller, Andrea Bozzo,
> who accepted §5's conclusion that Art. 36(1) consultation is not required and the §7.4
> gaps as stated. Gate G1 is `CLEARED` as of the same date and
> `ingest/px4_download.py` will now retrieve — see
> [ADR-0011](adr/0011-the-dpia-is-a-precondition-of-retrieval.md). A second and
> independent flag, `R5-encryption-at-rest` in §4.2, gates the same wrapper: G1 asks
> whether this assessment was adopted, R5 whether one measure it relies on is real.
> Article 35(11) requires review
> when any §7.3 trigger fires; processing pauses until that review completes.

| | |
|---|---|
| Controller | Andrea Bozzo (individual; no establishment, no DPO — see §7.1) |
| Processing | occas — linking public PX4 flight telemetry to the external conditions it was flown in |
| Assessment required by | Art. 35(1) via WP248 criteria 4, 5, 6; and Art. 35(4) via Garante items 4 and 9 |
| Screening | [`08-dpia-screening.md`](08-dpia-screening.md), 2026-08-25 |
| Version | 1 |
| Drafted | 2026-08-25 |
| Adopted | **2026-08-25**, version 1 |
| Next review | on adoption + on any trigger in §7.3 |

Article 35(7) prescribes four elements. They are §§1–4 below. §§5–8 are the parts that
make it a live instrument rather than an essay: the residual-risk determination that
decides Article 36, the review triggers, and the adoption block.

---

## 1. Systematic description of the processing and its purposes — Art. 35(7)(a)

### 1.1 What is done, in order

1. **Metadata frame** *(already done, 2026-08-20)*. One HTTP request to
   `cdn.logs.px4.io/dbinfo.json`, a published CDN artefact: metadata for all 450,395
   public logs. **No coordinates.** Characterised in
   [`02b-dbinfo-inventory.md`](02b-dbinfo-inventory.md); this step is the reason the
   remaining steps can be small.
2. **Sampling**. A stratified sample is drawn from the frame of **79,477** non-SITL logs
   of ≥ 300 s.

   **The pilot was 100 runs, and it ran on 2026-08-25.** Its purpose was to establish
   whether conversion works, whether estimator configuration is readable across
   heterogeneous vehicles — gate G2's actual question — and whether the ERA5 join holds
   end to end. All three hold. **No agreement statistic was computed from it**: it tested
   the design, not the hypothesis.

   It found that usability splits almost entirely by airframe — 72 % and 52 % of
   fixed-wing/VTOL runs are usable against 8 % and 4 % of rotorcraft, because multirotors
   mostly do not log wind. **The H1 draw is therefore 1,600 fixed-wing/VTOL logs**
   (800 per retention cell, 1,584 distinct vehicles), expected to yield of order 10³
   usable runs — the design point, reached with about a third of the downloads a
   corpus-proportional draw would have needed.

   The frame is the upper bound; anything past it is outside this assessment (§7.3). At
   this size, and with raw logs deleted after conversion (§4.2), R5 stays under the
   severity cap §5 relies on.
3. **Retrieval**. The sampled `.ulg` files are downloaded through the maintainers' own
   client at its documented limits — 10 requests/minute, no bulk pull
   ([ADR-0005](adr/0005-sample-from-metadata-not-bulk-download.md),
   [ADR-0012](adr/0012-no-open-question-waits-for-a-reply.md)). Excluded records are never
   requested (§4.4).
4. **Conversion**. `ulog-convert` from `PX4/flight-review-rs` converts to columnar form.
   No parser is written here ([ADR-0001](adr/0001-no-ulog-converter.md)).
5. **Context join**. Each run's time and position window is joined to ERA5 reanalysis
   fields on a 0.25° (~25 km) grid. **Positions are sent nowhere**: ERA5 is retrieved by
   bounding box and hour, and those requests carry no identifier and no per-run data.
6. **Analysis**. Agreement statistics between ERA5 and the onboard EKF2 wind estimate, per
   regime ([ADR-0003](adr/0003-h1-is-agreement-not-calibration.md),
   [ADR-0006](adr/0006-what-h1-compares.md)). The unit of independence is the run.
7. **Publication**. Aggregate statistics only, under the constraints in §4.1. Raw logs and
   per-run positional rows are never redistributed
   ([ADR-0009](adr/0009-aggregate-only-for-positional-results.md)).

### 1.2 Categories of personal data

| Category | Where from | Notes |
|---|---|---|
| Flight trajectory — GPS position and time | inside the `.ulg` | The material category. Take-off and landing points are frequently homes or habitual sites. |
| `vehicle_uuid` | metadata | Persistent identifier linking every flight of one airframe. Personal data under Recital 26 even without a name. |
| Free text — `description`, `feedback`, `vehicle_name` | metadata | May contain names, places, or incident narrative. Never published (§4.1); read only where an analysis needs it, which at present is nowhere. |
| Flight date, duration, airframe, firmware | metadata | Low sensitivity alone; **the linkage set** that makes a rounded position re-identifiable against the public corpus (§3.2). |

No special categories under Art. 9. No Art. 10 data. No imagery or audio — a ULog carries
neither.

### 1.3 Categories of data subject

UAV operators who uploaded a flight report to PX4 Flight Review and thereby made it
public. **Not bystanders**: nothing in a ULog records third parties. Tens of thousands of
distinct uploaders across the corpus; of order 10³ in the sample.

The population is not a random slice of PX4 users. `is_public = 1` is reachable only
inside the `flightreport` upload branch, so the public corpus is the flight-report
population *by construction* — a selection statement that belongs in every claim made
from it, and one the data subjects did not choose.

### 1.4 Recipients, transfers, retention

- **Recipients:** none. Nothing is shared with third parties.
- **Transfers outside the EEA:** none. ERA5 is retrieved *from* Copernicus/ECMWF; no
  personal data is sent to them or to anyone else.
- **Retention:** downloaded logs and derived intermediates are kept only while the
  analysis they support is produced and verified, then deleted. Published aggregates are
  permanent and designed not to identify anyone. **The deletion step is in the pipeline as
  of 2026-08-25**, not in a promise: `ingest/convert.sh` with `PRUNE_RAW=1` removes each
  `.ulg` once its conversion has produced Parquet. A retention period that is never
  enforced is not a retention period.

### 1.5 The legitimate interest pursued — Art. 6(1)(f), first limb

The interest is **scientific**: establishing whether, and in which operational regimes,
atmospheric reanalysis is a trustworthy proxy for the conditions a real autonomous flight
actually met. Nobody has published that. It matters because reanalysis is already being
used as operational context for UAV work, and "used" is not "validated" — including
knowing where it fails, which is a publishable result in its own right
([`00-scope.md`](00-scope.md) gate G3).

The interest is real, present and specific, not speculative. It is also **third-party
benefiting**: the beneficiaries are UAV operators, regulators and researchers, which is
the category Recital 47 contemplates.

---

## 2. Necessity and proportionality — Art. 35(7)(b)

### 2.1 Lawfulness: the Article 6(1)(f) three-step test

Structured per EDPB Guidelines 1/2024.

**Step 1 — is the interest legitimate?** Yes. §1.5. Scientific research is named in
Recital 159 and Art. 89 as a purpose the Regulation actively accommodates.

**Step 2 — is the processing necessary for it?** Yes, and the necessity is unusually
tight, because each alternative fails for a stated reason rather than an inconvenience:

| Alternative | Why it does not answer H1 |
|---|---|
| Simulated flights (`PX4_SITL`) | A different population by construction, kept as a control and never merged. SITL wind is prescribed, so comparing ERA5 against it measures the simulator. |
| Existing curated datasets | Checked and rejected on the record: UAV-SEAD has global position on 8.8 % of flights and **no wind or airspeed topic at all**; ALFA is a different autopilot with no ULog; BASiC is SITL-only. Audit rows C2b, C3b, C4. |
| Metadata alone | `dbinfo` has **no coordinates**. Every geography-dependent question — which is all of H1 — needs the log. |
| Coarser positions at retrieval | Position is inside the `.ulg`; there is no interface that serves it pre-generalised. Coarsening happens immediately after conversion (§4.2), which is the earliest technically possible point. |
| Consent | Art. 14(5)(b) exists precisely because contacting tens of thousands of uploaders is disproportionate; and consent obtained from a self-selecting minority would bias the population, making the result worse *and* less lawful under Art. 5(1)(c). |
| Fewer runs | Below roughly 10³ runs the per-regime stratification collapses and the study cannot distinguish where agreement fails from noise — which is the entire question. |

**Step 3 — does the interest override the data subjects' interests and rights?** On
balance yes, and the reasoning is set out honestly in both directions.

*Toward the controller:* the logs were **deliberately published** by their uploaders,
under CC-BY, on a form that tells them logs may be used for statistical analysis. The
research purpose is remote from anything adverse to them. No decision is taken about any
person. Nothing is shared. Publication is aggregate-only.

*Toward the data subject:* location data engages freedom of movement, and take-off points
are often homes. WP248 is explicit that prior public availability is "a factor in the
assessment **if the data was expected to be further used for certain purposes**" — and
someone uploading a flight report to have a controller problem diagnosed did not have
population-scale research in view. **This factor runs against the controller and is not
treated as an exemption.** The uploaders are also not a group with any power to negotiate.

*What tips it:* not the public availability, which is weak. It is the combination of (a) a
purpose that needs no identification at all, (b) Art. 89(1)'s requirement — not
permission, requirement — that where purposes can be fulfilled without identifying
subjects, they *shall* be, which the aggregate-only design satisfies, (c) mitigations
that go beyond the ordinary (§4), and (d) an unconditional opt-out that is honoured by a
mechanism rather than a promise (§4.4). Remove (d) and this assessment would not conclude
in the controller's favour.

### 2.2 Purpose limitation — Art. 5(1)(b)

This is further processing of data collected by Dronecode for flight review and
debugging. Art. 5(1)(b) provides that further processing for scientific research purposes
is **not considered incompatible** with the initial purposes, subject to Art. 89(1)
safeguards, which §4 supplies.

### 2.3 Data minimisation — Art. 5(1)(c)

- Only the frame's sampled subset is retrieved; the other ~450,000 logs are never touched.
- Only the ULog topics H1 needs are converted and kept.
- Free text is not read into the analysis at all.
- `vehicle_uuid` is used for exactly two things — exclusion matching and clustering the
  bootstrap by vehicle — and never leaves the local store.

### 2.4 Accuracy, and the honesty constraints

Neither wind source is ground truth, and the project is forbidden from treating either as
such (ADR-0003). This is a scientific rule, but it is also a data-protection one: an
overstated result about individuals' operating conditions would be an inaccuracy the
subjects cannot correct.

### 2.5 Data subject rights, and how each is actually delivered

| Right | How it is delivered |
|---|---|
| Information (Art. 14) | Public notice under the 14(5)(b) exemption: [`../PRIVACY.md`](../PRIVACY.md), published where the subjects are per art. 6(3) of the deontological rules — the PX4 forum, not only the repository. **Outstanding: it is not a notice until published.** |
| Access, rectification, erasure, restriction | On request to the controller's published address. Feasible because the local store is small and keyed by `log_id` / `vehicle_uuid`. |
| **Object (Art. 21)** | Unconditional here: no reason required, no balancing applied against the objector. Honoured by `analysis/common/exclusions.py` — a permanent list, enforced before retrieval, covering later uploads of the same vehicle. §4.4. |
| Complaint | Garante, or the authority of the subject's residence. Stated in the notice. |

Art. 89(2) would permit derogating from access, rectification, restriction and objection
for research. **No derogation is claimed.** The rights are honoured in full, and that
choice is part of what makes §2.1 step 3 come out as it does.

---

## 3. Risks to the rights and freedoms of data subjects — Art. 35(7)(c)

### 3.1 Scale used

*Likelihood:* **remote** (needs an unlikely combination) · **possible** (a motivated party
could) · **likely** (expected in normal operation).
*Severity:* **limited** (annoyance, no lasting effect) · **significant** (real detriment,
recoverable) · **severe** (safety, home location, or irreversible exposure).

Risks are graded **before** mitigation, then again after, so the mitigations are visible
as doing work rather than assumed.

### 3.2 Risk register

| # | Risk | Inherent L | Inherent S | Residual L | Residual S |
|---|---|---|---|---|---|
| R1 | **Home or habitual site disclosed** through a published take-off position | likely | severe | remote | severe |
| R2 | **Re-identification of a "generalised" per-run row** by matching duration, airframe, firmware and date back against the public corpus | likely | significant | remote | significant |
| R3 | **Singling out from a sparse aggregate cell** — a cell with few runs effectively describes one operator | possible | significant | remote | significant |
| R4 | **Differencing across published tables** — two overlapping aggregations of the same runs reveal suppressed cells | possible | significant | remote | significant |
| R5 | **Local store compromised** — a corpus of geolocated trajectories on a personal machine | possible | severe | possible | significant |
| R6 | **Objection not honoured** because the mechanism is absent, forgotten, or lapses for later uploads | likely | significant | remote | significant |
| R7 | **Free text republished**, containing names or incident narrative | possible | significant | remote | significant |
| R8 | **Scope creep** — the corpus grows into a purpose this assessment never considered | possible | significant | remote | significant |

**R1 and R2 are the assessment's centre of gravity**, and they share a cause that is
outside the controller's power to remove: **the re-identification key is public and not
ours to delete.** WP216's escape route for event-level movement data is deleting the raw
data and publishing only high-level aggregates. Half of it is unavailable — PX4 publishes
the raw logs in perpetuity — so the other half has to carry the whole weight. That is why
§4.1 forbids per-run positional publication outright rather than rounding it.

**R5 is the risk that does not reduce to "remote"**, and it is stated plainly rather than
mitigated on paper: a personal machine is not a hardened environment. Severity falls from
severe to significant with encryption at rest and short retention; likelihood does not
fall much. It is the largest residual item in §5.

### 3.3 Risks explicitly assessed as not present

No automated decision-making (Art. 22). No profiling. No monitoring of a publicly
accessible area. No vulnerable-subject category. No special-category data. No
international transfer. Each was checked in [`08-dpia-screening.md`](08-dpia-screening.md)
rather than assumed.

---

## 4. Measures to address the risks — Art. 35(7)(d)

### 4.1 Publication controls *(R1, R2, R3, R4)*

- **No per-run row carrying a positional attribute is ever published, however
  generalised.** Rounding is pseudonymisation, not anonymisation (WP216 Table 6), and the
  public raw corpus defeats it. ADR-0009.
- **No `vehicle_uuid`, raw or hashed.** Hashing does not defeat singling out.
- **No free text** from `description`, `vehicle_name` or `feedback` *(R7)*.
- **Threshold:** no published cell draws on fewer than **20 runs from at least 10 distinct
  `vehicle_uuid`s**. Suppressed cells are reported *with their count*, because suppression
  that conceals its own occurrence introduces a distortion of its own. The Garante's
  deontological rules
  set a floor of three and require it to rise with sensitivity; 20/10 sits well above it
  *(R3)*.
- **Spatial resolution never finer than the 0.25° analysis grid** — chosen scientifically,
  coarse as a by-product rather than by design, and not relied on as the protection.
- **Cross-table check:** art. 5(e) of the deontological rules requires published results
  about the same population not to permit linkage between them. Every published table is
  checked against those already published, not only against its own threshold *(R4)*.

### 4.2 Processing controls *(R1, R5)*

- Positions are reduced to what the join needs immediately after conversion — the earliest
  technically possible point, since no interface serves position pre-generalised.
- Positions are never transmitted. ERA5 is fetched by bounding box and hour.
- **Local store encrypted at rest.** Done 2026-08-25: EFS on `data/`, where the corpus
  lands, via `cipher /e /s:data`. New files inherit it. Full-disk BitLocker was not used —
  it needs elevation, and the exposure is one directory, not the machine.

  **R5-encryption-at-rest: CONFIRMED**

  `ingest/px4_download.py` reads that flag and fails closed on anything else, so the
  measure gates the code rather than sitting in prose. What EFS covers: another local
  account, and the drive read outside this Windows user. What it does not: compromise of
  this account while logged in. That residual is R5's, and §5 grades it accordingly.
- Deletion on completion of the analysis the data supports.
- Manifests record what was read, so minimisation is auditable rather than asserted
  ([ADR-0004](adr/0004-no-result-without-a-manifest.md)).

### 4.3 Gate controls *(R8)*

- `ingest/px4_download.py` fails closed on a dedicated `G1-status` flag. It blocks on a
  missing file, a missing line, or any unrecognised value. It once turned on a phrase in
  prose and was opened by an edit; that is why it is a flag now.
- Every retrieval writes a record stamping `publication_eligibility`, so a constraint
  travels with the data rather than living in a document.
- Scope is bounded by [`00-scope.md`](00-scope.md), and H2/H3/DEM/GNSS are explicitly
  downstream of H1 and outside this assessment until reviewed (§7.3).

### 4.4 The Article 21 mechanism *(R6)* — built, not promised

`analysis/common/exclusions.py`, with `tests/test_exclusions.py`:

- A **missing** exclusion list is a fatal error, not zero exclusions. "Nobody objected" and
  "I did not check" are different states and only the first is safe to act on. Declaring
  the first costs an empty file.
- Checked **before anything is retrieved**, in `ingest/px4_download.py`.
- An objection naming a vehicle covers **later uploads of that vehicle**, so it does not
  quietly lapse.
- A malformed entry is fatal rather than skipped — skipping would drop exactly the record
  whose purpose is not to be dropped.
- Objectors may send a `vehicle_uuid`, a log id, **or a link**, because requiring a person
  exercising a right to look up an internal identifier makes the right harder to use.
- **The list is never published.** It lives outside version control. Publishing it would
  announce which operators exercised a right — a more revealing disclosure than the flight
  data the objection concerned. Manifests record the list's **digest and count**, never its
  contents.
- The acknowledged cost: a third party cannot reproduce our exact excluded set. Between
  reproducibility of a suppression list and the privacy of the people on it, this project
  takes the side of the people on it, and says so.

---

## 5. Residual risk, and whether Article 36 is triggered

Art. 36(1) requires prior consultation with the supervisory authority where the DPIA
"indicates that the processing would result in a high risk **in the absence of measures
taken by the controller to mitigate the risk**".

Read literally, that condition is met by almost any processing that needed a DPIA, which
cannot be the intent; the settled reading is that consultation is required where a **high
residual risk remains after** mitigation.

**Assessment: residual risk is not high, with one qualification.**

- R1–R4, R6–R8 fall to *remote* likelihood, because the mitigations are structural rather
  than procedural — a rule that forbids publishing a class of row cannot be forgotten in
  the way a rule that says "be careful" can.
- **R5 does not.** A corpus of geolocated trajectories on a personal machine carries a
  *possible* likelihood of compromise and a *significant* severity after encryption and
  short retention. It is the one item that mitigation reduces rather than removes.

R5 alone is judged not to constitute high residual risk, because its severity is capped by
the small sample size, short retention, and the fact that the underlying logs are already
public — the marginal exposure from a compromise is the *aggregation*, not the trajectories
themselves, which anyone can already download.

**Conclusion: prior consultation under Art. 36(1) is not required.** This is a judgement
and the controller owns it. Consultation is available and free, and is the right response
if any §7.3 trigger fires — particularly a scope increase beyond 10³ runs, which would
raise R5's severity by making the local store a genuinely unique asset.

## 6. Data subjects' views — Art. 35(9)

Art. 35(9) says the controller "shall, where appropriate, seek the views of data subjects
or their representatives". It is qualified, not absolute.

Views have been **sought and not obtained**. A thread on the PX4 forum has been open since
2026-08-20 with no replies. Under [ADR-0012](adr/0012-no-open-question-waits-for-a-reply.md)
that is recorded as a fact rather than treated as a blocker. Publishing the privacy notice
in the same channel is itself a further solicitation: it states the objection route, and
an objection is a view.

**No claim is made that data subjects have endorsed this processing.** They have not been
asked in a way that produced an answer, and silence is not consent.

---

## 7. Governance

### 7.1 DPO

Not required. Art. 37(1) triggers are core-activity large-scale systematic monitoring, or
large-scale special-category processing. Neither applies: there is no monitoring, and no
Art. 9 data. Recorded because "no DPO" should be a finding, not an omission.

### 7.2 Records of processing — Art. 30

Art. 30(5) exempts organisations under 250 people **unless** the processing is not
occasional or involves special categories. This processing is not occasional, so the
exemption does not apply and a record is required. §1 of this document is that record in
substance; it should be extractable as one.

### 7.3 Review triggers — Art. 35(11)

Review is mandatory when any of these occurs, and processing pauses until it completes:

- sample size exceeds **10³ runs by more than an order of magnitude**, or the frame's
  definition changes materially;
- any new data category enters — imagery, uploader email, anything from a source other
  than the public corpus;
- scope extends to H2, H3, DEM or GNSS;
- publication moves beyond aggregate statistics in any respect;
- a university affiliation arises, which makes the Garante's deontological rules binding
  and adds art. 3's documented-project requirement. **Confirmed 2026-08-25: none exists
  and none is planned**, so the rules stay a voluntary benchmark. This trigger fires on
  the affiliation arising, not on someone later noticing that it did;
- an objection cannot be honoured by the §4.4 mechanism;
- any personal-data breach, whether or not notifiable;
- relevant new guidance or case law — the General Court's judgment on remittal in
  *EDPS v SRB* (C-413/23 P) is a specific one to watch.

### 7.4 Known gaps in this draft

Stated rather than glossed, because a DPIA that hides its own soft spots is worth less
than one that names them:

- Art. 35(1), 35(3), 35(4) and 36(1) were read from two independent mirrors that agree
  verbatim; **EUR-Lex returned an empty document on four attempts.** Art. 35(7)'s
  subparagraphs are followed in substance, not quoted. Confirm against EUR-Lex before
  adoption.
- The retention period in §1.4 is a policy, not yet a pipeline step. It should become one
  before it is relied on.
- Encryption at rest (§4.2) — **closed 2026-08-25**, EFS on `data/`. Listed here as it
  stood at drafting, when it was outstanding.
- R5's severity cap assumes the sample stays of order 10³. §7.3 makes that a review
  trigger for exactly this reason.

---

## 8. Adoption

Adopted. Adoption meant accepting §5's conclusion that Art. 36(1) consultation is not
required, and the §7.4 gaps as acceptable or closed.

| | |
|---|---|
| Adopted by | **Andrea Bozzo** |
| Role | Controller |
| Date | **2026-08-25** |
| Version adopted | **1** |
| Art. 36(1) consultation | **not required** — §5 |
| §7.4 gaps | **accepted as stated** |

The gaps accepted, restated so that accepting them is a decision on the record and not a
sentence someone scrolled past:

1. Art. 35(1), 35(3), 35(4) and 36(1) are quoted from **two independent mirrors that agree
   verbatim**, because EUR-Lex returned an empty document on four attempts. Art. 35(7)'s
   subparagraphs are followed in substance rather than quoted. Nothing in the reasoning
   turns on a disputed word, but the confirmation remains outstanding.
2. ~~The retention period in §1.4 is a policy, not yet a pipeline step.~~ **Closed
   2026-08-25**: `ingest/convert.sh` deletes each `.ulg` once its conversion has produced
   Parquet (`PRUNE_RAW=1`). The guard is deliberately strong — `ulog-convert` reports
   `"converted": true` and creates an output directory for a file that is not a ULog at
   all, so neither its success flag nor the directory's existence is evidence, and this is
   a delete. Only Parquet on disk counts. Roughly a two-thirds reduction in the geolocated
   corpus held locally, which is R5's exposure.
3. **Encryption at rest — closed the same day.** EFS applied to `data/`; the
   `R5-encryption-at-rest` flag is `CONFIRMED` and gates the download wrapper. The part it
   does not cover — compromise of the logged-in account — is stated in §4.2 and graded in
   §5 rather than left unlisted.

**Both items with teeth are now closed** — encryption on 2026-08-25, retention the same
day. What remains outstanding is item 1, the EUR-Lex confirmation, which affects the
citation of the articles and not the reasoning drawn from them.

**On adoption**, in the same change: set `**G1-status: CLEARED**` in
[`01-source-audit.md`](01-source-audit.md), which is the single flag
`ingest/px4_download.py` reads, and note the adoption date in
[`outreach/README.md`](outreach/README.md). `tests/test_ingest_gate.py` contains a test
asserting the gate still blocks; **updating that test is the deliberate act of clearing
the gate**, and it should be done in the same commit and nowhere else.
