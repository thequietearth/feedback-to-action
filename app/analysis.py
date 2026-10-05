"""Discovery analysis: pure functions, DataFrame in, numbers and tables out.

No Streamlit here, so every figure the readout shows can be unit-tested on a
small hand-built log with a known answer. All assumptions come from settings.py.
"""

from dataclasses import dataclass
from datetime import timedelta, timezone

import numpy as np
import pandas as pd

import settings

TZ = timezone(timedelta(hours=settings.UTC_OFFSET_HOURS))
MINUTES_PER_DAY = (settings.WORKDAY_END_HOUR - settings.WORKDAY_START_HOUR) * 60
MINUTES_PER_HOUR = 60


# --- 2. Loading -----------------------------------------------------------------

def prepare(log: pd.DataFrame) -> pd.DataFrame:
    """Put timestamps in local time and sort each case's events chronologically."""
    log = log.copy()
    if not isinstance(log["timestamp"].dtype, pd.DatetimeTZDtype):  # CSV text, not yet parsed
        log["timestamp"] = pd.to_datetime(log["timestamp"], format="ISO8601")
    log["timestamp"] = log["timestamp"].dt.tz_convert(TZ)
    return log.sort_values(["case_id", "timestamp"], kind="stable").reset_index(drop=True)


def load_log(path) -> pd.DataFrame:
    """Read an event log CSV (ISO 8601 timestamps with offset), keeping column order."""
    return prepare(pd.read_csv(path))


def remove_duplicates(log: pd.DataFrame) -> pd.DataFrame:
    """Drop exact duplicate rows. Missing events are never imputed."""
    return log.drop_duplicates().reset_index(drop=True)


# --- 3. Data quality --------------------------------------------------------------

def sequence_break_cases(log: pd.DataFrame) -> set[str]:
    """Cases where an activity appears more often than its prerequisite before it.

    E.g. a second `Clarification received` needs a second `Clarification requested`
    earlier in the case; if that request is missing, the case is flagged.
    """
    broken: set[str] = set()
    for activity, prerequisite in settings.REQUIRES_EARLIER.items():
        is_act = log["activity"] == activity
        is_pre = log["activity"] == prerequisite
        done_so_far = is_act.groupby(log["case_id"]).cumsum()                # including this row
        required_before = is_pre.groupby(log["case_id"]).cumsum() - is_pre   # strictly before this row
        bad = is_act & (done_so_far > required_before)
        broken |= set(log.loc[bad, "case_id"])
    return broken


def is_working_time(ts: pd.Series) -> pd.Series:
    local = ts.dt.tz_convert(TZ)
    minutes = local.dt.hour * MINUTES_PER_HOUR + local.dt.minute + local.dt.second / 60
    start = settings.WORKDAY_START_HOUR * MINUTES_PER_HOUR
    end = settings.WORKDAY_END_HOUR * MINUTES_PER_HOUR
    weekday = np.is_busday(local.dt.tz_localize(None).values.astype("datetime64[D]"),
                           weekmask=settings.WEEKMASK)
    return pd.Series(weekday, index=ts.index) & (minutes >= start) & (minutes <= end)


def open_case_ids(log: pd.DataFrame) -> pd.Index:
    """Cases with no end state (still in flight when the data was exported)."""
    ended = log.loc[log["activity"].isin(settings.END_ACTIVITIES), "case_id"].unique()
    cases = pd.Index(log["case_id"].unique())
    return cases[~cases.isin(ended)]


def quality_report(raw: pd.DataFrame) -> dict:
    """Counts describing how far the raw log can be trusted."""
    clean = remove_duplicates(raw)
    first = clean.groupby("case_id", sort=False)["activity"].first()
    return {
        "events": len(raw),
        "cases": raw["case_id"].nunique(),
        "duplicate_rows": int(raw.duplicated().sum()),
        "bad_starts": int((first != settings.START_ACTIVITY).sum()),
        "sequence_breaks": len(sequence_break_cases(clean)),
        "open_cases": len(open_case_ids(clean)),
        "off_hours": int((~is_working_time(raw["timestamp"])).sum()),
        "first_event": clean["timestamp"].min(),
        "last_event": clean["timestamp"].max(),
    }


# --- 4. Process flow --------------------------------------------------------------

def directly_follows(log: pd.DataFrame) -> pd.DataFrame:
    """Count each (A -> B) pair where B directly follows A within a case."""
    nxt = log.groupby("case_id", sort=False)["activity"].shift(-1)
    pairs = pd.DataFrame({"source": log["activity"], "target": nxt}).dropna()
    counts = pairs.value_counts().rename("count").reset_index()
    return counts.sort_values(["count", "source", "target"], ascending=[False, True, True], ignore_index=True)


