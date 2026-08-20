"""ERA5 retrieval via the Copernicus CDS API, with cache and provenance.

Contract, once written (M4):

- request by (time interval, bounding box) for the variables H1 needs;
- cache on disk, keyed by request, so an analysis re-run does not re-download;
- record ``dataset/product ID``, version and ``retrieved_at`` for every retrieval into
  a ``SourceMetadata`` record. **ERA5T is preliminary** and can be replaced by the
  final product, typically within 2-3 months: which one was used must be recoverable
  from the manifest, or the result is not reproducible;
- carry the Copernicus attribution string into every derived artifact.

Blocked on: C5-C6 in docs/01-source-audit.md (licence version and how the preliminary
product is identified in the response).
"""
