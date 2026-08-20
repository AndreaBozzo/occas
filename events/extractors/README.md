# Event extractors

Empty on purpose. Event definition is the most fragile part of the project, and H1 is
deliberately constructed not to depend on it.

Extractors are written only after H1 is published, and even then they start from what
already exists — UAV-SEAD's annotated classes and the diagnostic analysers in
`flight-review-rs` (motor failure, GPS interference, battery brownout, EKF failure,
RC loss) — rather than from a new ontology.

Every extractor emits `OperationalEvent` records with `provenance.method` set to
`project_extractor`, so derived detections are never mistaken for expert annotations.
