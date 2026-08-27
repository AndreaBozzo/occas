"""The join records what it did, and flags rather than drops what it could not do well.

Every test here guards a way the join could produce a number that looks fine and is not:
a window placed in the wrong hour because the boot clock was never anchored, a row
silently dropped for being far from its grid point, or a tolerance breach that never
reached the output.

The fixtures describe no real flight: coordinates are round numbers near Milan and the
wind values are arbitrary.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime

import pytest

from context import align

# 2026-01-15 12:34:56 UTC, in microseconds. The boot clock starts wherever it likes.
UTC_BASE_US = int(datetime(2026, 1, 15, 12, 34, 56, tzinfo=UTC).timestamp() * 1e6)
BOOT_BASE_US = 4_000_000


def test_clock_anchor_recovers_utc_from_the_gps_pairing() -> None:
    gps = {
        "timestamp": [BOOT_BASE_US + i * 1_000_000 for i in range(5)],
        "time_utc_usec": [UTC_BASE_US + i * 1_000_000 for i in range(5)],
    }
    anchor = align.clock_anchor(gps)
    assert anchor.to_utc(BOOT_BASE_US) == datetime(2026, 1, 15, 12, 34, 56, tzinfo=UTC)
    assert anchor.trustworthy


def test_rows_without_a_fix_do_not_place_the_flight_in_1970() -> None:
    """``time_utc_usec`` is 0 before a fix. Treating it as an epoch is a 56-year error."""
    gps = {
        "timestamp": [BOOT_BASE_US, BOOT_BASE_US + 1_000_000],
        "time_utc_usec": [0, UTC_BASE_US + 1_000_000],
    }
    anchor = align.clock_anchor(gps)
    assert anchor.samples == 1
    assert anchor.to_utc(BOOT_BASE_US).year == 2026


def test_a_run_with_no_fix_at_all_is_fatal_not_guessed() -> None:
    """Without an anchor every window lands in an arbitrary hour.

    A join to the wrong hour is worse than no join, because it looks like data.
    """
    with pytest.raises(align.NoAbsoluteTime):
        align.clock_anchor({"timestamp": [BOOT_BASE_US], "time_utc_usec": [0]})


def test_a_jittery_clock_is_flagged_rather_than_trusted() -> None:
    gps = {
        "timestamp": [BOOT_BASE_US, BOOT_BASE_US + 1_000_000],
        # ten seconds of disagreement about what UTC is
        "time_utc_usec": [UTC_BASE_US, UTC_BASE_US + 11_000_000],
    }
    anchor = align.clock_anchor(gps)
    assert anchor.spread_s == pytest.approx(10.0)
    assert not anchor.trustworthy


def test_the_anchor_is_the_median_not_the_first_sample() -> None:
    """One outlying message must not move the whole run's UTC."""
    gps = {
        "timestamp": [BOOT_BASE_US] * 5,
        "time_utc_usec": [UTC_BASE_US + d for d in (5_000_000, 0, 0, 0, 0)],
    }
    assert align.clock_anchor(gps).offset_us == UTC_BASE_US - BOOT_BASE_US


@pytest.mark.parametrize(
    ("lat", "lon", "expected"),
    [
        (45.51, 9.19, (45.50, 9.25)),
        (45.62, 9.12, (45.50, 9.00)),  # 45.62 is nearer 45.50 than 45.75
        (-0.10, -0.10, (0.0, 0.0)),
    ],
)
def test_nearest_grid_point_snaps_to_the_era5_cell(lat, lon, expected) -> None:
    got = align.nearest_grid_point(lat, lon)
    assert got == pytest.approx(expected)


def test_haversine_is_a_real_distance() -> None:
    """0.25 degrees of latitude is about 27.8 km, everywhere."""
    assert align.haversine_km(45.0, 9.0, 45.25, 9.0) == pytest.approx(27.8, abs=0.3)
    assert align.haversine_km(45.0, 9.0, 45.0, 9.0) == 0.0


def _window(**overrides):
    base = {
        "run_id": "synthetic-run",
        "window_start": datetime(2026, 1, 15, 12, tzinfo=UTC),
        "window_end": datetime(2026, 1, 15, 13, tzinfo=UTC),
        "lat": 45.50,
        "lon": 9.25,
        "quality_flags": [],
    }
    return {**base, **overrides}


def _feature(window, *, grid_lat=45.50, grid_lon=9.25, context_time=None, **kwargs):
    return align.context_feature(
        window,
        feature_name="era5_100m_u",
        value=3.2,
        unit="m s-1",
        source={
            "source": "era5",
            "retrieved_at": "2026-08-25T12:00:00+00:00",
            "licence": "Licence to use Copernicus Products, revision 12",
        },
        grid_lat=grid_lat,
        grid_lon=grid_lon,
        context_time=context_time or datetime(2026, 1, 15, 12, 30, tzinfo=UTC),
        processing_version="test",
        **kwargs,
    )


