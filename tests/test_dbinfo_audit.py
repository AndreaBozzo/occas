"""The corpus audit counts what it claims to count.

Uses a hand-built fixture rather than the 356 MB dump: every branch that decides
whether a log is SITL, real, fixed-wing, long enough, or has a declared wind is
exercised by exactly one record, so a miscount points at one line.

The fixture also splits declared wind across upload types, because only flight reports
are ever asked for it: a corpus-wide coverage figure and a within-flightreport one are
different claims, and the fixture is built so a test that confused them would fail.
"""

from __future__ import annotations

import gzip
import json

from ingest.dbinfo_audit import MIN_DURATION_S, audit, records

ROWS = [
    # real, quadrotor, long enough for the frame, declared Breeze
    {
        "sys_hw": "PX4_FMU_V6C",
        "mav_type": "Quadrotor",
        "duration_s": 600,
        "wind_speed": 5,
        "type": "flightreport",
        "log_date": "2026-06-01",
        "estimator": "EKF2",
        "error_labels": [8],
        "rating": "good",
    },
    # real, fixed wing, exactly at the threshold -- must be admitted, not excluded
    {
        "sys_hw": "PX4_FMU_V5",
        "mav_type": "Fixed Wing",
        "duration_s": MIN_DURATION_S,
        "wind_speed": -1,
        "type": "personal",
        "log_date": "2026-06-02",
        "estimator": "EKF2",
        "error_labels": [],
    },
    # real, VTOL, one second short -- must be excluded from the frame
    {
        "sys_hw": "PX4_FMU_V5",
        "mav_type": "VTOL Standard",
        "duration_s": MIN_DURATION_S - 1,
        "wind_speed": 0,
        "type": "flightreport",
        "log_date": "2026-06-03",
        "estimator": "EKF2",
        "error_labels": [2],
    },
    # SITL: counted separately, never in the real population or the frame
    {
        "sys_hw": "PX4_SITL",
        "mav_type": "Quadrotor",
        "duration_s": 9000,
        "wind_speed": -1,
        "type": "personal",
        "log_date": "2026-06-04",
        "estimator": "EKF2",
        "error_labels": [],
    },
    # real, implausible duration: excluded from hours and frame, still a real log
    {
        "sys_hw": "CUAV_X7PRO",
        "mav_type": "Hexarotor",
        "duration_s": 10**9,
        "wind_speed": -1,
        "log_date": "2025-06-05",
        "estimator": "EKF2",
        "error_labels": [],
    },
]


def test_audit_partitions_the_population() -> None:
    result = audit(iter(ROWS))

    assert result["total_logs"] == 5
    assert result["sitl"] == 1
    assert result["real_hardware"] == 4
    assert result["implausible_duration"] == 1

    # 600 + 300 + 299 seconds; the SITL and the implausible record contribute nothing
    assert result["real_flight_hours"] == round(1199 / 3600)


def test_frame_boundary_is_inclusive() -> None:
    """A log of exactly MIN_DURATION_S is in the frame; one second less is not."""
    result = audit(iter(ROWS))
    assert result["h1_frame"]["non_sitl_logs_at_or_above"] == 2
    assert result["h1_frame"]["min_duration_s"] == MIN_DURATION_S


def test_fixed_wing_marker_catches_vtol_and_excludes_sitl() -> None:
    result = audit(iter(ROWS))
    # Fixed Wing and VTOL Standard, but not the SITL quadrotor or the hexarotor
    assert result["fixed_wing_or_vtol_real"] == 2


def test_declared_wind_is_labelled_not_numeric() -> None:
    result = audit(iter(ROWS))
    assert result["declared_wind_speed"]["logs"] == 2  # Breeze and Calm; -1 does not count
    by_label = result["declared_wind_speed"]["by_label"]
    assert by_label["Breeze"] == 1
    assert by_label["Calm"] == 1
    assert by_label["not given"] == 3


def test_declared_wind_coverage_is_reported_per_upload_type() -> None:
    """Corpus-wide coverage and coverage-where-asked are different numbers.

    Only ``flightreport`` uploads are shown the wind field, so 2 declarations out of 5
    logs is 40% of the corpus and 100% of the population that was asked. The fixture
    makes the two disagree; reading either one as the other is then visible.
    """
    by_type = audit(iter(ROWS))["declared_wind_speed"]["by_upload_type"]
    assert by_type["flightreport"] == {"logs": 2, "declared": 2}
    assert by_type["personal"] == {"logs": 2, "declared": 0}
    # a record with no `type` at all is counted, not dropped: coverage is recorded,
    # never silently filtered
    assert by_type["unset"] == {"logs": 1, "declared": 0}


def test_error_labels_are_counted_per_occurrence() -> None:
    result = audit(iter(ROWS))
    assert result["error_label_counts"] == {"8": 1, "2": 1}


def test_records_parses_the_dump_format(tmp_path) -> None:
    """The moving-index decoder round-trips a gzipped JSON array."""
    path = tmp_path / "dbinfo.json.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(ROWS, handle)
    assert [r["sys_hw"] for r in records(path)] == [r["sys_hw"] for r in ROWS]
