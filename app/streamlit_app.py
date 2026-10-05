"""Discovery readout: why feedback stalls at Tessellate.

Run:  streamlit run app/streamlit_app.py

Layout and wording only. Every number on screen comes from analysis.py, and
every assumption from settings.py.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for folder in ("app", "generator"):
    if str(ROOT / folder) not in sys.path:
        sys.path.insert(0, str(ROOT / folder))

import streamlit as st  # noqa: E402

import analysis  # noqa: E402
import settings  # noqa: E402
from generate import build_log  # noqa: E402

st.set_page_config(page_title="Feedback discovery readout", layout="wide")


# --- Data and analysis (cached per dataset) -------------------------------------

@st.cache_data
def load_raw(dataset: str):
    if dataset == settings.DATASET_EFFECT_OFF:
        return analysis.prepare(build_log(detail_effect=False))
    return analysis.load_log(ROOT / settings.DATA_PATH)


@st.cache_data
def analyse(dataset: str) -> dict:
    """Everything that doesn't depend on a sidebar control."""
    raw = load_raw(dataset)
    log = analysis.remove_duplicates(raw)
    wait_rows = analysis.waits(log)
    stall_rows = analysis.stalls(wait_rows)
    delays = analysis.intake_delays(log)
    ageing = analysis.open_ageing(log)
    return {
        "log": log,
        "quality": analysis.quality_report(raw),
        "edges": analysis.directly_follows(log),
        "activity_counts": log["activity"].value_counts(),
        "variants": analysis.variants(log),
        "transitions": analysis.transition_waits(stall_rows),
        "parties": analysis.party_shares(stall_rows),
        "active_work": analysis.active_work(wait_rows),
        "ageing": ageing,
        "ageing_bands": analysis.ageing_bands(ageing),
        "intake": analysis.intake_medians(delays),
        "verdict": analysis.detail_verdict(delays),
        "clarification": analysis.clarification_rate(log),
        "resolution": analysis.resolution_by_detail(log),
    }


# --- Sidebar --------------------------------------------------------------------

st.sidebar.header("Controls")
dataset = st.sidebar.radio(
    "Dataset", [settings.DATASET_DEFAULT, settings.DATASET_EFFECT_OFF],
    help="'Detail effect off' regenerates the log with the link between detail level and "
         "clarification removed. Section 5 should then find no pattern.",
)
rate = st.sidebar.slider(
    f"Product ops hourly cost ({settings.CURRENCY})",
    settings.HOURLY_RATE_MIN, settings.HOURLY_RATE_MAX, settings.HOURLY_RATE,
)
min_edge = st.sidebar.slider(
    "Process map: hide steps seen fewer than (times)",
    1, settings.MAP_MIN_EDGE_COUNT_MAX, settings.MAP_MIN_EDGE_COUNT,
)
st.sidebar.caption("All data is synthetic. Assumptions: `app/settings.py`, `generator/config.py`.")

r = analyse(dataset)
q = r["quality"]
cur = settings.CURRENCY

st.title("Why feedback stalls at Tessellate")
st.caption(
    f"Discovery readout · {dataset} · {q['cases']:,} feedback items, "
    f"{q['first_event']:%d %b %Y} to {q['last_event']:%d %b %Y}"
)


# --- 1. Data quality ------------------------------------------------------------

st.header("1. Can we trust the data?")
st.info(
    f"Mostly, yes. {q['duplicate_rows']:,} duplicate rows ({q['duplicate_rows'] / q['events']:.1%}) were removed, "
    f"{q['sequence_breaks']:,} items ({q['sequence_breaks'] / q['cases']:.1%}) have a gap from a missing event, "
    f"and {q['open_cases']:,} were still open when the data was exported."
)
cols = st.columns(6)
cols[0].metric("Events", f"{q['events']:,}")
cols[1].metric("Items", f"{q['cases']:,}")
cols[2].metric("Duplicate rows", f"{q['duplicate_rows']:,}")
cols[3].metric("Missing first step", f"{q['bad_starts']:,}")
cols[4].metric("Sequence gaps", f"{q['sequence_breaks']:,}")
cols[5].metric("Out-of-hours events", f"{q['off_hours']:,}")
st.caption(
    "Duplicates are dropped from every section below. Missing events are counted, never filled in: "
    "inventing data would bias the analysis."
)


# --- 2. Process flow ------------------------------------------------------------

st.header("2. How work flows")
top = r["variants"]
st.info(
    f"No two journeys look alike: the {len(top)} most common paths cover only {top['share'].sum():.0%} of items, "
    f"because clarification loops, nudges and reassignments make each journey different."
)
st.graphviz_chart(analysis.to_dot(r["edges"], r["activity_counts"], min_edge), width="stretch")
st.caption(f"Each arrow shows how many times one step directly followed another. Arrows seen fewer than {min_edge} times are hidden.")
st.subheader("Most common paths")
st.dataframe(
    top.assign(share=top["share"].map("{:.1%}".format)), hide_index=True, width="stretch",
)


# --- 3. Stalls ------------------------------------------------------------------

