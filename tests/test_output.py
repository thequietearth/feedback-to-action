"""The written CSV: schema, reproducibility, the detail-level switch, working hours."""

import time

import numpy as np
import pandas as pd
import pytest

import config
from generate import COLUMNS, main, simulate


@pytest.fixture(scope="module")
def default_csv(tmp_path_factory):
    """Run the CLI once with defaults (to a temp folder) and time it."""
    path = tmp_path_factory.mktemp("out") / "event_log.csv"
    start = time.perf_counter()
    main(["--out", str(path)])
    return path, time.perf_counter() - start


def read_raw(path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


# --- 6.1 Output format -----------------------------------------------------------

def test_columns_exact_and_in_order(default_csv):
    path, _ = default_csv
    assert list(read_raw(path).columns) == COLUMNS


def test_allowed_activity_values(default_csv):
    allowed = set(config.HANDLE_TIME_MIN)  # one entry per activity
    assert set(read_raw(default_csv[0])["activity"]) <= allowed


def test_sorted_by_case_then_timestamp(default_csv):
    log = read_raw(default_csv[0])
    ts = pd.to_datetime(log["timestamp"], format="ISO8601")
    keys = pd.DataFrame({"case_id": log["case_id"], "ts": ts})
    assert keys.equals(keys.sort_values(["case_id", "ts"], kind="stable"))


# --- 6.2 Reproducibility -----------------------------------------------------------

def test_same_seed_gives_identical_bytes(default_csv, tmp_path):
    path, _ = default_csv
    again = tmp_path / "again.csv"
    main(["--out", str(again)])
    assert again.read_bytes() == path.read_bytes()


def test_different_seed_gives_different_file(default_csv, tmp_path):
    path, _ = default_csv
    other = tmp_path / "other.csv"
    main(["--out", str(other), "--seed", str(config.SEED + 1)])
    assert other.read_bytes() != path.read_bytes()


# --- 6.3 Detail-level switch -----------------------------------------------------

def clarification_share_by_detail(detail_effect: bool) -> pd.Series:
    log = simulate(np.random.default_rng(config.SEED), detail_effect=detail_effect)
    asked = log.loc[log["activity"] == "Clarification requested", "case_id"].unique()
    per_case = log.groupby("case_id")["detail_level"].first().to_frame()
    per_case["asked"] = per_case.index.isin(asked)
    return per_case.groupby("detail_level")["asked"].mean()


def test_effect_on_low_detail_needs_clarifying_far_more():
    share = clarification_share_by_detail(detail_effect=True)
    assert share["low"] >= 3 * share["high"], share.to_dict()


def test_effect_off_no_pattern():
    share = clarification_share_by_detail(detail_effect=False)
    assert share.max() <= 1.2 * share.min(), share.to_dict()


def test_cli_flag_turns_effect_off(tmp_path):
    on, off = tmp_path / "on.csv", tmp_path / "off.csv"
    main(["--out", str(on)])
    main(["--out", str(off), "--no-detail-effect"])
    assert on.read_bytes() != off.read_bytes()


# --- 6.4 Working hours on the final file, and run time -----------------------------

def test_timestamps_in_working_hours_sgt(default_csv):
    raw = read_raw(default_csv[0])["timestamp"]
    offset = f"+{config.UTC_OFFSET_HOURS:02d}:00"
    assert raw.str.endswith(offset).all()
    ts = pd.to_datetime(raw, format="ISO8601")
    minutes = ts.dt.hour * 60 + ts.dt.minute
    assert (ts.dt.dayofweek < 5).all()
    assert (minutes >= config.WORKDAY_START_HOUR * 60).all()
    assert (minutes <= config.WORKDAY_END_HOUR * 60).all()


def test_full_run_is_fast(default_csv):
    _, seconds = default_csv
    assert seconds < 30, seconds
