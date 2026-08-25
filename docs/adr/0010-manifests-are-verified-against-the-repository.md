# ADR-0010 — A manifest is verified against the repository, not against itself

- **Status:** accepted
- **Date:** 2026-08-25
- **Tightens:** [ADR-0004](0004-no-result-without-a-manifest.md), which required that a
  manifest exist and said nothing about it being checkable by anyone else.

## Context

Three defects were found together, in review of the only analysis this project has so
far run. Each is small. Together they meant the provenance chain closed on paper and
nowhere else.

**1. The recorded output hash reproduced for nobody.** `main()` wrote the artifact with
`Path.write_text`, which translates `\n` to `\r\n` on Windows. `hash_file` then hashed
those CRLF bytes. `.gitattributes` is `* text=auto eol=lf`, so git stored and checked
the file back out as LF. The committed artifact hashed to `382ca78a…`; the committed
manifest asserted `522349d3…`. Restoring the CRLF reproduces the recorded hash exactly,
which is how the cause was identified. Nothing detected it: CI's CRLF check passes,
because by the time git has the file it *is* LF, and the manifest tests only ever
hashed a temporary file they had written moments earlier.

**2. `code.dirty` could not be false.** `build_manifest` captures `git status` over the
whole tree, and it was called *after* the artifact was written. The artifact is tracked.
So any run that changed its own result dirtied the tree before its own state was read,
and reported `dirty: true` — as both committed manifests do. `require_publishable`
existed, was correct, and was unreachable for this entrypoint. "Run it from a clean
checkout" was not a fix, because the run makes the checkout unclean.

**3. Two numbers in [`../02b-dbinfo-inventory.md`](../02b-dbinfo-inventory.md) were not
produced by the script that page says produces every number on it.** The `≥ 120 s` tier
was correct but computed ad hoc; the rotorcraft total was off by 25 and its provenance
is unknown. A third number, the fixed-wing subtype breakdown, was script-produced but
counted over a different population than the total it was printed beside — the
distribution included SITL, the total did not, and neither said so.

## Decision

A manifest asserts facts about the repository, so the repository is where they are
checked: every committed artifact must re-hash to a hash some committed manifest
records, and that is a test. Code state is captured before outputs are written, hashed
bytes are written `newline="\n"`, and any figure that appears in prose is emitted by
the script that computed it.

## Consequences

- `tests/test_manifest.py::test_every_committed_artifact_is_attested_by_a_committed_manifest`
  re-hashes what is committed. *Some* manifest, not all: a superseded manifest
  attests an earlier version of the same path, and that history is kept rather than
  rewritten. Both new tests were confirmed to fail against the unfixed tree first.
- `build_manifest` must be called before the outputs it will describe. Its docstring
  says so; `add_output` already said the converse. Analyses written later inherit the
  constraint whether or not they read this file.
- `dirty: false` is now reachable, so `require_publishable` becomes a usable gate
  rather than a decorative one. It is still not wired into the audit entrypoint —
  exploratory runs are legitimate and must stay cheap. What changed is that the clean
  run is now possible at all.
- Publication needs one more step than before: commit the code, *then* run, *then*
  commit the artifact and manifest together. The manifest names the commit that
  produced the result, which is the commit before the one that carries it.
- The audit emits `mav_type_all` / `mav_type_real` / `mav_type_sitl` untruncated, four
  cumulative duration tiers, and an `airframe_class_real` partition that sums to
  `real_hardware`. Prose that mixes two populations now contradicts an artifact instead
  of contradicting nothing.

## Alternatives considered

**Hash with newlines normalised, so the platform stops mattering.** Rejected: it makes
the hash a hash of an interpretation rather than of a file, and it would silently
succeed on a genuinely different byte stream. The rule that a hash is over bytes is
worth more than the convenience.

**Write the artifact outside git and commit only the manifest.** Rejected: the artifact
is 4 KB and is the evidence. A manifest attesting a file nobody has is a receipt for a
missing parcel.

**Let `require_publishable` reject dirty runs at the entrypoint.** Rejected for now, and
deliberately: a gate that blocks exploratory runs gets bypassed, and a bypassed gate is
worse than an unwired one. The gate belongs at the point where a number is published,
which does not exist yet.
