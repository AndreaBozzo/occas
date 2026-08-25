"""Spatio-temporal join between run windows and external context, with quality flags.

The core of M4 and the one piece of logic in this repository that is genuinely ours.

**The clock problem comes first.** ULog ``timestamp`` is microseconds since boot, not
wall clock, and ERA5 is indexed by UTC. The only absolute time in a PX4 log is
``vehicle_gps_position.time_utc_usec``, which is published alongside the same boot
``timestamp``, so the offset between the two clocks is recoverable -- as their median
difference over rows with a real fix. The median rather than the first row, because a
single sample lands on whatever jitter that message had, and the spread across samples is
itself the evidence for whether the anchor can be trusted. A run whose spread is wide
gets a quality flag rather than a silently wrong UTC.

**Windows are ERA5 hours.** The reanalysis publishes hourly fields, so a window shorter
than an hour buys nothing and a window longer than one straddles two values. Splitting a
run at hour boundaries makes the temporal mismatch a property we measure rather than
choose.

Every emitted row records the declared tolerances *and* the actual distance-to-grid-point
and time mismatch, per ``schemas/context_feature.json``. That is the difference between a
join that can be audited and one that has to be believed: a row 40 km from its grid point
and a row 2 km from it are not the same evidence, and averaging them without saying so
would hide the disagreement H1 exists to measure.

``context_uncertainty`` is deliberately *not* filled in here. It is a regime property
pointing at a ``ValidationArtifact``, and no validation exists until H1 has run -- so
writing anything into it now would be inventing the result this join is meant to produce.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

# ERA5 single levels, as retrieved by context/era5.py.
GRID_DEG = 0.25
ERA5_TEMPORAL_RESOLUTION_S = 3600.0
# Half a cell diagonal at mid latitudes is ~17 km, so a nearest-grid-point join can
# legitimately be that far. The tolerance is what we declare acceptable, not what we
# observed; both are recorded and the sensitivity analysis varies this one.
SPATIAL_TOLERANCE_KM = 30.0
# Half an hour: the furthest a window centre can sit from the nearest hourly stamp.
TEMPORAL_TOLERANCE_S = 1800.0
# Below this many samples a window's mean is not worth calling a mean.
MIN_SAMPLES_PER_WINDOW = 5
# If the boot-to-UTC offset varies by more than this across GPS samples, the anchor is
# not trustworthy enough to place a window inside a particular hour.
MAX_CLOCK_SPREAD_S = 2.0
# A recovered time before this means the receiver never obtained a date, whatever it
# reported in time_utc_usec or fix_type. PX4 did not exist in 2000; any real flight is
# after it, and the failure mode this catches lands in 1970.
MIN_PLAUSIBLE_UTC = datetime(2000, 1, 1, tzinfo=UTC)
# log_date is the *upload* date, so the cross-check it supports is one-sided: a flight may
# precede its upload by any amount, but cannot follow it. This is the slack on the
# impossible direction only -- enough for a timezone and a midnight crossing.
MAX_DATE_DISAGREEMENT_DAYS = 2
EARTH_RADIUS_KM = 6371.0088


class NoAbsoluteTime(ValueError):
    """Raised when a run carries no usable UTC anchor.

    Fatal for that run rather than papered over: without it every window would be placed
    in an arbitrary hour, and a join to the wrong hour is worse than no join because it
    looks like data.
    """


@dataclass(frozen=True)
class ClockAnchor:
    """The boot-clock to UTC offset, and how much the samples disagreed about it."""

    offset_us: int
    spread_s: float
    samples: int

    @property
    def trustworthy(self) -> bool:
        return self.spread_s <= MAX_CLOCK_SPREAD_S

    def to_utc(self, boot_us: int | float) -> datetime:
        return datetime.fromtimestamp((boot_us + self.offset_us) / 1e6, UTC)


def clock_anchor(gps: dict[str, list], *, expected_date: str | None = None) -> ClockAnchor:
    """Recover UTC from the pairing of ``time_utc_usec`` and the boot ``timestamp``.

    Rows with a zero ``time_utc_usec`` are dropped: that is the field's "no fix yet"
    value, and treating it as an epoch timestamp would place the flight in 1970.

    **Non-zero is not the same as valid, and a fix type is not evidence either.** Run
    ``405385f7`` in the 2026-08-25 pilot reports ``fix_type = 3`` on all 676 GPS rows with
    a non-zero ``time_utc_usec`` — whose values begin at 32 seconds and track the boot
    clock. The receiver never obtained a date and said so in no way that a null check
    would catch. So the recovered time is sanity-checked against an epoch, and, where the
    caller supplies one, against the corpus ``log_date`` -- in one direction only, because
    that field is the *upload* date and a flight may precede its upload by years.

    Both failures are fatal for the run rather than flagged. A window placed in the wrong
    hour joins to the wrong weather, and that is worse than no join because it looks like
    data.
    """
    offsets = [
        int(utc) - int(boot)
        for utc, boot in zip(gps["time_utc_usec"], gps["timestamp"], strict=False)
        if utc
    ]
    if not offsets:
        raise NoAbsoluteTime("no vehicle_gps_position rows carry a non-zero time_utc_usec")
    offsets.sort()
    median = offsets[len(offsets) // 2]
    spread = (offsets[-1] - offsets[0]) / 1e6
    anchor = ClockAnchor(offset_us=median, spread_s=spread, samples=len(offsets))

    recovered = anchor.to_utc(gps["timestamp"][0])
    if recovered < MIN_PLAUSIBLE_UTC:
        raise NoAbsoluteTime(
            f"recovered UTC {recovered.isoformat()} predates {MIN_PLAUSIBLE_UTC.date()}: "
            f"time_utc_usec is populated but carries no date"
        )
    if expected_date:
        # One-sided, and the asymmetry is the whole point. `log_date` is the *upload*
        # date, not the flight date: in the 2026-08-25 pilot, 41 of 100 runs recovered a
        # GPS time earlier than their log_date, by 3 to 2,478 days, and **not one
        # recovered a later time**. A wrong clock would scatter in both directions; a
        # flown-then-uploaded-later corpus produces exactly this one-way lag. So a
        # recovered time before log_date is normal and carries no information about the
        # anchor's quality.
        #
        # A recovered time *after* the upload date is the impossible direction, and that
        # is what this rejects.
        lag_days = (datetime.fromisoformat(expected_date).date() - recovered.date()).days
        if lag_days < -MAX_DATE_DISAGREEMENT_DAYS:
            raise NoAbsoluteTime(
                f"recovered UTC {recovered.date()} is {-lag_days} days after the corpus "
                f"log_date {expected_date}: a flight cannot postdate its own upload"
            )
    return anchor


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance. Used for the actual distance to the grid point."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def nearest_grid_point(lat: float, lon: float, grid_deg: float = GRID_DEG) -> tuple[float, float]:
    """The ERA5 cell centre a position falls in. Longitudes are kept in the input's frame."""
    return round(lat / grid_deg) * grid_deg, round(lon / grid_deg) * grid_deg


