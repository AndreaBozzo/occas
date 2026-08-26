"""Read the same windows through both ERA5 routes and record where they differ.

Not an agreement analysis. ``adr/0003`` forbids treating either wind source as truth,
but that is about EKF2 against ERA5 -- two different *methods*. This compares two copies
of one product, the CDS's own NetCDF against ARCO-ERA5's Zarr, so a difference here is a
difference in packaging or in release, never in the weather. The statistic is a maximum
absolute difference, not a bias with limits of agreement, precisely because the two are
not being treated as independent measurements of anything.

It exists for two reasons, and both outlive the decision it was written for:

1. **It is the evidence for ``adr/0013``** -- switching H1's bulk reads from the CDS to
   the account-free copy is only defensible if the copy returns the same numbers, and
   the way to know that is to read windows already retrieved through the CDS and look.
2. **It is the mechanism for the ERA5T obligation.** Six of the pilot's 42 windows were
   served as ERA5T (``expver=0005``), which final ERA5 replaces two to three months on.
   Re-running this after that release says exactly which windows moved and by how much,
   instead of leaving a note in a limitations section.

    uv run python -m analysis.h1_agreement.compare_era5_routes
    uv run python -m analysis.h1_agreement.compare_era5_routes --limit 5   # spot check
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any

from analysis.common.manifest import add_output, build_manifest, write_manifest
from context import era5

# The paired row's field name -> the short name the ARCO read returns it under.
COMPARED = {
    "era5_100m_u": "u100",
    "era5_100m_v": "v100",
    "era5_10m_u": "u10",
    "era5_10m_v": "v10",
}


def compare_row(dataset: Any, coverage: era5.ArcoCoverage, row: dict[str, Any]) -> dict[str, Any]:
    """One window through the second route, beside what the first route recorded."""
    when = datetime.fromisoformat(row["window_start"])
    values, grid_lat, grid_lon = era5.arco_values_at(dataset, when, row["lat"], row["lon"])
    return {
        "run_id": row["run_id"],
        "window_start": row["window_start"],
        "lat": row["lat"],
        "lon": row["lon"],
        "arco_grid_lat": grid_lat,
        "arco_grid_lon": grid_lon,
        "cds_release_marker": row["release_marker"],
        "arco_release_marker": coverage.release_marker(when),
        "values": {
            field: {
                "cds": row[field],
                "arco": values[short],
                # None rather than a difference when the CDS route recorded no value:
                # a missing field is recorded as missing, never quietly read as zero.
                "difference": None if row[field] is None else values[short] - row[field],
            }
            for field, short in COMPARED.items()
        },
    }


def summarise(comparisons: list[dict[str, Any]], coverage: era5.ArcoCoverage) -> dict[str, Any]:
    """Largest and typical disagreement per variable, and every marker that differs."""
    per_variable: dict[str, Any] = {}
    for field in COMPARED:
        differences = [
            abs(c["values"][field]["difference"])
            for c in comparisons
            if c["values"][field]["difference"] is not None
        ]
        per_variable[field] = {
            "compared": len(differences),
            "max_abs_difference": max(differences) if differences else None,
            "median_abs_difference": median(differences) if differences else None,
        }

    disagreements = [
        {
            "window_start": c["window_start"],
            "cds": c["cds_release_marker"],
            "arco": c["arco_release_marker"],
        }
        for c in comparisons
        if c["cds_release_marker"] != c["arco_release_marker"]
    ]
    return {
        "windows": len(comparisons),
        "unit": "m s-1",
        "per_variable": per_variable,
        "release_marker": {
            "agree": len(comparisons) - len(disagreements),
            "disagree": len(disagreements),
            "disagreements": disagreements,
            # Both routes' tallies, because the ERA5T *share* is what a published result
            # has to report and it is route-dependent.
            "cds_era5t": sum(1 for c in comparisons if c["cds_release_marker"] == "0005"),
            "arco_era5t": sum(1 for c in comparisons if c["arco_release_marker"] == "0005"),
        },
        "arco_coverage": coverage.state(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pairs", type=Path, default=Path("data/pilot-pairs.jsonl"))
    parser.add_argument("--out", type=Path, default=Path("artifacts/era5-route-comparison.json"))
    parser.add_argument("--per-window", type=Path, default=Path("data/era5-route-comparison.jsonl"))
    parser.add_argument("--limit", type=int, default=None, help="Compare only the first N windows.")
    args = parser.parse_args(argv)

    rows = [
        json.loads(line)
        for line in args.pairs.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if args.limit:
        rows = rows[: args.limit]

    dataset, coverage = era5.open_arco()
    try:
        # Built after the store is open, because the boundaries it declares are part of
        # what identifies this run and they are only knowable once it has been read.
        manifest = build_manifest(
            name="era5-route-comparison",
            hypothesis="H1",
            entrypoint="analysis/h1_agreement/compare_era5_routes.py",
            inputs=[args.pairs],
            description="The same run windows read through the CDS and through "
            "ARCO-ERA5, compared value by value and marker by marker. Evidence for "
            "adr/0013 and the re-check for the ERA5T windows.",
            parameters={
                "compared_fields": list(COMPARED),
                "arco_coverage": coverage.state(),
            },
        )
        comparisons = [compare_row(dataset, coverage, row) for row in rows]
    finally:
        # Without this the process does not exit: gcsfs leaves its event loop running
        # and the interpreter waits on it forever, which looks exactly like a hung read.
        dataset.close()

    summary = summarise(comparisons, coverage)
    args.per_window.parent.mkdir(parents=True, exist_ok=True)
    args.per_window.write_text(
        "".join(json.dumps(c) + "\n" for c in comparisons), encoding="utf-8", newline="\n"
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")

    add_output(manifest, args.out)
    path = write_manifest(manifest)
    print(json.dumps(summary, indent=2))
    print(f"per-window: {args.per_window}\nmanifest: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
