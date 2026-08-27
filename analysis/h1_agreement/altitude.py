"""Height above the takeoff point, per run, for H1's altitude regime axis.

``docs/04-methodology.md`` declares altitude as an a priori stratum and
``adr/0006`` specifies that the altitude used for the comparison is **AGL**. AGL is not
recoverable from this corpus.

**Measured rather than assumed.** ``vehicle_local_position`` carries ``dist_bottom`` from a
downward rangefinder, which would be true AGL where it is valid. Across 40 converted runs
``dist_bottom_valid`` is true for a median of 0.4% of rows, and the median height at those
rows is -0.4 m: the sensor reads at touchdown and not in cruise. Deriving AGL properly
needs a terrain model, which this project has not built.

What is recoverable is ``z``, the NED down coordinate relative to the local origin, so
``-z`` is height above the point the estimator's origin was set at -- in practice the
takeoff point. That is a **proxy for altitude, not altitude AGL**, and it is named as one
wherever it is reported. Over flat terrain near the takeoff site the two agree; over a
ridge they do not, and this corpus cannot tell which case a run is.

    uv run python -m analysis.h1_agreement.altitude
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow.parquet as pq

from analysis.common.manifest import add_output, build_manifest, write_manifest

PROCESSING_VERSION = "altitude/1"

# Bands in metres above the takeoff point. 120 m is the ceiling of the EU open category,
# which gives the upper cut an operational meaning rather than an arbitrary one; 50 m
# separates circuit-height work from cruise. Chosen for interpretability after the corpus
# existed, which adr/0016 records: they define cells, not a decision threshold.
ALTITUDE_BANDS = (50.0, 120.0)


def band_of(height_m: float | None) -> str:
    if height_m is None:
        return "unknown"
    low, high = ALTITUDE_BANDS
    if height_m < low:
        return f"agl_proxy_lt_{low:.0f}m"
    if height_m < high:
        return f"agl_proxy_{low:.0f}_to_{high:.0f}m"
    return f"agl_proxy_ge_{high:.0f}m"


def run_height(run_dir: Path) -> dict[str, Any]:
    """Median and 90th-percentile height above the local origin for one run.

    The median rather than the mean, because a flight spends its first and last minutes
    near zero and a mean over the whole log would drag every run toward the ground.
    """
    path = run_dir / "vehicle_local_position.parquet"
    if not path.exists():
        return {"run_id": run_dir.name, "median_height_m": None, "reason": "no_local_position"}

    table = pq.read_table(path, columns=["z", "z_valid"])
    z = table.column("z").to_numpy(zero_copy_only=False).astype(float)
    valid = table.column("z_valid").to_numpy(zero_copy_only=False).astype(bool)
    height = -z[valid & np.isfinite(z)]
    if height.size == 0:
        return {"run_id": run_dir.name, "median_height_m": None, "reason": "no_valid_z"}

    return {
        "run_id": run_dir.name,
        "median_height_m": float(np.median(height)),
        "p90_height_m": float(np.percentile(height, 90)),
        "max_height_m": float(height.max()),
        "samples": int(height.size),
        "reason": None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--inventory", type=Path, default=Path("data/h1-inventory.jsonl"))
    parser.add_argument("--parquet", type=Path, default=Path("data/parquet"))
    parser.add_argument("--out", type=Path, default=Path("data/h1-altitude.jsonl"))
    parser.add_argument("--summary", type=Path, default=Path("artifacts/h1-altitude.json"))
    args = parser.parse_args(argv)

    usable = [
        json.loads(line)["log_id"]
        for line in args.inventory.read_text(encoding="utf-8").splitlines()
        if line.strip() and json.loads(line).get("usable_for_h1")
    ]

    manifest = build_manifest(
        name="h1-altitude",
        hypothesis="H1",
        entrypoint="analysis/h1_agreement/altitude.py",
        description="Height above the takeoff point per usable run, as a named proxy for "
        "altitude AGL, which this corpus cannot recover.",
        parameters={
            "altitude_bands_m": list(ALTITUDE_BANDS),
            "statistic": "median of -z over rows with z_valid",
            "proxy_for": "altitude_agl",
            "why_not_agl": "dist_bottom_valid is true for a median 0.4% of rows and reads "
            "at touchdown; a terrain model would be needed and none is built",
            "processing_version": PROCESSING_VERSION,
        },
    )

    rows = [run_height(args.parquet / run_id) for run_id in usable]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8", newline="\n")

    heights = [r["median_height_m"] for r in rows if r["median_height_m"] is not None]
    bands: dict[str, int] = {}
    for r in rows:
        bands[band_of(r["median_height_m"])] = bands.get(band_of(r["median_height_m"]), 0) + 1
    summary = {
        "runs": len(rows),
        "with_height": len(heights),
        "without_height": len(rows) - len(heights),
        "median_height_m": {
            "min": round(min(heights), 1),
            "median": round(float(np.median(heights)), 1),
            "max": round(max(heights), 1),
        }
        if heights
        else {},
        "bands": dict(sorted(bands.items())),
        "note": "Height above the takeoff point, a proxy for altitude AGL and labelled as "
        "one. The rangefinder that would give true AGL is valid for a median 0.4% of rows "
        "and reads at touchdown; see the module docstring and adr/0006.",
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")

    add_output(manifest, args.summary)
    path = write_manifest(manifest)
    print(json.dumps(summary, indent=2))
    print(f"manifest: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