def _column(table, name: str) -> list:
    return table.column(name).to_pylist() if name in table.column_names else []


def run_windows(
    run_dir: Path,
    *,
    min_samples: int = MIN_SAMPLES_PER_WINDOW,
    expected_date: str | None = None,
) -> list[dict[str, Any]]:
    """Split one converted run into hourly windows of onboard wind and mean position.

    Wind and position are logged on different topics at different rates, so each is
    averaged within the window rather than paired sample-by-sample. That is the honest
    operation: H1 compares an hourly reanalysis value against the onboard estimate *over
    that hour*, and pretending to a finer pairing would imply a resolution ERA5 does not
    have.
    """
    gps = pq.read_table(run_dir / "vehicle_gps_position.parquet")
    anchor = clock_anchor(
        {"time_utc_usec": _column(gps, "time_utc_usec"), "timestamp": _column(gps, "timestamp")},
        expected_date=expected_date,
    )

    wind = pq.read_table(run_dir / "wind.parquet")
    position = pq.read_table(run_dir / "vehicle_global_position.parquet")

    buckets: dict[datetime, dict[str, list]] = {}

    def bucket(moment: datetime) -> dict[str, list]:
        hour = moment.replace(minute=0, second=0, microsecond=0)
        return buckets.setdefault(hour, {"u": [], "v": [], "var": [], "lat": [], "lon": []})

    for ts, north, east, vn, ve in zip(
        _column(wind, "timestamp"),
        _column(wind, "windspeed_north"),
        _column(wind, "windspeed_east"),
        _column(wind, "variance_north"),
        _column(wind, "variance_east"),
        strict=False,
    ):
        if north is None or east is None:
            continue
        cell = bucket(anchor.to_utc(ts))
        cell["u"].append(east)  # east component, ADR-0006's "u"
        cell["v"].append(north)
        if vn is not None and ve is not None:
            cell["var"].append((vn + ve) / 2)

    for ts, lat, lon in zip(
        _column(position, "timestamp"),
        _column(position, "lat"),
        _column(position, "lon"),
        strict=False,
    ):
        if lat is None or lon is None:
            continue
        cell = bucket(anchor.to_utc(ts))
        cell["lat"].append(lat)
        cell["lon"].append(lon)

    windows = []
    for hour, cell in sorted(buckets.items()):
        flags = []
        if not cell["u"] or not cell["lat"]:
            # A window with wind but no position, or the reverse, cannot be joined. It is
            # recorded as a window and flagged, not dropped: the count of these is part
            # of the coverage story.
            flags.append("incomplete_window")
        if len(cell["u"]) < min_samples:
            flags.append("few_wind_samples")
        if len(cell["lat"]) < min_samples:
            flags.append("few_position_samples")
        if not anchor.trustworthy:
            flags.append("clock_anchor_uncertain")

        windows.append(
            {
                "run_id": run_dir.name,
                "window_start": hour,
                "window_end": hour + timedelta(hours=1),
                "onboard_u": _mean(cell["u"]),
                "onboard_v": _mean(cell["v"]),
                "onboard_variance": _mean(cell["var"]),
                "wind_samples": len(cell["u"]),
                "position_samples": len(cell["lat"]),
                "lat": _mean(cell["lat"]),
                "lon": _mean(cell["lon"]),
                "clock_spread_s": anchor.spread_s,
                "quality_flags": flags,
            }
        )
    return windows


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def join_flags(
    *,
    distance_km: float | None,
    mismatch_s: float | None,
    spatial_tolerance_km: float,
    temporal_tolerance_s: float,
    window_flags: list[str],
) -> list[str]:
    """Window flags plus whatever the join itself breached.

    Out-of-tolerance rows are flagged, never dropped. A join that silently discarded
    them would report agreement over exactly the subset where alignment was easiest,
    which is the sensitivity analysis answering itself.
    """
    flags = list(window_flags)
    if distance_km is not None and distance_km > spatial_tolerance_km:
        flags.append("outside_spatial_tolerance")
    if mismatch_s is not None and abs(mismatch_s) > temporal_tolerance_s:
        flags.append("outside_temporal_tolerance")
    return flags


