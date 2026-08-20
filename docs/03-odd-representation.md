# 03 — ODD representation

## Architecture

```text
ASAM OpenODD      = representation model (metamodel)
ISO 34503         = automotive vocabulary, reused where semantically applicable
UAS ODD taxonomy  = domain vocabulary, adapted or produced by this project
```

ASAM OpenODD 1.0 is a **metamodel, not a taxonomy**: it defines how to represent
taxonomies, supports multiple taxonomies, custom concepts and user-defined types, and
can import external taxonomies. It is explicitly in service of measuring ODD coverage
and its boundaries — which is exactly what H3 needs.

ISO 34503:2023 specifies ODD for **road vehicles / ADS**. Its vocabulary is reusable
where semantically applicable. It is not a reference standard for UAS.

## Wording

Use:

> *UAS-specific ODD taxonomy represented using the ASAM OpenODD model, reusing
> ISO 34503 concepts where semantically applicable.*

Do **not** use: "UAS corpus aligned to ISO 34503". Alignment and conformance are
claims about a standard that does not cover this domain.

## Prior art check — blocking

[`../schemas/odd_taxonomy.yaml`](../schemas/odd_taxonomy.yaml) **must not be written**
before this section is filled in. The gap is that ODD machinery is mature for
automotive and absent for UAS — but adapting automotive ODD to a new domain is an
already-practised pattern (an agricultural ODD framework built on OpenODD/ISO 34503
exists). This is a known move applied to an uncovered domain, not an invention.

| Body | What to look for | Found? | Checked on |
|---|---|---|---|
| JARUS | Any ODD or operating-envelope taxonomy work for UAS | TBD | — |
| ASTM (F38 and related) | UAS operational-limitation taxonomies | TBD | — |
| EASA | ODD-equivalent structures in SORA 2.5 / Specific category material | TBD | — |
| ASAM | Existing non-automotive OpenODD taxonomies, aviation or otherwise | TBD | — |
| Literature | Published UAS ODD taxonomies | TBD | — |

If a usable taxonomy exists, **use it** and contribute to it. Producing a competing
one would be a cost with no result.

A first machine-readable OpenODD-compatible UAS ODD taxonomy is a possible **secondary
outcome**, not the thesis of the project.
