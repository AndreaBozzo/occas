# Schemas

JSON Schema (2020-12) definitions for the data model. These are normative; the prose
in [`../docs/02-data-model.md`](../docs/02-data-model.md) explains them.

| File | Entity |
|---|---|
| `run.json` | `Run` |
| `source_metadata.json` | `SourceMetadata` (referenced by most others) |
| `estimator_config.json` | `EstimatorConfig` |
| `operational_event.json` | `OperationalEvent` |
| `context_feature.json` | `ContextFeatureWindow` |
| `validation_artifact.json` | `ValidationArtifact` |
| `analysis_manifest.json` | `AnalysisManifest` |

`TelemetryFeatureWindow` and `ODDAnnotation` are not defined yet. They are written
when an analysis in progress needs them — the telemetry window when M3 produces one,
the ODD annotation only after the prior-art check below.

## `odd_taxonomy.yaml` is intentionally absent

It stays absent until the M0 prior-art check against JARUS, ASTM, EASA and ASAM is
complete and recorded in [`../docs/03-odd-representation.md`](../docs/03-odd-representation.md).
If a usable UAS ODD taxonomy already exists, this project adopts it rather than
competing with it. Writing the file before the check is how the check stops happening.
