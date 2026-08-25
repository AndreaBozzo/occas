"""Characterise the public PX4 log corpus from the published metadata dump.

Produces every number in ``docs/02b-dbinfo-inventory.md``, and an ``AnalysisManifest``
alongside them, because a number without a manifest is not publishable (``adr/0004``).

The dump is a CDN artifact regenerated daily, so the manifest records the content hash
and ``Last-Modified`` of the exact file the numbers came from. Re-running on a later
day produces different numbers from a different frame, which is why the frame is
recorded rather than assumed.

No logs are downloaded. See ``adr/0005`` for why this is the sampling frame rather
than a preliminary to a bulk pull.

    uv run python -m ingest.dbinfo_audit
"""

from __future__ import annotations

import argparse
import gzip
import json
from collections import Counter
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from analysis.common.manifest import add_output, build_manifest, hash_file, write_manifest

DBINFO_URL = "https://review.px4.io/dbinfo"

# PROVISIONAL inclusion threshold, to be revised against the first real logs.
#
# It is not derived from ERA5: a reanalysis supplies a background field for a
# 120-second flight as readily as for a 20-minute one. What a short log fails to
# supply is the *other* side of the comparison -- enough post-takeoff flight for the
# EKF wind state to converge, enough movement to excite it, and enough samples clear
# of transients to summarise. Where that boundary actually falls is an empirical
# question about the estimator, and it is unanswerable until logs exist.
#
# 300 s is a placeholder chosen to exclude bench runs and the 79-second median. The
# manifest records it as a parameter precisely so a later value can be compared
# against this one. See docs/adr/0006-what-h1-compares.md for the comparison itself.
MIN_DURATION_S = 300
# Because the threshold is provisional, its neighbours are counted in the same pass.
# "Where does the boundary actually fall" is then a question answered against one
# artifact rather than by re-running the audit with the constant changed, and the tier
# quoted in prose is one the script emitted. MIN_DURATION_S is one of them by
# construction.
DURATION_TIERS = (120, 180, MIN_DURATION_S, 600)
# Above this, duration_s is not a flight; a handful of records carry sentinel values.
MAX_PLAUSIBLE_DURATION_S = 24 * 3600
SITL_HW = "PX4_SITL"
# Dronecode announced a 12-month retention policy for uploaded logs on 2024-10-14,
# retroactively ("we will automatically remove everything older than one year"), yet
# this dump still describes records from 2016 -- so metadata plainly outlives something.
# Whether it outlives the .ulg is unanswered (audit row A8) and decides how much of the
# frame can actually be retrieved. The window is measured back from the newest log_date
# in the dump rather than from the wall clock, so the figure is a property of the input
# and re-running next year does not silently move it.
RETENTION_WINDOW_DAYS = 365
FIXED_WING_MARKERS = ("Fixed", "Plane", "VTOL")
# Matched lowercased, and only on what the fixed-wing markers did not already claim:
# "Tiltrotor VTOL" contains "rotor" and is not a rotorcraft. "Ground Rover" contains
# neither. Whatever matches nothing is counted as "other" rather than dropped.
ROTORCRAFT_MARKERS = ("rotor", "copter", "helicopter")
# Verified in flight_review source, not inferred from the values seen: the mapping is
# ``DBData.wind_speed_str_static`` in ``app/plot_app/db_entry.py``, and
# ``app/tornado_handlers/upload.py`` only reads ``windSpeed`` from the form when the
# upload type is ``flightreport`` -- otherwise the field keeps its -1 default. So a
# corpus-wide "not given" rate mostly counts uploads that were never asked.
WIND_SPEED_LABELS = {-1: "not given", 0: "Calm", 5: "Breeze", 8: "Gale", 10: "Storm"}
PX4_ATTRIBUTION = "Flight logs from PX4 Flight Review (logs.px4.io), CC-BY PX4."


def fetch(cache: Path) -> Path:
    """Download the dump once and keep it. A cached copy is never re-fetched."""
    if cache.exists():
        return cache
    import httpx

    cache.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream("GET", DBINFO_URL, follow_redirects=True, timeout=600) as response:
        response.raise_for_status()
        with cache.open("wb") as handle:
            for chunk in response.iter_bytes():
                handle.write(chunk)
        meta = {
            "url": DBINFO_URL,
            "final_url": str(response.url),
            "last_modified": response.headers.get("Last-Modified"),
            "retrieved_at": datetime.now(UTC).isoformat(),
        }
    headers_path(cache).write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return cache


