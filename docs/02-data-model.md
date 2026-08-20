# 02 — Data model

Schemas live in [`../schemas/`](../schemas/) and are the normative form; this file
explains them.

## Entities

| Entity | Meaning |
|---|---|
| `Run` | One flight, with vehicle / firmware / source metadata |
| `EstimatorConfig` | Mechanism, parameters and uncertainty of the onboard estimator |
| `OperationalEvent` | A time window with class, severity and confidence |
| `TelemetryFeatureWindow` | Features derived from onboard telemetry |
| `ContextFeatureWindow` | Features derived from external sources |
| `ODDAnnotation` | Position of the run within the operating space |
| `SourceMetadata` | Licence, version, retrieval |
| `ValidationArtifact` | Agreement statistics per regime |
| `AnalysisManifest` | Versions, parameters, hashes, reproducibility |

`EstimatorConfig` and `ValidationArtifact` exist because of how H1 is framed: if
neither wind source is ground truth, the configuration and uncertainty of the onboard
estimator are part of the data, not an implementation detail.

## Join key

```text
(run_id, time_interval, geospatial_extent)  →  external_context(time, location)
```

Every context feature carries:

```text
source · source_version · retrieved_at · processing_version
spatial_resolution · temporal_resolution · join_method
interpolation_method · quality_flags
context_uncertainty · validation_model_id · validation_regime
```

### `context_uncertainty` is a regime property, not a per-row error

There is no observed error per row, because there is no ground truth to subtract.
`context_uncertainty` points at a `ValidationArtifact` through `validation_model_id`,
and `validation_regime` declares which population that estimate applies to. The error
statistics live in the validation artifact; they are not replicated onto every row.

Reading a context feature therefore always answers two questions: what value was
joined, and under which measured agreement regime that value was produced.

## Run admission

Field-level **coverage is recorded explicitly**; a run is not silently dropped for a
missing field, it is recorded as missing.

Desired fields: coherent timestamps; position; mode transitions; GNSS quality;
estimator state **and estimator configuration**; wind estimate **with variances**;
IMU/attitude; airspeed where present; battery; event/failsafe; firmware and airframe
metadata.

`PX4_SITL` is excluded from the real-flight study corpus and kept as a separate
control population — never merged, never silently mixed.

## Storage

Parquet for portable artifacts (consistent with `flight-review-rs`), Arrow for
in-memory representation, DuckDB for local queries, DataFusion if an embeddable
engine is ever needed, Lance only if real versioned multimodal workloads appear.

**The format is never a differentiator. Do not invent one.**
