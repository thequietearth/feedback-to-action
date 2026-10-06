"""Business case page: which fix to fund, with assumptions you can move.

Layout and wording only. Numbers come from business_case/model.py; the
recommendation and comparison table are the same functions the brief uses.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for folder in ("app", "business_case"):
    if str(ROOT / folder) not in sys.path:
        sys.path.insert(0, str(ROOT / folder))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

import assumptions as A  # noqa: E402
import brief  # noqa: E402
import model  # noqa: E402
import settings  # noqa: E402

st.set_page_config(page_title="Business case", layout="wide")
cur = settings.CURRENCY


@st.cache_data
def baseline() -> model.Baseline:
    return model.default_baseline()


# --- Sidebar: the assumptions an exec is most likely to challenge ---------------

st.sidebar.header("Test the assumptions")
rate = st.sidebar.slider(f"Product ops hourly cost ({cur})",
                         settings.HOURLY_RATE_MIN, settings.HOURLY_RATE_MAX, settings.HOURLY_RATE)
eng_low, eng_mode, eng_high = A.ENGINEER_WEEKLY_COST
engineer = st.sidebar.slider(f"Engineer weekly cost, most likely ({cur})",
                             eng_low, eng_high, eng_mode, step=A.COST_SLIDER_STEP)
st.sidebar.caption("Most likely share of targeted effort each option saves:")
overrides = {}
for key, option in A.OPTIONS.items():
    low, mode, high = option["share_saved"]
    share = st.sidebar.slider(option["name"], float(low), float(high), float(mode),
                              step=A.SHARE_SLIDER_STEP, format="%.2f")
    overrides[key] = {"share_saved": (low, share, high), "engineer_weekly_cost": (eng_low, engineer, eng_high)}

b = baseline()
results = model.run_all(b, rate=rate, overrides=overrides)
hours = sum(b.hours_per_year.values())

st.title("Which fix to fund")
st.caption(
    f"Business case · product ops spends about {hours:,.0f} hours a year chasing "
    f"({brief.money(hours * rate)} at {cur} {rate}/hour) · {A.N_RUNS:,} simulated runs per option"
)

st.header("Recommendation")
st.info("\n\n".join(brief.recommendation(results)))

st.header("The options")
st.dataframe(brief.comparison_table(results), hide_index=True, width="stretch")
st.caption(f"Medians, with P10–P90 for net benefit. ROI is undiscounted over {A.HORIZON_YEARS} years and counts "
           f"product ops hours saved only. Each run draws every assumption from its (low, most likely, high) range.")

st.header("Value vs feasibility")
chart = pd.DataFrame({
    "option": [r.name for r in results],
    "feasibility (1–5)": [r.feasibility for r in results],
    f"median 3-year net ({cur})": [r.value for r in results],
})
st.scatter_chart(chart, x="feasibility (1–5)", y=f"median 3-year net ({cur})", color="option", size=200)
st.caption("Top right is the place to be: high value and easy to deliver. Feasibility scores and their "
           "reasons are in `business_case/assumptions.py`.")
with st.expander("Feasibility scores and reasons"):
    rows = [{"option": opt["name"], "criterion": A.CRITERIA_LABELS[c], "score": score, "why": why}
            for opt in A.OPTIONS.values() for c, (score, why) in opt["feasibility"].items()]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

st.header("What moves the result most")
cols = st.columns(len(results))
for col, r in zip(cols, results):
    with col:
        st.subheader(r.name)
        table = r.sensitivity.head(3).assign(
            range=lambda d: [f"{brief.money(min(lo, hi))} to {brief.money(max(lo, hi))}"
                             for lo, hi in zip(d.net_at_low, d.net_at_high)])
        st.dataframe(table[["label", "range"]].rename(columns={"label": "assumption", "range": "3-year net"}),
                     hide_index=True, width="stretch")
st.caption("Each assumption swung to its low and high value, with the others held at most likely.")

st.header("Not counted in the ROI")
st.markdown("\n".join(f"- {line}" for line in brief.uncounted(results)))
st.caption("Counts per year (medians). Provider and owner time, faster delivery and the time value "
           "of money are also left out.")
