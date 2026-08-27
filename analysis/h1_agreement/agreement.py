"""H1: agreement between ERA5 and the onboard EKF2 wind estimate, per regime.

**Neither source is ground truth** (``adr/0003``). Every quantity computed here is a
limit of agreement between two measurement methods. Neither source is regressed on the
other, and the onboard estimate is not treated as a reference. The difference is formed
in one declared direction, ``era5 - onboard``, and that direction is recorded in the
manifest: a positive bias indicates that ERA5 reads higher, not that the onboard estimate
is in error.

What is computed was fixed before this module could observe any result:

- ``adr/0006`` -- components are primary, ``u`` east and ``v`` north; the magnitude of
  the vector difference beside them; scalar speed secondary and labelled; direction
  wrapped to (-180, 180] and reported only where defined; 100 m primary, 10 m secondary.
- ``adr/0014`` -- stratum results are primary, a pooled number is a reweighted one
  reported beside the unweighted sample statistic, and the bootstrap resamples **runs**
  within stratum.
- ``adr/0015`` -- direction is undefined below 2.0 m s-1 and the cutoff is swept;
  ``useful_proxy`` is the upper limit of agreement on the vector difference magnitude at
  or below 3.0 m s-1, reported beside the estimator-relative ratio per component.

The regime axis used here is the retention stratum, which ``adr/0014`` makes mandatory.
The remaining axes declared a priori in ``docs/04-methodology.md`` -- airframe, airspeed
sensor, variance band, altitude, terrain, season -- are deferred to a separate pass. Cell
counts are not outcomes, so selecting among those axes after observing how many runs fall
into each is not a retrospective choice about a result; selecting a threshold or an
estimand in that manner would be.

    uv run python -m analysis.h1_agreement.agreement --pairs data/h1-pairs.jsonl
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime
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
# was made from. These are N_h.
FRAME_SIZES = {
    "fixed_wing_or_vtol|within_window": 6185,
    "fixed_wing_or_vtol|older": 10497,
}

# Runs drawn per stratum. The draw was 800/800 by design (adr/0014), and this is the
# denominator of the inclusion probability, so it is the denominator of the design weight
# -- see design_weights and adr/0016 correction 1.
N_DRAWN_PER_STRATUM = 800

# A regime thinner than this reports its stratum result alone and is not pooled into a
# reweighted number, per adr/0014. The value is borrowed from adr/0009's publication
# floor rather than derived: 20 runs is where that ADR stopped trusting a cell, and
# reweighting inside a cell smaller than that is unstable for the same reason. It is a
# manifest parameter so a reader can see it was a choice.
MIN_RUNS_PER_REGIME = 20

# The second half of the same threshold. docs/09-dpia.md 4.1 states one condition -- "no
# published cell draws on fewer than 20 runs from at least 10 distinct vehicle_uuids" --
# and twenty runs contributed by three vehicles represent three operators rather than
# twenty. A check on the run count alone is satisfied identically with and without the
# protection the threshold is intended to provide.
#
# The count is used and never published: adr/0009 prohibits emitting a vehicle_uuid at
# all, "raw or hashed", so only the cardinality leaves this module.
MIN_VEHICLES_PER_REGIME = 10

# Bands of the onboard estimator's own reported sigma, in m s-1. Round numbers chosen for
# interpretability **after** the distribution was seen, which adr/0016 records: they are
# manifest parameters and they define cells, not a decision threshold. No verdict moves
# with them; useful_proxy is still adr/0015's 3.0 m s-1 band.
SIGMA_BANDS = (0.5, 1.0)

VERTICAL_REFERENCES = {
    "era5_100m": ("era5_100m_u", "era5_100m_v"),
    "era5_10m": ("era5_10m_u", "era5_10m_v"),
}

SERIES_KEYS = ("u", "v", "vector_difference_magnitude", "speed")
# The keys a signed Bland-Altman analysis applies to. The vector difference magnitude is
# deliberately not among them: it is non-negative and right-skewed, so it is summarised by
# empirical quantiles instead (adr/0016 correction 2).
LOA_KEYS = ("u", "v", "speed")
MAGNITUDE_KEY = "vector_difference_magnitude"

# ``04-methodology.md`` makes this mandatory rather than optional: "if the result moves
# under plausible tolerance choices, that is the finding." 30 km is the declared spatial
# tolerance, so the sweep runs from well inside it up to it.
SENSITIVITY_DISTANCE_KM = (10.0, 15.0, 20.0, 30.0)


def airframe_class(mav_type: str) -> str:
    """Fixed-wing against VTOL, the split ``04-methodology.md`` declares as *airframe type*.

    The draw contains one plain fixed-wing label and five VTOL variants -- standard,
    tiltrotor, and three tailsitter spellings. They are grouped because the mechanism that
    matters for a wind estimate is whether the airframe flies on a wing in cruise, and
    because splitting five ways puts most cells under the publication floor.
    """
    return "fixed_wing" if mav_type.strip().lower() == "fixed wing" else "vtol"


def season_of(when: datetime, lat: float) -> str:
    """Meteorological season at the window, corrected for hemisphere.

    The corpus is global, so a northern-hemisphere season label would put a January flight
    in Australia in the same cell as one in Norway. Only the sign of the latitude is used
    and only a season name is emitted; no coordinate leaves this function.
    """
    northern = ("DJF", "MAM", "JJA", "SON")[((when.month % 12) // 3)]
    if lat >= 0:
        return northern
    return {"DJF": "JJA", "MAM": "SON", "JJA": "DJF", "SON": "MAM"}[northern]


def sigma_band(row: dict) -> str:
    """Which band the window's mean onboard sigma falls in."""
    sigma = math.sqrt((row["onboard_variance_u"] + row["onboard_variance_v"]) / 2.0)
    low, high = SIGMA_BANDS
    if sigma < low:
        return f"sigma_lt_{low}"
    if sigma < high:
        return f"sigma_{low}_to_{high}"
    return f"sigma_ge_{high}"


