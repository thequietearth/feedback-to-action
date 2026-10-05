"""The Streamlit readout: renders without errors, in order, and follows the data."""

import time
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import analysis
import settings

REPO = Path(__file__).resolve().parents[1]
APP = str(REPO / "app" / "streamlit_app.py")
SECTIONS = [
    "1. Can we trust the data?",
    "2. How work flows",
    "3. Where items stall",
    "4. What chasing costs",
    "5. Does vague feedback cause delay?",
]


def run_app(dataset: str) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    if dataset != settings.DATASET_DEFAULT:
        at.sidebar.radio[0].set_value(dataset)
        at.run()
    return at


@pytest.fixture(scope="module")
def default_app():
    return run_app(settings.DATASET_DEFAULT)


@pytest.fixture(scope="module")
def effect_off_app():
    return run_app(settings.DATASET_EFFECT_OFF)


@pytest.mark.parametrize("app_fixture", ["default_app", "effect_off_app"])
def test_renders_five_sections_in_order(app_fixture, request):
    at = request.getfixturevalue(app_fixture)
    assert not at.exception, at.exception
    assert [h.value for h in at.main.header] == SECTIONS  # main page only, not the sidebar


def test_each_section_opens_with_a_finding(default_app):
    assert len(default_app.info) == len(SECTIONS)


def test_findings_follow_the_dataset(default_app, effect_off_app):
    on = [i.value for i in default_app.info]
    off = [i.value for i in effect_off_app.info]
    assert on != off
    assert on[-1].startswith("Yes.")
    assert off[-1].startswith("No pattern.")


def test_full_analysis_under_five_seconds():
    start = time.perf_counter()
    raw = analysis.load_log(REPO / settings.DATA_PATH)
    log = analysis.remove_duplicates(raw)
    analysis.quality_report(raw)
    analysis.to_dot(analysis.directly_follows(log), log["activity"].value_counts(), settings.MAP_MIN_EDGE_COUNT)
    analysis.variants(log)
    wait_rows = analysis.waits(log)
    analysis.transition_waits(wait_rows)
    analysis.party_shares(wait_rows)
    analysis.ageing_bands(analysis.open_ageing(log))
    analysis.chasing_cost(log, settings.HOURLY_RATE)
    delays = analysis.intake_delays(log)
    analysis.intake_medians(delays)
    analysis.detail_verdict(delays)
    analysis.clarification_rate(log)
    analysis.resolution_by_detail(log)
    elapsed = time.perf_counter() - start
    assert elapsed < 5, elapsed
