# Design

## Context

Phase 1 left a committed log (`data/event_log.csv`, 15,296 events, 2,000 cases) and a generator with `build_log(seed, n_cases, detail_effect)`. The venv has pandas 3.0.6, numpy 2.5.3 and pytest 9.1.1. A dry run shows Streamlit 1.64 adds about 30 packages, including Altair for charts. See proposal.md for motivation and specs/discovery-app/spec.md for requirements.

A probe on the committed data (seed 42) shaped two decisions below:

| Dataset | Median intake delay, low / high detail | Ratio | Naive permutation p |
|---|---|---|---|
| Effect on | 16.4h / 6.9h | 2.36× | 0.000 |
| Effect off | 8.8h / 10.3h | 0.85× | **0.041** |

With the effect off, a plain two-sided test still crosses p < 0.05: a false positive, and in the wrong direction.

## Goals / Non-Goals

**Goals:** every number on screen comes from a tested function; the app reads any log in the Phase 1 schema; the readout can be presented without narration notes.

**Non-Goals:** reusable dashboard components, session state beyond two sidebar controls, styling.

## Layout

```
app/settings.py        all analysis assumptions
app/analysis.py        pure functions: DataFrame in, numbers/tables out
app/streamlit_app.py   layout and wording only; calls analysis.py
tests/test_analysis.py, tests/test_app.py
```

## Decisions

**1. Analysis is separate from display.** `analysis.py` has no Streamlit import, so every number can be unit-tested on small hand-built logs with known answers.
- *Alternative:* compute inside the Streamlit script.
- *Rejected:* untestable, and the numbers are the deliverable.

**2. Process map in pandas, drawn by Streamlit.** Directly-follows pairs come from shifting each case's activities by one row. The result is written as a Graphviz DOT string and rendered by `st.graphviz_chart` in the browser.
- *Alternative:* pm4py.
- *Rejected:* it is AGPL-3.0, adds about 15 packages, and its own rendering needs a separate Graphviz install. We only need a directly-follows graph.

**3. Waits in working hours.** Each wait is measured with numpy business-day counts plus clipping to 09:00–18:00.
- *Alternative:* calendar hours.
- *Rejected:* every Friday hand-off would look like a 64-hour stall. Working time is what product ops experiences, and it matches how the generator schedules work.

**4. Each wait is attributed by the *previous* activity.** After `Clarification requested`, the case waits on the provider. After `Routed to owner`, `Nudge sent` or similar, it waits on the owner. After submission, triage or a reply, it waits on product ops. A mapping in settings holds this.
- *Alternative:* attribute to whoever performs the next event.
- *Rejected:* a nudge is performed by product ops, but the wait before it was on the owner.
- *Revised during the build:* time after `In progress` was first charged to the owner as waiting. It is the owner actively working (28% of all measured time), and it made `In progress → Resolved` the headline "stall". It is now labelled "owner working" and reported separately. The true top stall is `Nudge sent → Nudge sent`: owners staying silent through repeated nudges.

**5. Verdict needs direction, significance and size.** The test is a one-sided permutation test (low detail slower than high) on the difference in medians, using 5,000 seeded shuffles, vectorised in numpy. "Pattern" requires p < 0.05 **and** a low/high ratio of at least 1.5×.
- *Alternative:* a two-sided Mann-Whitney test from scipy.
- *Rejected:* it adds a dependency, and the probe shows a p-value alone flags a false pattern.

**6. Verdict on intake delay; time to resolution shown as context.** Intake delay runs from submission to the first routing or merge, and it alone decides the verdict. Time to resolution by detail level is shown beside it, because an executive will ask, and is labelled with the number of open cases it leaves out.
- *Alternative:* base the verdict on time to resolution.
- *Rejected:* only closed cases have one (censoring bias), and owner-phase waits would drown the intake effect we're testing.

**7. Remove duplicates; never impute missing events.** Exact duplicate rows are dropped. Missing events are counted as sequence breaks and left alone.
- *Alternative:* infer missing events.
- *Rejected:* that would invent data we then analyse.

**8. The "effect off" dataset is generated in the app.** The app calls `build_log(detail_effect=False)`, cached with `st.cache_data`.
- *Alternative:* commit a second CSV.
- *Rejected:* a second 1.7 MB file could drift from the config. The cost is that the app imports the generator; a real deployment would not have that toggle.

**9. Annualise from the data.** Weeks covered = (last timestamp − first) / 7 days; annual = total × 52 / weeks.
- *Alternative:* read the window from generator config.
- *Rejected:* the app should work on any log in this schema.

**10. Findings are code-written sentences** (f-strings with the computed numbers). No LLM in this phase.

**11. Smoke test with Streamlit's built-in `AppTest`**, which runs the script headless and fails on any exception. It needs no extra dependency.

## Assumptions

All values live in `app/settings.py`, which is the source of truth.

| Assumption | Starting value |
|---|---|
| Hourly rate | SGD 60, product ops fully loaded |
| Chasing activities | Clarification requested, Nudge sent, Escalated |
| Rework activities | Reassigned |
| Working hours | Mon–Fri 09:00–18:00, UTC+08:00 |
| Waiting on provider | after Clarification requested |
| Waiting on owner | after Routed to owner, Reassigned, Nudge sent, Escalated, Owner acknowledged |
| Owner working (not a stall) | after In progress |
| Waiting on product ops | after Feedback submitted, Triaged, Clarification received |
| Verdict thresholds | p < 0.05, low/high ≥ 1.5× |
| Permutations / seed | 5,000 / 0 |
| Map minimum edge count | 20 (sidebar adjustable) |
| Variants listed | top 10 |

## Risks / Trade-offs

- **[A permutation p-value varies with the seed]** → The seed is fixed; with 5,000 shuffles the p-value's own error is about ±0.003, far from the threshold in both datasets.
- **[Working-hours logic is duplicated from the generator]** → It's deliberate: the app must not depend on generator internals to read a real export. A test checks the Friday → Monday case.
- **[The effect-on verdict is the result we planted]** → That's what the off-switch test is for. Both verdicts are tested.
- **[Streamlit changes between versions]** → Pin the exact version.

## Known limitations

- No public holidays in the working calendar.
- Intake delay excludes items still in clarification at the cut-off, so it slightly understates low-detail delay.
- Wait attribution is a simplification; some waits are shared.
- The test compares low against high only, with medium shown but not tested.
- Annualising assumes steady volume across the year.

## In a real deployment

- Use the client's working calendar, holidays and team time zones.
- Confirm the hourly rate with finance, and validate the waiting-on mapping with product ops before presenting costs.
- Run the app inside the client's environment on a pseudonymised export; nothing leaves their network.
- Check licensing before adding process-mining libraries; many legal teams block AGPL.
- Present the readout live to the head of product ops, then interview owners on the waits attributed to them.
