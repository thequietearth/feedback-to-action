# Design

## Context

Phase 2's `app/analysis.py` already computes chasing hours per activity and annualises them. At default settings the annual baseline is:

| Baseline (per year) | Value |
|---|---|
| Clarification requests (product ops) | 361 hours |
| Nudges | 616 hours |
| Escalations | 64 hours |
| Items | 4,129 |
| Items lost after an unanswered clarification | 223 |

The project rate is SGD 60/hour (`app/settings.py`). No new dependencies: numpy covers the simulation, Streamlit the page, and GitHub renders Mermaid charts in Markdown natively. See proposal.md for motivation and specs/business-case/spec.md for requirements.

## Goals / Non-Goals

**Goals:** one arithmetic function used everywhere; every number in the brief traceable to an assumption or the log; a result that can come out against AI without anyone changing code.

**Non-Goals:** combined packages, discounting, portfolio optimisation.

## Layout

```
business_case/assumptions.py   ranges, costs, feasibility scores and rationale, weights, seed
business_case/model.py         baseline, deterministic calc, simulation, sensitivity, scoring
business_case/brief.py         writes docs/exec_brief.md (run as a script)
app/pages/1_Business_case.py   Streamlit page (Streamlit lists files in app/pages/ automatically)
```

## Decisions

**1. One deterministic function, reused.** `evaluate(inputs)` computes benefit, cost, payback and ROI for one set of input values. It works on numpy arrays, so the simulation calls it once with 10,000 draws per input. The sensitivity view calls it with low/high swings, and the test calls it with collapsed ranges.
- *Alternative:* separate code for the simulation and the sensitivity view.
- *Rejected:* two copies of the arithmetic can drift. "Collapsed ranges equal the hand calculation" is only a meaningful test if they share code.

**2. Triangular distributions.** Each input is (low, most likely, high), which is how people naturally estimate.
- *Alternative:* PERT or normal distributions.
- *Rejected:* PERT is smoother but harder to explain. A normal distribution can go negative and is symmetric, while estimates like build time are skewed.

**3. Hours saved are the only benefit; simple 3-year ROI.** These were your choices: conservative and defensible. ROI = (3 × annual benefit − total 3-year cost) ÷ total 3-year cost, undiscounted. Payback = build cost ÷ (annual net benefit ÷ 12), and "never" when net benefit ≤ 0.
- *Alternative:* NPV, or putting a dollar value on rescued items.
- *Rejected:* both rest on assumptions finance would challenge (discount rate, value per item). Outcomes are reported as counts instead.

**4. Sensitivity by one-at-a-time swings.** Each input is set to low and then high, with the others held at most likely, and inputs are ranked by the swing in 3-year net benefit.
- *Alternative:* rank correlation across the simulation draws.
- *Rejected:* swings are what an exec can read ("if the effect is low, we lose SGD X"). The limitation is that this misses interactions between inputs.

**5. Options are compared, not added.** The intake form and the AI check draw on the same pool (clarification effort), so their savings can't be summed. Follow-through draws on a separate pool (nudges and escalations). The brief says that follow-through can be combined with either, but it does not model combinations.

**6. Fixed value axis for the chart.** The value × feasibility chart plots median 3-year net benefit on a fixed SGD scale set in the assumptions, not rescaled between options. Rescaling would always push the weakest option to zero, even if it pays back. The brief uses a Mermaid quadrant chart; the app uses an Altair scatter in SGD.

**7. The brief is generated and tested.** `brief.py` builds the Markdown from model results with f-strings. Recommendation sentences are chosen by rules, such as ranking by median net benefit, or "does not pay back on hours alone" when P(ROI > 0) < 50%. A test regenerates the brief and compares it byte-for-byte with the committed file, so a changed assumption with a stale brief fails CI.