# The a priori axes from docs/04-methodology.md that the data on disk can cut. Firmware
# version is not carried by the sampling frame, and altitude AGL needs a DEM this project
# has not built -- both are named in the summary as declared-but-not-cut rather than
# quietly dropped.
REGIME_AXES: dict[str, Any] = {
    "airframe": lambda row: row["airframe_class"],
    # A topic is not a sensor. This is "the log carries an airspeed topic", which is a
    # proxy for airspeed sensing and is named as one wherever it is reported.
    "airspeed_topic": lambda row: "present" if row["has_airspeed_topic"] else "absent",
    "estimator_sigma": sigma_band,
    "season": lambda row: row["season"],
}


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
        raise ValueError("no windows: an agreement statistic over an empty regime is undefined")
    if weights is None:
        weights = np.ones_like(values)
    total = float(weights.sum())
    mean = float((weights * values).sum() / total)
    denominator = total - 1.0
    if denominator <= 0:
        return mean, 0.0
    return mean, math.sqrt(float((weights * (values - mean) ** 2).sum() / denominator))


def weighted_quantile(values: np.ndarray, q: float, weights: np.ndarray | None) -> float:
    """The ``q``-th weighted quantile, by linear interpolation on the weighted CDF.

    The plotting position is ``(i - 0.5) / n``, which is the usual choice for a weighted
    quantile. ``np.percentile`` defaults to ``(i - 1) / (n - 1)``. Both are legitimate
    estimators and they differ at small ``n`` -- by about 0.9 on eight points -- while
    converging as the sample grows; at the ~1,000 windows H1 reports over the difference
    is immaterial, and ``tests/test_agreement.py`` asserts the convergence rather than an
    exact match that does not hold.
    """
    order = np.argsort(values)
    v = np.asarray(values, dtype=float)[order]
    w = np.ones_like(v) if weights is None else np.asarray(weights, dtype=float)[order]
    cumulative = np.cumsum(w) - 0.5 * w
    cumulative /= w.sum()
    return float(np.interp(q, cumulative, v))


