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
