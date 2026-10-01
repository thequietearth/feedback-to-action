"""Working-time clock: every timestamp must land inside working hours."""

from datetime import datetime

import numpy as np

import config
from generate import TZ, add_working_minutes, observation_end_offset, sample_submission_offsets, to_calendar


def sgt(y, m, d, hh, mm=0):
    return datetime(y, m, d, hh, mm, tzinfo=TZ)


def is_working_time(ts: datetime) -> bool:
    start = ts.replace(hour=config.WORKDAY_START_HOUR, minute=0, second=0)
    end = ts.replace(hour=config.WORKDAY_END_HOUR, minute=0, second=0)
    return ts.weekday() < 5 and start <= ts <= end


def test_friday_evening_rolls_to_monday():
    # 2026-01-09 is a Friday: 30 minutes left on Friday, 30 more on Monday.
    assert add_working_minutes(sgt(2026, 1, 9, 17, 30), 60) == sgt(2026, 1, 12, 9, 30)


def test_early_start_snaps_to_nine():
    assert add_working_minutes(sgt(2026, 1, 6, 7, 15), 0) == sgt(2026, 1, 6, 9, 0)


def test_weekend_start_snaps_to_monday():
    assert add_working_minutes(sgt(2026, 1, 10, 12, 0), 0) == sgt(2026, 1, 12, 9, 0)


def test_within_day_addition():
    assert add_working_minutes(sgt(2026, 1, 6, 10, 0), 90) == sgt(2026, 1, 6, 11, 30)


def test_offset_zero_is_window_start():
    start = config.WINDOW_START
    assert to_calendar(0) == sgt(start.year, start.month, start.day, config.WORKDAY_START_HOUR)


def test_submissions_fall_in_working_hours_and_window():
    rng = np.random.default_rng(0)
    offsets = sample_submission_offsets(rng, 5_000)
    assert offsets.max() < observation_end_offset()
    for off in offsets:
        ts = to_calendar(off)
        assert is_working_time(ts), ts
        assert config.WINDOW_START <= ts.date() <= config.WINDOW_END
