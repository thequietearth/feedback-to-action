# Tasks

## 1. Setup

- [x] 1.1 Create `business_case/`, `docs/` and `app/pages/`, and add `business_case` to `pythonpath` in `pytest.ini`; verify the existing 83 tests still pass

## 2. Assumptions

- [x] 2.1 Write `business_case/assumptions.py` with every value from the design's Assumptions and Feasibility tables, including a rationale string for each feasibility score; verify it imports
- [x] 2.2 Add tests that every range is ordered low ≤ most likely ≤ high, shares lie in [0, 1], scores lie in 1–5 with a non-empty rationale, and feasibility weights sum to 1; verify they pass

## 3. Baseline

- [x] 3.1 Implement the baseline from the event log (annual hours per chasing activity, annual items, annual items lost after an unanswered clarification) using `app/analysis.py`; verify with a test that annual chasing hours equal the readout's `annual_hours`

## 4. Deterministic calculation

- [x] 4.1 Implement `evaluate()` for array inputs: annual benefit, annual cost, payback months ("never" as infinity when net ≤ 0) and simple 3-year ROI; verify with a hand-calculated test case and a test that zero hours saved gives zero benefit and negative ROI
- [x] 4.2 Implement the uncounted outcomes (items rescued, clarification rounds avoided, nudges avoided per year); verify with a hand-calculated test

## 5. Simulation

- [x] 5.1 Implement seeded triangular sampling and the summary (P10/P50/P90, P(payback ≤ 12 months), P(ROI > 0)); verify with tests that the same seed gives identical results and collapsed ranges reproduce `evaluate()` exactly

## 6. Scoring and sensitivity

- [x] 6.1 Implement weighted feasibility scores, value (median 3-year net benefit) and the ranking; verify with a test that all-5 scores give 5 and weights are applied correctly
- [x] 6.2 Implement one-at-a-time sensitivity swings, ranked largest first; verify with tests that the order is descending and an input with a collapsed range has zero swing

## 7. Exec brief

- [x] 7.1 Implement `business_case/brief.py` writing `docs/exec_brief.md`: rule-based recommendation, comparison table, Mermaid quadrant chart, what each option rests on, what isn't counted, next steps; verify with a test that an option with P(ROI > 0) below 50% is described as not paying back on hours alone
- [x] 7.2 Generate and commit `docs/exec_brief.md`; verify with a test that regenerating gives a byte-identical file and that the brief renders as one page (under 600 words)

## 8. App page

- [x] 8.1 Build `app/pages/1_Business_case.py` with sliders (hourly rate, engineer weekly cost, each option's most likely effect), comparison table, value × feasibility scatter, sensitivity ranking and uncounted outcomes; verify `streamlit run app/streamlit_app.py` shows the page in navigation
- [x] 8.2 Add `AppTest` tests: the page renders with no errors and shows all three options, and raising the hourly rate raises every option's median annual benefit; verify they pass
- [x] 8.3 Add a test that the full model (simulation and sensitivity for all options) runs in under 5 seconds; verify all tests pass

## 9. Documentation

- [x] 9.1 Update CLAUDE.md's Phase 3 line (what was built, key decisions) and its Commands section; verify the commands run as written
- [x] 9.2 Update the README memo with the Phase 3 findings and a link to the brief; verify the documented commands run as written
