"""Spatio-temporal join between run windows and external context, with quality flags.

The core of M4 and the one piece of logic in this repository that is genuinely ours.
Deliberately unwritten until there are real runs and real ERA5 fields to join, because
the tolerances are an empirical choice and the failure modes are not guessable.

Contract, once written (docs/04-methodology.md):

- join key ``(run_id, time_interval, geospatial_extent) -> external_context(time, location)``;
- every emitted row records the join method, the interpolation method, the spatial and
  temporal tolerances *and the actual* distance-to-grid-point and time mismatch, plus
  quality flags -- see ``schemas/context_feature.json``;
- sensitivity analysis over those tolerances is part of the deliverable, not an extra:
  if the result moves under plausible choices, that is the finding;
- ``context_uncertainty`` is attached by regime, pointing at a ``ValidationArtifact``,
  and is marked non-applicable where a row falls outside every validated regime.

``tests/test_alignment.py`` is written together with this module, against fixtures.
"""