def variants(log: pd.DataFrame, top: int = settings.TOP_VARIANTS) -> pd.DataFrame:
    """Most common complete paths through the process, with case counts and shares."""
    paths = log.groupby("case_id", sort=False)["activity"].agg(" → ".join)
    counts = paths.value_counts()
    table = pd.DataFrame({"path": counts.index, "cases": counts.values})
    table["share"] = table["cases"] / len(paths)
    return table.head(top)


def to_dot(edges: pd.DataFrame, activity_counts: pd.Series, min_count: int) -> str:
    """Graphviz DOT for the process map, hiding edges seen fewer than min_count times."""
    shown = edges[edges["count"] >= min_count]
    nodes = sorted(set(shown["source"]) | set(shown["target"]))
    top = shown["count"].max() if len(shown) else 1
    span = settings.EDGE_PENWIDTH_MAX - settings.EDGE_PENWIDTH_MIN
    lines = ["digraph process {", "  rankdir=TB;", '  node [shape=box, style="rounded"];']
    for node in nodes:
        lines.append(f'  "{node}" [label="{node}\\n({activity_counts.get(node, 0):,})"];')
    for row in shown.itertuples(index=False):
        width = settings.EDGE_PENWIDTH_MIN + span * row.count / top
        lines.append(f'  "{row.source}" -> "{row.target}" [label="{row.count:,}", penwidth={width:.1f}];')
    lines.append("}")
    return "\n".join(lines)


# --- 5. Stalls --------------------------------------------------------------------

def _working_minutes(ts: pd.Series, origin: np.datetime64) -> np.ndarray:
    """Working minutes from `origin` to each timestamp (nights and weekends skipped).

    Times before 09:00 count as 09:00; after 18:00 or at weekends, as the start
    of the next working day.
    """
    local = ts.dt.tz_convert(TZ).dt.tz_localize(None)
    days = local.values.astype("datetime64[D]")
    whole_days = np.busday_count(origin, days, weekmask=settings.WEEKMASK)
    minute = (local.dt.hour * MINUTES_PER_HOUR + local.dt.minute + local.dt.second / 60).to_numpy()
    minute = np.clip(minute - settings.WORKDAY_START_HOUR * MINUTES_PER_HOUR, 0, MINUTES_PER_DAY)
    minute = np.where(np.is_busday(days, weekmask=settings.WEEKMASK), minute, 0)
    return whole_days * MINUTES_PER_DAY + minute


def working_hours_between(start: pd.Series, end: pd.Series) -> pd.Series:
    """Working hours between paired timestamps (Mon-Fri, 09:00-18:00 local)."""
    if start.empty:
        return pd.Series(dtype=float, index=start.index)
    origin =min(start.min(), end.min()).tz_convert(TZ).tz_localize(None).to_datetime64().astype("datetime64[D]")
    minutes = _working_minutes(end, origin) - _working_minutes(start, origin)
    return pd.Series(minutes / MINUTES_PER_HOUR, index=start.index)


def waits(log: pd.DataFrame) -> pd.DataFrame:
    """One row per event after a case's first: how long it waited, and on whom."""
    prev = log.groupby("case_id", sort=False)[["activity", "timestamp"]].shift(1)
    has_prev = prev["activity"].notna()
    out = pd.DataFrame({
        "case_id": log.loc[has_prev, "case_id"],
        "from_activity": prev.loc[has_prev, "activity"],
        "to_activity": log.loc[has_prev, "activity"],
        "wait_h": working_hours_between(prev.loc[has_prev, "timestamp"], log.loc[has_prev, "timestamp"]),
    })
    out["waiting_on"] = out["from_activity"].map(settings.WAITING_ON).fillna(settings.UNATTRIBUTED)
    return out.reset_index(drop=True)


def stalls(wait_rows: pd.DataFrame) -> pd.DataFrame:
    """Waits only: drop time that is someone actively working (e.g. after In progress)."""
    return wait_rows[~wait_rows["waiting_on"].isin(settings.ACTIVE_WORK)].reset_index(drop=True)


def active_work(wait_rows: pd.DataFrame) -> dict:
    """Active working time, reported on its own rather than as a stall."""
    hours = wait_rows.loc[wait_rows["waiting_on"].isin(settings.ACTIVE_WORK), "wait_h"]
    return {"hours": float(hours.sum()), "median_h": float(hours.median()) if len(hours) else 0.0,
            "share_of_time": float(hours.sum() / wait_rows["wait_h"].sum()) if len(wait_rows) else 0.0}


