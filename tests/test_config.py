"""Sanity checks on the assumptions in config.py."""

import math

import pytest

import config

MIXES = {
    "SOURCE_MIX": config.SOURCE_MIX,
    "DETAIL_MIX": config.DETAIL_MIX,
    "TIER_MIX": config.TIER_MIX,
    "PRODUCT_AREA_MIX": config.PRODUCT_AREA_MIX,
    "OUTCOME_MIX": config.OUTCOME_MIX,
    "NUDGE_CHANNEL_MIX": config.NUDGE_CHANNEL_MIX,
    "ESCALATION_CHANNEL_MIX": config.ESCALATION_CHANNEL_MIX,
    **{f"CLARIFICATION_CHANNEL_MIX[{k}]": v for k, v in config.CLARIFICATION_CHANNEL_MIX.items()},
}

PROBABILITIES = {
    **{f"P_NEEDS_CLARIFICATION[{k}]": v for k, v in config.P_NEEDS_CLARIFICATION.items()},
    **{f"P_PROVIDER_NEVER_REPLIES[{k}]": v for k, v in config.P_PROVIDER_NEVER_REPLIES.items()},
    "P_STILL_UNCLEAR": config.P_STILL_UNCLEAR,
    "P_DUPLICATE": config.P_DUPLICATE,
    "P_MISROUTED": config.P_MISROUTED,
    "P_ESCALATE": config.P_ESCALATE,
    "MISSING_EVENT_RATE": config.MISSING_EVENT_RATE,
    "DUPLICATE_EVENT_RATE": config.DUPLICATE_EVENT_RATE,
}


@pytest.mark.parametrize("name", MIXES)
def test_mix_sums_to_one(name):
    assert math.isclose(sum(MIXES[name].values()), 1.0), name


@pytest.mark.parametrize("name", PROBABILITIES)
def test_probability_in_range(name):
    assert 0.0 <= PROBABILITIES[name] <= 1.0, name


def test_mix_keys_cover_every_level():
    assert set(config.P_NEEDS_CLARIFICATION) == set(config.DETAIL_MIX)
    assert set(config.SUBMITTER_ROLE) == set(config.SOURCE_MIX)
    assert set(config.SUBMISSION_CHANNEL) == set(config.SOURCE_MIX)


def test_channels_used_are_declared():
    used = set(config.SUBMISSION_CHANNEL.values()) | set(config.NUDGE_CHANNEL_MIX) | set(config.ESCALATION_CHANNEL_MIX)
    for mix in config.CLARIFICATION_CHANNEL_MIX.values():
        used |= set(mix)
    assert used <= set(config.CHANNELS)


def test_window_starts_on_weekday_and_ends_after_start():
    assert config.WINDOW_START.weekday() < 5
    assert config.WINDOW_END > config.WINDOW_START
