"""Inventory of a converted log sample: coverage, quality, estimator config, dedup.

Deliberately unwritten. This is the M2 deliverable and it cannot be designed against
imagined files: what it must compute is *what is actually present* in the logs, and
that is unknown until a sample exists on disk.

Contract, once written (docs/00-scope.md, M2):

- per-run field coverage, as a fraction of the run, written to ``schemas/run.json``
  shape -- a missing field is recorded as missing, never a dropped run;
- firmware and airframe distribution;
- geographic and seasonal distribution;
- share of ``PX4_SITL``, kept as a separate control population and never merged;
- estimator configuration and reported variance per run
  (``schemas/estimator_config.json``), including ``reconstructible: false`` where it
  cannot be recovered -- that count is itself an M2 finding and feeds the risk that
  the study narrows to fixed-wing with airspeed;
- duplicate detection across re-uploads of the same flight.

Blocked on: M1 (may we download), M3 (converted Parquet available).
"""
