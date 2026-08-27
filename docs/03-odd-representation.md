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

`schemas/odd_taxonomy.yaml` **must not be written**
before this section is filled in. The gap is that ODD machinery is mature for
automotive and absent for UAS — but adapting automotive ODD to a new domain is an
already-practised pattern (an agricultural ODD framework built on OpenODD/ISO 34503
exists). This is a known move applied to an uncovered domain, not an invention.

| Body | Finding | Checked on |
|---|---|---|
| ASAM | **OpenODD 1.0.0 released 2025-04-03**, free of charge — a released standard, not a concept paper. Automotive-scoped, but explicitly a metamodel supporting custom concepts and imported taxonomies. No aviation taxonomy published in it. | 2026-08-20 |
| ISO / BSI | ISO 34503:2023 supersedes PAS 1883:2020. **PAS 1883:2025** exists as an *implementation guide* for BS ISO 34503, not a rival taxonomy. Both remain road-vehicle scoped. | 2026-08-20 |
| Literature (aviation) | **Closest prior art found.** Torens, Gupta, Roy, Sprockhoff, Durak, *From Operational Design Domain to Runtime Monitoring of AI-Based Aviation Systems*, DASC 2024, DOI 10.1109/DASC62030.2024.10749267 (DLR + TU Clausthal, open access). Models a UAS ODD, exports YAML, transforms it into an RTLola runtime-monitoring specification, and **checks flight log files for ODD violations** — validated on PX4/Pixhawk 4 flight-test logs from DLR HorizonUAM. | 2026-08-20 |
| Literature (other domains) | Felske, Redenius, Happich, Schöning, *Toward an Agricultural Operational Design Domain: A Framework*, arXiv 2511.02937 (Nov 2025) — Ag-ODD built on ASAM OpenODD and CityGML, extending the PEGASUS 6-layer model. Confirms "adapt automotive ODD to a new domain" as an established pattern. | 2026-08-20 |
| JARUS | *Methodology for Evaluation of Automation for UAS Operations*, approved at the Rome Plenary 2023-04-21, uses ODD as the operational-boundary concept for UAS. **Whether it contains an actual taxonomy is unverified** — the JARUS site returned a TLS error. Must be read before any taxonomy work. | 2026-08-20, unresolved |
| ASTM | No ODD-specific F38 standard found. ASTM **F3269** (runtime assurance reference architecture) is the adjacent standard, and is what the DASC paper builds toward. Committee-level search only; not exhaustive. | 2026-08-20, weak |

### What the DASC 2024 paper does and does not occupy

It occupies **"historical envelope violations"** — row 3 of
[`05-sora-evidence-map.md`](05-sora-evidence-map.md). Checking logs against a declared
ODD is done, published, and demonstrated on PX4 logs.

It does not occupy this project's thesis. Their ODD is vehicle state only — flight
altitude, speed, pitch, roll — bounded by what an onboard ML constituent was trained
on. There is no external context, no corpus, and no population: two use cases, their
own flight tests.

Their stated open problem is this project's premise, verbatim:

> "For weather information, it might be necessary to rely on external data rather than
> attempting to identify the degree of rain at the moment. In this case, the ODD
> develops into a complex hierarchical model that relies on a multitude of sensors,
> inputs, and online information."

Their future work — "automated mapping using standardized log files or tagged log
files" — is a collaboration hook, not a competing claim.

If a usable taxonomy exists, **use it** and contribute to it. Producing a competing
one would be a cost with no result.

A first machine-readable OpenODD-compatible UAS ODD taxonomy is a possible **secondary
outcome**, not the thesis of the project.
