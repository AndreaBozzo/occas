# Privacy notice

**Status: the operative notice is the forum post, not this file.** This repository is
private, so a link here reaches nobody it is meant to inform —
[`docs/outreach/privacy-notice-post.md`](docs/outreach/privacy-notice-post.md) therefore
carries the whole Article 14 notice inline and depends on no link at all. This file is the
same notice in the repository, kept in step with it, and becomes a useful durable copy if
the repository is ever made public: a forum thread can be edited or deleted.

Publishing the post is the controller's to do, and it is recorded in
[`docs/outreach/README.md`](docs/outreach/README.md) when done.

This notice exists because of Article 14(5)(b) GDPR. This project processes personal data
that it did not obtain from the people it concerns, so the ordinary duty is to inform each
of them individually. With tens of thousands of uploaders that is a disproportionate
effort, and the research exemption applies — but only on the condition that the controller
takes appropriate measures "including making the information publicly available". This is
that measure. The reasoning behind every statement here is in
[`docs/07-personal-data.md`](docs/07-personal-data.md).

## Who is responsible

| | |
|---|---|
| Controller | Andrea Bozzo |
| Contact | <andreabozzo92@gmail.com> |
| Project | occas — an open research corpus linking PX4 flight telemetry to the external conditions it was flown in |

## What data, and where it comes from

Nothing is collected from you directly. Everything comes from the **public** PX4 Flight
Review corpus at `logs.px4.io`, which publishes logs their uploaders chose to make public
under CC-BY.

From the published metadata: `vehicle_uuid`, `vehicle_name`, free-text `description` and
`feedback`, flight date and duration, airframe and firmware fields.

From the log files themselves: flight trajectory — GPS position and time — and onboard
sensor and estimator data.

Some of this may relate to you as an identifiable person: `vehicle_uuid` links every
flight of one airframe, free text may name people or places, and take-off and landing
points are often homes or regular flying sites.

## Why, and on what legal basis

**Purpose:** scientific research into how well public weather reanalysis (ERA5) agrees
with onboard wind estimates, and under which conditions it does not. The results are
published openly.

**Legal basis:** Article 6(1)(f) — legitimate interests. The interest is the research
above; it cannot be pursued without real flights flown in real conditions, and simulated
flights are a scientifically different population. The balancing takes account of the fact
that these logs were deliberately published by their uploaders under a licence, on a form
stating that logs are always allowed to be used for statistical analysis. It also takes
account of the fact that location data is sensitive in effect, which is why publication is
restricted as described below.

This is further processing for scientific research purposes, which Article 5(1)(b) does
not treat as incompatible with the original purpose, subject to the safeguards in Article
89(1).

## What is published, and what never is

**Published:** statistics aggregated across many flights — agreement between reanalysis
and onboard estimates, by regime. No cell of a published table draws on fewer than 20
flights from at least 10 distinct airframes, and spatial resolution is never finer than
the 0.25° (about 25 km) grid of the weather data itself. Cells below that threshold are
reported as suppressed, with their count.

**Never published:**

- any per-flight record containing a position, however coarsely rounded;
- `vehicle_uuid`, in any form, including hashed;
- free text from `description`, `vehicle_name` or `feedback`.

Raw logs are never redistributed. What is published instead is the pipeline, so that
anyone can re-run the analysis against the original public logs.

## Recipients and transfers

None. Nothing is shared with third parties. External services are used to *retrieve*
weather data (Copernicus/ECMWF), which involves sending them no personal data at all.

## How long

Downloaded logs and derived intermediate data are kept only while the analysis they
support is being produced and verified, and are deleted afterwards. Published aggregate
results are permanent, and are designed not to identify anyone.

## Your rights

You may request access to your data, its rectification or erasure, restriction of
processing, and — because the basis is legitimate interests — **you may object at any
time under Article 21**. Objecting is enough; you do not have to give a reason for us to
consider it, and in practice we will simply exclude your logs.

**If you would rather your flights were not used**, write to the contact address above
with your `vehicle_uuid`, a log id, or a link to your log. It will be excluded from the
corpus and added to a permanent exclusion list so that later runs do not re-include it.
This applies to logs which remain public on `logs.px4.io` — this project does not control
that service, and removing something there is a separate request to its operators.

You may also lodge a complaint with the Italian supervisory authority, the Garante per la
protezione dei dati personali (`garanteprivacy.it`), or with the authority in your country
of residence.

## What we do not do

No automated decision-making, no profiling of individuals, no attempt to identify anyone,
no advertising, and no sale of data. The research question is about the weather, not about
people.

---

*Last reviewed: 2026-08-24. Changes to this notice are tracked in the repository's git
history.*