def test_the_emitted_row_satisfies_the_schema() -> None:
    from analysis.common.schema import validate

    validate(_feature(_window()), "context_feature.json")


def test_the_row_records_the_actual_distance_and_mismatch_not_only_the_tolerances() -> None:
    """A row 40 km from its grid point and one 2 km away are not the same evidence."""
    feature = _feature(_window(lat=45.50, lon=9.25), grid_lat=45.75, grid_lon=9.25)
    join = feature["join"]
    assert join["distance_to_grid_point_km"] == pytest.approx(27.8, abs=0.3)
    assert join["spatial_tolerance_km"] == align.SPATIAL_TOLERANCE_KM
    assert join["temporal_resolution_s"] == 3600.0


def test_the_temporal_mismatch_is_signed_against_the_window_centre() -> None:
    """The window centre is 12:30; a 12:00 field is half an hour early, not late."""
    feature = _feature(_window(), context_time=datetime(2026, 1, 15, 12, tzinfo=UTC))
    assert feature["join"]["temporal_mismatch_s"] == pytest.approx(-1800.0)


def test_a_breach_of_tolerance_is_flagged_and_the_row_is_still_emitted() -> None:
    """Dropping out-of-tolerance rows would be the sensitivity analysis answering itself.

    Agreement measured only where alignment was easiest is not agreement.
    """
    feature = _feature(_window(lat=45.0, lon=9.0), grid_lat=45.5, grid_lon=9.0)
    assert feature["value"] == 3.2
    assert "outside_spatial_tolerance" in feature["join"]["quality_flags"]


def test_window_flags_survive_into_the_joined_row() -> None:
    feature = _feature(_window(quality_flags=["few_wind_samples", "clock_anchor_uncertain"]))
    flags = feature["join"]["quality_flags"]
    assert "few_wind_samples" in flags
    assert "clock_anchor_uncertain" in flags


def test_context_uncertainty_is_left_null_until_a_validation_exists() -> None:
    """It is a regime property pointing at a ValidationArtifact, and none exists yet.

    Filling it now would invent the result the join exists to produce.
    """
    assert _feature(_window())["context_uncertainty"] is None


def test_a_window_without_a_position_reports_no_distance_rather_than_zero() -> None:
    """Zero would read as a perfect join. None reads as what it is."""
    feature = _feature(_window(lat=None, lon=None))
    assert feature["join"]["distance_to_grid_point_km"] is None


def test_grid_snapping_keeps_every_position_within_half_a_cell() -> None:
    """The property the join rests on: nearest-grid-point is bounded, not merely close."""
    half_diagonal_km = math.hypot(27.8, 27.8) / 2
    for lat in (45.0, 45.1, 45.37, 45.62):
        for lon in (9.0, 9.13, 9.24, 9.49):
            glat, glon = align.nearest_grid_point(lat, lon)
            assert align.haversine_km(lat, lon, glat, glon) <= half_diagonal_km


def test_a_populated_but_dateless_clock_is_rejected() -> None:
    """Non-zero is not valid, and a 3D fix is not evidence.

    Run 405385f7 in the 2026-08-25 pilot reports fix_type 3 on all 676 GPS rows with a
    non-zero time_utc_usec whose values begin at 32 seconds and track the boot clock.
    The receiver never got a date. A null check does not catch that; an epoch check does,
    and without it the run joins to weather in 1970.
    """
    gps = {
        "timestamp": [57_474_600 + i * 1_000_000 for i in range(5)],
        "time_utc_usec": [32_660_000 + i * 1_000_000 for i in range(5)],
    }
    with pytest.raises(align.NoAbsoluteTime, match="carries no date"):
        align.clock_anchor(gps)


def test_a_flight_may_long_predate_its_upload_date() -> None:
    """`log_date` is the upload date, and the check must be one-sided because of it.

    In the 2026-08-25 pilot, 41 of 100 runs recovered a GPS time earlier than their
    log_date -- by 3 to 2,478 days -- and not one recovered a later time. A wrong clock
    scatters both ways; a flown-then-uploaded-later corpus lags one way. A symmetric
    check rejected 41 runs whose anchors were fine, which is how this was found.
    """
    gps = {"timestamp": [BOOT_BASE_US], "time_utc_usec": [UTC_BASE_US]}  # 2026-01-15
    align.clock_anchor(gps, expected_date="2026-01-15")
    align.clock_anchor(gps, expected_date="2026-01-20")  # uploaded five days later
    align.clock_anchor(gps, expected_date="2032-11-30")  # uploaded years later


def test_a_flight_cannot_postdate_its_own_upload() -> None:
    """The impossible direction, and the only one worth rejecting on."""
    gps = {"timestamp": [BOOT_BASE_US], "time_utc_usec": [UTC_BASE_US]}  # 2026-01-15
    with pytest.raises(align.NoAbsoluteTime, match="after the corpus"):
        align.clock_anchor(gps, expected_date="2025-06-02")


