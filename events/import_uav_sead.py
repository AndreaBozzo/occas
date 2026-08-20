"""Import UAV-SEAD expert annotations as ``OperationalEvent`` records.

UAV-SEAD has the annotations; this project has the context. The event vocabulary comes
from there and from the diagnostic analysers already in ``flight-review-rs`` -- no
ontology is rebuilt here.

Expert annotation and derived detection are never conflated: ``provenance.method``
distinguishes them at the record level.

Blocked on: C1-C2 in docs/01-source-audit.md (licence, and what the four classes
actually annotate).
"""