def transition_waits(wait_rows: pd.DataFrame, top: int = settings.TOP_TRANSITIONS) -> pd.DataFrame:
    """Transitions ranked by total waiting time, with median wait and who it's on."""
    grouped = wait_rows.groupby(["from_activity", "to_activity", "waiting_on"])["wait_h"]
    table = grouped.agg(times="size", total_h="sum", median_h="median").reset_index()
    return table.sort_values("total_h", ascending=False, ignore_index=True).head(top)


def party_shares(wait_rows: pd.DataFrame) -> pd.DataFrame:
    """Each party's share of all waiting time (shares sum to 1)."""
    hours = wait_rows.groupby("waiting_on")["wait_h"].sum()
    table = pd.DataFrame({"hours": hours, "share": hours / hours.sum()})
    return table.sort_values("hours", ascending=False).rename_axis("waiting_on").reset_index()


def open_ageing(log: pd.DataFrame) -> pd.DataFrame:
    """Open cases: how long each has waited since its last event, up to the export time."""
    open_ids = open_case_ids(log)
    last = log[log["case_id"].isin(open_ids)].groupby("case_id", sort=False).tail(1)
    export_time = pd.Series(log["timestamp"].max(), index=last.index)
    table = pd.DataFrame({
        "case_id": last["case_id"],
        "last_activity": last["activity"],
        "waiting_on": last["activity"].map(settings.WAITING_ON).fillna(settings.UNATTRIBUTED),
        "waiting_h": working_hours_between(last["timestamp"], export_time),
    })
    table["waiting_days"] = table["waiting_h"] / (MINUTES_PER_DAY / MINUTES_PER_HOUR)
    return table.sort_values("waiting_h", ascending=False, ignore_index=True)


def ageing_bands(ageing: pd.DataFrame) -> pd.DataFrame:
    """Count open cases by age band, in working days (bands from settings)."""
    edges = [0, *settings.AGEING_BUCKETS_DAYS, np.inf]
    labels = [f"under {settings.AGEING_BUCKETS_DAYS[0]} day"] + [
        f"{lo}–{hi} days" for lo, hi in zip(settings.AGEING_BUCKETS_DAYS, settings.AGEING_BUCKETS_DAYS[1:])
    ] + [f"{settings.AGEING_BUCKETS_DAYS[-1]}+ days"]
    bands = pd.cut(ageing["waiting_days"], bins=edges, labels=labels, right=False)
    return bands.value_counts(sort=False).rename_axis("age").reset_index(name="open_cases")


# --- 6. Cost of chasing -----------------------------------------------------------

def weeks_covered(log: pd.DataFrame) -> float:
    span = log["timestamp"].max() - log["timestamp"].min()
    return span / pd.Timedelta(weeks=1)


def chasing_cost(log: pd.DataFrame, hourly_rate: float) -> dict:
    """Product ops chasing effort and its cost, plus misrouting rework, annualised."""
    chasing = log[log["activity"].isin(settings.CHASING_ACTIVITIES)]
    rework = log[log["activity"].isin(settings.REWORK_ACTIVITIES)]
    minutes = int(chasing["handle_time_min"].sum())
    hours = minutes / MINUTES_PER_HOUR
    cost = hours * hourly_rate
    weeks = weeks_covered(log)
    annual = settings.WEEKS_PER_YEAR / weeks
    by_activity = chasing.groupby("activity")["handle_time_min"].agg(events="size", minutes="sum").reset_index()
    by_activity["hours"] = by_activity["minutes"] / MINUTES_PER_HOUR
    by_activity["cost"] = by_activity["hours"] * hourly_rate
    rework_hours = rework["handle_time_min"].sum() / MINUTES_PER_HOUR
    return {
        "minutes": minutes,
        "hours": hours,
        "cost": cost,
        "weeks": weeks,
        "annual_hours": hours * annual,
        "annual_cost": cost * annual,
        "rework_hours": rework_hours,
        "rework_cost": rework_hours * hourly_rate,
        "by_activity": by_activity.sort_values("minutes", ascending=False, ignore_index=True),
    }


# --- 7. Detail-level verdict ------------------------------------------------------

def _first_time(log: pd.DataFrame, activities: list[str]) -> pd.Series:
    return log[log["activity"].isin(activities)].groupby("case_id")["timestamp"].first()