def test_a_valid_anchor_passes_both_checks() -> None:
    gps = {
        "timestamp": [BOOT_BASE_US + i * 1_000_000 for i in range(3)],
        "time_utc_usec": [UTC_BASE_US + i * 1_000_000 for i in range(3)],
    }
    anchor = align.clock_anchor(gps, expected_date="2026-01-15")
    assert anchor.to_utc(BOOT_BASE_US).year == 2026


def test_an_unrepresentable_clock_is_rejected_not_raised_as_an_oserror() -> None:
    """The third clock trap, and the one that only 1,600 runs produced.

    ``MIN_PLAUSIBLE_UTC`` catches an anchor that recovers a representable but impossible
    date. This is the other kind: an offset far enough out that the sum leaves the
    platform's epoch range entirely, where ``datetime.fromtimestamp`` raises -- ``OSError``
    on Windows, not the ``OverflowError`` the documentation implies.

    It has to surface as ``NoAbsoluteTime`` because that is what every caller catches. On
    2026-08-27 it did not, and one run aborted the inventory of all 1,600 from inside a
    list comprehension: no summary, no manifest, no partial result.
    """
    anchor = align.ClockAnchor(offset_us=-(10**18), spread_s=0.0, samples=10)
    with pytest.raises(align.NoAbsoluteTime, match="outside representable time"):
        anchor.to_utc(BOOT_BASE_US)


def test_an_unrepresentable_clock_is_fatal_for_its_run_only() -> None:
    """Fatal for the run, and it must be reachable through clock_anchor's own path.

    The guard belongs where every caller already looks, so that a run with a broken clock
    is one unusable run rather than a stopped inventory.
    """
    # Far enough forward to leave the epoch range rather than land in 1970: a value of 1
    # here would be caught by MIN_PLAUSIBLE_UTC instead, and this test would pass with
    # the guard removed -- which it did, on the first attempt at writing it.
    far_future_us = 10**18
    gps = {
        "time_utc_usec": [far_future_us, far_future_us, far_future_us],
        "timestamp": [BOOT_BASE_US, BOOT_BASE_US + 1, BOOT_BASE_US + 2],
    }
    with pytest.raises(align.NoAbsoluteTime, match="outside representable time"):
        align.clock_anchor(gps)


def _one_window_run(tmp_path, *, variance_north: float, variance_east: float):
    """A one-hour run whose wind variance differs by component. Returns the run dir.

    Six samples of each topic, so no ``few_*_samples`` flag fires and the window under
    test is an ordinary one rather than a flagged edge case.
    """
    import pyarrow as pa
    import pyarrow.parquet as pq

    run_dir = tmp_path / "0000aaaa-0000-0000-0000-00000000aaaa"
    run_dir.mkdir()
    steps = list(range(6))
    pq.write_table(
        pa.table(
            {
                "time_utc_usec": [UTC_BASE_US + i for i in steps],
                "timestamp": [BOOT_BASE_US + i for i in steps],
            }
        ),
        run_dir / "vehicle_gps_position.parquet",
    )
    pq.write_table(
        pa.table(
            {
                "timestamp": [BOOT_BASE_US + i for i in steps],
                "windspeed_north": [3.0] * 6,
                "windspeed_east": [4.0] * 6,
                "variance_north": [variance_north] * 6,
                "variance_east": [variance_east] * 6,
            }
        ),
        run_dir / "wind.parquet",
    )
    pq.write_table(
        pa.table(
            {
                "timestamp": [BOOT_BASE_US + i for i in steps],
                "lat": [45.5] * 6,
                "lon": [9.25] * 6,
            }
        ),
        run_dir / "vehicle_global_position.parquet",
    )
    return run_dir


def test_the_two_wind_variances_reach_the_window_apart() -> None:
    """The estimator's uncertainty is a vector, and averaging it answers no question.

    ``adr/0015`` compares a component-wise limit of agreement against the estimator's own
    sigma on the *same* component. Until 2026-08-27 this function averaged
    ``variance_north`` and ``variance_east`` into one scalar, which cannot serve that
    comparison and is ADR-0006's own error -- a vector collapsed to a scalar, then used
    to make the stronger claim -- one level down.

    The asymmetry here is not hypothetical: the first real run measured after the split
    reported 0.048 against 0.087, anisotropic by 1.8x.
    """
    import tempfile
    from pathlib import Path as _Path

    with tempfile.TemporaryDirectory() as raw:
        run_dir = _one_window_run(_Path(raw), variance_north=0.09, variance_east=0.04)
        windows = align.run_windows(run_dir)

    assert len(windows) == 1
    window = windows[0]
    # v is north and u is east, the mapping ADR-0006 fixed and build_pairs relies on.
    # Averaging would put 0.065 in both, so an assertion that they merely exist passes
    # against the old code; asserting each carries its own component does not.
    assert window["onboard_variance_v"] == pytest.approx(0.09)
    assert window["onboard_variance_u"] == pytest.approx(0.04)
    assert "onboard_variance" not in window, "the collapsed scalar must not come back"