**8. A Streamlit page, not a new app.** A file in `app/pages/` becomes a second page with sidebar navigation. It reuses the analysis for the baseline.
- *Cost:* Streamlit then labels the main page "streamlit app" in the navigation. Renaming it would mean restructuring the Phase 2 entry point, so the label is accepted.

**9. A shared hourly rate.** The product ops rate is read from `app/settings.py`, so the readout and the business case can't disagree. Engineer cost lives in the business case assumptions.

## Assumptions

All values live in `business_case/assumptions.py`, which is the source of truth. Ranges are (low / most likely / high).

| Input | AI intake check | Structured form | Owner follow-through |
|---|---|---|---|
| Effort pool reduced | Clarification requests | Clarification requests | Nudges + escalations |
| Share of pool saved | 40 / 60 / 80% | 15 / 30 / 45% | 30 / 50 / 70% |
| Build (engineer-weeks) | 4 / 6 / 10 | 1 / 1.5 / 3 | 3 / 5 / 8 |
| Maintenance (% of build per year) | 15 / 20 / 30% | 5 / 10 / 15% | 10 / 15 / 25% |
| Run cost (SGD per year) | 500 / 1,500 / 3,000 | 0 | 300 / 1,000 / 2,000 |
| Review of medium-confidence items | 15 / 25 / 40% of items × 1 / 2 / 4 min | none | none |
| Items rescued (share of lost items) | 30 / 50 / 70% | 10 / 20 / 35% | none |

Shared: engineer cost SGD 2,800 / 3,300 / 4,000 per week (fully loaded); 3-year horizon; 10,000 runs; seed 0; value axis SGD −50,000 to 100,000.

**Feasibility** (1 = hard, 5 = easy). Weights: complexity 25%, data and integration 25%, adoption 25%, risk 15%, time to value 10%.

| Criterion | AI intake | Form | Follow-through |
|---|---|---|---|
| Technical complexity | 2: classifier + LLM + confidence gating | 5: form fields | 3: scheduling and digests |
| Data and integration | 3: needs feedback text at submission | 5: none | 4: uses existing tracker fields |
| Adoption | 3: providers answer while engaged | 2: rigid forms get junk or deter submissions | 3: owners may ignore digests |
| Risk | 3: wrong or annoying questions | 4: low | 4: no escalation, soft levers only |
| Time to value | 2: weeks plus tuning | 5: days | 4: weeks |

**Hand calculation at the most likely values:** AI intake has a 3-year ROI of −8% (does not pay back on hours alone), the form +203%, and follow-through +127%. *(Corrected during the build: the planning estimate for the form, about +250%, left out its maintenance cost.)* The simulated medians come out lower (−21%, +145%, +103%) because the cost ranges are right-skewed: build effort can overrun more than it can underrun.

## Risks / Trade-offs

- **[The result goes against the AI option the project is about to build]** → That is a legitimate finding. The brief will say what the AI check rests on (rescued items, faster intake), and Phase 5 tests those outcomes.
- **[Assumed effect sizes drive everything]** → The sensitivity view shows exactly how much, and the app sliders let an exec test their own numbers.
- **[False precision]** → Results are shown as ranges (P10–P90), and costs are rounded in the brief.
- **[The brief drifts from the model]** → The byte-identical test.

## Known limitations

- Effect sizes are assumptions, not measurements; Phase 5 measures the AI check's real effect.
- Combinations aren't modelled, and the intake form's effect on submission volume isn't modelled.
- Simple ROI ignores the time value of money.
- Provider and owner time is not counted, only product ops time.
- Feasibility scores are analyst judgement, written down so they can be challenged.

## In a real deployment

- Replace assumed costs with real engineering estimates and vendor pricing, and confirm the hourly rate with finance.
- Run a short workshop with the head of product ops, an owner and an engineer to challenge the feasibility scores before presenting them.
- Pilot the cheapest option first and measure its real effect before funding the next.
- Present ranges and the sensitivity view, not just the median; agree in advance which result would change the decision.