def headers_path(cache: Path) -> Path:
    return cache.with_name(cache.name + ".headers.json")


def records(cache: Path) -> Iterator[dict[str, Any]]:
    """Yield each metadata record.

    The dump is a single 356 MB JSON array. It is decoded with a moving index rather
    than by re-slicing the buffer, which turns an accidentally quadratic scan into a
    linear one - the difference between eight seconds and not finishing.
    """
    with gzip.open(cache, "rt", encoding="utf-8") as handle:
        data = handle.read()
    decoder = json.JSONDecoder()
    i = data.index("[") + 1
    end = len(data)
    while i < end:
        while i < end and data[i] in " \t\n\r,":
            i += 1
        if i >= end or data[i] == "]":
            return
        obj, i = decoder.raw_decode(data, i)
        yield obj


def _retention_exposure(frame_dates: list[str]) -> dict[str, Any]:
    """How much of the H1 frame a 12-month retention policy would still leave.

    This counts metadata records, and metadata is what we have: whether the ``.ulg``
    behind an old record is still downloadable is audit row A8, and is unanswered. So
    the number is an *upper bound on what could be lost*, not a measured loss. It is
    computed anyway because it is the difference between a frame of 79k and a frame of
    28k, and that decides how the sample is stratified rather than merely how large it
    is.
    """
    if not frame_dates:
        return {}
    newest = max(frame_dates)
    cutoff = (
        (datetime.fromisoformat(newest) - timedelta(days=RETENTION_WINDOW_DAYS)).date().isoformat()
    )
    within = sum(1 for d in frame_dates if d >= cutoff)
    return {
        "window_days": RETENTION_WINDOW_DAYS,
        "newest_log_date": newest,
        "cutoff": cutoff,
        "frame_within_window": within,
        "frame_older_than_window": len(frame_dates) - within,
    }


