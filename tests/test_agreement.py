"""H1's statistics, on fixtures whose answers can be worked out by hand.

Every test here guards a way the agreement analysis could produce a number that looks
publishable and is not: a difference formed in the wrong direction, so every sentence
about who reads higher is inverted; a directional error computed across the wrap point;
low-wind windows dropped instead of counted; a bootstrap that treats consecutive hours of
one flight as independent evidence and reports an interval the design never earned; a
pooled number that describes the draw rather than the frame.

The fixtures describe no real flight. Wind values are small integers chosen so the
arithmetic is checkable without running the code.
"""

from __future__ import annotations

import math

import pytest

from analysis.h1_agreement import agreement

WITHIN = "fixed_wing_or_vtol|within_window"
OLDER = "fixed_wing_or_vtol|older"


def _row(
    *,
    run_id: str,
    stratum: str = WITHIN,
    onboard=(0.0, 0.0),
    era5=(0.0, 0.0),
    variance=(0.25, 0.25),
) -> dict:
    """One paired window. ``era5`` and ``onboard`` are ``(u, v)``, east then north."""
    return {
        "run_id": run_id,
        "stratum": stratum,
        "onboard_u": onboard[0],
        "onboard_v": onboard[1],
        "onboard_variance_u": variance[0],
        "onboard_variance_v": variance[1],
        "era5_100m_u": era5[0],
        "era5_100m_v": era5[1],
        "era5_10m_u": era5[0],
        "era5_10m_v": era5[1],
    }


def test_the_difference_is_era5_minus_onboard_not_the_reverse() -> None:
    """A sign flip here inverts every sentence H1 will ever write.

    "ERA5 reads 1.5 m/s higher than the onboard estimate" and its opposite are the same
    number with the same magnitude, and only the manifest's declared direction says which
    one was computed. So the direction is asserted against a fixture where the two sources
    are unambiguously ordered, not inferred from the code.
    """
    rows = [_row(run_id="a", onboard=(2.0, 0.0), era5=(5.0, 0.0))]
    series = agreement.series_arrays(rows, "era5_100m")
    assert series["u"][0] == pytest.approx(3.0)
    assert agreement.bland_altman(series["u"])["bias"] == pytest.approx(3.0)


def test_limits_of_agreement_are_the_bias_either_side_of_the_spread() -> None:
    """Bias and 1.96 standard deviations, on four differences that average to 2."""
    rows = [
        _row(run_id="a", era5=(1.0, 0.0)),
        _row(run_id="b", era5=(1.0, 0.0)),
        _row(run_id="c", era5=(3.0, 0.0)),
        _row(run_id="d", era5=(3.0, 0.0)),
    ]
    statistic = agreement.bland_altman(agreement.series_arrays(rows, "era5_100m")["u"])
    # Sample sd of (1, 1, 3, 3) about a mean of 2 is sqrt(4/3).
    dispersion = math.sqrt(4 / 3)
    assert statistic["bias"] == pytest.approx(2.0)
    assert statistic["dispersion"] == pytest.approx(dispersion)
    assert statistic["limits_of_agreement"] == pytest.approx(
        [2.0 - 1.96 * dispersion, 2.0 + 1.96 * dispersion]
    )


def test_an_empty_regime_raises_rather_than_reporting_a_bias_of_zero() -> None:
    """Zero is a number a reader would believe. There is no agreement over no windows."""
    with pytest.raises(ValueError, match="empty regime"):
        agreement.bland_altman(agreement.series_arrays([], "era5_100m")["u"])


@pytest.mark.parametrize(
    ("angle", "expected"),
    [(0.0, 0.0), (190.0, -170.0), (-190.0, 170.0), (540.0, 180.0), (180.0, 180.0)],
)
def test_angles_wrap_into_the_declared_interval(angle, expected) -> None:
    """(-180, 180], closed at the top: adr/0006 fixed the interval, including its ends."""
    assert agreement.wrap_degrees(angle) == pytest.approx(expected)


def test_direction_across_the_wrap_point_is_the_small_angle() -> None:
    """359 degrees against 1 degree is 2 degrees, not 358.

    The wrap point is not rare, and a statistic that treats bearing as a real number is
    wrong there by almost a full turn -- large enough to move a regime's whole result.
    """
    # Two vectors either side of due east, 2 degrees apart.
    a = (math.cos(math.radians(359.0)), math.sin(math.radians(359.0)))
    b = (math.cos(math.radians(1.0)), math.sin(math.radians(1.0)))
    assert agreement.bearing_difference_deg(a[0], a[1], b[0], b[1]) == pytest.approx(-2.0)


