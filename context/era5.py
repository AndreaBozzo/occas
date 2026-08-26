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

**There are two routes to the same data, and this module holds both.** The CDS above is
the authoritative one and stays the citable identity of the product. ARCO-ERA5 -- the
account-free copy in Google Cloud Public Datasets -- is the one H1 reads at scale, because
a thousand usable runs is a thousand requests to a queued free service and that is more
than it should be asked for (``adr/0013``). The copy marks the release boundary with store
attributes rather than a per-field ``expver``, so the same requirement is met with
different evidence, and the two do not always agree: see ``ArcoCoverage``.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
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


# --------------------------------------------------------------------------------------
# ARCO-ERA5: the account-free route (adr/0013)
# --------------------------------------------------------------------------------------

# Read anonymously; the bucket is part of Google Cloud Public Datasets. The "-v3" is part
# of the store's name, not its Zarr format -- it carries v2 consolidated metadata, which
# is why it opens in one request instead of several hundred.
ARCO_STORE = "gs://gcp-public-data-arco-era5/ar/full_37-1h-0p25deg-chunk-1.zarr-v3"
ARCO_SOURCE_URL = "https://cloud.google.com/storage/docs/public-datasets/era5"
# The data stays under the Copernicus licence above; the copy asks to be cited too
# (audit row C5). Both travel, because dropping either is a licence problem.
ARCO_CITATION = "Carver & Merose, ARCO-ERA5, 22nd Conf. on AI for Env. Science, AMS, 2023"

# The store spells the variables out. Everything downstream speaks the CDS NetCDF short
# names, so the mapping lives here rather than in the analysis: one vocabulary, whichever
# route produced the numbers.
ARCO_VARIABLES: dict[str, str] = {
    "100m_u_component_of_wind": "u100",
    "100m_v_component_of_wind": "v100",
    "10m_u_component_of_wind": "u10",
    "10m_v_component_of_wind": "v10",
}

# Verified against the store on 2026-08-26, because getting either wrong is silent:
# latitude runs 90 -> -90 descending, and longitude runs 0 -> 359.75. The CDS route works
# in -180..180. A position at -122.3 asked of this store with no conversion does not
# fail -- `method="nearest"` clamps it to longitude 0.0 and returns a plausible wind
# speed from the Gulf of Guinea.
ARCO_LON_MIN, ARCO_LON_MAX = 0.0, 360.0


class OutsideStoreCoverage(RuntimeError):
    """Raised when a time falls outside what the ARCO store currently holds.

    Fatal, and it has to be: the store's ``time`` axis runs from 1900 to 2050 while its
    data begins in 1940 and ends a few days ago. Selecting an hour beyond the end does
    not raise -- the chunk is simply absent and Zarr hands back the fill value. Without
    this check a flight from next week would join to a field of NaNs, or worse to zeros,
    and nothing downstream would look wrong.
    """


@dataclass(frozen=True)
class ArcoCoverage:
    """What the store said about its own release boundaries, when it was opened.

    Recorded at read time and never inferred, for the reason ``adr/0004`` gives: these
    move. ``valid_time_stop`` advances monthly as final ERA5 is published and
    ``valid_time_stop_era5t`` advances daily, so the same window read three months apart
    can be ERA5T once and final the next time -- which is the whole point of recording a
    release marker at all.

    **The two routes can disagree, and on 2026-08-26 they did.** Of the pilot's 42
    windows, 41 got the same marker from the CDS and from this rule; one -- 2026-05-07 --
    was final ERA5 to the CDS on 2026-08-25 and ERA5T here, because this copy's
    ``valid_time_stop`` was still 2026-04-30. The copy lags the authority by about a
    month. That is a property of the copy, not an error, and it is why the marker is
    recorded together with the store and these boundaries rather than on its own.
    """

    valid_time_start: str
    valid_time_stop: str
    valid_time_stop_era5t: str
    last_updated: str
    store: str = ARCO_STORE

    @classmethod
    def from_dataset(cls, dataset: Any, store: str = ARCO_STORE) -> ArcoCoverage:
        try:
            return cls(
                valid_time_start=str(dataset.attrs["valid_time_start"]),
                valid_time_stop=str(dataset.attrs["valid_time_stop"]),
                valid_time_stop_era5t=str(dataset.attrs["valid_time_stop_era5t"]),
                last_updated=str(dataset.attrs["last_updated"]),
                store=store,
            )
        except KeyError as error:
            # The same rule as the CDS route's missing expver: a store that stopped
            # declaring its boundaries cannot support a release marker, and guessing one
            # is worse than stopping.
            raise MissingReleaseMarker(
                f"{store} does not declare {error}; the ERA5 release of anything read "
                f"from it would be unrecoverable (docs/adr/0008)."
            ) from error

    def release_marker(self, when: datetime) -> str:
        """``0001`` for final ERA5, ``0005`` for ERA5T -- the CDS's own vocabulary.

        The boundaries are dates and the data is hourly, so the comparison is by date and
        the boundary day is included: ``valid_time_stop = 2026-04-30`` means final ERA5
        covers every hour of 30 April.
        """
        day = when.astimezone(UTC).date()
        if day < date.fromisoformat(self.valid_time_start):
            raise OutsideStoreCoverage(
                f"{when.isoformat()} precedes the store's {self.valid_time_start}."
            )
        if day <= date.fromisoformat(self.valid_time_stop):
            return "0001"
        if day <= date.fromisoformat(self.valid_time_stop_era5t):
            return "0005"
        raise OutsideStoreCoverage(
            f"{when.isoformat()} is beyond the store's ERA5T horizon "
            f"({self.valid_time_stop_era5t}); it holds no data there and would return "
            f"a fill value rather than fail."
        )

    def state(self) -> dict[str, str]:
        """The boundaries as they were read, for a manifest's parameters."""
        return {
            "store": self.store,
            "valid_time_start": self.valid_time_start,
            "valid_time_stop": self.valid_time_stop,
            "valid_time_stop_era5t": self.valid_time_stop_era5t,
            "last_updated": self.last_updated,
        }


