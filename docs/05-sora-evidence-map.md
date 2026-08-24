# 05 — SORA evidence map

## What is established

Regulatory pull exists: EASA SORA 2.5 and Reg. (EU) 2019/947 define 10 steps, SAIL
I-VI and 24 Operational Safety Objectives, and require operational procedures to
consider environmental and meteorological conditions and the methods for obtaining
forecasts of them.

## What is not established

It is **not** established that an operational-coverage matrix derived from flight logs
is an artifact that an operator, a SORA consultant or an NAA would consider useful in
a safety case.

While the validation column below is empty, "safety-case evidence" is a **positioning
hypothesis, not product-market validation.** It may be written as a hypothesis. It may
not be announced as a value proposition.

## What SORA actually asks for

Read from **JARUS SORA v2.5 Annex E** (`JAR_doc_28`, 2024 public release), not from
recollection or from summaries of it. Three places in the framework touch weather, and
they ask for different things:

- **OSO #08, Criterion #1** — operational procedures, required from SAIL I upward,
  must include "procedures to evaluate environmental conditions before and during the
  mission (i.e., real-time evaluation) including assessment of meteorological
  conditions (METAR, TAFOR, etc.) with a simple recording system", and "procedures to
  cope with unintended adverse environmental conditions".
- **OSO #09** — the remote-crew training syllabus explicitly includes "meteorology and
  assessment of meteorological conditions".
- **OSO #24** — "UAS designed and qualified for adverse environmental conditions",
  applicable at Medium from SAIL III and High from SAIL IV. Integrity: "the UAS is
  designed to perform as intended in the environmental conditions **defined and
  reflected in the flight manual** or equivalent document." Assurance at Medium: "the
  applicant has supporting evidence that the required level of integrity is achieved.
  This is typically done by testing, analysis, simulation, inspection, design review
  **or through operational experience**."

**This relocates the hypothesis.** OSO #08 and #09 are about *forecasting and
procedure* — what the crew checks before and during a flight, and what they are trained
to do. A historical distribution of conditions is not that, and the first version of
this map quietly assumed it was. The artifact that a corpus can speak to is OSO #24:
the environmental envelope *declared in the flight manual*, and evidence that the
declaration is supported.

Annex E also opens a quantified route, its **alternative criterion for functional
test-based (FTB) methods**, available up to SAIL IV: evidence of FTB flight hours
"proportionate to the risk/SAIL of the operation", flown "within the full operational
scope/envelope intended by the UAS Operator" and under the procedures and training in
the operational authorisation. Its own worked example is 3,000 flight hours for a
SAIL III operation.

**And that is where the corpus stops.** FTB hours and in-service experience are the
*applicant's own*, on their UAS, under their authorisation. 24,924 hours of other
people's flights are not an applicant's evidence and no framing makes them so. What a
corpus can plausibly do is inform how an envelope is *defined* before it is declared,
and show how often real operations left declared envelopes. Anything beyond that is
an overclaim, and it is written here so that a later draft cannot make it by accident.

## The map

| Corpus artifact | Possible SORA use | Evidence required | Validated by a practitioner? |
|---|---|---|---|
| Weather-exposure distribution | Informing the environmental envelope declared under OSO #24 — not OSO #08, which asks for forecast procedures | Integrity: envelope "defined and reflected in the flight manual". Assurance at Medium (SAIL III): supporting evidence via testing, analysis, simulation, inspection, design review or operational experience; at High (SAIL IV+): "a competent third party validates the claimed level of integrity" | no |
| Operational coverage matrix | Scoping an FTB campaign — showing which parts of an intended envelope real operations actually cover | FTB flight hours proportionate to SAIL, within the full intended envelope, under the authorised procedures (Annex E worked example: 3,000 FH ≈ SAIL III). **Must be the applicant's own hours** | no |
| Historical envelope violations | OSO #08 contingency procedures "to cope with unintended adverse environmental conditions" — evidence about how often the case arises, not evidence of a procedure | Procedure definition and validation; the corpus informs the content, it does not discharge the objective | no |

The middle column is now answered from the standard. The last column is not, and cannot
be: it asks whether a practitioner would *use* this, which no document can say.

## How the column gets populated

Not by reasoning about it. By asking practitioners — operators in the Specific
category, SORA consultants, NAA-facing safety engineers — whether they would use such
an artifact, in which step, and what would have to be true for them to trust it. A
"yes, interesting" is not a validation; a description of where it would sit in their
own submission is.

Having read Annex E, the question to put to them is narrower and much more answerable
than "would this be useful":

1. When you declare an environmental envelope for OSO #24, where does the declaration
   come from today — the manufacturer's flight manual, your own flight experience, or
   a number chosen to be defensible?
2. Would evidence about conditions encountered across a *population* of flights change
   how you set that envelope, or is only your own fleet's experience admissible to you?
3. For an FTB campaign, how do you establish that your hours covered "the full
   operational scope/envelope"? Is under-coverage of the envelope something you have
   been challenged on?
4. Annex E says NAAs may define adequate standards, and that it "will be updated at a
   later point in time with a list of adequate standards based on the feedback provided
   by the NAAs". Is anyone you know of feeding into that?

Question 2 is the one that decides G5. If the answer is "only my own fleet counts",
the product trajectory ends there and the OSS stands — which is the outcome this gate
exists to detect early, not a failure.

If G5 fails: stop the product trajectory, keep the OSS. The research path M0-M5 has
value independently and its cost is already sunk into work that stands on its own.
