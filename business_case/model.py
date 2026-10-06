"""Business case model: baseline, one shared calculation, simulation, scoring.

`evaluate()` is the only place the money arithmetic lives. The simulation calls
it with 10,000 draws per input, the sensitivity view with low/high swings, and
the tests with collapsed ranges, so all three always agree.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

import analysis
import assumptions as A
import settings

ROOT = Path(__file__).resolve().parent.parent
INPUTS = list(A.INPUT_LABELS)   # fixed order, so seeded draws are reproducible
MINUTES_PER_HOUR = 60


# --- 3. Baseline --------------------------------------------------------------

@dataclass(frozen=True)
class Baseline:
    hours_per_year: dict          # chasing activity -> product ops hours per year
    events_per_year: dict         # chasing activity -> events per year
    items_per_year: float
    lost_per_year: float          # closed as stale straight after an unanswered clarification
    weeks: float


def baseline_from_log(log: pd.DataFrame) -> Baseline:
    """Annual baseline from a de-duplicated event log, via the discovery analysis."""
    cost = analysis.chasing_cost(log, settings.HOURLY_RATE)
    per_year = settings.WEEKS_PER_YEAR / cost["weeks"]
    by_activity = cost["by_activity"].set_index("activity")
    wait_rows = analysis.waits(log)
    lost = ((wait_rows["from_activity"] == settings.CLARIFICATION_ACTIVITY)
            & (wait_rows["to_activity"] == "Closed as stale")).sum()
    return Baseline(
        hours_per_year=(by_activity["hours"] * per_year).to_dict(),
        events_per_year=(by_activity["events"] * per_year).to_dict(),
        items_per_year=log["case_id"].nunique() * per_year,
        lost_per_year=float(lost * per_year),
        weeks=cost["weeks"],
    )


def default_baseline() -> Baseline:
    return baseline_from_log(analysis.remove_duplicates(analysis.load_log(ROOT / settings.DATA_PATH)))


def pool_totals(option: dict, baseline: Baseline) -> tuple[float, float]:
    """(hours per year, events per year) in the effort pool this option targets."""
    hours = sum(baseline.hours_per_year.get(a, 0.0) for a in option["pool"])
    events = sum(baseline.events_per_year.get(a, 0.0) for a in option["pool"])
    return hours, events


# --- 4. The one calculation -----------------------------------------------------

def evaluate(v: dict, option: dict, baseline: Baseline, rate: float) -> dict:
    """Benefit, cost, payback, ROI and uncounted outcomes for input values `v`.

    Every value in `v` may be a number or a numpy array (one entry per run).
    Benefit is product ops hours saved x hourly rate, and nothing else.
    """
    pool_hours, pool_events = pool_totals(option, baseline)
    hours_saved = v["share_saved"] * pool_hours
    benefit = hours_saved * rate
    build = v["build_weeks"] * v["engineer_weekly_cost"]
    review_hours = v["review_share"] * baseline.items_per_year * v["review_minutes"] / MINUTES_PER_HOUR
    annual_cost = v["maintenance_share"] * build + v["run_cost"] + review_hours * rate
    net = benefit - annual_cost
    with np.errstate(divide="ignore", invalid="ignore"):
        payback = np.where(net > 0, build / (net / A.MONTHS_PER_YEAR), np.inf)
        total_cost = build + A.HORIZON_YEARS * annual_cost
        net_horizon = A.HORIZON_YEARS * benefit - total_cost
        roi = np.where(total_cost > 0, net_horizon / total_cost, np.nan)
    return {
        "hours_saved": hours_saved,
        "benefit": benefit,
        "build_cost": build,
        "annual_cost": annual_cost,
        "payback_months": payback,
        "net_3yr": net_horizon,
        "roi_3yr": roi,
        # Reported as counts only: no dollar value is put on these.
        "items_rescued": v["rescue_share"] * baseline.lost_per_year,
        "events_avoided": v["share_saved"] * pool_events,
    }


# --- 5. Simulation --------------------------------------------------------------

def ranges(option: dict, overrides: dict | None = None) -> dict:
    """The option's (low, most likely, high) for every input, with any overrides applied."""
    r = {name: option[name] for name in INPUTS if name != "engineer_weekly_cost"}
    r["engineer_weekly_cost"] = A.ENGINEER_WEEKLY_COST
    r.update(overrides or {})
    return r


