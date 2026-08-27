# ADR-0012 — No open question waits for a reply

- **Status:** accepted
- **Date:** 2026-08-25
- **Supersedes in part:** the standing arrangement in
  [`../outreach/README.md`](../outreach/README.md), under which four audit rows were
  parked on a forum thread.

## Context

The M0 thread was posted on 2026-08-20 and asked four questions. As of 2026-08-25 it has
had **no replies in five days**, against 21 views. Two of the four were answered without
it — the `wind_speed` encoding from `flight_review` source, and `expver` from real
retrievals. The remaining two, plus A8 and B2's second half, were still recorded as
"pending on the thread".

That is a dependency on an event nobody controls and nobody has promised. It is also a
dependency of a specific kind: the questions are *judgements* about someone else's
service, so no amount of further reading resolves them, and waiting is the only strategy
the current framing allows. A project with a time-box rule that forbids extensions
justified by sunk cost should not have an open-ended wait as its critical path.

Asking was right. Waiting was never the plan; it became the plan by default.

## Decision

**Every open question carries a decision that holds without an answer, plus a statement
of what an answer would change.** A reply is treated as new evidence that may revise a
recorded position, never as a precondition for taking one.

The four parked rows are decided as follows.

**A2 — acceptable retrieval volume. Decided: operate strictly inside the upstream
client's own documented limits.** `app/download_logs.py`, which the maintainers write and
ship, defaults to a 6-second delay (10 requests/minute), caps at `--max-num 10`, warns
above 100 files, backs off on `503` honouring `Retry-After`, and treats `403`/`444` as a
block. Those limits are the service's published position, expressed in code they
maintain — a maintainer's opinion could only be equal or more permissive. Operating at
their own stated limits requires no further permission. If asked to stop, stop: that is
a consequence of the position, not a condition on it.

**A6 — is `dbinfo` a supportable interface. Decided: assume it is not.** It is treated as
a convenience that may vanish without notice. The consequence is already in place: the
manifest records the content hash and `Last-Modified` of the exact dump used, so the
frame is pinned to a file rather than to an endpoint. If it disappears, the analysis
remains describable and the frame remains stated; it does not remain re-derivable, and
that is recorded as a known limitation rather than discovered as a surprise. The dump is
not redistributed to work around this — it is 450,395 people's metadata, and CC-BY does
not make that a good idea.

**A8 — are old `.ulg` files still downloadable. Decided: measure it, as a byproduct of
the first stratified sample.** Every sampled log either downloads or does not, so
availability is recorded per record as an outcome of the requests the analysis already
needs. This answers the question with **zero additional load**, which is what made a
separate probe uncomfortable: `robots.txt` disallows every path, and a survey crawl would
have been a crawl. If availability proves low, the sampler re-draws within the surviving
population and the frame is restated in `02b` with both numbers.

**B2's second half — is PX4's own notice at upload adequate. Decided: out of scope,
permanently.** It is a question about Dronecode's obligations as controller of their
service. Our Article 14(5)(b) route does not turn on the answer: our notice is required
whatever they did, and their compliance is neither our defence nor our liability. Closing
it removes a row that could never have been closed here.

## Consequences

- The M0 thread stops being a dependency and becomes a **channel**. It is still needed
  for one thing, and that thing is a posting rather than a waiting: art. 6(3) of the
  Garante's deontological rules requires the privacy notice to be published where the
  data subjects actually are, and for this population that is the forum, not a file in a
  repository. Posting does not require anyone to reply.
- A8 moves off the "blocked on you" list and into the sampler's requirements. The sampler
  must record per-record availability, which it would otherwise not have bothered to do.
- The critical path shortens to one item: the DPIA and its adoption. Nothing else is
  waiting on anybody.
- Audit rows A2, A6, A8 and B2b are rewritten from "pending" to "decided, and here is
  what would change our mind". A late reply is welcome and revises them.

## Alternatives considered

**Wait longer.** The thread may still be answered — but no date can be put on it, and
every week of waiting is a week the time-box rule says should have forced a scope
reduction instead. Waiting is also asymmetric: the questions are opinions, so a reply
mostly *confirms* a decision we can already justify.

**Escalate to the Dronecode Discord**, where the dev calls actually happen. Reasonable,
and it would probably work. Rejected as the primary route for the same reason as waiting:
it substitutes one unowned event for another. It stays available as a courtesy channel
once there is something worth reporting back — which, after a first sample, there will
be.

**Proceed with bulk retrieval on the theory that CC-BY permits it.** The licence governs
copyright, `robots.txt` expresses the operator's wishes, and the two are not the same
instrument. ADR-0005 already decided this and nothing here reopens it.
