"""Case simulation: lifecycle rules on the clean (noise-free) log."""

import numpy as np
import pandas as pd
import pytest

import config
from generate import TERMINAL_ACTIVITIES, simulate, to_calendar, observation_end_offset


@pytest.fixture(scope="module")
def log() -> pd.DataFrame:
    return simulate(np.random.default_rng(config.SEED))


def cases(log):
    return log.groupby("case_id", sort=False)


def test_attributes_use_config_values(log):
    assert set(log["source"]) <= set(config.SOURCE_MIX)
    assert set(log["product_area"]) <= set(config.PRODUCT_AREA_MIX)
    assert set(log["detail_level"]) <= set(config.DETAIL_MIX)
    assert set(log["customer_tier"]) <= set(config.TIER_MIX)
    assert set(log["role"]) <= set(config.ROLES)
    assert set(log["channel"]) <= set(config.CHANNELS)


def test_case_attributes_constant_within_case(log):
    per_case = log.groupby("case_id")[["source", "product_area", "detail_level", "customer_tier"]].nunique()
    assert (per_case == 1).all().all()


def test_resources_are_anonymised_ids(log):
    prefixes = {prefix for prefix, _ in config.RESOURCE_POOLS.values()}
    assert not log["resource"].str.contains(r"[\s@]").any()
    assert set(log["resource"].str.split("-").str[0]) <= prefixes


def test_clarification_request_is_answered_or_closed(log):
    for _, events in cases(log):
        acts = events["activity"].tolist()
        if acts[-1] not in TERMINAL_ACTIVITIES:
            continue  # censored at window end: the reply may simply not have happened yet
        for i, act in enumerate(acts):
            if act == "Clarification requested":
                assert acts[i + 1] in {"Clarification received", "Closed as stale"}, acts


def test_merged_duplicate_ends_case(log):
    for _, events in cases(log):
        acts = events["activity"].tolist()
        if "Merged as duplicate" in acts:
            assert acts[-1] == "Merged as duplicate"
            assert acts.count("Merged as duplicate") == 1


def test_escalation_follows_a_nudge(log):
    escalated = 0
    for _, events in cases(log):
        acts = events["activity"].tolist()
        if "Escalated" in acts:
            escalated += 1
            assert "Nudge sent" in acts[: acts.index("Escalated")]
    assert escalated > 0  # the rule is exercised, not vacuously true


def test_escalation_is_rare(log):
    routed = log.loc[log["activity"] == "Routed to owner", "case_id"].nunique()
    escalated = log.loc[log["activity"] == "Escalated", "case_id"].nunique()
    assert escalated / routed < 0.10


def test_no_event_after_window_and_censored_cases_stay_open(log):
    end = to_calendar(observation_end_offset() - 1)
    assert log["timestamp"].max() <= end
    last = cases(log)["activity"].last()
    open_cases = last[~last.isin(TERMINAL_ACTIVITIES)]
    assert len(open_cases) > 0  # late submissions are still in flight


def test_every_case_starts_with_submission(log):
    first = cases(log)["activity"].first()
    assert (first == "Feedback submitted").all()


def test_timestamps_never_decrease_within_case(log):
    assert cases(log)["timestamp"].apply(lambda ts: ts.is_monotonic_increasing).all()


def test_at_most_one_terminal_and_it_is_last(log):
    for _, events in cases(log):
        acts = events["activity"].tolist()
        terminals = [a for a in acts if a in TERMINAL_ACTIVITIES]
        assert len(terminals) <= 1, acts
        if terminals:
            assert acts[-1] == terminals[0], acts


def test_all_cases_present(log):
    assert log["case_id"].nunique() == config.N_CASES
