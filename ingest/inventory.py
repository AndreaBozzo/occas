"""Inventory of the converted pilot sample: what H1 actually has to work with. Gate G2.

G2 asks whether the usable-run rate is sufficient and whether estimator configuration is
readable. Both are questions about *what is in the logs*, and neither could be designed
against imagined files -- which is why this module stayed unwritten until a sample
existed on disk.

A run is usable for H1 when it carries both halves of the comparison:

- ``wind`` -- the EKF2 wind estimate, ``windspeed_north``/``windspeed_east``. Without it
  there is no onboard side to compare against, and ADR-0003 forbids substituting anything
  for it.
- ``vehicle_global_position`` -- ``lat``/``lon``. Without it there is nothing to join ERA5
  *to*. Local or vision position does not substitute: a flight logged on
  ``vehicle_local_position`` alone has coordinates in a frame whose origin is unknown.

``variance_north``/``variance_east`` on the wind topic are recorded separately, because
that is what ``EstimatorConfig`` calls the reported variance, and its
``reconstructible: false`` case exists for logs that lack it. Whether that case is rare
or common is itself an M2 finding.

**Coverage is recorded, never filtered.** A run missing a topic is counted as missing it,
with the reason, and stays in the denominator. The unusable share is the finding, not an
inconvenience to be dropped on the way to a rate.

    uv run python -m ingest.inventory
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from analysis.common.manifest import add_output, build_manifest, write_manifest
from context import align

# Both halves of H1's comparison, and the join key. Absence of any of these makes a run
# unusable for H1 -- not lower quality, unusable.
REQUIRED_TOPICS = ("wind", "vehicle_global_position")
WIND_COMPONENTS = ("windspeed_north", "windspeed_east")
WIND_VARIANCE = ("variance_north", "variance_east")
POSITION_COLUMNS = ("lat", "lon")
# Topics worth counting even though H1 does not require them: they decide which fallbacks
# and cross-checks are open, and their absence is a finding about the corpus.
OPTIONAL_TOPICS = ("airspeed", "airspeed_wind", "estimator_status", "vehicle_local_position")


def topic(run_dir: Path, name: str) -> tuple[bool, int, list[str]]:
    """``(present, rows, columns)`` for one topic, tolerant of an unreadable file.

    An unreadable Parquet is reported as absent rather than raised: it is a fact about
    the corpus in exactly the way a missing topic is, and one bad file must not stop the
    inventory of ninety-nine good ones.
    """
    path = run_dir / f"{name}.parquet"
    if not path.exists():
        return False, 0, []
    try:
        table = pq.read_table(path)
    except Exception:
        return False, 0, []
    return True, table.num_rows, list(table.column_names)


ULOG_CONVERT_REV = "flight-review-rs@0fb44f74"


def tool_version(summary_path: Path) -> str:
    """What produced the Parquet, pinned tightly enough to fetch again."""
    reported = "unknown"
    if summary_path.exists():
        reported = json.loads(summary_path.read_text(encoding="utf-8")).get(
            "tool_version", reported
        )
    return f"{reported} ({ULOG_CONVERT_REV})"


def inspect(run_dir: Path, expected_date: str | None = None) -> dict[str, Any]:
    """Everything G2 needs to know about one converted run."""
    record: dict[str, Any] = {"log_id": run_dir.name, "topics": {}}

    for name in (*REQUIRED_TOPICS, *OPTIONAL_TOPICS):
        present, rows, columns = topic(run_dir, name)
        record["topics"][name] = {"present": present, "rows": rows}
        if name == "wind" and present:
            record["wind_components"] = all(c in columns for c in WIND_COMPONENTS)
            # EstimatorConfig's reported variance. Its reconstructible:false case is for
            # exactly the logs where this is False.
            record["wind_variance_reconstructible"] = all(c in columns for c in WIND_VARIANCE)
        if name == "vehicle_global_position" and present:
            record["position_columns"] = all(c in columns for c in POSITION_COLUMNS)

    record.setdefault("wind_components", False)
    record.setdefault("wind_variance_reconstructible", False)
    record.setdefault("position_columns", False)

    missing = [n for n in REQUIRED_TOPICS if not record["topics"][n]["present"]]
    empty = [
        n
        for n in REQUIRED_TOPICS
        if record["topics"][n]["present"] and not record["topics"][n]["rows"]
    ]
    # Absolute time is a third requirement, and it is not visible as a missing topic.
    # Run 405385f7 carries wind, position, and a GPS reporting fix_type 3 with a
    # non-zero time_utc_usec that never contained a date -- so it looked usable and
    # would have joined to weather in 1970. Checked here rather than discovered later.
    try:
        gps = pq.read_table(run_dir / "vehicle_gps_position.parquet")
        anchor = align.clock_anchor(
            {
                "time_utc_usec": gps.column("time_utc_usec").to_pylist(),
                "timestamp": gps.column("timestamp").to_pylist(),
            },
            expected_date=expected_date,
        )
        record["absolute_time"] = True
        record["clock_spread_s"] = anchor.spread_s
        record["clock_anchor_reason"] = None
    except (align.NoAbsoluteTime, FileNotFoundError, KeyError) as error:
        record["absolute_time"] = False
        record["clock_spread_s"] = None
        record["clock_anchor_reason"] = str(error)[:120]

    record["missing_required"] = missing
    record["empty_required"] = empty
    record["usable_for_h1"] = (
        not missing
        and not empty
        and record["wind_components"]
        and record["position_columns"]
        and record["absolute_time"]
    )
    return record


def summarise(records: list[dict[str, Any]], strata: dict[str, str]) -> dict[str, Any]:
    by_stratum: dict[str, dict[str, int]] = defaultdict(lambda: {"runs": 0, "usable": 0})
    reasons: dict[str, int] = defaultdict(int)
    topic_presence: dict[str, int] = defaultdict(int)
    variance_ok = 0

    for record in records:
        cell = by_stratum[strata.get(record["log_id"], "unknown")]
        cell["runs"] += 1
        if record["usable_for_h1"]:
            cell["usable"] += 1
        else:
            for name in record["missing_required"]:
                reasons[f"missing:{name}"] += 1
            for name in record["empty_required"]:
                reasons[f"empty:{name}"] += 1
            if not record["absolute_time"]:
                reasons["no_absolute_time"] += 1
            elif not record["missing_required"] and not record["empty_required"]:
                reasons["columns_absent"] += 1
        for name, info in record["topics"].items():
            if info["present"]:
                topic_presence[name] += 1
        if record["wind_variance_reconstructible"]:
            variance_ok += 1

    runs = len(records)
    usable = sum(1 for r in records if r["usable_for_h1"])
    return {
        "runs": runs,
        "usable_for_h1": usable,
        "usable_rate": round(usable / runs, 4) if runs else None,
        "unusable_reasons": dict(sorted(reasons.items())),
        "topic_presence": dict(sorted(topic_presence.items())),
        # Of the runs that have a wind topic at all, how many report their own variance.
        "wind_variance_reconstructible": variance_ok,
        "wind_variance_rate_of_wind_runs": (
            round(variance_ok / topic_presence["wind"], 4) if topic_presence.get("wind") else None
        ),
        "by_stratum": {k: dict(v) for k, v in sorted(by_stratum.items())},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--parquet", type=Path, default=Path("data/parquet"))
    parser.add_argument("--sample", type=Path, default=Path("data/pilot-sample.jsonl"))
    parser.add_argument("--out", type=Path, default=Path("artifacts/pilot-inventory.json"))
    parser.add_argument("--per-run", type=Path, default=Path("data/pilot-inventory.jsonl"))
    args = parser.parse_args(argv)

    conversion = args.parquet / "conversion-summary.json"
    manifest = build_manifest(
        name="px4-pilot-inventory",
        hypothesis="none",
        entrypoint="ingest/inventory.py",
        description="Field coverage and H1 usability of the converted pilot sample. Gate G2.",
        # The schema allows a tool exactly a name and a version, so the version string
        # carries the git rev too: "0.1.0" alone does not identify a build of an
        # unreleased crate, and the whole point of recording the tool is to be able to
        # get the same one back.
        external_tools=[{"name": "ulog-convert", "version": tool_version(conversion)}],
        parameters={
            "required_topics": list(REQUIRED_TOPICS),
            "wind_components": list(WIND_COMPONENTS),
            "position_columns": list(POSITION_COLUMNS),
            # Which draw this inventory is of. The corpus directory holds more than one,
            # so the summary is not reproducible without naming the sample that bounds it.
            "sample": str(args.sample),
        },
    )

    # encoding is explicit everywhere here: these files are UTF-8 and Windows would
    # otherwise decode them as cp1252, which fails on the first non-ASCII byte.
    strata: dict[str, str] = {}
    dates: dict[str, str | None] = {}
    if args.sample.exists():
        for line in args.sample.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                strata[row["log_id"]] = row["stratum"]
                dates[row["log_id"]] = (row.get("log_date") or "")[:10] or None

    # The inventory is of *this sample*, not of whatever happens to be in the corpus
    # directory. One directory now holds two draws: the pilot's 100 runs and the H1
    # draw's 1,600, overlapping in 50. Walking it whole would have pooled the pilot's 50
    # rotorcraft -- 8% usable against fixed-wing's 72% -- into H1's usable rate, and
    # symmetrically swept 1,500 H1 runs into a re-run of the pilot's, which is why that
    # artifact had quietly stopped reproducing. `summarise` did file the strangers under
    # an "unknown" stratum, so they were visible; they were still counted in the
    # headline rate, and visible-but-counted is the shape of most pooling errors.
    #
    # Same rule as PX4_SITL: populations are separated, never merged under a label. The
    # count of what was set aside is recorded rather than dropped silently.
    run_dirs = [d for d in sorted(args.parquet.iterdir()) if d.is_dir()]
    outside = [d for d in run_dirs if strata and d.name not in strata]
    if outside:
        run_dirs = [d for d in run_dirs if d.name in strata]
        print(
            f"{len(outside)} converted runs in {args.parquet} are not in {args.sample} "
            f"and are excluded: a different draw, not a stratum of this one."
        )

    records = [inspect(d, expected_date=dates.get(d.name)) for d in run_dirs]
    summary = summarise(records, strata)
    summary["runs_outside_sample_excluded"] = len(outside)

    args.per_run.parent.mkdir(parents=True, exist_ok=True)
    args.per_run.write_text(
        "".join(json.dumps(r) + "\n" for r in records), encoding="utf-8", newline="\n"
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")

    add_output(manifest, args.out)
    path = write_manifest(manifest)
    print(json.dumps(summary, indent=2))
    print(f"per-run: {args.per_run} (not committed)\nmanifest: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