def magnitude_limits(values: np.ndarray, weights: np.ndarray | None = None) -> dict[str, Any]:
    """Empirical upper limits for a non-negative, right-skewed error magnitude.

    **Introduced on 2026-08-27, after H1 had been run** (``adr/0016`` correction 2). The
    vector difference magnitude is ``hypot(du, dv)`` and cannot be negative, so
    ``mean +/- 1.96 sd`` is not a limit of agreement on it: on the published run that
    construction returned a lower limit of -3.043 m s-1 for a quantity whose observed
    minimum was 0.034, and no window at all fell below it. The upper half was close to the
    empirical 97.5th percentile, but by coincidence of this sample rather than by
    construction.

    ``useful_proxy`` is evaluated against ``p97_5``, which is the same 95% coverage the
    upper limit of agreement was intended to express, read off the distribution instead of
    assumed from it. The declared 3.0 m s-1 band is unchanged.
    """
    array = np.asarray(values, dtype=float)
    if array.size == 0:
        raise ValueError("no windows: an agreement statistic over an empty regime is undefined")
    mean, dispersion = weighted_mean_and_sd(array, weights)
    return {
        "mean": mean,
        "dispersion": dispersion,
        "p50": weighted_quantile(array, 0.50, weights),
        "p90": weighted_quantile(array, 0.90, weights),
        "p95": weighted_quantile(array, 0.95, weights),
        "p97_5": weighted_quantile(array, 0.975, weights),
    }


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

    Computed once for the whole regime and indexed into by the bootstrap rather than
    recomputed per resample, since the resampling selects rows from a fixed set of
    differences and does not alter them.
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
    """Design weight ``N_h / n_drawn_h`` per window: the inverse inclusion probability.

    **Corrected on 2026-08-27, after H1 had been run** (``adr/0016`` correction 1). This
    previously divided by the *usable* count, which forces each stratum's total weight
    back to its full frame size ``N_h`` and therefore weights the pooled statistic by the
    composition of the pre-usability frame -- 62.9%/37.1%. ``adr/0014`` states the estimand
    is the usable subpopulation, so that was the wrong target.

    A usable run's inclusion probability is unaffected by how many other runs turned out
    usable: it is ``n_drawn_h / N_h``, so the weight is ``N_h / n_drawn_h``. Restricting to
    the usable domain is then done by simply not weighting up the runs that are not in it,
    and the implied usable population is ``N_h * n_usable_h / n_drawn_h`` -- 57.3%/42.7%
    over about 8,809 runs.

    Constant within a stratum, so it is also constant through the bootstrap, which draws
    ``n_h`` runs with replacement and reproduces the design's own sample size.
    """
    return np.array(
        [FRAME_SIZES[row["stratum"]] / N_DRAWN_PER_STRATUM for row in rows], dtype=float
    )


def implied_usable_population(rows: Sequence[dict]) -> dict[str, float]:
    """``N_h * n_usable_h / n_drawn_h`` per stratum: what the pooled estimate describes."""
    return {
        stratum: FRAME_SIZES[stratum]
        * len({r["run_id"] for r in rows if r["stratum"] == stratum})
        / N_DRAWN_PER_STRATUM
        for stratum in sorted({r["stratum"] for r in rows})
    }


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
    absolute = np.abs(array)
    # Circular mean and resultant length, not a linear mean and standard deviation.
    # **Changed on 2026-08-27, after H1 had been run** (adr/0016 correction 3): the wrapped
    # angles were being summarised with mean +/- 1.96 sd, which treats a circular quantity
    # as a real one. mean_absolute_deg is unaffected -- it is a mean of |angle| on [0, 180]
    # and was always a valid summary -- so it stays, and the limits are replaced by
    # quantiles of absolute angular error, which is what a reader of this table wants.
    radians = np.radians(array)
    resultant = float(np.hypot(np.sin(radians).mean(), np.cos(radians).mean()))
    return {
        "speed_threshold_ms": threshold,
        "n_defined": len(defined),
        "n_undefined": undefined,
        "mean_absolute_deg": float(absolute.mean()),
        "median_absolute_deg": float(np.median(absolute)),
        "p90_absolute_deg": float(np.percentile(absolute, 90)),
        "p95_absolute_deg": float(np.percentile(absolute, 95)),
        "circular_mean_deg": float(
            np.degrees(np.arctan2(np.sin(radians).mean(), np.cos(radians).mean()))
        ),
        "circular_resultant_length": resultant,
        # 1 - R is the circular variance; sqrt(-2 ln R) is the circular standard deviation
        # in radians, which is the dispersion measure a circular statistic actually has.
        "circular_sd_deg": float(np.degrees(math.sqrt(-2.0 * math.log(resultant))))
        if resultant > 0
        else None,
    }


