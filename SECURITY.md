# Security and data protection

This repository ships no network service and no deployed system. Its risk surface is the
data it processes and the results it publishes, not an exploitable runtime.

## Reporting

Report privately to **<andreabozzo92@gmail.com>**. Do not open a public issue for
anything in the categories below, because the issue itself would publish what it reports.

Expect an acknowledgement within seven days.

## What is in scope

- **Personal data appearing in a published artifact.** Coordinates, `vehicle_uuid`
  values, operator-identifying text, or an aggregate cell that draws on fewer than 20
  runs from 10 distinct vehicles
  ([ADR-0009](docs/adr/0009-aggregate-only-for-positional-results.md),
  [`docs/09-dpia.md`](docs/09-dpia.md) §4.1). Include the file and the manifest id.
- **A re-identification route** through published aggregates, including linkage between
  two separately published tables — a risk the DPIA records and does not consider
  closed.
- **A credential or token committed to history.** The CDS personal access token is read
  from the environment and `.env` and `.cdsapirc` are gitignored, but report anything
  that reached a commit.
- **A published number that cannot be regenerated** from the manifest that attests it.
  This is a defect in the project's only durable claim
  ([ADR-0004](docs/adr/0004-no-result-without-a-manifest.md)).

## What is not in scope

Dependency advisories with no path to this code, findings against `PX4/flight-review-rs`
(report those upstream), and the deliberate absence of a usefulness threshold's
regulatory backing — the 3.0 m s⁻¹ band is asserted rather than cited, and says so in
[`docs/06-limitations.md`](docs/06-limitations.md).

## Objecting to the use of your flight data

This is a data-protection request, not a security report, and it does not require a
reason. Write to the address above; the procedure and your rights under Articles 15–21
are set out in [`PRIVACY.md`](PRIVACY.md). Logs are removed from the corpus and added to
a permanent exclusion list so that later runs do not re-include them.
