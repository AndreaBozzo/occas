# M0b — the privacy notice, as a forum post

**Not sent — but complete, as of 2026-08-25.** Draft for the PX4 forum, carrying the full Article 14 notice inline so it needs no working link to be effective. Publishing it is the controller's to do.

## Why the forum and not just the repository

Article 14(5)(b) GDPR lets a research project skip informing tens of thousands of people
individually, on condition that it makes the information publicly available instead. The
Italian deontological rules for statistical and scientific research are more specific
about what that means (Allegato A5, art. 6(3)): where individual notice is a
disproportionate effort, the controller uses "idonee forme di pubblicità", and among the
listed forms is "inserzione in strumenti informativi di cui gli interessati sono
normalmente destinatari" — publication in the channels the data subjects actually read.

For PX4 log uploaders, that is not a file in a git repository nobody has heard of. It is
`discuss.px4.io`. Those rules do not bind an unaffiliated researcher
([`../07-personal-data.md`](../07-personal-data.md)), but they describe what adequate
publicity looks like, and the cost of following them here is one forum post.

Post it in the same category as the M0 thread. Linking it from that thread costs nothing
and reaches the people who already engaged.

---

## Draft post

**Title:** Using public PX4 logs for a weather-agreement study — what we process, and how
to opt out

Hi all,

Some of you replied to or read my earlier thread about characterising the public log
corpus. This is the follow-up I owe you: a plain statement of what the project does with
your logs, and how to tell me to leave yours out.

**What the project is.** An open research corpus that links public PX4 flight logs to the
weather they were flown in, to answer one question: how well does ERA5 reanalysis wind
agree with the onboard EKF2 wind estimate, and in which conditions does it stop agreeing.
Neither source is treated as ground truth — it is an agreement study, not a validation of
one against the other.

**What it processes.** Only logs that are already public on `logs.px4.io`, plus the public
metadata dump. That includes `vehicle_uuid`, vehicle names, the free-text description and
feedback fields, and — inside the logs — the flight trajectory. Some of that can relate to
an identifiable person: a `vehicle_uuid` links all flights of one airframe, and take-off
points are often someone's home or regular field.

**What gets published.** Aggregate statistics only. Nothing per-flight that contains a
position, no matter how coarsely rounded, because a rounded row can still be matched back
to its log through the public corpus. No `vehicle_uuid`, hashed or otherwise. No free
text. Every published cell aggregates at least 20 flights from at least 10 different
airframes, at a spatial resolution no finer than the weather grid itself (0.25°, about
25 km). What gets published instead of data is the pipeline, so anyone can re-run it
against the same public logs.

**Legal basis** is legitimate interests, Article 6(1)(f), for scientific research, as
further processing for research purposes under Article 5(1)(b) with the safeguards in
Article 89(1). This post *is* the notice — everything Article 14 requires is below rather
than behind a link, so there is nothing to click and nothing to rot.

**Who is responsible.** Controller: Andrea Bozzo. Contact: <andreabozzo92@gmail.com>. No
DPO is appointed; the processing does not meet the Article 37(1) thresholds.

**Where the data comes from.** Nothing is collected from you directly. Everything comes
from the public corpus at `logs.px4.io` and its public metadata dump.

**Recipients and transfers.** None. Nothing is shared with anyone. Weather data is
*retrieved from* Copernicus/ECMWF, which involves sending them nothing about you.

**How long.** Downloaded logs are deleted once converted; derived intermediate data is
kept only while the analysis it supports is being produced and verified. Published
aggregates are permanent and are designed not to identify anyone.

**Your rights.** Access, rectification, erasure, restriction, and — because the basis is
legitimate interests — the right to **object at any time under Article 21**. You may also
complain to the Garante per la protezione dei dati personali (`garanteprivacy.it`) or to
the authority where you live.

**What this project does not do.** No automated decision-making, no profiling of people,
no attempt to identify anyone, no advertising, no sale of data. The question is about the
weather, not about you.

**If you would rather your flights were not used**, reply here or write to
<andreabozzo92@gmail.com> with your `vehicle_uuid`, a log id, or a link. I will exclude them and
keep them excluded — no reason needed, and no argument from me. Note that this only
affects my corpus; your log stays public on `logs.px4.io` unless you ask the maintainers
separately.

Happy to answer questions about the method, and criticism of it is welcome — that is
rather the point of posting.

---

## Before posting

- ~~fill in the contact address~~ — done 2026-08-25;
- ~~publish `PRIVACY.md` at a stable URL~~ — **dropped 2026-08-25, and the post rewritten
  to carry the whole notice inline.** The repository is private, so a link to `PRIVACY.md`
  would have 404'd for every single person it was meant to inform — which is not
  "making the information publicly available" in any sense Article 14(5)(b) recognises.
  A notice that depends on a link is a notice that can fail; this one cannot. When the
  repository goes public, add the link *as a backup*, because a forum thread can be
  edited or deleted and `PRIVACY.md` is then the durable copy;
- record the date and the URL in [`README.md`](README.md) in this folder, since the
  outreach log is the record, not the thread;
- decide whether to accept opt-outs by forum reply as well as by email. Accepting replies
  is friendlier and makes the mechanism visible to others, at the cost of having to watch
  the thread.