def estimator_relative_ratio(rows: Sequence[dict], level: str) -> dict[str, Any]:
    """Limit-of-agreement half-width over the estimator's own sigma, per component.

    The second view defined by ``adr/0015``. The onboard variance is EKF2's
    self-assessment rather than an independent measurement, so this quantity is reported
    alongside the verdict and never as the verdict: a regime in which the filter reports
    high uncertainty satisfies it readily.

    Reported per component because ``adr/0006`` makes components primary, and because the
    variance is anisotropic in practice -- the estimator constrains wind more tightly along
    the direction in which its airspeed vector has varied than across it.
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


def one_window_per_run(rows: Sequence[dict], seed: int = BOOTSTRAP_SEED) -> list[dict]:
    """One window drawn at random per run, removing within-run clustering entirely.

    Added on 2026-08-27 after H1 had been run (``adr/0016``). The bootstrap already
    resamples runs, so the *interval* accounts for clustering, but the point estimates are
    computed over all windows as though they were one difference distribution. Clustering
    here is shallow -- 1,059 windows over 871 runs, about 1.22 per run -- so the effect is
    expected to be small, which is exactly why reporting it is cheap and settles the
    question rather than arguing about it.
    """
    rng = np.random.default_rng(seed)
    by_run: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_run[row["run_id"]].append(row)
    return [run_rows[int(rng.integers(0, len(run_rows)))] for run_rows in by_run.values()]


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
        key: {"bias": [], "loa_lower": [], "loa_upper": []} for key in LOA_KEYS
    }
    magnitude: dict[str, list[float]] = {"mean": [], "p95": [], "p97_5": []}

    for _ in range(resamples):
        parts = []
        for runs in runs_by_stratum.values():
            picked = rng.integers(0, len(runs), size=len(runs))
            parts.extend(runs[index] for index in picked)
        index = np.concatenate(parts)
        resampled_weights = None if weights is None else weights[index]
        for key in LOA_KEYS:
            statistic = bland_altman(series[key][index], resampled_weights)
            draws[key]["bias"].append(statistic["bias"])
            draws[key]["loa_lower"].append(statistic["limits_of_agreement"][0])
            draws[key]["loa_upper"].append(statistic["limits_of_agreement"][1])
        limits = magnitude_limits(series[MAGNITUDE_KEY][index], resampled_weights)
        for name in magnitude:
            magnitude[name].append(limits[name])

    out: dict[str, dict[str, Any]] = {
        key: {
            "bias_ci": _percentiles(draws[key]["bias"]),
            "limits_ci": [
                _percentiles(draws[key]["loa_lower"]),
                _percentiles(draws[key]["loa_upper"]),
            ],
        }
        for key in LOA_KEYS
    }
    out[MAGNITUDE_KEY] = {f"{name}_ci": _percentiles(values) for name, values in magnitude.items()}
    return out


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
    for key in LOA_KEYS:
        statistics[key] = bland_altman(series[key], weights)
    statistics[MAGNITUDE_KEY] = magnitude_limits(series[MAGNITUDE_KEY], weights)
    statistics["direction"] = direction_statistics(rows, level, direction_threshold)

    for key, interval in bootstrap(
        rows, level, weights=weights, resamples=resamples, seed=seed
    ).items():
        statistics[key].update(interval)

    # adr/0015: the verdict is the absolute band, and adr/0016 correction 2 applies it to
    # the empirical 97.5th percentile rather than to mean + 1.96 sd. Same declared band,
    # same intended 95% coverage, read off the distribution instead of assumed from it.
    # The estimator-relative ratio is reported alongside in the summary and deliberately
    # not folded into this boolean.
    upper_limit = statistics[MAGNITUDE_KEY]["p97_5"]

    return {
        "validation_model_id": f"h1-{label}-{level}-{'reweighted' if weighted else 'sample'}",
        "regime": {"label": label, "criteria": criteria},
        "sources_compared": ["era5_wind", "px4_ekf2_wind"],
        "vertical_reference": level,
        "n_runs": len({row["run_id"] for row in rows}),
        "n_windows": len(rows),
        "statistics": statistics,
        "bootstrap": {"unit": "run", "n_resamples": resamples, "seed": seed},
        "useful_proxy": bool(upper_limit <= USEFUL_PROXY_LOA_MS),
        "manifest_id": manifest_id,
    }


def tolerance_sensitivity(
    by_stratum: dict[str, list[dict]],
    *,
    level: str,
    min_runs: int,
    min_vehicles: int,
    caps: Sequence[float] = SENSITIVITY_DISTANCE_KM,
) -> dict[str, Any]:
    """Does the verdict survive a tighter join tolerance?

    ``04-methodology.md`` requires this analysis and states its purpose: a result that
    moves when the distance-to-grid-point cap moves is a result about the cap. The
    ``useful_proxy`` verdict is therefore recomputed at each cap, since a verdict that
    changes between 10 km and 30 km is itself the finding.

    The k-threshold is re-applied at every cap. A tighter cap removes windows, and removing
    windows removes runs and vehicles with them, so a subset that is publishable at 30 km
    may fall below the floor at 10 km. A threshold evaluated only on the full set would not
    detect this.

    No bootstrap is performed here. The question is whether the point estimate and the
    verdict move under the cap, which the point estimate alone answers.
    """
    out: dict[str, Any] = {}
    for cap in caps:
        subset = {
            stratum: [
                row
                for row in rows
                if row.get("distance_to_grid_point_km") is not None
                and row["distance_to_grid_point_km"] <= cap
            ]
            for stratum, rows in by_stratum.items()
        }
        subset = {stratum: rows for stratum, rows in subset.items() if rows}
        thick, suppressed = publishable_regimes(
            subset, min_runs=min_runs, min_vehicles=min_vehicles
        )
        regimes: dict[str, Any] = {}
        for stratum in thick:
            rows = subset[stratum]
            series = series_arrays(rows, level)
            magnitude = magnitude_limits(series[MAGNITUDE_KEY])
            upper = magnitude["p97_5"]
            regimes[stratum] = {
                "n_runs": len({r["run_id"] for r in rows}),
                "n_vehicles": len({r["vehicle_uuid"] for r in rows}),
                "n_windows": len(rows),
                "bias_u": bland_altman(series["u"])["bias"],
                "bias_v": bland_altman(series["v"])["bias"],
                "vector_difference_p97_5": upper,
                "useful_proxy": bool(upper <= USEFUL_PROXY_LOA_MS),
            }
        out[str(cap)] = {"regimes": regimes, "suppressed": suppressed}
    return out


def temporal_mismatch_report(rows: Sequence[dict]) -> dict[str, Any]:
    """What the temporal half of the mandated sensitivity analysis can actually say.

    The mismatch cannot be swept, and reporting that is the accurate result. A window is
    the ERA5 hour beginning at its stamp, the field is instantaneous at that stamp, and
    ``align`` measures the mismatch against the window's *centre*, so every window in the
    corpus is offset by exactly -1800 s by construction. Varying a tolerance across a
    constant would produce a table of identical rows.

    The mismatch is instead a systematic effect: the reanalysis value is located at the
    start of the interval over which the onboard estimate is averaged rather than at its
    midpoint, so any within-hour trend in the wind enters the comparison as bias rather
    than as dispersion. That belongs in the limitations. This function derives the
    constancy from the rows rather than asserting it, so that a value other than -1800
    contradicts the claim rather than being absorbed into it.
    """
    observed = sorted({row["temporal_mismatch_s"] for row in rows})
    return {
        "distinct_values_s": observed,
        "is_constant_by_construction": len(observed) == 1,
        "note": "A window is the hour beginning at its stamp and the field is "
        "instantaneous there, so the mismatch against the window centre is -1800 s for "
        "every window. It is a property of the design, not of the data, and cannot be "
        "swept. The reanalysis value therefore sits at the start of the averaging "
        "interval rather than its centre; see docs/06-limitations.md.",
    }


def with_complete_era5(rows: Sequence[dict]) -> tuple[list[dict], dict[str, int]]:
    """Split off rows missing an ERA5 component, and count them rather than crash on them.

    On the ARCO route all four components come back for every read, so this is expected to
    partition nothing. It exists for the CDS route, which ``adr/0013`` keeps as the
    authoritative one and which omits a variable its response did not carry.

    Without this partition the failure is silent rather than immediate.
    ``np.array([1.0, None], dtype=float)`` does not raise; it yields ``nan``. A single
    incomplete window therefore renders an entire regime's bias, limits and bootstrap
    ``nan``, and since ``nan <= 3.0`` evaluates to ``False``, that regime would be
    published as *not a useful proxy* on the basis of one missing value. This behaviour
    was verified rather than assumed, after an earlier version of this docstring stated
    that numpy would raise.

    Incomplete windows are counted and reported rather than silently discarded: field
    coverage is recorded in this project, and a run disappearing between the pairs file and
    the result is the failure this rule exists to prevent.
    """
    keys = [key for pair in VERTICAL_REFERENCES.values() for key in pair]
    complete, missing = [], 0
    for row in rows:
        values = [row.get(key) for key in keys]
        if any(value is None or value != value for value in values):
            missing += 1
            continue
        complete.append(row)
    return complete, {"windows_without_complete_era5": missing}


def publishable_regimes(
    by_stratum: dict[str, list[dict]], *, min_runs: int, min_vehicles: int
) -> tuple[list[str], dict[str, dict[str, int]]]:
    """Which strata may be reported, and the counts of those that may not.

    ``docs/09-dpia.md`` 4.1 states a single threshold with two components -- "no published
    cell draws on fewer than 20 runs from at least 10 distinct vehicle_uuids" -- so a cell
    must satisfy both. Twenty runs contributed by three airframes represent three
    operators, which a check on the run count alone does not detect.

    Suppressed cells are returned with their counts, since a suppression that conceals its
    own occurrence introduces its own distortion (``adr/0009``). The counts are integers;
    no identifier leaves this function.
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


