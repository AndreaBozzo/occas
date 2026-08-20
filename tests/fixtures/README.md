# Fixtures

Synthetic, hand-written by this project, describing no real flight and no real person.
Kept that way on purpose: the licence and personal-data questions for real PX4 logs are
open (see [`../../docs/01-source-audit.md`](../../docs/01-source-audit.md)), and a test
fixture is not a good reason to answer them by assumption.

When real logs become admissible, fixtures may be replaced by a minimal excerpt with a
verified licence, recorded here with its attribution.

`records/` holds one valid example per schema, plus deliberately invalid variants under
`records/invalid/` — a validator that never rejects anything guards nothing.