def most_likely(option: dict, overrides: dict | None = None) -> dict:
    return {name: rng[1] for name, rng in ranges(option, overrides).items()}


def draw(rng: np.random.Generator, low: float, mode: float, high: float, n: int) -> np.ndarray:
    """Triangular draws; numpy rejects low == high, so a collapsed range is a constant."""
    if low == high:
        return np.full(n, float(mode))
    return rng.triangular(low, mode, high, n)


def simulate(option: dict, baseline: Baseline, rate: float, n: int = A.N_RUNS,
             seed: int = A.SEED, overrides: dict | None = None) -> dict:
    """Run `n` seeded draws of every input through evaluate().

    Each option starts from the same seed, so shared inputs (engineer cost) get
    the same draws across options and the comparison is like-for-like.
    """
    rng = np.random.default_rng(seed)
    r = ranges(option, overrides)
    values = {name: draw(rng, *r[name], n) for name in INPUTS}
    return evaluate(values, option, baseline, rate)


def summarise(runs: dict) -> dict:
    """Percentiles of the key outputs, plus the two headline probabilities."""
    out = {}
    for metric in ("hours_saved", "benefit", "build_cost", "annual_cost", "net_3yr", "roi_3yr", "payback_months",
                   "items_rescued", "events_avoided"):
        out[metric] = dict(zip(A.PERCENTILES, np.percentile(runs[metric], A.PERCENTILES)))
    out["p_payback_target"] = float(np.mean(runs["payback_months"] <= A.PAYBACK_TARGET_MONTHS))
    out["p_roi_positive"] = float(np.mean(runs["roi_3yr"] > 0))
    return out


# --- 6. Scoring and sensitivity ---------------------------------------------------

def feasibility_score(option: dict) -> float:
    return sum(A.FEASIBILITY_WEIGHTS[c] * score for c, (score, _) in option["feasibility"].items())


def value_position(value: float) -> float:
    """Where a median 3-year net benefit sits on the fixed value axis, from 0 to 1."""
    low, high = A.VALUE_AXIS
    return float(np.clip((value - low) / (high - low), 0, 1))


def sensitivity(option: dict, baseline: Baseline, rate: float, overrides: dict | None = None) -> pd.DataFrame:
    """Swing each input to low and high (others at most likely); rank by swing in 3-year net."""
    r = ranges(option, overrides)
    base = most_likely(option, overrides)
    rows = []
    for name in INPUTS:
        low, _, high = r[name]
        at_low = float(evaluate({**base, name: low}, option, baseline, rate)["net_3yr"])
        at_high = float(evaluate({**base, name: high}, option, baseline, rate)["net_3yr"])
        rows.append({"input": name, "label": A.INPUT_LABELS[name], "low": low, "high": high,
                     "net_at_low": at_low, "net_at_high": at_high, "swing": abs(at_high - at_low)})
    return pd.DataFrame(rows).sort_values("swing", ascending=False, ignore_index=True)


@dataclass
class OptionResult:
    key: str
    name: str
    pool: tuple                   # activities in the effort pool it targets
    pool_label: str
    rests_on: str
    summary: dict
    feasibility: float
    value: float                  # median 3-year net benefit
    sensitivity: pd.DataFrame


def run_all(baseline: Baseline, rate: float = settings.HOURLY_RATE, n: int = A.N_RUNS,
            seed: int = A.SEED, overrides: dict | None = None) -> list[OptionResult]:
    """Simulate, score and rank every option (highest value first).

    `overrides` maps option key -> {input: (low, most likely, high)}.
    """
    results = []
    for key, option in A.OPTIONS.items():
        opt_overrides = (overrides or {}).get(key)
        summary = summarise(simulate(option, baseline, rate, n, seed, opt_overrides))
        results.append(OptionResult(
            key=key, name=option["name"], pool=tuple(option["pool"]), pool_label=option["pool_label"], rests_on=option["rests_on"],
            summary=summary, feasibility=feasibility_score(option), value=summary["net_3yr"][50],
            sensitivity=sensitivity(option, baseline, rate, opt_overrides),
        ))
    return sorted(results, key=lambda res: res.value, reverse=True)
