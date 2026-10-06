"""The business case page renders, shows every option, and responds to its sliders."""

import time
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import assumptions as A
import model

REPO = Path(__file__).resolve().parents[1]
PAGE = str(REPO / "app" / "pages" / "1_Business_case.py")


def run_page(rate: int | None = None) -> AppTest:
    at = AppTest.from_file(PAGE, default_timeout=120)
    at.run()
    if rate is not None:
        at.sidebar.slider[0].set_value(rate)   # first slider: product ops hourly cost
        at.run()
    return at


def median_hours_benefit(at: AppTest) -> dict:
    """Median annual benefit per option as displayed, e.g. '340 h · SGD 20k' -> 20."""
    table = at.dataframe[0].value.set_index("Option")
    return {name: float(cell.split("·")[1].split()[-1].rstrip("k").replace(",", ""))
            for name, cell in table["Saved / yr"].items()}


@pytest.fixture(scope="module")
def page():
    return run_page()


def test_page_renders_with_all_options(page):
    assert not page.exception, page.exception
    shown = set(page.dataframe[0].value["Option"])
    assert shown == {opt["name"] for opt in A.OPTIONS.values()}


def test_raising_the_rate_raises_every_benefit(page):
    before = median_hours_benefit(page)
    after = median_hours_benefit(run_page(rate=page.sidebar.slider[0].value + 30))
    assert all(after[name] > before[name] for name in before)


def test_full_model_under_five_seconds():
    start = time.perf_counter()
    model.run_all(model.default_baseline())
    assert time.perf_counter() - start < 5
