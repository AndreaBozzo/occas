"""Draw the stratified pilot sample from the metadata frame.

The pilot is 50-100 runs and its purpose is gate G2, not H1: does conversion work, is
estimator configuration readable across heterogeneous vehicles, does the ERA5 join hold.
No agreement statistic is published from it (``docs/09-dpia.md`` §1.1).

**The strata are chosen so that one set of downloads answers two questions.** Cells are
airframe class x retention side:

- *airframe class* -- fixed-wing/VTOL against rotorcraft -- because G2's real risk is that
  ``EstimatorConfig`` is reconstructible on one and not the other, and H1's declared
  fallback is to narrow to fixed-wing with airspeed. A pilot that sampled the corpus's
  natural mix would be ~85% rotorcraft and would answer that badly.
- *retention side* -- logged inside or outside a 365-day window -- because audit row A8 is
  unanswered and [ADR-0012] decided to measure it here rather than ask. Every sampled log
  either downloads or does not, so availability falls out of requests the analysis already
  makes, at no extra load. Balancing the cells is what turns a byproduct into a
  measurement: an unstratified draw would put ~64% of the sample on the older side and
  estimate the newer side poorly.

**One log per vehicle.** The corpus is heavily unbalanced -- a single airframe can account
for thousands of logs -- so an unconstrained draw would mostly measure one operator's
setup. It also serves the publication rule that cells need distinct vehicles, and it is
the honest unit for a question about whether configuration is readable *across* vehicles.

Deterministic: the sample is a function of the dump's content hash, the seed and the
parameters, all of which the manifest records. **It is therefore reproducible without
being published**, which is why the drawn ids go to ``data/`` -- gitignored, encrypted --
and only stratum counts reach ``artifacts/``.

    uv run python -m ingest.sample
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from analysis.common import exclusions
from analysis.common.manifest import add_output, build_manifest, hash_file, write_manifest
from ingest.dbinfo_audit import (
    FIXED_WING_MARKERS,
    MAX_PLAUSIBLE_DURATION_S,
    MIN_DURATION_S,
    PX4_ATTRIBUTION,
    RETENTION_WINDOW_DAYS,
    SITL_HW,
    headers_path,
    records,
)

SEED = 20260825
PER_CELL = 25  # 4 cells -> 100 runs, the top of the pilot band in docs/09-dpia.md
MAX_PER_VEHICLE = 1


def eligible(row: dict[str, Any], excluded: exclusions.Exclusions) -> bool:
    """The frame, plus the objections. Both are conditions of being sampled at all."""
    if (row.get("sys_hw") or "") == SITL_HW:
        return False
    duration = row.get("duration_s")
    if not isinstance(duration, int | float) or not 0 <= duration <= MAX_PLAUSIBLE_DURATION_S:
        return False
    if duration < MIN_DURATION_S:
        return False
    return not excluded.excludes(log_id=row.get("log_id"), vehicle_uuid=row.get("vehicle_uuid"))


def airframe_class(mav_type: str) -> str:
    return "fixed_wing_or_vtol" if any(m in mav_type for m in FIXED_WING_MARKERS) else "rotorcraft"


def draw(
    rows: list[dict[str, Any]],
    *,
    cutoff: str,
    per_cell: int = PER_CELL,
    seed: int = SEED,
    classes: tuple[str, ...] = ("fixed_wing_or_vtol", "rotorcraft"),
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Pick up to ``per_cell`` runs per stratum, at most one per vehicle.

    Shuffled once with a seeded RNG and then taken in order, rather than sampled per
    cell: one shuffle makes the vehicle cap interact with the cells deterministically,
    where independent per-cell draws would let cell order decide who wins a tie.
    """
    ordered = sorted(rows, key=lambda r: r["log_id"])  # stable regardless of dump order
    random.Random(seed).shuffle(ordered)

    chosen: list[dict[str, Any]] = []
    per_stratum: Counter = Counter()
    per_vehicle: Counter = Counter()
    available: dict[str, int] = defaultdict(int)

    for row in ordered:
        klass = airframe_class(row.get("mav_type") or "")
        side = "within_window" if (row.get("log_date") or "")[:10] >= cutoff else "older"
        stratum = f"{klass}|{side}"
        available[stratum] += 1
        if klass not in classes:
            continue
        if per_stratum[stratum] >= per_cell:
            continue
        vehicle = row.get("vehicle_uuid")
        if vehicle and per_vehicle[vehicle] >= MAX_PER_VEHICLE:
            continue
        per_stratum[stratum] += 1
        if vehicle:
            per_vehicle[vehicle] += 1
        chosen.append(
            {
                "log_id": row.get("log_id"),
                "download_url": row.get("download_url"),
                "stratum": stratum,
                "log_date": row.get("log_date"),
                "duration_s": row.get("duration_s"),
                "mav_type": row.get("mav_type"),
                "sys_hw": row.get("sys_hw"),
                "vehicle_uuid": vehicle,
                # Filled in by the retrieval, which is what closes audit row A8.
                "ulg_available": None,
            }
        )
    return chosen, dict(available)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cache", type=Path, default=Path("data/dbinfo.json.gz"))
    parser.add_argument("--out", type=Path, default=Path("data/pilot-sample.jsonl"))
    parser.add_argument("--summary", type=Path, default=Path("artifacts/pilot-sample-summary.json"))
    parser.add_argument("--per-cell", type=int, default=PER_CELL)
    parser.add_argument(
        "--classes",
        default="fixed_wing_or_vtol,rotorcraft",
        help="Airframe classes to draw from. The pilot measured 72%% and 52%% of "
        "fixed-wing/VTOL draws usable against 8%% and 4%% of rotorcraft, because "
        "multirotors mostly do not log wind -- so an H1 draw restricted to "
        "fixed_wing_or_vtol costs about a third as many downloads per usable run.",
    )
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args(argv)

    classes = tuple(c.strip() for c in args.classes.split(",") if c.strip())
    excluded = exclusions.load()
    headers = {}
    if headers_path(args.cache).exists():
        headers = json.loads(headers_path(args.cache).read_text(encoding="utf-8"))

    # Named after the draw it made, as ingest/inventory.py and
    # analysis/h1_agreement/build_pairs.py are. This is the third entrypoint to have
    # carried "pilot" in a hardcoded manifest name: run over the H1 draw it produced
    # artifacts/h1-sample-summary.json under the name px4-pilot-sample, so the provenance
    # record named a population the summary beside it did not describe.
    draw = args.out.stem.removesuffix("-sample")
    manifest = build_manifest(
        name=f"px4-{draw}-sample",
        hypothesis="none",
        entrypoint="ingest/sample.py",
        description=(
            f"Stratified {draw} sample of the >=300 s non-SITL frame, for gate G2. "
            "Draws ids only; no logs retrieved."
        ),
        inputs=[
            {
                "path": args.cache.as_posix(),
                "content_hash": hash_file(args.cache),
                "source": {
                    "source": "px4_flight_review",
                    "source_version": headers.get("last_modified"),
                    "source_url": headers.get("final_url"),
                    "retrieved_at": headers.get("retrieved_at", "1970-01-01T00:00:00+00:00"),
                    "licence": "CC-BY-4.0",
                    "attribution": PX4_ATTRIBUTION,
                },
            }
        ],
        parameters={
            "min_duration_s": MIN_DURATION_S,
            "per_cell": args.per_cell,
            "max_per_vehicle": MAX_PER_VEHICLE,
            "classes": list(classes),
            "retention_window_days": RETENTION_WINDOW_DAYS,
            "exclusions": excluded.state(),
        },
        seed=args.seed,
    )

    rows = [r for r in records(args.cache) if eligible(r, excluded)]
    newest = max((r.get("log_date") or "")[:10] for r in rows)
    cutoff = (datetime.fromisoformat(newest) - timedelta(days=RETENTION_WINDOW_DAYS)).date()
    chosen, available = draw(
        rows,
        cutoff=cutoff.isoformat(),
        per_cell=args.per_cell,
        seed=args.seed,
        classes=classes,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        "".join(json.dumps(c) + "\n" for c in chosen), encoding="utf-8", newline="\n"
    )

    summary = {
        "frame_size": len(rows),
        "drawn": len(chosen),
        "cutoff": cutoff.isoformat(),
        "per_stratum": dict(Counter(c["stratum"] for c in chosen)),
        "frame_per_stratum": available,
        "distinct_vehicles": len({c["vehicle_uuid"] for c in chosen if c["vehicle_uuid"]}),
        "classes": list(classes),
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")

    add_output(manifest, args.summary)
    path = write_manifest(manifest)
    print(json.dumps(summary, indent=2))
    print(f"ids: {args.out} (not committed)\nmanifest: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