def audit(rows: Iterator[dict[str, Any]]) -> dict[str, Any]:
    """Compute the population summary. Takes an iterator so tests can pass fixtures."""
    counters: dict[str, Counter] = {
        k: Counter()
        for k in ("mav_type", "sys_hw", "estimator", "source", "rating", "year", "wind_speed")
    }
    error_labels: Counter = Counter()
    upload_types: Counter = Counter()
    declared_by_type: Counter = Counter()
    # mav_type is counted three ways because it was previously counted once, over every
    # log, and then quoted in prose next to a fixed-wing total counted over real
    # hardware only. The two do not sum, and nothing in the artifact said why.
    mav_type_real: Counter = Counter()
    mav_type_sitl: Counter = Counter()
    tiers: Counter = Counter()
    frame_dates: list[str] = []
    total = sitl = real = fixed_wing_real = rotorcraft_real = declared_wind = 0
    implausible_duration = 0
    durations: list[float] = []
    real_seconds = 0.0

    for row in rows:
        total += 1
        hardware = row.get("sys_hw") or ""
        for key in ("mav_type", "sys_hw", "estimator", "source", "rating", "wind_speed"):
            counters[key][row.get(key)] += 1
        counters["year"][(row.get("log_date") or "")[:4]] += 1
        for label in row.get("error_labels") or []:
            error_labels[label] += 1

        wind = row.get("wind_speed")
        wind = -1 if wind is None else wind
        upload_type = row.get("type") or "unset"
        upload_types[upload_type] += 1
        if wind >= 0:
            declared_wind += 1
            declared_by_type[upload_type] += 1

        mav_type = row.get("mav_type") or ""
        if hardware == SITL_HW:
            sitl += 1
            mav_type_sitl[row.get("mav_type")] += 1
            continue

        real += 1
        mav_type_real[row.get("mav_type")] += 1
        if any(marker in mav_type for marker in FIXED_WING_MARKERS):
            fixed_wing_real += 1
        elif any(marker in mav_type.lower() for marker in ROTORCRAFT_MARKERS):
            rotorcraft_real += 1

        duration = row.get("duration_s")
        if not isinstance(duration, int | float) or not 0 <= duration <= MAX_PLAUSIBLE_DURATION_S:
            implausible_duration += 1
            continue
        durations.append(duration)
        real_seconds += duration
        for tier in DURATION_TIERS:
            if duration >= tier:
                tiers[tier] += 1
        if duration >= MIN_DURATION_S:
            frame_dates.append((row.get("log_date") or "")[:10])

    durations.sort()
    n = len(durations)
    return {
        "retention_exposure": _retention_exposure(frame_dates),
        "total_logs": total,
        "sitl": sitl,
        "real_hardware": real,
        "real_flight_hours": round(real_seconds / 3600),
        "implausible_duration": implausible_duration,
        "duration_s": {
            "median": durations[n // 2],
            "p90": durations[int(n * 0.9)],
            "p99": durations[int(n * 0.99)],
            "max": durations[-1],
        }
        if n
        else {},
        "h1_frame": {
            "min_duration_s": MIN_DURATION_S,
            "non_sitl_logs_at_or_above": tiers[MIN_DURATION_S],
            "non_sitl_logs_by_tier": {str(tier): tiers[tier] for tier in DURATION_TIERS},
        },
        "fixed_wing_or_vtol_real": fixed_wing_real,
        # Every real log lands in exactly one class, so the three sum to real_hardware
        # and "other" -- rovers, boats, generic and unknown types -- stays visible
        # instead of being the difference between two numbers quoted in prose.
        "airframe_class_real": {
            "fixed_wing_or_vtol": fixed_wing_real,
            "rotorcraft": rotorcraft_real,
            "other": real - fixed_wing_real - rotorcraft_real,
        },
        "declared_wind_speed": {
            "logs": declared_wind,
            "by_label": {
                WIND_SPEED_LABELS.get(k, str(k)): v for k, v in counters["wind_speed"].most_common()
            },
            # The corpus-wide rate understates the field: only flight reports are asked
            # for it. Coverage within the population that is asked is the honest figure,
            # so both are reported and neither is presented alone.
            "by_upload_type": {
                str(name): {"logs": count, "declared": declared_by_type.get(name, 0)}
                for name, count in upload_types.most_common()
            },
        },
        "error_label_counts": {str(k): v for k, v in error_labels.most_common()},
        "distributions": {
            k: {str(v): c for v, c in counters[k].most_common(15)}
            for k in ("year", "estimator", "rating", "sys_hw", "source")
        }
        # Split by population and not truncated. The top-15 cut was hiding the VTOL
        # variants that FIXED_WING_MARKERS does match, so even the all-log subtypes did
        # not sum to the all-log total.
        | {
            "mav_type_all": {str(v): c for v, c in counters["mav_type"].most_common()},
            "mav_type_real": {str(v): c for v, c in mav_type_real.most_common()},
            "mav_type_sitl": {str(v): c for v, c in mav_type_sitl.most_common()},
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cache", type=Path, default=Path("data/dbinfo.json.gz"))
    parser.add_argument("--out", type=Path, default=Path("artifacts/dbinfo-audit.json"))
    args = parser.parse_args(argv)

    cache = fetch(args.cache)
    hp = headers_path(cache)
    headers = json.loads(hp.read_text(encoding="utf-8")) if hp.exists() else {}

    # Built before the artifact is written, not after. ``build_manifest`` captures the
    # state of the working tree, and args.out is tracked in git: rewriting it first
    # dirties the tree, so every run that changed its own result used to report
    # ``dirty: true`` and could never be published. See docs/adr/0010.
    manifest = build_manifest(
        name="px4-dbinfo-corpus-audit",
        hypothesis="none",
        entrypoint="ingest/dbinfo_audit.py",
        description="Population characterisation of the public PX4 log corpus from its "
        "published metadata dump. No logs downloaded.",
        inputs=[
            {
                "path": cache.as_posix(),
                "content_hash": hash_file(cache),
                "source": {
                    "source": "px4_flight_review",
                    "source_version": headers.get("last_modified"),
                    "source_url": headers.get("final_url", DBINFO_URL),
                    "retrieved_at": headers.get("retrieved_at", "1970-01-01T00:00:00+00:00"),
                    "licence": "CC-BY-4.0",
                    "attribution": PX4_ATTRIBUTION,
                },
            }
        ],
        parameters={
            "min_duration_s": MIN_DURATION_S,
            "duration_tiers": list(DURATION_TIERS),
            "max_plausible_duration_s": MAX_PLAUSIBLE_DURATION_S,
            "retention_window_days": RETENTION_WINDOW_DAYS,
            "sitl_hw": SITL_HW,
        },
    )

    result = audit(records(cache))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    # newline="\n": the manifest records a hash of these bytes, and the repository
    # stores and checks the file back out as LF.
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")

    add_output(manifest, args.out)
    path = write_manifest(manifest)
    state = "exploratory: dirty tree" if manifest["code"]["dirty"] else "publishable"
    print(f"{args.out} ({result['total_logs']} logs, {state})\nmanifest: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
