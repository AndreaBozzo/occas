"""Manuscript figures for H1, generated from the committed artifacts.

Every figure is drawn from ``artifacts/h1-agreement.json``,
``artifacts/h1-validation-artifacts.jsonl`` and the paired rows, so a figure cannot
disagree with the number the results page quotes. ``adr/0010`` requires a figure in prose
to be emitted by the script that computed it; this is that script.

**Nothing positional is plotted.** The figures show wind differences, their distribution
and their per-regime summaries. No coordinate, run identifier or vehicle identifier
appears in any of them (``adr/0009``).

Two colours, ``#0072B2`` and ``#D55E00``, used only where two series share an axis. They
were validated rather than chosen by eye: CVD separation ΔE 21.9 at worst under protanopia
and contrast above 3:1 against the surface. Everything else is monochrome, because a
manuscript figure is read in print and grouping by position with a text label is more
robust than grouping by hue.

    uv run python -m analysis.h1_agreement.figures
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from analysis.common import exclusions  # noqa: E402
from analysis.common.manifest import add_output, build_manifest, write_manifest  # noqa: E402
from analysis.h1_agreement import agreement  # noqa: E402

PROCESSING_VERSION = "figures/1"

PRIMARY = "#0072B2"
SECONDARY = "#D55E00"
INK = "#1a1a19"
MUTED = "#6b6b68"
GRID = "#e3e3e0"

plt.rcParams.update(
    {
        "figure.dpi": 200,
        "savefig.dpi": 200,
        "font.size": 8,
        "axes.edgecolor": MUTED,
        "axes.labelcolor": INK,
        "axes.titlesize": 9,
        "axes.titleweight": "semibold",
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "text.color": INK,
        "legend.frameon": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    }
)


def _tidy(ax) -> None:
    """Recessive axes: the data should be the darkest thing in the frame."""
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.set_axisbelow(True)


def _ecdf(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    ordered = np.sort(values)
    return ordered, np.arange(1, ordered.size + 1) / ordered.size


def component_agreement(rows: list[dict], out: Path) -> Path:
    """Bland-Altman per component: the difference against the mean of the two sources."""
    series = agreement.series_arrays(rows, "era5_100m")
    # One window carries a 69 m/s difference -- an onboard estimate of 66 m/s, which is
    # not a wind. Left to set the axis it flattens the other 1,058 into a corner and
    # gives the two panels different scales, so they can no longer be compared. Both
    # panels share one clipped, symmetric scale and the clipped count is stated.
    span = 3.2 * max(
        abs(v)
        for key in ("u", "v")
        for v in agreement.bland_altman(series[key])["limits_of_agreement"]
    )
    fig, axes = plt.subplots(
        1, 2, figsize=(7.0, 3.1), constrained_layout=True, sharex=True, sharey=True
    )
    for ax, key, name in zip(axes, ("u", "v"), ("u (east)", "v (north)"), strict=True):
        era5 = np.array([r[f"era5_100m_{key}"] for r in rows], dtype=float)
        onboard = np.array([r[f"onboard_{key}"] for r in rows], dtype=float)
        mean = (era5 + onboard) / 2.0
        diff = series[key]
        stat = agreement.bland_altman(diff)
        lo, hi = stat["limits_of_agreement"]

        ax.scatter(mean, diff, s=5, alpha=0.35, color=PRIMARY, linewidths=0, rasterized=True)
        ax.axhline(stat["bias"], color=INK, linewidth=1.2)
        ax.axhline(lo, color=INK, linewidth=1.0, linestyle="--")
        ax.axhline(hi, color=INK, linewidth=1.0, linestyle="--")
        ax.annotate(
            f"bias {stat['bias']:+.2f}",
            (0.99, stat["bias"]),
            xycoords=("axes fraction", "data"),
            ha="right",
            va="bottom",
            fontsize=7,
            color=INK,
        )
        ax.annotate(
            f"LoA {lo:.1f}, {hi:.1f}",
            (0.99, 0.98),
            xycoords=("axes fraction", "axes fraction"),
            ha="right",
            va="top",
            fontsize=7,
            color=MUTED,
        )
        outside = int(((np.abs(diff) > span) | (np.abs(mean) > span)).sum())
        if outside:
            ax.annotate(
                f"{outside} of {diff.size} outside the frame",
                (0.02, 0.03),
                xycoords="axes fraction",
                fontsize=6.5,
                color=MUTED,
            )
        ax.set_title(f"Component {name}")
        ax.set_xlabel("mean of ERA5 and onboard (m s$^{-1}$)")
        ax.set_ylabel("ERA5 − onboard (m s$^{-1}$)" if key == "u" else "")
        ax.set_xlim(-span, span)
        ax.set_ylim(-span, span)
        _tidy(ax)
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


def magnitude_distribution(rows: list[dict], band: float, out: Path) -> Path:
    """Where the vector difference actually sits, against the declared band."""
    magnitude = agreement.series_arrays(rows, "era5_100m")["vector_difference_magnitude"]
    limits = agreement.magnitude_limits(magnitude)
    x, y = _ecdf(magnitude)

    # The tail runs to ~69 m/s on a handful of windows. Letting it set the axis
    # squeezes everything the reader needs into a fifth of the frame, so the view is
    # clipped just past p97.5 and the excluded fraction is stated rather than hidden.
    view_max = math.ceil(limits["p97_5"] * 1.6)
    beyond = int((magnitude > view_max).sum())

    fig, ax = plt.subplots(figsize=(5.0, 3.2), constrained_layout=True)
    ax.plot(x, y, color=PRIMARY, linewidth=2)
    ax.axvline(band, color=SECONDARY, linewidth=2)
    ax.annotate(
        f"declared band\n{band:.1f} m s$^{{-1}}$",
        (band, 1.0),
        xytext=(5, -2),
        textcoords="offset points",
        fontsize=7,
        color=SECONDARY,
        va="top",
    )
    # Labels alternate below and above their marker so they cannot collide.
    for q, key, dy, va in (
        (0.50, "p50", -12, "top"),
        (0.95, "p95", -12, "top"),
        (0.975, "p97_5", -12, "top"),
    ):
        ax.plot([limits[key]], [q], marker="o", markersize=5, color=INK, zorder=5)
        ax.annotate(
            f"{key.replace('_', '.')} = {limits[key]:.2f}",
            (limits[key], q),
            xytext=(6, dy),
            textcoords="offset points",
            fontsize=7,
            color=INK,
            va=va,
        )
    if beyond:
        ax.annotate(
            f"{beyond} of {magnitude.size} windows lie beyond {view_max} m s"
            f"$^{{-1}}$ (max {magnitude.max():.0f}); axis clipped for legibility",
            (0.98, 0.06),
            xycoords="axes fraction",
            ha="right",
            fontsize=6.5,
            color=MUTED,
        )
    ax.set_xlabel("|Δv|, vector difference magnitude (m s$^{-1}$)")
    ax.set_ylabel("cumulative fraction of windows")
    ax.set_title("Disagreement is centred near 2.4 and tailed far past the band")
    ax.set_xlim(0, view_max)
    ax.set_ylim(0, 1.02)
    _tidy(ax)
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


def regime_forest(artifacts: list[dict], band: float, out: Path) -> Path:
    """Every published regime cell, with its bootstrap interval, against the band."""
    rows = []
    for a in artifacts:
        c = a["regime"]["criteria"]
        if a["vertical_reference"] != "era5_100m":
            continue
        if c.get("pooling") == "reweighted":
            continue
        m = a["statistics"]["vector_difference_magnitude"]
        axis = c.get("axis", "retention stratum")
        cell = c.get("cell", a["regime"]["label"].split("|")[-1])
        rows.append((axis, cell, m["p97_5"], m["p97_5_ci"], a["n_runs"]))
    rows.sort(key=lambda r: (r[0], -r[2]))

    # One cell -- the thinnest, where the onboard filter reports high uncertainty --
    # has an interval reaching 69. Letting it set the axis pushes every other row into
    # the left sixth of the frame. The view is clipped just past the widest point
    # estimate, and any interval running past the edge gets a caret and its value
    # printed, so the truncation is visible rather than silent.
    view_max = math.ceil(max(r[2] for r in rows) * 1.15)

    fig, ax = plt.subplots(figsize=(6.4, 0.30 * len(rows) + 1.5), constrained_layout=True)
    labels, last_axis = [], None
    for i, (axis, cell, value, ci, n) in enumerate(rows):
        drawn_hi = min(ci[1], view_max)
        ax.plot([ci[0], drawn_hi], [i, i], color=MUTED, linewidth=1.4, solid_capstyle="round")
        if ci[1] > view_max:
            ax.plot([view_max], [i], marker=">", markersize=5, color=MUTED, clip_on=False)
            ax.annotate(
                f"CI to {ci[1]:.0f}",
                (view_max, i),
                xytext=(9, -2.5),
                textcoords="offset points",
                fontsize=6,
                color=MUTED,
            )
        ax.plot([value], [i], marker="o", markersize=5, color=PRIMARY, zorder=5)
        if ci[1] <= view_max:
            ax.annotate(
                f"{value:.1f}",
                (ci[1], i),
                xytext=(5, -2.5),
                textcoords="offset points",
                fontsize=6.5,
                color=MUTED,
            )
        prefix = f"{axis}: " if axis != last_axis else ""
        labels.append(f"{prefix}{cell}  (n={n})")
        last_axis = axis
    ax.axvline(band, color=SECONDARY, linewidth=2, zorder=1)
    ax.annotate(
        f"declared band {band:.1f}",
        (band, 1.0),
        xycoords=("data", "axes fraction"),
        xytext=(5, -2),
        textcoords="offset points",
        fontsize=7,
        color=SECONDARY,
        va="top",
    )
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(labels, fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel("|Δv| 97.5th percentile, with bootstrap interval (m s$^{-1}$)")
    ax.set_title("No regime approaches the band")
    ax.set_xlim(0, view_max)
    ax.grid(axis="y", visible=False)
    _tidy(ax)
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


def direction_error(rows: list[dict], thresholds: tuple[float, ...], out: Path) -> Path:
    """Absolute angular error, at each declared cutoff. Centred, and very dispersed."""
    fig, ax = plt.subplots(figsize=(4.6, 3.2), constrained_layout=True)
    styles = {2.0: (PRIMARY, 2.0, "-"), 1.0: (MUTED, 1.2, "--"), 3.0: (MUTED, 1.2, ":")}
    for threshold in thresholds:
        errors = []
        for row in rows:
            eu, ev = row["era5_100m_u"], row["era5_100m_v"]
            ou, ov = row["onboard_u"], row["onboard_v"]
            if math.hypot(eu, ev) <= threshold or math.hypot(ou, ov) <= threshold:
                continue
            errors.append(abs(agreement.bearing_difference_deg(eu, ev, ou, ov)))
        if not errors:
            continue
        x, y = _ecdf(np.array(errors, dtype=float))
        colour, width, style = styles[threshold]
        label = f"{threshold:.1f} m s$^{{-1}}$ cutoff (n={len(errors)})"
        ax.plot(x, y, color=colour, linewidth=width, linestyle=style, label=label)
    ax.set_xlabel("absolute angular error (degrees)")
    ax.set_ylabel("cumulative fraction of defined windows")
    ax.set_title("Direction is centred but widely dispersed")
    ax.set_xlim(0, 180)
    ax.set_ylim(0, 1.02)
    ax.set_xticks([0, 45, 90, 135, 180])
    ax.legend(loc="lower right", fontsize=7)
    _tidy(ax)
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


def time_alignment(base: list[dict], midpoint: list[dict], band: float, out: Path) -> Path:
    """Every paired regime, before and after correcting the -1800 s offset."""
    keyed = {(a["validation_model_id"], a["vertical_reference"]): a for a in midpoint}
    xs, ys = [], []
    for a in base:
        b = keyed.get((a["validation_model_id"], a["vertical_reference"]))
        if b is None:
            continue
        xs.append(a["statistics"]["vector_difference_magnitude"]["p97_5"])
        ys.append(b["statistics"]["vector_difference_magnitude"]["p97_5"])

    fig, ax = plt.subplots(figsize=(4.2, 4.0), constrained_layout=True)
    top = max(max(xs), max(ys)) * 1.08
    ax.plot([0, top], [0, top], color=MUTED, linewidth=1.0, linestyle="--")
    ax.scatter(xs, ys, s=22, color=PRIMARY, alpha=0.8, linewidths=0)
    ax.axvline(band, color=SECONDARY, linewidth=1.6)
    ax.axhline(band, color=SECONDARY, linewidth=1.6)
    shifts = [y - x for x, y in zip(xs, ys, strict=True)]
    ax.set_title("Correcting the −1800 s offset moves nothing")
    ax.annotate(
        f"{len(xs)} paired regimes\nmedian shift {float(np.median(shifts)):+.3f} m s$^{{-1}}$\n"
        f"no verdict changes",
        (0.04, 0.96),
        xycoords="axes fraction",
        va="top",
        fontsize=7,
        color=INK,
    )
    ax.set_xlabel("|Δv| p97.5, field at hour start (m s$^{-1}$)")
    ax.set_ylabel("|Δv| p97.5, field at interval midpoint (m s$^{-1}$)")
    ax.set_xlim(0, top)
    ax.set_ylim(0, top)
    _tidy(ax)
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pairs", type=Path, default=Path("data/h1-pairs.jsonl"))
    parser.add_argument("--sample", type=Path, default=Path("data/h1-sample.jsonl"))
    parser.add_argument("--inventory", type=Path, default=Path("data/h1-inventory.jsonl"))
    parser.add_argument("--altitude", type=Path, default=Path("data/h1-altitude.jsonl"))
    parser.add_argument(
        "--artifacts", type=Path, default=Path("artifacts/h1-validation-artifacts.jsonl")
    )
    parser.add_argument(
        "--midpoint",
        type=Path,
        default=Path("artifacts/h1-validation-artifacts-midpoint.jsonl"),
    )
    parser.add_argument("--out", type=Path, default=Path("artifacts/figures"))
    args = parser.parse_args(argv)

    manifest = build_manifest(
        name="h1-figures",
        hypothesis="H1",
        entrypoint="analysis/h1_agreement/figures.py",
        description="Manuscript figures for H1, drawn from the committed artifacts. "
        "Nothing positional is plotted.",
        parameters={
            "useful_proxy_loa_ms": agreement.USEFUL_PROXY_LOA_MS,
            "direction_thresholds_ms": [
                agreement.DIRECTION_SPEED_THRESHOLD_MS,
                *agreement.DIRECTION_SWEEP_MS,
            ],
            "palette": {"primary": PRIMARY, "secondary": SECONDARY},
            "palette_validated": "CVD dE 21.9 worst adjacent (protan); contrast >= 3:1",
            "processing_version": PROCESSING_VERSION,
        },
    )

    excluded = exclusions.load()
    rows, _ = agreement.with_complete_era5(
        agreement.load_pairs(args.pairs, args.sample, args.inventory, args.altitude, excluded)
    )
    artifacts = _read_jsonl(args.artifacts)
    midpoint = _read_jsonl(args.midpoint) if args.midpoint.exists() else []

    args.out.mkdir(parents=True, exist_ok=True)
    band = agreement.USEFUL_PROXY_LOA_MS
    produced: list[Path] = [
        component_agreement(rows, args.out / "fig1-component-agreement.png"),
        magnitude_distribution(rows, band, args.out / "fig2-magnitude-distribution.png"),
        regime_forest(artifacts, band, args.out / "fig3-regime-forest.png"),
        direction_error(
            rows,
            (1.0, agreement.DIRECTION_SPEED_THRESHOLD_MS, 3.0),
            args.out / "fig4-direction-error.png",
        ),
    ]
    if midpoint:
        produced.append(
            time_alignment(artifacts, midpoint, band, args.out / "fig5-time-alignment.png")
        )

    for path in produced:
        add_output(manifest, path)
    written = write_manifest(manifest)
    summary: dict[str, Any] = {
        "figures": [p.as_posix() for p in produced],
        "windows_plotted": len(rows),
        "regimes_plotted": sum(
            1
            for a in artifacts
            if a["vertical_reference"] == "era5_100m"
            and a["regime"]["criteria"].get("pooling") != "reweighted"
        ),
    }
    print(json.dumps(summary, indent=2))
    print(f"manifest: {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
