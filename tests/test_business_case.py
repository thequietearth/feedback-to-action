"""Business case model: assumptions, baseline, the shared calculation, simulation, scoring."""

import math
from pathlib import Path

import numpy as np
import pytest

import analysis
import assumptions as A
import model
import settings

REPO = Path(__file__).resolve().parents[1]
SHARES = ("share_saved", "maintenance_share", "review_share", "rescue_share")


@pytest.fixture(scope="module")
def baseline():
    return model.default_baseline()


# A tiny, hand-checkable baseline: 100 clarification hours/yr, 1,000 items, 40 lost.
TOY = model.Baseline(
    hours_per_year={"Clarification requested": 100.0},
    events_per_year={"Clarification requested": 200.0},
    items_per_year=1_000.0, lost_per_year=40.0, weeks=52.0,
)
TOY_OPTION = {"pool": ["Clarification requested"]}


# --- 2. Assumptions -------------------------------------------------------------

@pytest.mark.parametrize("key", A.OPTIONS)
def test_ranges_are_ordered_and_shares_bounded(key):
    for name, (low, mode, high) in model.ranges(A.OPTIONS[key]).items():
        assert low <= mode <= high, (key, name)
        if name in SHARES:
            assert 0 <= low and high <= 1, (key, name)


@pytest.mark.parametrize("key", A.OPTIONS)
def test_feasibility_scores_have_rationale(key):
    scores = A.OPTIONS[key]["feasibility"]
    assert set(scores) == set(A.FEASIBILITY_WEIGHTS)
    for criterion, (score, why) in scores.items():
        assert 1 <= score <= 5, (key, criterion)
        assert why.strip(), (key, criterion)


def test_weights_sum_to_one():
    assert math.isclose(sum(A.FEASIBILITY_WEIGHTS.values()), 1.0)


# --- 3. Baseline ----------------------------------------------------------------

def test_baseline_matches_the_readout(baseline):
    log = analysis.remove_duplicates(analysis.load_log(REPO / settings.DATA_PATH))
    readout = analysis.chasing_cost(log, settings.HOURLY_RATE)
    assert sum(baseline.hours_per_year.values()) == pytest.approx(readout["annual_hours"])
    assert baseline.lost_per_year > 0 and baseline.items_per_year > 0


# --- 4. The one calculation -----------------------------------------------------

HAND = {"share_saved": 0.5, "build_weeks": 2, "engineer_weekly_cost": 3_000, "maintenance_share": 0.1,
        "run_cost": 400, "review_share": 0.1, "review_minutes": 3, "rescue_share": 0.5}


def test_evaluate_matches_hand_calculation():
    r = model.evaluate(HAND, TOY_OPTION, TOY, rate=60)
    # 50h saved x 60 = 3,000 benefit. Build 2 x 3,000 = 6,000.
    # Review: 0.1 x 1,000 items x 3 min = 5h x 60 = 300. Annual cost 600 + 400 + 300 = 1,300.
    assert r["benefit"] == 3_000
    assert r["annual_cost"] == pytest.approx(1_300)
    assert float(r["payback_months"]) == pytest.approx(6_000 / (1_700 / 12))
    assert r["net_3yr"] == pytest.approx(9_000 - 9_900)
    assert float(r["roi_3yr"]) == pytest.approx(-900 / 9_900)


def test_zero_hours_saved_means_zero_benefit_and_negative_roi():
    r = model.evaluate({**HAND, "share_saved": 0}, TOY_OPTION, TOY, rate=60)
    assert r["benefit"] == 0
    assert float(r["roi_3yr"]) < 0
    assert math.isinf(float(r["payback_months"]))  # never pays back


def test_uncounted_outcomes_are_counts():
    r = model.evaluate(HAND, TOY_OPTION, TOY, rate=60)
    assert r["items_rescued"] == 20      # 0.5 x 40 lost items
    assert r["events_avoided"] == 100    # 0.5 x 200 clarification requests


# --- 5. Simulation --------------------------------------------------------------

def test_same_seed_same_results(baseline):
    option = A.OPTIONS["ai_intake"]
    a = model.simulate(option, baseline, 60, n=2_000, seed=3)
    b = model.simulate(option, baseline, 60, n=2_000, seed=3)
    assert all(np.array_equal(a[k], b[k]) for k in a)


def test_collapsed_ranges_equal_the_hand_calculation(baseline):
    option = A.OPTIONS["follow_through"]
    collapsed = {name: (v, v, v) for name, v in model.most_likely(option).items()}
    runs = model.simulate(option, baseline, 60, n=500, overrides=collapsed)
    exact = model.evaluate(model.most_likely(option), option, baseline, 60)
    for metric in ("benefit", "annual_cost", "net_3yr", "roi_3yr", "payback_months"):
        assert np.all(runs[metric] == exact[metric]), metric


def test_summary_probabilities_are_shares(baseline):
    s = model.summarise(model.simulate(A.OPTIONS["intake_form"], baseline, 60, n=2_000))
    assert 0 <= s["p_payback_target"] <= 1 and 0 <= s["p_roi_positive"] <= 1
    assert s["net_3yr"][10] <= s["net_3yr"][50] <= s["net_3yr"][90]


# --- 6. Scoring and sensitivity ---------------------------------------------------

def test_feasibility_weighting():
    all_fives = {"feasibility": {c: (5, "x") for c in A.FEASIBILITY_WEIGHTS}}
    assert model.feasibility_score(all_fives) == pytest.approx(5)
    only_complexity = {"feasibility": {c: (5 if c == "complexity" else 1, "x") for c in A.FEASIBILITY_WEIGHTS}}
    assert model.feasibility_score(only_complexity) == pytest.approx(1 + 4 * A.FEASIBILITY_WEIGHTS["complexity"])


def test_value_axis_is_fixed_not_rescaled():
    low, high = A.VALUE_AXIS
    assert model.value_position(low) == 0 and model.value_position(high) == 1
    assert model.value_position((low + high) / 2) == pytest.approx(0.5)


def test_sensitivity_ranked_and_collapsed_input_has_no_swing(baseline):
    table = model.sensitivity(A.OPTIONS["intake_form"], baseline, 60)
    assert table["swing"].is_monotonic_decreasing
    # The form has no run cost: run_cost is (0, 0, 0), so it cannot move the result.
    assert table.set_index("input").loc["run_cost", "swing"] == 0


def test_run_all_ranks_by_value(baseline):
    results = model.run_all(baseline, n=2_000)
    values = [r.value for r in results]
    assert values == sorted(values, reverse=True)
    assert {r.key for r in results} == set(A.OPTIONS)