def open_arco(store: str = ARCO_STORE) -> tuple[Any, ArcoCoverage]:
    """Open the ARCO store read-only and anonymously. Returns ``(dataset, coverage)``.

    ``chunks=None`` keeps Dask out of it: a chunk here is one whole global field for one
    hour, so there is nothing to parallelise over for a point read and a scheduler would
    only add a dependency. ``consolidated=True`` is what makes the open cost one request
    rather than several hundred over 273 variables.
    """
    import xarray as xr

    dataset = xr.open_zarr(
        store,
        chunks=None,
        consolidated=True,
        decode_timedelta=False,
        storage_options={"token": "anon"},
    )
    return dataset, ArcoCoverage.from_dataset(dataset, store)


def arco_values_at(
    dataset: Any, when: datetime, lat: float, lon: float
) -> tuple[dict[str, float], float, float]:
    """The four ADR-0006 wind components at the grid point nearest a position.

    Returns the values under the CDS short names, plus the grid point actually used in
    the caller's own ``-180..180`` frame -- so the recorded distance-to-grid-point means
    the same thing whichever route produced the row.

    One point read pulls one whole global field per variable, because the store is
    chunked ``[1, 721, 1440]``. That is about 4 MB uncompressed per variable-hour and it
    is the price of the route: the caller should ask once per distinct hour, not once per
    window.
    """
    point = dataset[list(ARCO_VARIABLES)].sel(
        time=when.astimezone(UTC).replace(tzinfo=None),
        latitude=lat,
        longitude=lon % ARCO_LON_MAX,
        method="nearest",
    )
    values = {short: float(point[name].values.ravel()[0]) for name, short in ARCO_VARIABLES.items()}
    grid_lat = float(point["latitude"].values)
    grid_lon = float(point["longitude"].values)
    # Back to the frame the window is in, so haversine_km compares like with like rather
    # than measuring the long way round the planet.
    if grid_lon > 180.0:
        grid_lon -= 360.0
    return values, grid_lat, grid_lon


def arco_source_metadata(
    *,
    release_marker: str,
    coverage: ArcoCoverage,
    retrieved_at: datetime | None = None,
) -> dict[str, Any]:
    """A ``SourceMetadata`` record for an ARCO read.

    ``content_hash`` is ``None`` and that is honest rather than lazy: nothing is
    downloaded to a file to hash, and hashing the global field a point came from would
    record 4 MB of the planet as the provenance of one number. What identifies the read
    instead is the store, its ``last_updated``, and the boundaries that produced the
    marker -- all of which the manifest carries in its parameters via
    ``ArcoCoverage.state()``.
    """
    moment = retrieved_at or datetime.now(UTC)
    return {
        "source": "era5",
        "source_version": (
            f"arco-era5 {coverage.store} last_updated={coverage.last_updated} "
            f"expver={release_marker}"
        ),
        "source_url": ARCO_SOURCE_URL,
        "retrieved_at": moment.isoformat(),
        "licence": LICENCE,
        "attribution": f"{ATTRIBUTION_MODIFIED.format(year=moment.year)}. {ARCO_CITATION}",
        "content_hash": None,
    }


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
