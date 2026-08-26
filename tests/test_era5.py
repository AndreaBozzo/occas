"""ERA5 retrieval records its release, or it fails.

No network here. The release-marker tests build NetCDF files carrying the shapes the
CDS has actually been observed to return -- a scalar ``expver`` coordinate, an array of
them across the ERA5/ERA5T boundary, and none at all -- because the one that matters is
the one nobody can produce on demand from a live service.

The fixtures describe no real retrieval: the wind values are arbitrary.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from context import era5

xr = pytest.importorskip("xarray", reason="the context extra is optional")
np = pytest.importorskip("numpy")


def _write(path, expver):
    """A minimal ERA5-shaped NetCDF. ``expver`` of None omits the coordinate entirely."""
    dataset = xr.Dataset(
        {"u100": (("valid_time",), np.array([3.5], dtype="float32"))},
        coords={"valid_time": np.array([0], dtype="int64")},
    )
    if expver is not None:
        dataset = dataset.assign_coords(expver=expver)
    dataset.to_netcdf(path)
    return path


def test_scalar_release_marker_is_read(tmp_path) -> None:
    path = _write(tmp_path / "final.nc", "0001")
    assert era5.read_release_marker(path) == "0001"


def test_mixed_release_markers_are_both_recorded(tmp_path) -> None:
    """A window straddling the boundary carries both, and both must survive.

    Recording only one would name a release the file does not entirely contain, which
    is worse than recording none: it is wrong rather than missing.
    """
    path = _write(tmp_path / "mixed.nc", np.array(["0001", "0005"]))
    assert era5.read_release_marker(path) == "0001,0005"


def test_a_retrieval_without_a_release_marker_is_fatal(tmp_path) -> None:
    """adr/0008: not a warning, not a null field.

    ECMWF's documentation still claims NetCDF carries no marker. If a future CDS
    release makes that true again, this is the line that stops the pipeline instead of
    letting it record nothing.
    """
    path = _write(tmp_path / "unmarked.nc", None)
    with pytest.raises(era5.MissingReleaseMarker, match="no expver"):
        era5.read_release_marker(path)


def test_request_covers_every_hour_the_window_touches() -> None:
    """A flight from 10:50 to 11:10 needs both hours, not the one it started in."""
    request = era5.build_request(
        start=datetime(2026, 1, 15, 10, 50, tzinfo=UTC),
        end=datetime(2026, 1, 15, 11, 10, tzinfo=UTC),
        bbox=(45.6, 9.0, 45.4, 9.3),
    )
    assert request["time"] == ["10:00", "11:00"]
    assert request["day"] == ["15"]
    assert request["variable"] == list(era5.WIND_VARIABLES)


def test_request_spanning_midnight_keeps_both_days() -> None:
    request = era5.build_request(
        start=datetime(2026, 1, 15, 23, 30, tzinfo=UTC),
        end=datetime(2026, 1, 16, 0, 30, tzinfo=UTC),
        bbox=(45.6, 9.0, 45.4, 9.3),
    )
    assert request["day"] == ["15", "16"]
    assert request["time"] == ["00:00", "23:00"]


def test_request_across_a_month_boundary_is_refused() -> None:
    """The CDS grammar is a cross-product, so this would silently over-request."""
    with pytest.raises(ValueError, match="more than one calendar month"):
        era5.build_request(
            start=datetime(2026, 1, 31, 23, 30, tzinfo=UTC),
            end=datetime(2026, 2, 1, 0, 30, tzinfo=UTC),
            bbox=(45.6, 9.0, 45.4, 9.3),
        )


def test_reversed_interval_is_refused() -> None:
    with pytest.raises(ValueError, match="precedes"):
        era5.build_request(
            start=datetime(2026, 1, 15, 12, tzinfo=UTC),
            end=datetime(2026, 1, 15, 11, tzinfo=UTC),
            bbox=(45.6, 9.0, 45.4, 9.3),
        )


def test_the_cache_key_ignores_ordering_but_not_values() -> None:
    """Two spellings of one request must share a cache entry; two requests must not."""
    base = era5.build_request(
        start=datetime(2026, 1, 15, 10, tzinfo=UTC),
        end=datetime(2026, 1, 15, 10, tzinfo=UTC),
        bbox=(45.6, 9.0, 45.4, 9.3),
    )
    reordered = dict(reversed(list(base.items())))
    assert era5.request_key(base) == era5.request_key(reordered)

    moved = dict(base, area=[45.7, 9.0, 45.4, 9.3])
    assert era5.request_key(base) != era5.request_key(moved)


def test_retrieve_returns_the_cache_without_a_client(tmp_path) -> None:
    """A cache hit must not touch the network -- ``cdsapi`` is not even imported.

    If this ever regressed, the failure would be an unnecessary request to a free
    service rather than a wrong number, which is exactly the kind of thing no
    assertion elsewhere would catch.
    """
    request = era5.build_request(
        start=datetime(2026, 1, 15, 10, tzinfo=UTC),
        end=datetime(2026, 1, 15, 10, tzinfo=UTC),
        bbox=(45.6, 9.0, 45.4, 9.3),
    )
    path = era5.cache_path(request, tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"not really netcdf")

    got, was_cached = era5.retrieve(request, tmp_path)
    assert (got, was_cached) == (path, True)


def test_source_metadata_satisfies_the_schema() -> None:
    from analysis.common.schema import validate

    record = era5.source_metadata(
        release_marker="0005",
        retrieved_at=datetime(2026, 8, 25, 12, tzinfo=UTC),
    )
    validate(record, "source_metadata.json")
    assert record["source_version"].endswith("expver=0005")
    assert record["attribution"] == (
        "Contains modified Copernicus Climate Change Service information 2026"
    )


def test_attribution_is_the_modified_form() -> None:
    """Clause 5: a publication containing adapted products needs "Contains modified".

    Everything this project publishes is derived, so the unmodified wording would be a
    licence breach rather than a stylistic slip. Audit row C5.
    """
    record = era5.source_metadata(release_marker="0001")
    assert record["attribution"].startswith("Contains modified")
    assert record["licence"] == "Licence to use Copernicus Products, revision 12"


# --------------------------------------------------------------------------------------
# ARCO-ERA5, the second route (adr/0013). Still no network: the store's grid convention
# and its release boundaries are both reproducible offline, and both are places where a
# mistake returns a plausible number instead of an error.
# --------------------------------------------------------------------------------------

# The boundaries the real store declared on 2026-08-26, which is when the semantics below
# were established by reading 42 windows through both routes.
COVERAGE = era5.ArcoCoverage(
    valid_time_start="1940-01-01",
    valid_time_stop="2026-04-30",
    valid_time_stop_era5t="2026-08-20",
    last_updated="2026-08-26 03:15:47.457969+00:00",
)


def _arco_shaped(lons, lats, values):
    """A store-shaped dataset: longitudes 0..360, latitudes descending, one hour."""
    when = np.array([np.datetime64("2026-01-15T12:00:00")])
    data = np.asarray(values, dtype="float32").reshape(1, len(lats), len(lons))
    return xr.Dataset(
        {name: (("time", "latitude", "longitude"), data) for name in era5.ARCO_VARIABLES},
        coords={
            "time": when,
            "latitude": np.array(lats, dtype="float32"),
            "longitude": np.array(lons, dtype="float32"),
        },
    )


def test_a_western_longitude_reaches_the_western_cell() -> None:
    """The trap this route brings with it, and the reason it is worth a test.

    ARCO is on ERA5's native 0..360 grid; everything else here works in -180..180. A
    position at -122.25 asked of the store unconverted does not fail -- ``nearest``
    clamps it to longitude 0.0 and returns a wind speed from the Gulf of Guinea. Four of
    the pilot's 42 windows are at negative longitudes, so this is the ordinary case, not
    an edge one.
    """
    dataset = _arco_shaped(lons=[0.0, 237.75], lats=[37.75], values=[[[-99.0, 4.25]]])
    when = datetime(2026, 1, 15, 12, tzinfo=UTC)

    values, grid_lat, grid_lon = era5.arco_values_at(dataset, when, 37.75, -122.25)

    assert values["u100"] == 4.25, "read the prime meridian instead of California"
    assert grid_lat == 37.75
    # Reported back in the caller's frame: align.haversine_km compares this against the
    # window's own longitude, and 237.75 against -122.25 is most of a hemisphere.
    assert grid_lon == -122.25


def test_an_eastern_longitude_is_left_alone() -> None:
    dataset = _arco_shaped(lons=[104.25, 237.75], lats=[30.5], values=[[[1.5, -99.0]]])
    values, _, grid_lon = era5.arco_values_at(
        dataset, datetime(2026, 1, 15, 12, tzinfo=UTC), 30.5, 104.166
    )
    assert values["v10"] == 1.5
    assert grid_lon == 104.25


def test_the_release_marker_follows_the_stores_own_boundaries() -> None:
    """Final ERA5 up to and including ``valid_time_stop``; ERA5T beyond it.

    The boundary day is included: the attributes are dates and the data is hourly, so
    ``valid_time_stop = 2026-04-30`` covers every hour of 30 April.
    """
    assert COVERAGE.release_marker(datetime(2026, 4, 30, 23, tzinfo=UTC)) == "0001"
    assert COVERAGE.release_marker(datetime(2026, 5, 1, 0, tzinfo=UTC)) == "0005"
    assert COVERAGE.release_marker(datetime(2026, 8, 20, 23, tzinfo=UTC)) == "0005"


def test_an_hour_the_store_does_not_hold_is_fatal() -> None:
    """The store's time axis runs to 2050; its data does not.

    Selecting an hour past the end returns a fill value rather than raising, so the
    check has to happen before the read. A flight from next week joining to a field of
    zeros would look like data.
    """
    with pytest.raises(era5.OutsideStoreCoverage, match="ERA5T horizon"):
        COVERAGE.release_marker(datetime(2026, 8, 21, 0, tzinfo=UTC))
    with pytest.raises(era5.OutsideStoreCoverage, match="precedes"):
        COVERAGE.release_marker(datetime(1939, 12, 31, 23, tzinfo=UTC))


def test_a_store_that_stops_declaring_its_boundaries_is_fatal() -> None:
    """Same rule as a missing ``expver``: no marker, no retrieval (adr/0008).

    This route's marker is derived from store attributes rather than read off a field,
    so the failure this guards against is the store quietly dropping one.
    """
    dataset = _arco_shaped(lons=[0.0], lats=[0.0], values=[[[1.0]]])
    dataset.attrs.update(valid_time_start="1940-01-01", valid_time_stop="2026-04-30")
    with pytest.raises(era5.MissingReleaseMarker, match="valid_time_stop_era5t"):
        era5.ArcoCoverage.from_dataset(dataset, store="test://store")


def test_the_arco_record_carries_both_attributions() -> None:
    """The Copernicus licence applies to the data; the copy asks to be cited as a copy.

    Dropping either is a licence problem, so both travel in one string (audit row C5).
    """
    from analysis.common.schema import validate

    record = era5.arco_source_metadata(
        release_marker="0005",
        coverage=COVERAGE,
        retrieved_at=datetime(2026, 8, 26, 12, tzinfo=UTC),
    )
    validate(record, "source_metadata.json")
    assert record["attribution"].startswith("Contains modified")
    assert "Carver & Merose" in record["attribution"]
    assert record["licence"] == era5.LICENCE
    # No file was downloaded, so there are no bytes to hash. Null rather than invented.
    assert record["content_hash"] is None
    assert "last_updated=2026-08-26" in record["source_version"]