def test_the_direction_difference_does_not_depend_on_the_from_or_to_convention() -> None:
    """Turning both sources through 180 degrees leaves their disagreement unchanged.

    Meteorology reports the direction wind blows *from*; a vector points where it blows
    *to*. Taking the angle between the two vectors rather than between two bearings means
    the result is the same whichever convention the corpus turns out to use -- which
    matters, because getting it wrong would show as a 180 degree bias and look like a
    finding.
    """
    straight = agreement.bearing_difference_deg(3.0, 4.0, 4.0, 3.0)
    flipped = agreement.bearing_difference_deg(-3.0, -4.0, -4.0, -3.0)
    assert straight == pytest.approx(flipped)


def test_low_wind_windows_are_counted_undefined_and_not_dropped() -> None:
    """Below the threshold direction is meaningless, and silence about it is a bias.

    Dropping them would tilt the direction statistics toward exactly the conditions where
    direction is well determined, and adr/0006 makes the count part of the result rather
    than a footnote.
    """
    rows = [
        _row(run_id="calm", onboard=(0.5, 0.0), era5=(0.4, 0.0)),
        _row(run_id="calm2", onboard=(5.0, 0.0), era5=(0.4, 0.0)),  # one side below
        _row(run_id="windy", onboard=(5.0, 0.0), era5=(0.0, 5.0)),
    ]
    stats = agreement.direction_statistics(rows, "era5_100m", 2.0)
    assert stats["n_defined"] == 1
    assert stats["n_undefined"] == 2
    assert stats["n_defined"] + stats["n_undefined"] == len(rows)
    assert stats["speed_threshold_ms"] == 2.0
    assert stats["mean_absolute_deg"] == pytest.approx(90.0)


def test_the_bootstrap_resamples_runs_and_not_windows() -> None:
    """The interval must reflect 2 flights, not 100 hours of them.

    One run carries 99 windows and another carries 1. Resampling *windows* would draw 100
    of them and land near 9.9 almost every time, giving a narrow interval that the design
    never earned. Resampling *runs* draws two runs with replacement, so a quarter of the
    replicates are the single-window run twice and the bias distribution has real mass at
    0 -- which is what the lower bound has to see.

    ``validation_artifact.json`` pins ``bootstrap.unit`` to ``run`` for this reason; this
    is the test that the pin is honoured rather than merely declared.
    """
    rows = [_row(run_id="lonely", era5=(0.0, 0.0))]
    rows += [_row(run_id="busy", era5=(10.0, 0.0)) for _ in range(99)]
    interval = agreement.bootstrap(rows, "era5_100m", weights=None, resamples=400, seed=1)
    low, high = interval["u"]["bias_ci"]
    assert low < 1.0, "a by-window bootstrap could never reach the single-window run's value"
    assert high == pytest.approx(10.0, abs=0.2)


def test_design_weights_use_the_realised_runs_not_the_drawn_ones() -> None:
    """N_h / n_h on the runs that survived, because dropout is not random (adr/0014)."""
    rows = [_row(run_id=f"w{i}", stratum=WITHIN) for i in range(4)]
    rows += [_row(run_id=f"o{i}", stratum=OLDER) for i in range(2)]
    weights = agreement.design_weights(rows)
    assert weights[0] == pytest.approx(agreement.FRAME_SIZES[WITHIN] / 4)
    assert weights[-1] == pytest.approx(agreement.FRAME_SIZES[OLDER] / 2)


def test_reweighting_moves_the_pooled_number_toward_the_undersampled_stratum() -> None:
    """The whole point of adr/0014, as a number.

    Ten runs per stratum, disagreeing by 0 in one and by 10 in the other. The unweighted
    pool splits the difference because the draw is 50/50. The frame is not: ``older`` is
    10,497 of 16,682, so the reweighted pool has to sit above 5 and near 6.29.
    """
    rows = [_row(run_id=f"w{i}", stratum=WITHIN, era5=(0.0, 0.0)) for i in range(10)]
    rows += [_row(run_id=f"o{i}", stratum=OLDER, era5=(10.0, 0.0)) for i in range(10)]
    series = agreement.series_arrays(rows, "era5_100m")

    unweighted = agreement.bland_altman(series["u"])["bias"]
    reweighted = agreement.bland_altman(series["u"], agreement.design_weights(rows))["bias"]

    frame_share = agreement.FRAME_SIZES[OLDER] / sum(agreement.FRAME_SIZES.values())
    assert unweighted == pytest.approx(5.0)
    assert reweighted == pytest.approx(10.0 * frame_share, abs=1e-9)
    assert reweighted > unweighted


