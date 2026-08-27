# ADR-0002 — OpenODD is the representation model, not the taxonomy

- **Status:** accepted
- **Date:** 2026-08-20

## Context

Earlier framings described the corpus as "aligned to ISO 34503 / PAS 1883". This is
wrong in a way that would not survive contact with anyone who works on the standards:
ISO 34503 specifies ODD for road vehicles and ADS, and PAS 1883 is an automotive
taxonomy which appears to have been withdrawn (to verify in M1). Neither is a
reference standard for UAS, and claiming alignment to them for a UAS corpus is a
claim about a standard that does not cover the domain.

ASAM OpenODD 1.0 is a different kind of object: a **metamodel**. It defines how to
represent taxonomies, supports multiple taxonomies, custom concepts and user-defined
types, can import external taxonomies, and exists explicitly in service of measuring
ODD coverage and its boundaries.

## Decision

Separate the three layers: OpenODD as the representation model, ISO 34503 as a
vocabulary reused where semantically applicable, and a UAS ODD taxonomy as the domain
vocabulary. Use the phrasing "UAS-specific ODD taxonomy represented using the ASAM
OpenODD model, reusing ISO 34503 concepts where semantically applicable". Never claim
alignment or conformance.

## Consequences

- The coverage question (H3) is expressible in the model that was designed for it.
- The project owes a UAS vocabulary — but only after the M0 prior-art check against
  JARUS, ASTM, EASA and ASAM. `schemas/odd_taxonomy.yaml` stays unwritten until then.
- If a usable UAS taxonomy already exists, the project adopts and contributes to it.
  That outcome costs the prior-art check and saves everything else.
- PAS 1883 is relegated to the bibliography regardless of its status.

## Alternatives considered

Inventing a bespoke ODD representation would be faster and would not be reusable by
others. Claiming ISO 34503 alignment would appear stronger to non-specialists while
discrediting the work among the specialists whose assessment matters.
