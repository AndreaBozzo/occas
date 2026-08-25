"""ERA5 retrieval via the Copernicus CDS API, with cache and provenance.

Retrieval metadata is captured *here*, at retrieval time, because it cannot be
reconstructed afterwards (``adr/0004``): which release was served, under which licence,
from which dataset version, when. The release marker in particular is not recoverable
later -- ERA5T is published with about five days' latency and may be replaced by final
ERA5 two to three months on, and a rerun after that revision moves without a line of
our code changing.

**A retrieval that cannot produce a release marker is an error** (``adr/0008``). Not a
warning, not a null field. The marker survives the CDS's NetCDF today only because of a
GRIB-to-NetCDF conversion step with a version number in it, and ECMWF's own
documentation still says it does not; a pipeline that silently recorded nothing would
fail months later, when a published number stops reproducing and no manifest can say
whether the data changed underneath it.

Variables follow ``adr/0006``: 100 m u/v is the primary vertical reference, 10 m u/v is
retained as the secondary whose difference from it is itself a stratifier for shear.

The CDS personal access token is read from the environment, never from this repository:
``COPERNICUS_API_KEY`` if set -- which is where this project keeps it, in a gitignored
``.env`` -- otherwise whatever ``cdsapi`` resolves for itself (``CDSAPI_URL`` /
``CDSAPI_KEY``, or ``~/.cdsapirc``). The token is not logged and does not enter a
manifest; what gets recorded is the retrieval, not the credential.

Still open: ARCO-ERA5, the account-free copy, marks the release boundary with a store
attribute ``valid_time_stop_era5t`` rather than a per-field ``expver``. It is a second
route to the same requirement and is deliberately unwritten -- no analysis needs it yet,
and it would add ``zarr`` and ``gcsfs`` to the dependency set to serve none.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

DATASET = "reanalysis-era5-single-levels"
# The dataset DOI, read from the CDS catalogue on 2026-08-24 (audit row C5). It is the
# citable identity of the product and belongs in the manifest next to the retrieval.
DATASET_DOI = "10.24381/cds.adbb2d47"
# Not an SPDX identifier, because there is none: the instrument is the Licence to use
# Copernicus Products, revision 12, licensor the European Union represented by ECMWF.
LICENCE = "Licence to use Copernicus Products, revision 12"
# Clause 5 prescribes the wording, and it differs for modified products. Everything this
# project publishes is derived, so the "Contains modified" form is the one that applies;
# the unmodified form is here because getting it wrong is a licence breach, not a typo.
ATTRIBUTION_MODIFIED = "Contains modified Copernicus Climate Change Service information {year}"
ATTRIBUTION_UNMODIFIED = "Generated using Copernicus Climate Change Service information {year}"
# Clause 5.1.3 requires this alongside the attribution in any publication.
DISCLAIMER = (
    "Neither the European Commission nor ECMWF is responsible for any use that may be "
    "made of the Copernicus information or data it contains."
)

# adr/0006: 100 m is the declared primary vertical reference and 10 m the secondary.
# Both are retrieved in one request because the difference between the two results is a
# reported stratifier, not an afterthought -- fetching 10 m later would be a second
# retrieval, at a second time, of a product that may have been revised in between.
WIND_VARIABLES: tuple[str, ...] = (
    "100m_u_component_of_wind",
    "100m_v_component_of_wind",
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
)

CACHE_DIR = Path("cache/era5")
CDS_API_URL = "https://cds.climate.copernicus.eu/api"


class MissingReleaseMarker(RuntimeError):
    """Raised when a retrieval produced no ``expver``.

    Deliberately fatal. See ``adr/0008``: the alternative is a manifest that cannot
    say which release its numbers came from, which is indistinguishable from a manifest
    that is wrong.
    """


def build_request(
    *,
    start: datetime,
    end: datetime,
    bbox: tuple[float, float, float, float],
    variables: Sequence[str] = WIND_VARIABLES,
) -> dict[str, Any]:
    """Assemble a CDS request for an hourly window over a bounding box.

    ``bbox`` is ``(north, west, south, east)`` in degrees -- the CDS's own ``area``
    order, kept rather than normalised so that what is sent is what is written down.

    The request is expanded to whole hours because ERA5 *is* hourly: asking for the
    interval a flight occupied would silently return the hours it touches anyway, and a
    request that does not describe what comes back cannot key a cache honestly.
    """
    if end < start:
        raise ValueError(f"end {end.isoformat()} precedes start {start.isoformat()}")
    hours = _hours_spanned(start, end)
    days = sorted({h.date() for h in hours})
    if len({(d.year, d.month) for d in days}) > 1:
        # The CDS request grammar is a cross-product of year x month x day x time, so a
        # window crossing a month boundary would silently over-request days that do not
        # exist in the other month. Splitting is the caller's decision, not ours to
        # paper over.
        raise ValueError("request spans more than one calendar month; split it")
    return {
        "product_type": ["reanalysis"],
        "variable": list(variables),
        "year": [f"{days[0].year:04d}"],
        "month": [f"{days[0].month:02d}"],
        "day": sorted({f"{d.day:02d}" for d in days}),
        "time": sorted({f"{h.hour:02d}:00" for h in hours}),
        "area": list(bbox),
        "data_format": "netcdf",
        "download_format": "unarchived",
    }


def _hours_spanned(start: datetime, end: datetime) -> list[datetime]:
    """Every whole hour touched by the interval, inclusive of both ends."""
    current = start.replace(minute=0, second=0, microsecond=0)
    hours = []
    while current <= end:
        hours.append(current)
        current += timedelta(hours=1)
    return hours


def request_key(request: dict[str, Any]) -> str:
    """A stable digest of the request, used as the cache filename.

    Sorted and JSON-encoded so that two requests differing only in key order or list
    order hit the same cache entry, and two differing in any value do not.
    """
    canonical = json.dumps(request, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def cache_path(request: dict[str, Any], cache_dir: Path = CACHE_DIR) -> Path:
    return cache_dir / f"{request_key(request)}.nc"


def retrieve(request: dict[str, Any], cache_dir: Path = CACHE_DIR) -> tuple[Path, bool]:
    """Fetch the request unless it is already cached. Returns ``(path, was_cached)``.

    A cached file is never re-fetched. That is a courtesy to a free service, and it is
    also what makes an analysis re-run reproduce rather than re-sample: the cache holds
    the bytes the manifest hashed, and a silent refresh would break that quietly.
    """
    path = cache_path(request, cache_dir)
    if path.exists():
        return path, True

    path.parent.mkdir(parents=True, exist_ok=True)
    # Downloaded to a temporary name and moved into place, so an interrupted retrieval
    # cannot leave a truncated file that the next run treats as a valid cache hit.
    partial = path.with_suffix(".partial")
    _client().retrieve(DATASET, request).download(str(partial))
    partial.replace(path)
    return path, False


def _client() -> Any:
    """A CDS client, preferring this project's own environment variable for the token.

    ``cdsapi`` looks only at ``CDSAPI_URL``/``CDSAPI_KEY`` or ``~/.cdsapirc``. The token
    here lives in a gitignored ``.env`` as ``COPERNICUS_API_KEY``, so without this the
    client would fail to authenticate while both the repository and the environment
    plainly contain a working key -- a confusing failure with an obvious cause.
    """
    import os

    import cdsapi

    key = os.environ.get("COPERNICUS_API_KEY")
    if key:
        return cdsapi.Client(url=CDS_API_URL, key=key)
    return cdsapi.Client()


def read_release_marker(path: Path) -> str:
    """Return the ``expver`` carried by a retrieved file, or raise.

    ``0001`` is final ERA5 and ``0005`` is ERA5T. A request that straddles the boundary
    can carry both, so the value is normalised to a sorted, comma-joined string rather
    than assumed scalar -- a mixed retrieval is a legitimate thing to record, and a
    silently-truncated one is not.
    """
    import xarray as xr

    with xr.open_dataset(path) as dataset:
        marker = dataset.coords.get("expver", dataset.attrs.get("expver"))
        if marker is None:
            raise MissingReleaseMarker(
                f"{path} carries no expver. ERA5 release is then unrecoverable and the "
                f"retrieval cannot be recorded (docs/adr/0008)."
            )
        values = getattr(marker, "values", marker)
        # A scalar coordinate, an array of them, or a plain string attribute: all three
        # are shapes the CDS has been observed to produce, and normalising here keeps
        # the caller from having to know which it got.
        if hasattr(values, "ravel"):
            found = sorted({str(v) for v in values.ravel()})
        else:
            found = [str(values)]
    if not found or found == [""]:
        raise MissingReleaseMarker(f"{path} carries an empty expver (docs/adr/0008).")
    return ",".join(found)


def source_metadata(
    *,
    release_marker: str,
    retrieved_at: datetime | None = None,
    content_hash: str | None = None,
) -> dict[str, Any]:
    """A ``SourceMetadata`` record for a retrieval, satisfying ``schemas/source_metadata.json``.

    This is the ``source`` block of a manifest input, not a manifest: the analysis that
    uses the retrieval passes it to ``build_manifest`` alongside the cached file's path
    and hash, the same shape ``ingest/dbinfo_audit.py`` uses for the PX4 dump.

    ``source_version`` carries the dataset, its DOI and the release marker together,
    because all three are needed to re-retrieve the same thing and any one alone is
    insufficient: the DOI identifies the product, the marker identifies which release of
    it was served.
    """
    moment = retrieved_at or datetime.now(UTC)
    return {
        "source": "era5",
        "source_version": f"{DATASET} doi:{DATASET_DOI} expver={release_marker}",
        "source_url": "https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels",
        "retrieved_at": moment.isoformat(),
        "licence": LICENCE,
        "attribution": ATTRIBUTION_MODIFIED.format(year=moment.year),
        "content_hash": content_hash,
    }