def _case_detail(log: pd.DataFrame) -> pd.Series:
    return log.groupby("case_id")["detail_level"].first()


def intake_delays(log: pd.DataFrame) -> pd.DataFrame:
    """Working hours from submission to first routing or merge, per case that has both."""
    start = _first_time(log, [settings.START_ACTIVITY])
    end = _first_time(log, settings.INTAKE_END_ACTIVITIES)
    both = pd.concat({"start": start, "end": end}, axis=1).dropna()
    both = both[both["end"] >= both["start"]]
    table = pd.DataFrame({
        "detail_level": _case_detail(log).reindex(both.index),
        "intake_h": working_hours_between(both["start"], both["end"]),
    })
    return table.rename_axis("case_id").reset_index()


def intake_medians(delays: pd.DataFrame) -> pd.DataFrame:
    """Median intake delay and case count per detail level (low, medium, high)."""
    grouped = delays.groupby("detail_level")["intake_h"]
    table = grouped.agg(median_h="median", cases="size").reindex(settings.DETAIL_LEVELS)
    return table.rename_axis("detail_level").reset_index()


def clarification_rate(log: pd.DataFrame) -> pd.Series:
    """Share of cases at each detail level with at least one clarification request."""
    asked = set(log.loc[log["activity"] == settings.CLARIFICATION_ACTIVITY, "case_id"])
    detail = _case_detail(log)
    rate = pd.Series(detail.index.isin(asked), index=detail.index).groupby(detail).mean()
    return rate.reindex(settings.DETAIL_LEVELS)


def permutation_p(low: np.ndarray, high: np.ndarray,
                  n: int = settings.N_PERMUTATIONS, seed: int = settings.PERMUTATION_SEED) -> float:
    """One-sided p-value that low-detail delays have a higher median than high-detail.

    Shuffle the detail labels n times; p is the share of shuffles whose median gap
    is at least as large as the real one. The +1s count the real split as one of
    the possible shuffles, so p is never exactly 0.
    """
    observed = np.median(low) - np.median(high)
    pooled = np.concatenate([low, high])
    rng = np.random.default_rng(seed)
    shuffled = rng.permuted(np.tile(pooled, (n, 1)), axis=1)
    gaps = np.median(shuffled[:, :len(low)], axis=1) - np.median(shuffled[:, len(low):], axis=1)
    return float((np.sum(gaps >= observed) + 1) / (n + 1))


@dataclass
class Verdict:
    median_low: float
    median_high: float
    ratio: float
    p_value: float
    n_low: int
    n_high: int
    pattern: bool


def decide(ratio: float, p_value: float) -> bool:
    """A pattern needs all three: right direction, unlikely to be chance, big enough to matter."""
    return ratio > 1 and p_value < settings.P_THRESHOLD and ratio >= settings.MIN_EFFECT_RATIO


def detail_verdict(delays: pd.DataFrame) -> Verdict:
    low = delays.loc[delays["detail_level"] == settings.DETAIL_LOW, "intake_h"].to_numpy()
    high = delays.loc[delays["detail_level"] == settings.DETAIL_HIGH, "intake_h"].to_numpy()
    median_low, median_high = float(np.median(low)), float(np.median(high))
    ratio = median_low / median_high if median_high > 0 else np.inf
    p_value = permutation_p(low, high)
    return Verdict(median_low, median_high, ratio, p_value, len(low), len(high), decide(ratio, p_value))


def resolution_by_detail(log: pd.DataFrame) -> pd.DataFrame:
    """Context only: median working hours to end state for closed cases, per detail level.

    Open cases have no end time, so they are left out and counted per level.
    """
    start = _first_time(log, [settings.START_ACTIVITY])
    end = _first_time(log, settings.END_ACTIVITIES)
    detail = _case_detail(log)
    closed = pd.concat({"start": start, "end": end}, axis=1).dropna()
    hours = working_hours_between(closed["start"], closed["end"])
    open_ids = open_case_ids(log)
    table = pd.DataFrame({
        "median_h": hours.groupby(detail.reindex(closed.index)).median(),
        "closed_cases": hours.groupby(detail.reindex(closed.index)).size(),
        "open_excluded": detail[detail.index.isin(open_ids)].value_counts(),
    }).reindex(settings.DETAIL_LEVELS)
    table["closed_cases"] = table["closed_cases"].fillna(0).astype(int)
    table["open_excluded"] = table["open_excluded"].fillna(0).astype(int)
    return table.rename_axis("detail_level").reset_index()
