"""Generate the one-page exec brief from the business case model.

Run:  python business_case/brief.py      (writes docs/exec_brief.md)

Every number comes from the model at default settings, and the recommendation
sentences are chosen by rules from the results, so the brief can never say
something the model doesn't. A test regenerates it and compares byte-for-byte.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for folder in ("app", "business_case"):
    if str(ROOT / folder) not in sys.path:
        sys.path.insert(0, str(ROOT / folder))

import math  # noqa: E402

import pandas as pd  # noqa: E402

import assumptions as A  # noqa: E402
import model  # noqa: E402
import settings  # noqa: E402

BRIEF_PATH = ROOT / "docs" / "exec_brief.md"
CUR = settings.CURRENCY


# --- Formatting -----------------------------------------------------------------

def money(x: float) -> str:
    """Rounded to thousands, e.g. 'SGD 31k' or '−SGD 11k'."""
    return f"{'−' if x < 0 else ''}{CUR} {abs(x) / 1_000:,.0f}k"


def months(x: float) -> str:
    return "never" if math.isinf(x) else f"{x:.0f} months"


def pct(x: float) -> str:
    return f"{'−' if x < 0 else ''}{abs(x):.0%}"


# --- Content shared with the app page ----------------------------------------------

def pays_back(r: model.OptionResult) -> bool:
    return r.summary["p_roi_positive"] >= A.P_ROI_POSITIVE_MIN


def recommendation(results: list[model.OptionResult]) -> list[str]:
    """Rule-based recommendation sentences; results are ranked by value already."""
    paying = [r for r in results if pays_back(r)]
    lines = []
    if paying:
        best = paying[0]
        s = best.summary
        lines.append(
            f"**Fund {best.name} first.** It saves about {s['hours_saved'][50]:,.0f} product ops hours a year "
            f"and returns a median {money(s['net_3yr'][50])} over three years "
            f"({money(s['net_3yr'][10])} to {money(s['net_3yr'][90])}), paying back in about "
            f"{months(s['payback_months'][50])}."
        )
        quick = min(paying, key=lambda r: r.summary["build_cost"][50])
        if quick is not best:
            together = (f"It targets {quick.pool_label}, not {best.pool_label}, so the two can run together."
                        if not set(quick.pool) & set(best.pool)
                        else f"It competes with {best.name} for the same work, so choose one.")
            lines.append(
                f"**{quick.name} is the quick win:** the cheapest to build (about "
                f"{money(quick.summary['build_cost'][50])}), paying back in about "
                f"{months(quick.summary['payback_months'][50])}. {together}"
            )
    else:
        lines.append("**No option pays back on product ops hours alone.**")
    for r in results:
        if not pays_back(r):
            lines.append(
                f"**{r.name} does not pay back on hours alone:** only a {pct(r.summary['p_roi_positive'])} "
                f"chance of a positive 3-year return. Its case rests on {r.rests_on}, which this ROI "
                f"does not count."
            )
    return lines


def comparison_table(results: list[model.OptionResult]) -> pd.DataFrame:
    rows = []
    for r in results:
        s = r.summary
        rows.append({
            "Option": r.name,
            "Targets": r.pool_label,
            "Saved / yr": f"{s['hours_saved'][50]:,.0f} h · {money(s['benefit'][50])}",
            "3-year net (P10 – P50 – P90)":
                f"{money(s['net_3yr'][10])} – {money(s['net_3yr'][50])} – {money(s['net_3yr'][90])}",
            "3-year ROI": pct(s["roi_3yr"][50]),
            "Payback": months(s["payback_months"][50]),
            "Chance ROI > 0": pct(s["p_roi_positive"]),
            "Feasibility (1–5)": f"{r.feasibility:.1f}",
        })
    return pd.DataFrame(rows)


def uncounted(results: list[model.OptionResult]) -> list[str]:
    lines = []
    for r in results:
        s = r.summary
        rescued = (f"about {s['items_rescued'][50]:,.0f} lost items rescued and "
                   if s["items_rescued"][50] > 0 else "")
        lines.append(f"**{r.name}:** {rescued}{s['events_avoided'][50]:,.0f} {r.pool_label} avoided a year.")
    return lines


# --- The brief ------------------------------------------------------------------------

def markdown_table(df: pd.DataFrame) -> str:
    header = "| " + " | ".join(df.columns) + " |"
    rule = "|" + "|".join("---" for _ in df.columns) + "|"
    rows = ["| " + " | ".join(str(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join([header, rule, *rows])


def quadrant(results: list[model.OptionResult]) -> str:
    low, high = A.VALUE_AXIS
    points = [f"    {r.name}: [{(r.feasibility - 1) / 4:.2f}, {model.value_position(r.value):.2f}]" for r in results]
    return "\n".join([
        "```mermaid",
        "quadrantChart",
        "    title Value vs feasibility",
        "    x-axis Harder to deliver --> Easier to deliver",
        f"    y-axis Lower value --> Higher value",
        "    quadrant-1 Do first",
        "    quadrant-2 Worth the effort",
        "    quadrant-3 Deprioritise",
        "    quadrant-4 Quick wins",
        *points,
        "```",
        f"*Value: median 3-year net benefit, fixed scale {money(low)} to {money(high)}. "
        f"Feasibility: weighted score of five criteria.*",
    ])


def build_brief(baseline: model.Baseline, results: list[model.OptionResult]) -> str:
    hours = sum(baseline.hours_per_year.values())
    rests = []
    for r in results:
        top = r.sensitivity.iloc[0]
        lo, hi = sorted([top.net_at_low, top.net_at_high])
        rests.append(f"- **{r.name}** rests on {r.rests_on}. Most sensitive to the {top.label}: "
                     f"{money(lo)} to {money(hi)} over three years.")
    best = next((r for r in results if pays_back(r)), results[0])
    next_steps = [
        "1. Confirm costs with engineering and finance; test the feasibility scores with product ops and an owner.",
        f"2. Pilot **{best.name}** and measure the real reduction in {best.pool_label} against the "
        f"{pct(A.OPTIONS[best.key]['share_saved'][1])} assumed.",
    ]
    for r in results:
        if not pays_back(r):
            next_steps.append(f"{len(next_steps) + 1}. Prototype **{r.name}** cheaply and measure the outcomes "
                              f"its case rests on before funding a full build.")
    sections = [
        "# Exec brief: fixing stalled feedback at Tessellate",
        f"*Generated by `business_case/brief.py` from {baseline.weeks:.0f} weeks of event data. "
        f"Synthetic data; costs are assumptions. Do not edit by hand.*",
        f"**Today**, product ops spends about {hours:,.0f} hours a year chasing feedback "
        f"({money(hours * settings.HOURLY_RATE)} at {CUR} {settings.HOURLY_RATE}/hour).",
        "## Recommendation",
        "\n\n".join(recommendation(results)),
        "## The options",
        markdown_table(comparison_table(results)),
        f"*Medians of {A.N_RUNS:,} simulated runs. ROI: undiscounted, {A.HORIZON_YEARS} years, "
        f"product ops hours only.*",
        "## Value vs feasibility",
        quadrant(results),
        "## What each option rests on",
        "\n".join(rests),
        "## Not counted in the ROI",
        "\n".join(f"- {line}" for line in uncounted(results))
        + "\n- Provider and owner time, faster delivery, and the time value of money.",
        "## Next steps",
        "\n".join(next_steps),
    ]
    return "\n\n".join(sections) + "\n"


def main() -> None:
    baseline = model.default_baseline()
    text = build_brief(baseline, model.run_all(baseline))
    BRIEF_PATH.parent.mkdir(parents=True, exist_ok=True)
    BRIEF_PATH.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {BRIEF_PATH} ({len(text.split())} words)")


if __name__ == "__main__":
    main()
