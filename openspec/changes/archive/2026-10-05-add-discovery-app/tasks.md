# Tasks

## 1. Setup

- [x] 1.1 Install `streamlit` into `.venv` (approved 2026-10-01) and pin its exact version in `requirements.txt`; verify `python -c "import streamlit"` works and `pip install -r requirements.txt` reports nothing to change
- [x] 1.2 Create `app/` and add it to `pythonpath` in `pytest.ini`; verify the existing 53 tests still pass

## 2. Settings and loading

- [x] 2.1 Write `app/settings.py` with every value from the design's Assumptions table, commented; verify it imports without error
- [x] 2.2 Implement `load_log(path)` (parse ISO timestamps with offset, keep column order) and the exact-duplicate removal; verify with tests that timestamps are tz-aware and N planted duplicates are removed

## 3. Data quality

- [x] 3.1 Implement the data quality report (counts, duplicates, bad starts, sequence breaks, open cases, off-hours timestamps); verify with tests on a hand-built log that each count is exact, including a `Clarification received` with no request

## 4. Process flow

- [x] 4.1 Implement directly-follows edges with counts and the top variants with case counts and shares; verify with a hand-built log that edge counts and variant shares are exact
- [x] 4.2 Implement DOT output that hides edges below a minimum count; verify with a test that a low-count edge is absent and a high-count one present

## 5. Stalls

- [x] 5.1 Implement working hours between two timestamps (weekdays, 09:00–18:00); verify with tests: Friday 17:00 → Monday 10:00 = 2h, and a same-day wait is exact
- [x] 5.2 Implement waits per transition (total and median) and attribution by previous activity; verify with a test that the parties' shares sum to 100% and a hand-built wait lands on the right party
- [x] 5.3 Implement the ageing view for open cases (working hours since last event, up to the last timestamp in the log); verify with a test on a hand-built open case
- [x] 5.4 Keep active work separate: label time after `In progress` as "owner working", exclude it from stall rankings and party shares, and report it on its own; verify with a test that an `In progress` → `Resolved` wait is in the active-work figure and not in the stalls

## 6. Cost of chasing

- [x] 6.1 Implement chasing hours, cost, annualised cost and rework hours; verify with a test that cost equals (summed minutes / 60) × rate exactly, and annualisation uses the weeks covered

## 7. Detail-level verdict

- [x] 7.1 Implement intake delay per case and clarification rate per detail level; verify with a hand-built test case
- [x] 7.2 Implement the one-sided seeded permutation test and the verdict rule; verify with tests: default dataset gives "pattern", effect-off dataset gives "no pattern", and a significant-but-small difference gives "no pattern"
- [x] 7.3 Implement time to resolution per detail level for closed cases, with open cases excluded and counted per level; verify with a hand-built log that an open case is excluded and counted, and that the verdict is unchanged

## 8. The app

- [x] 8.1 Build `app/streamlit_app.py`: sidebar (dataset, hourly rate, minimum edge count), five sections in order, each opening with a computed finding; cache loading and analysis; verify `streamlit run app/streamlit_app.py` opens and shows all sections
- [x] 8.2 Add `AppTest` smoke tests for both datasets (no exceptions, five section headers present, findings differ between datasets); verify they pass
- [x] 8.3 Add a test that the full analysis of the default dataset runs in under 5 seconds; verify all tests pass

## 9. Documentation

- [x] 9.1 Update CLAUDE.md's Phase 2 line (pandas process map, why pm4py was dropped) and its Commands section; verify the commands run as written
- [x] 9.2 Update the README memo with the Phase 2 findings (stalls, chasing cost, both verdicts) and the false-positive story; verify the documented commands run as written