def load_pairs(
    pairs: Path, sample: Path, inventory: Path, excluded: exclusions.Exclusions
) -> list[dict]:
    """Read the paired rows, attach each run's stratum, and drop excluded runs.

    This exclusion pass is not redundant with the one applied at retrieval. An objection
    arriving after a log is already on disk must also be removed from the results, which is
    what ``PRIVACY.md`` undertakes: "later runs do not re-include it". ``exclusions.load``
    raises when the list is absent, so a missing list halts H1 rather than being interpreted
    as an absence of objections.
    """
    strata: dict[str, str] = {}
    vehicles: dict[str, str] = {}
    airframes: dict[str, str] = {}
    for line in sample.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entry = json.loads(line)
            strata[entry["log_id"]] = entry["stratum"]
            vehicles[entry["log_id"]] = entry.get("vehicle_uuid") or ""
            airframes[entry["log_id"]] = airframe_class(entry.get("mav_type") or "")

    airspeed: dict[str, bool] = {}
    for line in inventory.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entry = json.loads(line)
            topic = entry.get("topics", {}).get("airspeed") or {}
            airspeed[entry["log_id"]] = bool(topic.get("present"))

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
        row["airframe_class"] = airframes[run_id]
        row["has_airspeed_topic"] = airspeed.get(run_id, False)
        row["season"] = season_of(datetime.fromisoformat(row["window_start"]), row["lat"])
        rows.append(row)
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pairs", type=Path, default=Path("data/h1-pairs.jsonl"))
    parser.add_argument("--sample", type=Path, default=Path("data/h1-sample.jsonl"))
    parser.add_argument("--inventory", type=Path, default=Path("data/h1-inventory.jsonl"))
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
    rows, coverage = with_complete_era5(
        load_pairs(args.pairs, args.sample, args.inventory, excluded)
    )
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
            "sensitivity_distance_km": list(SENSITIVITY_DISTANCE_KM),
            "sigma_bands_ms": list(SIGMA_BANDS),
            "regime_axes": sorted(REGIME_AXES),
            "regime_axes_declared_but_not_cut": ["firmware_version", "altitude_agl", "topography"],
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

    # The predeclared operational-regime axes (adr/0016 correction 6). A regime cell spans
    # both retention strata, so unlike a stratum result it does need the weighting
    # argument, and both pooled forms are emitted for each cell. Cells below the
    # publication floor are suppressed with their counts, per adr/0009.
    regimes: dict[str, Any] = {}
    for axis, classify in sorted(REGIME_AXES.items()):
        cells: dict[str, list[dict]] = defaultdict(list)
        for row in rows:
            cells[classify(row)].append(row)
        thick_cells, cell_suppressed = publishable_regimes(
            cells, min_runs=args.min_runs, min_vehicles=args.min_vehicles
        )
        regimes[axis] = {
            "cells": {
                cell: {
                    "n_runs": len({r["run_id"] for r in cells[cell]}),
                    "n_vehicles": len({r["vehicle_uuid"] for r in cells[cell]}),
                    "n_windows": len(cells[cell]),
                }
                for cell in thick_cells
            },
            "suppressed": cell_suppressed,
        }
        for level in VERTICAL_REFERENCES:
            for cell in thick_cells:
                for weighted in (False, True):
                    artifacts.append(
                        regime_artifact(
                            cells[cell],
                            label=f"{axis}={cell}",
                            criteria={
                                "axis": axis,
                                "cell": cell,
                                "airframe": "fixed_wing_or_vtol",
                                "pooling": "reweighted" if weighted else "unweighted_sample",
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

    # The sweep and the estimator-relative ratio are recorded in the summary rather than in
    # the ValidationArtifact: the schema fixes one threshold and one boolean per artifact,
    # and widening it to carry adr/0015's second view would be a schema change made to
    # accommodate a result. Both are reported, and reported together, as the ADR requires.
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

    # adr/0016: the bootstrap already resamples runs, so the interval accounts for
    # clustering; this checks whether the point estimates depend on runs that contributed
    # more windows than others. Clustering is shallow here, so a large shift would be a
    # surprise -- which is the point of measuring rather than asserting it.
    single = one_window_per_run(rows, seed=args.seed)
    one_window_summary = {
        "n_runs": len({r["run_id"] for r in single}),
        "n_windows": len(single),
    }
    for level in VERTICAL_REFERENCES:
        full = series_arrays(rows, level)
        drawn = series_arrays(single, level)
        one_window_summary[level] = {
            "bias_u_all_windows": bland_altman(full["u"])["bias"],
            "bias_u_one_per_run": bland_altman(drawn["u"])["bias"],
            "bias_v_all_windows": bland_altman(full["v"])["bias"],
            "bias_v_one_per_run": bland_altman(drawn["v"])["bias"],
            "p97_5_all_windows": magnitude_limits(full[MAGNITUDE_KEY])["p97_5"],
            "p97_5_one_per_run": magnitude_limits(drawn[MAGNITUDE_KEY])["p97_5"],
        }

    implied = implied_usable_population(rows)
    summary = {
        "n_runs": len({r["run_id"] for r in rows}),
        "n_windows": len(rows),
        "realised_by_stratum": {
            stratum: {
                "n_runs": runs_in[stratum],
                "n_vehicles": vehicles_in[stratum],
                "n_windows": len(by_stratum[stratum]),
                "frame_size": FRAME_SIZES.get(stratum),
                "n_drawn": N_DRAWN_PER_STRATUM,
                # N_h / n_drawn_h, matching design_weights. This previously reported
                # N_h / n_usable_h and would have contradicted the weight actually applied
                # (adr/0016 correction 1).
                "design_weight": FRAME_SIZES[stratum] / N_DRAWN_PER_STRATUM
                if stratum in FRAME_SIZES
                else None,
                "implied_usable_population": implied[stratum],
            }
            for stratum in sorted(by_stratum)
        },
        "validation_artifacts": len(artifacts),
        "suppressed_strata": suppressed,
        "implied_usable_population": implied,
        "regimes": regimes,
        "regime_axes_declared_but_not_cut": {
            "firmware_version": "not carried by the sampling frame",
            "altitude_agl": "needs a DEM this project has not built; height above takeoff "
            "is the available proxy and requires a pass over the converted runs",
            "topography": "same DEM dependency",
        },
        "one_window_per_run": one_window_summary,
        **coverage,
        "tolerance_sensitivity": {
            level: tolerance_sensitivity(
                {s: by_stratum[s] for s in thick},
                level=level,
                min_runs=args.min_runs,
                min_vehicles=args.min_vehicles,
            )
            for level in VERTICAL_REFERENCES
        },
        "temporal_mismatch": temporal_mismatch_report(rows),
        "direction_sweep": sweep,
        "estimator_relative_ratio": ratios,
        "useful_proxy": {a["validation_model_id"]: a["useful_proxy"] for a in artifacts},
        "note": "Neither source is ground truth. These are limits of agreement between "
        "two measurement methods; differences are formed as era5 minus onboard. The "
        "3.0 m s-1 usefulness band is asserted rather than cited: see adr/0015 and "
        "docs/06-limitations.md.",
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