def context_feature(
    window: dict[str, Any],
    *,
    feature_name: str,
    value: float | None,
    unit: str,
    source: dict[str, Any],
    grid_lat: float,
    grid_lon: float,
    context_time: datetime,
    processing_version: str,
    spatial_tolerance_km: float = SPATIAL_TOLERANCE_KM,
    temporal_tolerance_s: float = TEMPORAL_TOLERANCE_S,
) -> dict[str, Any]:
    """One ``ContextFeatureWindow``, satisfying ``schemas/context_feature.json``."""
    distance = (
        haversine_km(window["lat"], window["lon"], grid_lat, grid_lon)
        if window["lat"] is not None and window["lon"] is not None
        else None
    )
    centre = window["window_start"] + timedelta(seconds=ERA5_TEMPORAL_RESOLUTION_S / 2)
    mismatch = (context_time - centre).total_seconds()

    return {
        "run_id": window["run_id"],
        "window_start": window["window_start"].isoformat(),
        "window_end": window["window_end"].isoformat(),
        "feature_name": feature_name,
        "value": value,
        "unit": unit,
        "source": source,
        "processing_version": processing_version,
        "join": {
            "join_method": "nearest_grid_point",
            "interpolation_method": None,
            "spatial_resolution_deg": GRID_DEG,
            "temporal_resolution_s": ERA5_TEMPORAL_RESOLUTION_S,
            "distance_to_grid_point_km": distance,
            "temporal_mismatch_s": mismatch,
            "spatial_tolerance_km": spatial_tolerance_km,
            "temporal_tolerance_s": temporal_tolerance_s,
            "quality_flags": join_flags(
                distance_km=distance,
                mismatch_s=mismatch,
                spatial_tolerance_km=spatial_tolerance_km,
                temporal_tolerance_s=temporal_tolerance_s,
                window_flags=window["quality_flags"],
            ),
        },
        # Left null on purpose: it is a regime property pointing at a ValidationArtifact,
        # and no validation exists until H1 has run. Filling it now would invent the
        # result this join exists to produce.
        "context_uncertainty": None,
    }