st.header("3. Where items stall")
parties = r["parties"].set_index("waiting_on")
worst = r["transitions"].iloc[0]
provider_share = parties["share"].get("provider", 0.0)
st.info(
    f"The largest share of waiting is on the {parties.index[0]} ({parties['share'].iloc[0]:.0%} of all waiting time), "
    f"and {provider_share:.0%} is spent waiting for feedback providers to answer clarification questions. "
    f"The biggest single stall is '{worst['from_activity']} → {worst['to_activity']}': "
    f"{worst['total_h']:,.0f} working hours across {worst['times']:,} occurrences."
)
left, right = st.columns(2)
with left:
    st.subheader("Who the wait is on")
    st.bar_chart(parties["share"], horizontal=True, sort=False)
with right:
    st.subheader("Open items by age (working days)")
    st.bar_chart(r["ageing_bands"].set_index("age")["open_cases"], sort=False)
st.subheader("Biggest stalls")
st.dataframe(
    r["transitions"].round({"total_h": 0, "median_h": 1}), hide_index=True, width="stretch",
)
st.caption(
    f"Waits are working hours ({settings.WEEKMASK.split()[0]}–{settings.WEEKMASK.split()[-1]}, "
    f"{settings.WORKDAY_START_HOUR:02d}:00–{settings.WORKDAY_END_HOUR:02d}:00, UTC+{settings.UTC_OFFSET_HOURS}) "
    "between consecutive steps. Each wait is charged to whoever was expected to act next: "
    "e.g. the wait before a nudge counts against the owner. "
    f"Owners' active working time after 'In progress' ({r['active_work']['hours']:,.0f} hours, "
    f"{r['active_work']['share_of_time']:.0%} of all measured time) is work, not a stall, so it is left out here."
)


# --- 4. Cost of chasing ---------------------------------------------------------

st.header("4. What chasing costs")
cost = analysis.chasing_cost(r["log"], rate)
st.info(
    f"Product ops spent {cost['hours']:,.0f} hours chasing in {cost['weeks']:.0f} weeks: about "
    f"{cost['annual_hours']:,.0f} hours, or {cur} {cost['annual_cost']:,.0f}, a year at {cur} {rate}/hour."
)
cols = st.columns(3)
cols[0].metric("Chasing hours (period)", f"{cost['hours']:,.0f}")
cols[1].metric(f"Annual cost ({cur})", f"{cost['annual_cost']:,.0f}")
cols[2].metric(f"Misrouting rework, period ({cur})", f"{cost['rework_cost']:,.0f}")
st.dataframe(
    cost["by_activity"].round({"hours": 1, "cost": 0}), hide_index=True, width="stretch",
)
st.caption(
    f"Chasing = {', '.join(settings.CHASING_ACTIVITIES).lower()}. Annual figures scale the period's total "
    f"to {settings.WEEKS_PER_YEAR} weeks and assume steady volume. The hourly cost is an assumption; "
    "adjust it in the sidebar."
)


# --- 5. Detail level and delay --------------------------------------------------

st.header("5. Does vague feedback cause delay?")
v = r["verdict"]
if v.pattern:
    st.info(
        f"Yes. Low-detail items take {v.ratio:.1f}× as long to reach an owner as high-detail ones "
        f"({v.median_low:.1f} vs {v.median_high:.1f} working hours, median; p = {v.p_value:.4f})."
    )
else:
    st.info(
        f"No pattern. Low-detail items take {v.ratio:.2f}× as long to reach an owner as high-detail ones "
        f"(p = {v.p_value:.3f}), which does not meet the bar for a real effect."
    )
checks = [
    ("Right direction: low detail is slower", v.ratio > 1),
    (f"Unlikely to be chance: p < {settings.P_THRESHOLD}", v.p_value < settings.P_THRESHOLD),
    (f"Big enough to matter: at least {settings.MIN_EFFECT_RATIO}× as long", v.ratio >= settings.MIN_EFFECT_RATIO),
]
st.markdown("\n".join(f"- {'✅' if ok else '❌'} {label}" for label, ok in checks))
st.caption(
    f"A pattern needs all three. With the effect switched off, a plain two-sided significance test still "
    f"flags a false pattern, which is why the verdict also checks direction and size. "
    f"Test: one-sided permutation test on median intake delay, {settings.N_PERMUTATIONS:,} shuffles."
)
left, right = st.columns(2)
with left:
    st.subheader("Intake delay by detail level")
    st.dataframe(r["intake"].round({"median_h": 1}), hide_index=True, width="stretch")
    st.caption("Working hours from submission to routing or merge, median.")
with right:
    st.subheader("Items needing clarification")
    st.bar_chart(r["clarification"])
st.subheader("Context: time to resolution")
st.dataframe(r["resolution"].round({"median_h": 1}), hide_index=True, width="stretch")
st.caption(
    "Context only; it does not affect the verdict. Closed items only: open items have no end time and "
    "are counted in 'open_excluded'. Owner waits dominate this figure, which is why the verdict uses intake delay."
)
