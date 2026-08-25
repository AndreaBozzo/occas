"""Pair each usable run window with the ERA5 field over it. The input H1 will consume.

This builds the paired dataset and **computes no agreement statistic**. That is not
laziness, it is the pilot's terms: ``docs/09-dpia.md`` §1.1 records that the first
retrieval tests the design rather than the hypothesis, and a number produced from 34 runs
before the design is validated could only mislead — including us. Bias and limits of
agreement are H1's, pre-specified in ``adr/0006``, and they run on the full sample.

What this does produce is the thing H1 cannot be written without: for each ERA5-hour
window of each usable run, the onboard EKF2 wind estimate, the ERA5 field at the nearest
grid point, and the join metadata that says how far apart in space and time the two
actually were.

One CDS request per distinct (date, hour, grid cell). Windows from the same flight
usually share a cell, and the cache in ``context/era5.py`` means a repeat costs nothing,
so the request count is driven by how scattered the corpus is rather than by how many
windows there are.

    uv run python -m analysis.h1_agreement.build_pairs --limit 3    # validate
    uv run python -m analysis.h1_agreement.build_pairs              # all usable runs
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from analysis.common.manifest import add_output, build_manifest, hash_file, write_manifest
from analysis.common.schema import validate
from context import align, era5

PROCESSING_VERSION = "build_pairs/1"

# ERA5 variable -> the feature name it is emitted under. 100 m is the primary vertical
# reference and 10 m the secondary whose difference from it is a shear stratifier
# (adr/0006); both are retrieved in one request so they cannot drift apart.
FEATURES = {
    "u100": ("era5_100m_u", "m s-1"),
    "v100": ("era5_100m_v", "m s-1"),
    "u10": ("era5_10m_u", "m s-1"),
    "v10": ("era5_10m_v", "m s-1"),
}


def usable_runs(inventory: Path) -> list[dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in inventory.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return [r for r in rows if r.get("usable_for_h1")]


def era5_at(window: dict[str, Any], cache_dir: Path) -> tuple[dict[str, float], dict[str, Any]]:
    """Retrieve and read the ERA5 field for one window's hour and cell.

    The request box is a quarter-degree around the snapped grid centre, which is the
    smallest area that reliably returns the containing cell. Whatever the service sends
    back, the value taken is the nearest point to the *aircraft*, not to the box centre,
    and the distance to it is recorded by the caller.
    """
    import xarray as xr

    grid_lat, grid_lon = align.nearest_grid_point(window["lat"], window["lon"])
    request = era5.build_request(
        start=window["window_start"],
        end=window["window_start"],
        bbox=(grid_lat + 0.125, grid_lon - 0.125, grid_lat - 0.125, grid_lon + 0.125),
    )
    path, cached = era5.retrieve(request, cache_dir)
    marker = era5.read_release_marker(path)

    with xr.open_dataset(path) as dataset:
        point = dataset.sel(latitude=window["lat"], longitude=window["lon"], method="nearest")
        values = {
            name: float(point[name].values.ravel()[0])
            for name in FEATURES
            if name in point.data_vars
        }
        actual_lat = float(point["latitude"].values)
        actual_lon = float(point["longitude"].values)

    return values, {
        "grid_lat": actual_lat,
        "grid_lon": actual_lon,
        "release_marker": marker,
        "cached": cached,
        "source": era5.source_metadata(release_marker=marker, content_hash=hash_file(path)),
    }


def pair(window: dict[str, Any], cache_dir: Path) -> tuple[list[dict], dict[str, Any]]:
    """One window -> its schema-valid context features, plus the paired row H1 reads."""
    values, meta = era5_at(window, cache_dir)
    # ERA5 hourly fields are instantaneous at the stamp, and the window is the hour that
    # begins there, so the field sits at the window's start.
    context_time = window["window_start"]

    features = [
        align.context_feature(
            window,
            feature_name=FEATURES[name][0],
            value=value,
            unit=FEATURES[name][1],
            source=meta["source"],
            grid_lat=meta["grid_lat"],
            grid_lon=meta["grid_lon"],
            context_time=context_time,
            processing_version=PROCESSING_VERSION,
        )
        for name, value in values.items()
    ]
    join = features[0]["join"] if features else {}
    row = {
        "run_id": window["run_id"],
        "window_start": window["window_start"].isoformat(),
        "onboard_u": window["onboard_u"],
        "onboard_v": window["onboard_v"],
        "onboard_variance": window["onboard_variance"],
        "wind_samples": window["wind_samples"],
        "lat": window["lat"],
        "lon": window["lon"],
        "era5_100m_u": values.get("u100"),
        "era5_100m_v": values.get("v100"),
        "era5_10m_u": values.get("u10"),
        "era5_10m_v": values.get("v10"),
        "release_marker": meta["release_marker"],
        "distance_to_grid_point_km": join.get("distance_to_grid_point_km"),
        "temporal_mismatch_s": join.get("temporal_mismatch_s"),
        "quality_flags": join.get("quality_flags", []),
    }
    return features, row


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--inventory", type=Path, default=Path("data/pilot-inventory.jsonl"))
    parser.add_argument("--sample", type=Path, default=Path("data/pilot-sample.jsonl"))
    parser.add_argument("--parquet", type=Path, default=Path("data/parquet"))
    parser.add_argument("--cache", type=Path, default=Path("cache/era5"))
    parser.add_argument("--pairs", type=Path, default=Path("data/pilot-pairs.jsonl"))
    parser.add_argument("--features", type=Path, default=Path("data/pilot-context-features.jsonl"))
    parser.add_argument("--out", type=Path, default=Path("artifacts/pilot-join-summary.json"))
    parser.add_argument("--limit", type=int, default=None, help="First N usable runs only.")
    args = parser.parse_args(argv)

    dates = {}
    if args.sample.exists():
        for line in args.sample.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                dates[row["log_id"]] = (row.get("log_date") or "")[:10] or None

    manifest = build_manifest(
        name="h1-pilot-pairs",
        hypothesis="H1",
        entrypoint="analysis/h1_agreement/build_pairs.py",
        description="ERA5 fields paired to onboard wind per run window, for the pilot. "
        "Builds the input to H1; computes no agreement statistic.",
        parameters={
            "spatial_tolerance_km": align.SPATIAL_TOLERANCE_KM,
            "temporal_tolerance_s": align.TEMPORAL_TOLERANCE_S,
            "grid_deg": align.GRID_DEG,
            "min_samples_per_window": align.MIN_SAMPLES_PER_WINDOW,
            "era5_variables": list(era5.WIND_VARIABLES),
            "processing_version": PROCESSING_VERSION,
        },
    )

    runs = usable_runs(args.inventory)
    if args.limit:
        runs = runs[: args.limit]

    features_out: list[dict] = []
    pairs_out: list[dict] = []
    failures: Counter = Counter()
    flags: Counter = Counter()
    windows_seen = 0

    for entry in runs:
        run_id = entry["log_id"]
        try:
            windows = align.run_windows(args.parquet / run_id, expected_date=dates.get(run_id))
        except Exception as error:  # a run that cannot be windowed is a finding, not a stop
            failures[f"windows:{type(error).__name__}"] += 1
            continue
        for window in windows:
            windows_seen += 1
            if window["lat"] is None or not window["wind_samples"]:
                failures["window:incomplete"] += 1
                continue
            try:
                features, row = pair(window, args.cache)
            except Exception as error:
                failures[f"era5:{type(error).__name__}"] += 1
                continue
            features_out.extend(features)
            pairs_out.append(row)
            for flag in row["quality_flags"]:
                flags[flag] += 1
        print(f"{run_id[:8]} {len(pairs_out):>4} pairs so far", flush=True)

    for feature in features_out:
        validate(feature, "context_feature.json")

    args.pairs.parent.mkdir(parents=True, exist_ok=True)
    args.pairs.write_text(
        "".join(json.dumps(r) + "\n" for r in pairs_out), encoding="utf-8", newline="\n"
    )
    args.features.write_text(
        "".join(json.dumps(f) + "\n" for f in features_out), encoding="utf-8", newline="\n"
    )

    distances = [
        r["distance_to_grid_point_km"]
        for r in pairs_out
        if r["distance_to_grid_point_km"] is not None
    ]
    summary = {
        "runs_attempted": len(runs),
        "runs_paired": len({r["run_id"] for r in pairs_out}),
        "windows_seen": windows_seen,
        "windows_paired": len(pairs_out),
        "context_features": len(features_out),
        "failures": dict(failures),
        "quality_flags": dict(flags),
        "distance_to_grid_point_km": {
            "min": round(min(distances), 2),
            "median": round(sorted(distances)[len(distances) // 2], 2),
            "max": round(max(distances), 2),
        }
        if distances
        else {},
        "release_markers": dict(Counter(r["release_marker"] for r in pairs_out)),
        "note": "No agreement statistic is computed here. See docs/09-dpia.md 1.1.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")

    add_output(manifest, args.out)
    path = write_manifest(manifest)
    print(json.dumps(summary, indent=2))
    print(f"manifest: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
