"""Exec brief: recommendation rules, and the committed brief matches the model."""

import pandas as pd
import pytest

import brief
import model


def fake_result(name, value, p_roi, build=10_000, payback=12.0, pool=("Nudge sent",)):
    """A minimal OptionResult with just the numbers the rules read."""
    pct = lambda x: {10: x, 50: x, 90: x}  # noqa: E731
    summary = {"hours_saved": pct(100), "net_3yr": pct(value), "payback_months": pct(payback),
               "build_cost": pct(build), "p_roi_positive": p_roi}
    return model.OptionResult(key=name, name=name, pool=pool, pool_label="work", rests_on="something unpriced",
                              summary=summary, feasibility=3.0, value=value, sensitivity=pd.DataFrame())


@pytest.fixture(scope="module")
def default_text():
    baseline = model.default_baseline()
    return brief.build_brief(baseline, model.run_all(baseline))


def test_option_below_threshold_is_flagged():
    lines = brief.recommendation([fake_result("Paying", 30_000, 0.9), fake_result("Unpriced", -5_000, 0.3)])
    assert lines[0].startswith("**Fund Paying first.**")
    assert any("Unpriced does not pay back on hours alone" in line for line in lines)
    assert not any("Paying does not pay back" in line for line in lines)


def test_quick_win_is_the_cheapest_build_and_combinability_follows_pools():
    best = fake_result("Best", 40_000, 0.95, build=20_000, pool=("Nudge sent",))
    cheap = fake_result("Cheap", 10_000, 0.95, build=5_000, pool=("Clarification requested",))
    lines = brief.recommendation([best, cheap])
    assert "Cheap is the quick win" in lines[1] and "can run together" in lines[1]
    rival = fake_result("Rival", 10_000, 0.95, build=5_000, pool=("Nudge sent",))
    assert "choose one" in brief.recommendation([best, rival])[1]


def test_no_paying_option_says_so():
    assert brief.recommendation([fake_result("A", -1_000, 0.2)])[0] == \
        "**No option pays back on product ops hours alone.**"


def test_committed_brief_is_current(default_text):
    assert brief.BRIEF_PATH.read_bytes() == default_text.encode("utf-8"), \
        "docs/exec_brief.md is stale: run `python business_case/brief.py`"


def test_brief_fits_on_one_page(default_text):
    assert len(default_text.split()) < 600


def test_default_brief_flags_the_ai_option(default_text):
    assert "AI intake clarity check does not pay back on hours alone" in default_text
