# ADR-0007 — Licences travel with the data: the blanket CC-BY release does not hold

- **Status:** accepted
- **Date:** 2026-08-24

## Context

[`DATA_LICENSES.md`](../../DATA_LICENSES.md) stated that derived artifacts are released
under CC-BY-4.0, with a one-line escape clause for stricter upstream terms. That was
written when every source in the table was CC-BY or unverified. Closing the remaining
C-rows of the audit produced two sources that are neither.

**Copernicus DEM** (`COP-DEM-GLO-30-F`) is free of charge and grants adaptation and
redistribution, but it is not a Creative Commons licence. Article 6 prescribes two
notices word for word — a different one once the data are modified — requires a
liability sentence to be carried in whatever licence covers our distribution, forbids
conveying official endorsement, and obliges us to bind subsequent users to the same
terms. Article 9 terminates the licence on breach. Those obligations do not stay with
us: they travel to anyone who takes our artifact.

**METAR** is worse than restricted, it is asymmetrically restricted. The NCEI ISD
readme states that "the non-U.S. data in ISD are subject to WMO Resolution 40
restrictions, and cannot be redistributed to other users or customers". The IEM archive
ingests ISD, so the restriction flows through the convenient interface as well. The
corpus is global; the permission is not.

A blanket "our outputs are CC-BY" would therefore have been false the first time an
artifact touched elevation or a station observation, and false in a way no reader could
detect — a CC-BY label is exactly what a downstream user relies on to skip reading
further.

## Decision

Release terms are decided **per artifact, from the sources that artifact actually
used**, and recorded in its manifest — not declared once for the repository.

## Consequences

- The manifest is the right place for this, because it already records retrieval at run
  time (ADR-0004). Which sources an artifact consumed is a fact the run knows; the
  release terms follow from it rather than from an editorial decision made months
  earlier.
- A DEM-derived artifact carries the Copernicus notices and the liability sentence, and
  cannot be labelled plain CC-BY-4.0.
- METAR stays a *local* third reference: retrieved and processed, and published only for
  U.S. stations. Whether an aggregate over non-U.S. stations is a redistribution is the
  same question as B5 in the audit and is answered with it, not separately and not
  optimistically.
- H3's topography work inherits a licence obligation, which is a reason to keep the DEM
  out of anything published before that obligation is implemented.
- This forbids the shortcut of relicensing upstream data by aggregating it. Aggregation
  changes the personal-data analysis; it does not change a redistribution term.

## Alternatives considered

**Keep the blanket CC-BY and rely on the escape clause.** The clause is correct and
unenforceable by a reader: it puts the burden of noticing the exception on the person
least able to. A licence statement that is right only if you already know the answer is
not a licence statement.

**Drop the DEM and METAR to keep one clean licence.** This would buy tidiness with
evidence. The DEM is the only global elevation source with terms this permissive, and
METAR is the only independent surface wind measurement available near a meaningful
fraction of flights — the one source in the stack that is neither a reanalysis nor an
onboard estimate. Losing it to avoid writing three sentences of attribution would be a
poor trade.
