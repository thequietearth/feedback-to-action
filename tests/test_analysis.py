"""Discovery analysis: every number checked against a hand-built log with a known answer."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import analysis
import settings
from generate import build_log

REPO = Path(__file__).resolve().parents[1]

# 2026-01-06 is a Tuesday, 2026-01-09 a Friday, 2026-01-12 a Monday.


def make_log(rows) -> pd.DataFrame:
    """rows: (case_id, activity, 'YYYY-MM-DD HH:MM'[, detail_level[, handle_time_min]])."""
    records = []
    for row in rows:
        case_id, activity, when = row[:3]
        detail = row[3] if len(row) > 3 else "medium"
        handle = row[4] if len(row) > 4 else 5
        records.append({
            "case_id": case_id, "activity": activity, "timestamp": f"{when.replace(' ', 'T')}:00+08:00",
            "channel": "tracker", "role": "product_ops", "resource": "OPS-01", "handle_time_min": handle,
            "source": "support_ticket", "product_area": "billing", "detail_level": detail,
            "customer_tier": "smb",
        })
    return analysis.prepare(pd.DataFrame(records))


@pytest.fixture(scope="module")
def default_log():
    return analysis.remove_duplicates(analysis.load_log(REPO / settings.DATA_PATH))


@pytest.fixture(scope="module")
def effect_off_log():
    return analysis.remove_duplicates(analysis.prepare(build_log(detail_effect=False)))


# --- 2. Loading -----------------------------------------------------------------

def test_load_log_parses_offset_and_keeps_columns(tmp_path):
    csv = tmp_path / "log.csv"
    csv.write_text(
        "case_id,activity,timestamp,channel,role,resource,handle_time_min,source,product_area,detail_level,customer_tier\n"
        "FB-1,Feedback submitted,2026-01-06T09:30:00+08:00,tracker,customer,CUS-001,5,survey,billing,low,smb\n",
        encoding="utf-8",
    )
    log = analysis.load_log(csv)
    assert isinstance(log["timestamp"].dtype, pd.DatetimeTZDtype)
    assert log["timestamp"].iloc[0].utcoffset() == pd.Timedelta(hours=8)
    assert list(log.columns)[:3] == ["case_id", "activity", "timestamp"]


def test_remove_duplicates_drops_exactly_the_planted_rows():
    log = make_log([("A", "Feedback submitted", "2026-01-06 09:00"), ("A", "Triaged", "2026-01-06 10:00"),
                    ("B", "Feedback submitted", "2026-01-06 11:00")])
    with_dups = pd.concat([log, log.iloc[[0, 1, 1]]], ignore_index=True)
    assert len(analysis.remove_duplicates(with_dups)) == len(log)


# --- 3. Data quality --------------------------------------------------------------

def test_quality_report_counts_are_exact():
    log = make_log([
        # A: clean and closed
        ("A", "Feedback submitted", "2026-01-06 09:00"), ("A", "Triaged", "2026-01-06 10:00"),
        ("A", "Clarification requested", "2026-01-06 11:00"), ("A", "Clarification received", "2026-01-06 15:00"),
        ("A", "Routed to owner", "2026-01-06 16:00"), ("A", "Owner acknowledged", "2026-01-07 10:00"),
        ("A", "Resolved", "2026-01-08 10:00"),
        # B: bad start (submission missing) and a reply with no request
        ("B", "Triaged", "2026-01-06 10:00"), ("B", "Clarification received", "2026-01-06 12:00"),
        ("B", "Routed to owner", "2026-01-06 13:00"), ("B", "Owner acknowledged", "2026-01-07 09:30"),
        ("B", "Won't do", "2026-01-07 11:00"),
        # C: open, with one event logged at 20:00
        ("C", "Feedback submitted", "2026-01-06 09:00"), ("C", "Triaged", "2026-01-06 20:00"),
    ])
    raw = pd.concat([log, log.iloc[[0]]], ignore_index=True)  # one duplicate row
    report = analysis.quality_report(raw)
    assert report["events"] == len(raw)
    assert report["cases"] == 3
    assert report["duplicate_rows"] == 1
    assert report["bad_starts"] == 1
    assert report["sequence_breaks"] == 1
    assert report["open_cases"] == 1
    assert report["off_hours"] == 1


def test_missing_second_request_is_a_sequence_break():
    log = make_log([("A", "Clarification requested", "2026-01-06 10:00"),
                    ("A", "Clarification received", "2026-01-06 11:00"),
                    ("A", "Clarification received", "2026-01-06 12:00")])
    assert analysis.sequence_break_cases(log) == {"A"}


# --- 4. Process flow --------------------------------------------------------------

@pytest.fixture
def flow_log():
    return make_log([
        ("A", "Feedback submitted", "2026-01-06 09:00"), ("A", "Triaged", "2026-01-06 10:00"),
        ("B", "Feedback submitted", "2026-01-06 09:30"), ("B", "Triaged", "2026-01-06 10:30"),
        ("C", "Feedback submitted", "2026-01-06 11:00"), ("C", "Merged as duplicate", "2026-01-06 12:00"),
    ])


def test_directly_follows_counts(flow_log):
    edges = analysis.directly_follows(flow_log).set_index(["source", "target"])["count"]
    assert edges[("Feedback submitted", "Triaged")] == 2
    assert edges[("Feedback submitted", "Merged as duplicate")] == 1
    assert edges.sum() == 3


def test_variant_shares(flow_log):
    table = analysis.variants(flow_log)
    assert table.iloc[0]["path"] == "Feedback submitted → Triaged"
    assert table.iloc[0]["cases"] == 2
    assert table["share"].tolist() == pytest.approx([2 / 3, 1 / 3])


def test_dot_hides_rare_edges(flow_log):
    edges = analysis.directly_follows(flow_log)
    counts = flow_log["activity"].value_counts()
    dot = analysis.to_dot(edges, counts, min_count=2)
    assert '"Feedback submitted" -> "Triaged"' in dot
    assert '"Merged as duplicate"' not in dot


# --- 5. Stalls --------------------------------------------------------------------

def hours(a: str, b: str) -> float:
    ts = make_log([("X", "Triaged", a), ("Y", "Triaged", b)])["timestamp"]
    return analysis.working_hours_between(ts.iloc[[0]], ts.iloc[[1]].set_axis(ts.index[[0]])).iloc[0]


def test_friday_to_monday_is_two_working_hours():
    assert hours("2026-01-09 17:00", "2026-01-12 10:00") == 2.0


def test_same_day_and_early_start():
    assert hours("2026-01-06 10:00", "2026-01-06 11:30") == 1.5
    assert hours("2026-01-06 07:00", "2026-01-06 10:00") == 1.0  # before 09:00 counts from 09:00


@pytest.fixture
def stall_log():
    return make_log([
        ("A", "Feedback submitted", "2026-01-06 09:00"),
        ("A", "Clarification requested", "2026-01-06 10:00"),  # 1h waiting on product ops
        ("A", "Clarification received", "2026-01-06 14:00"),   # 4h waiting on the provider
        ("A", "Routed to owner", "2026-01-06 15:00"),          # 1h waiting on product ops
    ])


def test_waits_land_on_the_right_party(stall_log):
    w = analysis.waits(stall_log)
    provider = w[w["from_activity"] == "Clarification requested"].iloc[0]
    assert provider["wait_h"] == 4.0 and provider["waiting_on"] == "provider"
    assert analysis.transition_waits(w).iloc[0]["waiting_on"] == "provider"


def test_party_shares_sum_to_one(stall_log):
    shares = analysis.party_shares(analysis.waits(stall_log)).set_index("waiting_on")["share"]
    assert shares.sum() == pytest.approx(1.0)
    assert shares["provider"] == pytest.approx(4 / 6)


def test_active_work_is_reported_separately_not_as_a_stall():
    log = make_log([
        ("A", "Routed to owner", "2026-01-06 09:00"),
        ("A", "In progress", "2026-01-06 11:00"),   # 2h waiting on the owner
        ("A", "Resolved", "2026-01-06 17:00"),      # 6h of the owner working
    ])
    w = analysis.waits(log)
    stall_rows = analysis.stalls(w)
    assert "In progress" not in set(stall_rows["from_activity"])
    assert analysis.party_shares(stall_rows).set_index("waiting_on")["share"].to_dict() == {"owner": 1.0}
    work = analysis.active_work(w)
    assert work["hours"] == 6.0
    assert work["share_of_time"] == 0.75


def test_open_ageing_counts_up_to_export_time():
    log = make_log([
        ("A", "Feedback submitted", "2026-01-06 09:00"), ("A", "Routed to owner", "2026-01-06 10:00"),
        ("B", "Feedback submitted", "2026-01-06 09:00"), ("B", "Merged as duplicate", "2026-01-07 12:00"),
    ])
    ageing = analysis.open_ageing(log)
    assert ageing["case_id"].tolist() == ["A"]
    assert ageing.iloc[0]["waiting_h"] == 11.0  # Tue 10:00-18:00 (8h) + Wed 09:00-12:00 (3h)
    assert ageing.iloc[0]["waiting_on"] == "owner"
    assert analysis.ageing_bands(ageing)["open_cases"].sum() == 1


# --- 6. Cost of chasing -----------------------------------------------------------

def test_cost_reconciles_exactly_and_annualises_by_weeks():
    log = make_log([
        ("A", "Feedback submitted", "2026-01-06 09:00", "low", 5),
        ("A", "Clarification requested", "2026-01-06 10:00", "low", 10),
        ("A", "Nudge sent", "2026-01-07 10:00", "low", 20),
        ("A", "Escalated", "2026-01-08 10:00", "low", 30),
        ("A", "Reassigned", "2026-01-09 10:00", "low", 15),
        ("A", "Resolved", "2026-01-20 09:00", "low", 5),   # exactly two weeks after the first event
    ])
    rate = 60
    result = analysis.chasing_cost(log, rate)
    assert result["minutes"] == 60
    assert result["cost"] == (60 / 60) * rate
    assert result["weeks"] == 2.0
    assert result["annual_cost"] == pytest.approx(result["cost"] * settings.WEEKS_PER_YEAR / 2)
    assert result["rework_hours"] == 0.25


# --- 7. Detail-level verdict ------------------------------------------------------

def test_intake_delay_and_clarification_rate():
    log = make_log([
        ("A", "Feedback submitted", "2026-01-06 09:00", "low"),
        ("A", "Clarification requested", "2026-01-06 10:00", "low"),
        ("A", "Routed to owner", "2026-01-06 12:00", "low"),
        ("B", "Feedback submitted", "2026-01-06 09:00", "high"),
        ("B", "Merged as duplicate", "2026-01-06 10:00", "high"),
        ("C", "Feedback submitted", "2026-01-06 09:00", "high"),  # not routed yet: excluded
    ])
    table = analysis.intake_delays(log)
    delays = table.set_index("case_id")["intake_h"]
    assert delays.to_dict() == {"A": 3.0, "B": 1.0}
    medians = analysis.intake_medians(table).set_index("detail_level")
    assert medians.loc["low", "median_h"] == 3.0 and medians.loc["high", "cases"] == 1
    rate = analysis.clarification_rate(log)
    assert rate["low"] == 1.0 and rate["high"] == 0.0


def test_permutation_p_finds_a_clear_gap():
    rng = np.random.default_rng(1)
    slow, fast = rng.normal(20, 1, 200), rng.normal(5, 1, 200)
    assert analysis.permutation_p(slow, fast) == pytest.approx(1 / (settings.N_PERMUTATIONS + 1))


def test_permutation_p_is_calibrated_when_there_is_no_effect():
    # Any single no-effect draw can look "significant" by chance (about 5% of the
    # time), so check the false-positive rate across many draws instead.
    rng = np.random.default_rng(7)
    draws = 200
    p_values = np.array([analysis.permutation_p(*np.split(rng.normal(10, 1, 400), 2), n=500)
                         for _ in range(draws)])
    false_positive_rate = (p_values < settings.P_THRESHOLD).mean()
    assert 0.01 <= false_positive_rate <= 0.10, false_positive_rate


@pytest.mark.parametrize("ratio, p, expected", [
    (2.0, 0.01, True),    # all three conditions met
    (1.2, 0.001, False),  # significant but too small
    (0.8, 0.001, False),  # significant but reversed
    (2.0, 0.20, False),   # big but could be chance
])
def test_decision_rule(ratio, p, expected):
    assert analysis.decide(ratio, p) is expected


def test_default_dataset_shows_pattern(default_log):
    verdict = analysis.detail_verdict(analysis.intake_delays(default_log))
    assert verdict.pattern, verdict


def test_effect_off_dataset_shows_no_pattern(effect_off_log):
    verdict = analysis.detail_verdict(analysis.intake_delays(effect_off_log))
    assert not verdict.pattern, verdict


def test_resolution_context_excludes_and_counts_open_cases():
    log = make_log([
        ("A", "Feedback submitted", "2026-01-06 09:00", "low"), ("A", "Resolved", "2026-01-06 13:00", "low"),
        ("B", "Feedback submitted", "2026-01-06 09:00", "low"), ("B", "Routed to owner", "2026-01-06 10:00", "low"),
    ])
    table = analysis.resolution_by_detail(log).set_index("detail_level")
    assert table.loc["low", "median_h"] == 4.0
    assert table.loc["low", "closed_cases"] == 1
    assert table.loc["low", "open_excluded"] == 1


def test_verdict_ignores_end_states(default_log):
    without_ends = default_log[~default_log["activity"].isin(["Resolved", "Won't do", "Closed as stale"])]
    before = analysis.detail_verdict(analysis.intake_delays(default_log))
    after = analysis.detail_verdict(analysis.intake_delays(without_ends))
    assert before == after