def test_a_regime_artifact_satisfies_the_schema_and_carries_its_verdict() -> None:
    """The artifact is the deliverable, so it is validated as one, not merely built.

    The fixture disagrees by 1 m/s in u, which puts the upper limit of agreement on the
    vector difference magnitude below adr/0015's 3.0 m/s band, so this regime is a useful
    proxy and says so.
    """
    rows = [_row(run_id=f"r{i}", era5=(1.0, 0.0), onboard=(0.0, 0.0)) for i in range(25)]
    artifact = agreement.regime_artifact(
        rows,
        label=WITHIN,
        criteria={"retention_stratum": WITHIN},
        level="era5_100m",
        weighted=False,
        manifest_id="00000000-0000-0000-0000-000000000000",
        resamples=50,
        seed=7,
    )
    from analysis.common.schema import validate

    validate(artifact, "validation_artifact.json")
    assert artifact["bootstrap"]["unit"] == "run"
    assert artifact["n_runs"] == 25
    assert artifact["useful_proxy"] is True
    assert artifact["statistics"]["unit"] == "m s-1"


def test_a_regime_outside_the_band_is_reported_as_not_a_useful_proxy() -> None:
    """A false verdict is a publishable result (adr/0003), so it must be reachable."""
    rows = [_row(run_id=f"r{i}", era5=(float(i % 12), 0.0), onboard=(0.0, 0.0)) for i in range(24)]
    artifact = agreement.regime_artifact(
        rows,
        label=WITHIN,
        criteria={"retention_stratum": WITHIN},
        level="era5_100m",
        weighted=False,
        manifest_id="00000000-0000-0000-0000-000000000000",
        resamples=50,
        seed=7,
    )
    assert artifact["useful_proxy"] is False


def test_the_estimator_relative_ratio_is_reported_per_component() -> None:
    """adr/0015's second view, and it must not collapse the two components into one.

    The fixture's onboard variance is deliberately anisotropic -- 0.25 against 1.0, so
    sigma is 0.5 against 1.0 -- and the u and v disagreements are equal. If the two were
    averaged anywhere in the chain the two ratios would come back equal, which is exactly
    the collapse adr/0015 was written to stop.
    """
    rows = [
        _row(run_id=f"r{i}", era5=(float(i % 4), float(i % 4)), variance=(0.25, 1.0))
        for i in range(20)
    ]
    ratios = agreement.estimator_relative_ratio(rows, "era5_100m")
    assert ratios["u"]["mean_onboard_sigma_ms"] == pytest.approx(0.5)
    assert ratios["v"]["mean_onboard_sigma_ms"] == pytest.approx(1.0)
    # Same spread over half the sigma: the u ratio must be exactly twice the v ratio.
    assert ratios["u"]["ratio"] == pytest.approx(2 * ratios["v"]["ratio"])
    assert ratios["u"]["n_windows_with_variance"] == 20


def _rows_for(stratum: str, *, runs: int, vehicles: int) -> list[dict]:
    """``runs`` runs spread over ``vehicles`` distinct airframes."""
    return [
        {**_row(run_id=f"{stratum}-{i}", stratum=stratum), "vehicle_uuid": f"veh{i % vehicles}"}
        for i in range(runs)
    ]


def test_a_cell_with_enough_runs_but_too_few_vehicles_is_suppressed() -> None:
    """The half of the threshold that a run count alone cannot see.

    ``docs/09-dpia.md`` 4.1 is one condition with two halves: 20 runs *and* 10 distinct
    vehicles. Twenty-five runs flown by three airframes clears the first and is three
    operators, so it must not be published. A gate checking only the run count passes this
    fixture with and without the protection, which is to say it guards nothing.
    """
    by_stratum = {
        WITHIN: _rows_for(WITHIN, runs=25, vehicles=3),
        OLDER: _rows_for(OLDER, runs=25, vehicles=12),
    }
    thick, suppressed = agreement.publishable_regimes(by_stratum, min_runs=20, min_vehicles=10)

    assert thick == [OLDER]
    assert suppressed == {WITHIN: {"n_runs": 25, "n_vehicles": 3}}


def test_a_suppressed_cell_is_reported_with_its_counts() -> None:
    """Suppression that hides its own existence is its own distortion (adr/0009)."""
    by_stratum = {WITHIN: _rows_for(WITHIN, runs=4, vehicles=2)}
    thick, suppressed = agreement.publishable_regimes(by_stratum, min_runs=20, min_vehicles=10)

    assert thick == []
    assert suppressed[WITHIN] == {"n_runs": 4, "n_vehicles": 2}
    # Counts, never identifiers: adr/0009 forbids emitting a vehicle_uuid raw or hashed.
    assert all(isinstance(value, int) for value in suppressed[WITHIN].values())


def test_a_cell_clearing_both_halves_is_published() -> None:
    """The gate has to let the ordinary case through, or it is just an outage."""
    by_stratum = {WITHIN: _rows_for(WITHIN, runs=400, vehicles=180)}
    thick, suppressed = agreement.publishable_regimes(by_stratum, min_runs=20, min_vehicles=10)

    assert thick == [WITHIN]
    assert suppressed == {}
