"""H1: agreement between ERA5 and the onboard EKF2 wind estimate, per regime.

**Neither source is ground truth** (``adr/0003``). Everything here is a limit of
agreement between two measurement methods; nothing is regressed on anything, and the
onboard estimate is never called truth. The difference is formed in one declared
direction -- ``era5 - onboard`` -- and that direction is recorded in the manifest, so a
positive bias means ERA5 reads higher, not that the aircraft was wrong.

What is computed was fixed before this file could see a number:

- ``adr/0006`` -- components are primary, ``u`` east and ``v`` north; the magnitude of
  the vector difference beside them; scalar speed secondary and labelled; direction
  wrapped to (-180, 180] and reported only where defined; 100 m primary, 10 m secondary.
- ``adr/0014`` -- stratum results are primary, a pooled number is a reweighted one
  reported beside the unweighted sample statistic, and the bootstrap resamples **runs**
  within stratum.
- ``adr/0015`` -- direction is undefined below 2.0 m s-1 and the cutoff is swept;
  ``useful_proxy`` is the upper limit of agreement on the vector difference magnitude at
  or below 3.0 m s-1, reported beside the estimator-relative ratio per component.

The regime axis here is the retention stratum, which is the one ``adr/0014`` makes
mandatory. The other axes declared a priori in ``docs/04-methodology.md`` -- airframe,
airspeed sensor, variance band, altitude, terrain, season -- are a separate pass. Cell
counts are not an outcome, so choosing which of them to cut *after* seeing how many runs
land in each is not a retrospective choice about a result; choosing a threshold or an
estimand that way would be.

    uv run python -m analysis.h1_agreement.agreement --pairs data/h1-pairs.jsonl
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

from analysis.common import exclusions
from analysis.common.manifest import add_output, build_manifest, write_manifest
from analysis.common.schema import validate

PROCESSING_VERSION = "agreement/1"

# adr/0015. Both are manifest parameters and neither may move after a result is seen.
DIRECTION_SPEED_THRESHOLD_MS = 2.0
DIRECTION_SWEEP_MS = (1.0, 3.0)
USEFUL_PROXY_LOA_MS = 3.0

# 95% limits of agreement. 1.96 rather than a t quantile: the smallest regime reported
# is in the hundreds of windows, where the difference is in the third decimal.
LOA_Z = 1.96

BOOTSTRAP_RESAMPLES = 2000
BOOTSTRAP_SEED = 20260827

# adr/0014's frame, from the dbinfo dump pinned on 2026-08-20 -- the same file the draw
# was made from. These are N_h; n_h is whatever the realised usable runs turn out to be.
FRAME_SIZES = {
    "fixed_wing_or_vtol|within_window": 6185,
    "fixed_wing_or_vtol|older": 10497,
}

# A regime thinner than this reports its stratum result alone and is not pooled into a
# reweighted number, per adr/0014. The value is borrowed from adr/0009's publication
# floor rather than derived: 20 runs is where that ADR stopped trusting a cell, and
# reweighting inside a cell smaller than that is unstable for the same reason. It is a
# manifest parameter so a reader can see it was a choice.
MIN_RUNS_PER_REGIME = 20

# The other half of the same threshold, and not optional. ``docs/09-dpia.md`` 4.1 states
# it as one condition -- "no published cell draws on fewer than 20 runs from at least 10
# distinct vehicle_uuids" -- and 20 runs from three vehicles is three operators, not
# twenty. Enforcing the run count alone would be a gate built one step short of the path
# it exists to block, which passes with and without the protection.
#
# The count is used and never published: adr/0009 forbids emitting a vehicle_uuid at all,
# "raw or hashed", so what leaves this module is how many there were.
MIN_VEHICLES_PER_REGIME = 10

VERTICAL_REFERENCES = {
    "era5_100m": ("era5_100m_u", "era5_100m_v"),
    "era5_10m": ("era5_10m_u", "era5_10m_v"),
}

SERIES_KEYS = ("u", "v", "vector_difference_magnitude", "speed")


def wrap_degrees(angle: float) -> float:
    """Wrap a signed angle to (-180, 180], the interval ``adr/0006`` declared."""
    wrapped = (angle + 180.0) % 360.0 - 180.0
    # The half turn lands on the open end of the interval; it belongs at the closed one.
    return 180.0 if wrapped == -180.0 else wrapped


def bearing_difference_deg(u_a: float, v_a: float, u_b: float, v_b: float) -> float:
    """Signed angle from vector b to vector a, wrapped to (-180, 180].

    Taken between the two vectors rather than between two compass bearings, which makes
    it independent of the "blowing from" / "blowing to" convention: both sources are read
    in the same convention, and the difference of two bearings is unchanged when both are
    turned through 180 degrees.
    """
    return wrap_degrees(math.degrees(math.atan2(v_a, u_a) - math.atan2(v_b, u_b)))


def weighted_mean_and_sd(values: np.ndarray, weights: np.ndarray | None) -> tuple[float, float]:
    """Mean and standard deviation, optionally under design weights.

    Design weights are frequency weights -- one sampled run stands for ``N_h / n_h`` runs
    of the frame -- so the denominator is the sum of the weights rather than the count of
    rows, and Bessel's correction subtracts one from that sum. With weights all 1 this is
    the ordinary sample mean and standard deviation.
    """
    if values.size == 0:
        raise ValueError("no windows: an agreement statistic over an empty regime is not a number")
    if weights is None:
        weights = np.ones_like(values)
    total = float(weights.sum())
    mean = float((weights * values).sum() / total)
    denominator = total - 1.0
    if denominator <= 0:
        return mean, 0.0
    return mean, math.sqrt(float((weights * (values - mean) ** 2).sum() / denominator))


def bland_altman(values: np.ndarray, weights: np.ndarray | None = None) -> dict[str, Any]:
    """Bias and 95% limits of agreement for one difference series.

    No confidence interval here -- these are point estimates. Intervals come from
    ``bootstrap``, which resamples runs, because windows within a run are not independent.
    """
    bias, dispersion = weighted_mean_and_sd(np.asarray(values, dtype=float), weights)
    return {
        "bias": bias,
        "limits_of_agreement": [bias - LOA_Z * dispersion, bias + LOA_Z * dispersion],
        "dispersion": dispersion,
    }


def series_arrays(rows: Sequence[dict], level: str) -> dict[str, np.ndarray]:
    """The four difference series for one vertical reference, all ``era5 - onboard``.

    Computed once for the whole regime and indexed into by the bootstrap, rather than
    recomputed per resample: 2,000 resamples over a thousand windows is a million rows of
    arithmetic either way, and only one of the two is worth doing two thousand times.
    """
    era5_u_key, era5_v_key = VERTICAL_REFERENCES[level]
    era5_u = np.array([row[era5_u_key] for row in rows], dtype=float)
    era5_v = np.array([row[era5_v_key] for row in rows], dtype=float)
    onboard_u = np.array([row["onboard_u"] for row in rows], dtype=float)
    onboard_v = np.array([row["onboard_v"] for row in rows], dtype=float)
    du = era5_u - onboard_u
    dv = era5_v - onboard_v
    return {
        "u": du,
        "v": dv,
        "vector_difference_magnitude": np.hypot(du, dv),
        "speed": np.hypot(era5_u, era5_v) - np.hypot(onboard_u, onboard_v),
    }


def design_weights(rows: Sequence[dict]) -> np.ndarray:
    """Design weight ``N_h / n_h`` per window, on the **realised usable** ``n_h``.

    On the realised count and not the drawn 800, because the runs that drop out of the
    draw are not a random subset of it -- usability differs by stratum, 72% against 52%
    (``adr/0014``).

    Computed once, from the data as it stands, and then held fixed through the bootstrap.
    A resample draws ``n_h`` runs with replacement and so reproduces the design's own
    sample size; recomputing the weight from the *distinct* runs a replicate happens to
    contain -- about 63% of them -- would inflate it by half and make every replicate
    weight a different population.
    """
    realised = {
        stratum: len({r["run_id"] for r in rows if r["stratum"] == stratum})
        for stratum in {r["stratum"] for r in rows}
    }
    return np.array(
        [FRAME_SIZES[row["stratum"]] / realised[row["stratum"]] for row in rows], dtype=float
    )


def direction_statistics(rows: Sequence[dict], level: str, threshold: float) -> dict[str, Any]:
    """Circular difference, computed only where both sources exceed ``threshold``.

    Windows below it are counted as undefined rather than dropped: at low wind direction
    is not noisy, it is meaningless, and dropping them silently would bias the result
    toward exactly the conditions where direction is well determined (``adr/0006``).
    """
    era5_u_key, era5_v_key = VERTICAL_REFERENCES[level]
    defined: list[float] = []
    undefined = 0
    for row in rows:
        era5_u, era5_v = row[era5_u_key], row[era5_v_key]
        onboard_u, onboard_v = row["onboard_u"], row["onboard_v"]
        if math.hypot(era5_u, era5_v) <= threshold or math.hypot(onboard_u, onboard_v) <= threshold:
            undefined += 1
            continue
        defined.append(bearing_difference_deg(era5_u, era5_v, onboard_u, onboard_v))

    if not defined:
        return {
            "speed_threshold_ms": threshold,
            "n_defined": 0,
            "n_undefined": undefined,
            "mean_absolute_deg": None,
            "limits_of_agreement_deg": None,
        }
    array = np.array(defined, dtype=float)
    mean, dispersion = weighted_mean_and_sd(array, None)
    return {
        "speed_threshold_ms": threshold,
        "n_defined": len(defined),
        "n_undefined": undefined,
        "mean_absolute_deg": float(np.abs(array).mean()),
        "limits_of_agreement_deg": [mean - LOA_Z * dispersion, mean + LOA_Z * dispersion],
    }


def estimator_relative_ratio(rows: Sequence[dict], level: str) -> dict[str, Any]:
    """Limit-of-agreement half-width over the estimator's own sigma, per component.

    ``adr/0015``'s second view. The onboard variance is EKF2's self-assessment and not an
    independent measurement, so this is reported as a number beside the verdict and never
    as the verdict: a regime where the filter is very unsure of itself passes it easily.

    Per component because ``adr/0006`` makes components primary and because the variance
    genuinely is anisotropic -- the estimator constrains wind better along the direction
    its airspeed vector has varied in than across it.
    """
    series = series_arrays(rows, level)
    out: dict[str, Any] = {}
    for component in ("u", "v"):
        sigmas = [
            math.sqrt(row[f"onboard_variance_{component}"])
            for row in rows
            if row.get(f"onboard_variance_{component}") is not None
        ]
        lower, upper = bland_altman(series[component])["limits_of_agreement"]
        half_width = (upper - lower) / 2.0
        mean_sigma = float(np.mean(sigmas)) if sigmas else None
        out[component] = {
            "loa_half_width_ms": half_width,
            "mean_onboard_sigma_ms": mean_sigma,
            "ratio": (half_width / mean_sigma) if mean_sigma else None,
            "n_windows_with_variance": len(sigmas),
        }
    return out


def _run_indices_by_stratum(rows: Sequence[dict]) -> dict[str, list[np.ndarray]]:
    """Row positions of each run, grouped by the stratum that run was drawn from."""
    positions: dict[str, list[int]] = defaultdict(list)
    stratum_of: dict[str, str] = {}
    for index, row in enumerate(rows):
        positions[row["run_id"]].append(index)
        stratum_of[row["run_id"]] = row["stratum"]
    grouped: dict[str, list[np.ndarray]] = defaultdict(list)
    for run_id, indices in positions.items():
        grouped[stratum_of[run_id]].append(np.array(indices, dtype=int))
    return dict(grouped)


def bootstrap(
    rows: Sequence[dict],
    level: str,
    *,
    weights: np.ndarray | None,
    resamples: int = BOOTSTRAP_RESAMPLES,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, dict[str, Any]]:
    """Percentile confidence intervals, resampling **runs** within stratum.

    Bootstrapping windows would treat consecutive hours of one flight as independent
    evidence and report an interval far tighter than the design earned; the
    ``validation_artifact.json`` schema pins ``bootstrap.unit`` to ``run`` for that
    reason. Stratifying the resample keeps the interval consistent with the design that
    produced the point estimate (``adr/0014``).
    """
    series = series_arrays(rows, level)
    runs_by_stratum = _run_indices_by_stratum(rows)
    rng = np.random.default_rng(seed)
    draws: dict[str, dict[str, list[float]]] = {
        key: {"bias": [], "loa_lower": [], "loa_upper": []} for key in SERIES_KEYS
    }

    for _ in range(resamples):
        parts = []
        for runs in runs_by_stratum.values():
            picked = rng.integers(0, len(runs), size=len(runs))
            parts.extend(runs[index] for index in picked)
        index = np.concatenate(parts)
        resampled_weights = None if weights is None else weights[index]
        for key in SERIES_KEYS:
            statistic = bland_altman(series[key][index], resampled_weights)
            draws[key]["bias"].append(statistic["bias"])
            draws[key]["loa_lower"].append(statistic["limits_of_agreement"][0])
            draws[key]["loa_upper"].append(statistic["limits_of_agreement"][1])

    return {
        key: {
            "bias_ci": _percentiles(draws[key]["bias"]),
            "limits_ci": [
                _percentiles(draws[key]["loa_lower"]),
                _percentiles(draws[key]["loa_upper"]),
            ],
        }
        for key in SERIES_KEYS
    }


def _percentiles(values: Sequence[float]) -> list[float]:
    array = np.asarray(values, dtype=float)
    return [float(np.percentile(array, 2.5)), float(np.percentile(array, 97.5))]


def regime_artifact(
    rows: Sequence[dict],
    *,
    label: str,
    criteria: dict[str, Any],
    level: str,
    weighted: bool,
    manifest_id: str,
    resamples: int,
    seed: int,
    direction_threshold: float = DIRECTION_SPEED_THRESHOLD_MS,
) -> dict[str, Any]:
    """One ``ValidationArtifact``: the statistics for one regime at one vertical reference."""
    weights = design_weights(rows) if weighted else None
    series = series_arrays(rows, level)
    statistics: dict[str, Any] = {"unit": "m s-1"}
    for key in SERIES_KEYS:
        statistics[key] = bland_altman(series[key], weights)
    statistics["direction"] = direction_statistics(rows, level, direction_threshold)

    for key, interval in bootstrap(
        rows, level, weights=weights, resamples=resamples, seed=seed
    ).items():
        statistics[key].update(interval)

    # adr/0015: the verdict is the absolute band. The estimator-relative ratio is reported
    # beside it, in the summary, and is deliberately not folded into this boolean -- a
    # regime may pass one and fail the other, and that disagreement is itself the result.
    upper_loa = statistics["vector_difference_magnitude"]["limits_of_agreement"][1]

    return {
        "validation_model_id": f"h1-{label}-{level}-{'reweighted' if weighted else 'sample'}",
        "regime": {"label": label, "criteria": criteria},
        "sources_compared": ["era5_wind", "px4_ekf2_wind"],
        "vertical_reference": level,
        "n_runs": len({row["run_id"] for row in rows}),
        "n_windows": len(rows),
        "statistics": statistics,
        "bootstrap": {"unit": "run", "n_resamples": resamples, "seed": seed},
        "useful_proxy": bool(upper_loa <= USEFUL_PROXY_LOA_MS),
        "manifest_id": manifest_id,
    }


def publishable_regimes(
    by_stratum: dict[str, list[dict]], *, min_runs: int, min_vehicles: int
) -> tuple[list[str], dict[str, dict[str, int]]]:
    """Which strata may be reported, and the counts of those that may not.

    ``docs/09-dpia.md`` 4.1 states one threshold with two halves -- "no published cell
    draws on fewer than 20 runs from at least 10 distinct vehicle_uuids" -- so a cell has
    to clear both. Twenty runs from three airframes is three operators wearing a
    twenty-run disguise, and the run count alone would not see it.

    Suppressed cells come back **with their counts**, because a suppression that hides its
    own existence is its own distortion (``adr/0009``). The counts are integers; no
    identifier leaves this function.
    """
    thick = sorted(
        stratum
        for stratum, rows in by_stratum.items()
        if len({r["run_id"] for r in rows}) >= min_runs
        and len({r["vehicle_uuid"] for r in rows}) >= min_vehicles
    )
    suppressed = {
        stratum: {
            "n_runs": len({r["run_id"] for r in rows}),
            "n_vehicles": len({r["vehicle_uuid"] for r in rows}),
        }
        for stratum, rows in sorted(by_stratum.items())
        if stratum not in thick
    }
    return thick, suppressed


def load_pairs(pairs: Path, sample: Path, excluded: exclusions.Exclusions) -> list[dict]:
    """Read the paired rows, attach each run's stratum, and drop excluded runs.

    The exclusion pass is not redundant with the one at retrieval. An objection arriving
    after a log is already on disk has to remove it from the *results* too, which is what
    ``PRIVACY.md`` promises: "later runs do not re-include it". ``exclusions.load`` raises
    when the list is absent, so a missing list stops H1 rather than quietly meaning that
    nobody objected.
    """
    strata: dict[str, str] = {}
    vehicles: dict[str, str] = {}
    for line in sample.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entry = json.loads(line)
            strata[entry["log_id"]] = entry["stratum"]
            vehicles[entry["log_id"]] = entry.get("vehicle_uuid") or ""

    rows = []
    for line in pairs.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        run_id = row["run_id"]
        if run_id in excluded.log_ids or vehicles.get(run_id) in excluded.vehicle_uuids:
            continue
        row["stratum"] = strata[run_id]
        # Carried on the row so a regime can be counted against the k-threshold, and
        # never written out: every output of this module is built as a fresh dict.
        row["vehicle_uuid"] = vehicles.get(run_id, "")
        rows.append(row)
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pairs", type=Path, default=Path("data/h1-pairs.jsonl"))
    parser.add_argument("--sample", type=Path, default=Path("data/h1-sample.jsonl"))
    parser.add_argument(
        "--artifacts", type=Path, default=Path("artifacts/h1-validation-artifacts.jsonl")
    )
    parser.add_argument("--out", type=Path, default=Path("artifacts/h1-agreement.json"))
    parser.add_argument("--resamples", type=int, default=BOOTSTRAP_RESAMPLES)
    parser.add_argument("--seed", type=int, default=BOOTSTRAP_SEED)
    parser.add_argument("--min-runs", type=int, default=MIN_RUNS_PER_REGIME)
    parser.add_argument("--min-vehicles", type=int, default=MIN_VEHICLES_PER_REGIME)
    args = parser.parse_args(argv)

    excluded = exclusions.load()
    rows = load_pairs(args.pairs, args.sample, excluded)
    if not rows:
        raise SystemExit(f"{args.pairs} yielded no rows to compare")

    manifest = build_manifest(
        name="h1-agreement",
        hypothesis="H1",
        entrypoint="analysis/h1_agreement/agreement.py",
        description="Agreement between ERA5 and the onboard EKF2 wind estimate, per regime "
        "and per vertical reference. Neither source is ground truth.",
        seed=args.seed,
        parameters={
            "difference_direction": "era5_minus_onboard",
            "loa_z": LOA_Z,
            "direction_speed_threshold_ms": DIRECTION_SPEED_THRESHOLD_MS,
            "direction_sweep_ms": list(DIRECTION_SWEEP_MS),
            "useful_proxy_loa_ms": USEFUL_PROXY_LOA_MS,
            "min_runs_per_regime": args.min_runs,
            "min_vehicles_per_regime": args.min_vehicles,
            "bootstrap_resamples": args.resamples,
            "frame_sizes": FRAME_SIZES,
            "processing_version": PROCESSING_VERSION,
            "exclusions": excluded.state(),
        },
    )
    manifest_id = manifest["manifest_id"]

    by_stratum: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_stratum[row["stratum"]].append(row)
    runs_in = {s: len({r["run_id"] for r in rs}) for s, rs in by_stratum.items()}
    vehicles_in = {s: len({r["vehicle_uuid"] for r in rs}) for s, rs in by_stratum.items()}
    thick, suppressed = publishable_regimes(
        by_stratum, min_runs=args.min_runs, min_vehicles=args.min_vehicles
    )
    poolable = [row for row in rows if row["stratum"] in thick]

    artifacts: list[dict] = []
    for level in VERTICAL_REFERENCES:
        # Strata first, and they are the primary result: a number that names the stratum
        # it was computed on needs no weighting argument to be true (adr/0014).
        for stratum in thick:
            artifacts.append(
                regime_artifact(
                    by_stratum[stratum],
                    label=stratum,
                    criteria={"retention_stratum": stratum, "airframe": "fixed_wing_or_vtol"},
                    level=level,
                    weighted=False,
                    manifest_id=manifest_id,
                    resamples=args.resamples,
                    seed=args.seed,
                )
            )
        # Then both pooled numbers -- two where a reader expects one, because the gap
        # between them is the size of the design effect (adr/0014).
        for weighted in (False, True):
            artifacts.append(
                regime_artifact(
                    poolable,
                    label="all_fixed_wing_or_vtol",
                    criteria={
                        "airframe": "fixed_wing_or_vtol",
                        "pooling": "reweighted" if weighted else "unweighted_sample",
                        "strata_pooled": thick,
                    },
                    level=level,
                    weighted=weighted,
                    manifest_id=manifest_id,
                    resamples=args.resamples,
                    seed=args.seed,
                )
            )

    for artifact in artifacts:
        validate(artifact, "validation_artifact.json")

    # The sweep and the estimator-relative ratio live in the summary rather than in the
    # ValidationArtifact: the schema pins one threshold per artifact and one boolean, and
    # widening it to carry adr/0015's second view would be a schema change made to fit a
    # result. Both are reported, and reported together, which is what the ADR asks.
    sweep: dict[str, Any] = {}
    ratios: dict[str, Any] = {}
    for level in VERTICAL_REFERENCES:
        for stratum in thick:
            key = f"{stratum}|{level}"
            sweep[key] = {
                str(threshold): direction_statistics(by_stratum[stratum], level, threshold)
                for threshold in sorted({DIRECTION_SPEED_THRESHOLD_MS, *DIRECTION_SWEEP_MS})
            }
            ratios[key] = estimator_relative_ratio(by_stratum[stratum], level)

    summary = {
        "n_runs": len({r["run_id"] for r in rows}),
        "n_windows": len(rows),
        "realised_by_stratum": {
            stratum: {
                "n_runs": runs_in[stratum],
                "n_vehicles": vehicles_in[stratum],
                "n_windows": len(by_stratum[stratum]),
                "frame_size": FRAME_SIZES.get(stratum),
                "design_weight": FRAME_SIZES[stratum] / runs_in[stratum]
                if stratum in FRAME_SIZES
                else None,
            }
            for stratum in sorted(by_stratum)
        },
        "validation_artifacts": len(artifacts),
        "suppressed_strata": suppressed,
        "direction_sweep": sweep,
        "estimator_relative_ratio": ratios,
        "useful_proxy": {a["validation_model_id"]: a["useful_proxy"] for a in artifacts},
        "note": "Neither source is ground truth; these are limits of agreement between "
        "measurement methods, and differences are era5 minus onboard. The 3.0 m s-1 "
        "usefulness band is asserted, not cited: adr/0015 and 06-limitations.md.",
    }

    args.artifacts.parent.mkdir(parents=True, exist_ok=True)
    args.artifacts.write_text(
        "".join(json.dumps(a) + "\n" for a in artifacts), encoding="utf-8", newline="\n"
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")

    add_output(manifest, args.out)
    add_output(manifest, args.artifacts)
    path = write_manifest(manifest)
    print(json.dumps(summary, indent=2))
    print(f"manifest: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
