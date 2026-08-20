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
from datetime import UTC, datetime
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
# Above this, duration_s is not a flight; a handful of records carry sentinel values.
MAX_PLAUSIBLE_DURATION_S = 24 * 3600
SITL_HW = "PX4_SITL"
FIXED_WING_MARKERS = ("Fixed", "Plane", "VTOL")
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


def audit(rows: Iterator[dict[str, Any]]) -> dict[str, Any]:
    """Compute the population summary. Takes an iterator so tests can pass fixtures."""
    counters: dict[str, Counter] = {
        k: Counter()
        for k in ("mav_type", "sys_hw", "estimator", "source", "rating", "year", "wind_speed")
    }
    error_labels: Counter = Counter()
    total = sitl = real = fixed_wing_real = declared_wind = 0
    implausible_duration = 0
    frame = 0
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
        if wind >= 0:
            declared_wind += 1

        if hardware == SITL_HW:
            sitl += 1
            continue

        real += 1
        if any(marker in (row.get("mav_type") or "") for marker in FIXED_WING_MARKERS):
            fixed_wing_real += 1

        duration = row.get("duration_s")
        if not isinstance(duration, int | float) or not 0 <= duration <= MAX_PLAUSIBLE_DURATION_S:
            implausible_duration += 1
            continue
        durations.append(duration)
        real_seconds += duration
        if duration >= MIN_DURATION_S:
            frame += 1

    durations.sort()
    n = len(durations)
    return {
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
            "non_sitl_logs_at_or_above": frame,
        },
        "fixed_wing_or_vtol_real": fixed_wing_real,
        "declared_wind_speed": {
            "logs": declared_wind,
            "by_label": {
                WIND_SPEED_LABELS.get(k, str(k)): v for k, v in counters["wind_speed"].most_common()
            },
        },
        "error_label_counts": {str(k): v for k, v in error_labels.most_common()},
        "distributions": {
            k: {str(v): c for v, c in counters[k].most_common(15)}
            for k in ("year", "mav_type", "estimator", "rating", "sys_hw", "source")
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

    result = audit(records(cache))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

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
            "max_plausible_duration_s": MAX_PLAUSIBLE_DURATION_S,
            "sitl_hw": SITL_HW,
        },
    )
    add_output(manifest, args.out)
    path = write_manifest(manifest)
    print(f"{args.out} ({result['total_logs']} logs)\nmanifest: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
