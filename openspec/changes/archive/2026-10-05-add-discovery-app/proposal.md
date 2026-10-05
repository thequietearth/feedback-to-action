# Proposal

## Why

**Roadmap phase 2.** We need a discovery readout that shows where feedback stalls, what chasing costs, and whether the core hypothesis holds: *unactionable feedback is what makes items stall.* It decides which fix Phase 3 builds a business case for.

## What Changes

- A local Streamlit app that tells the story top to bottom, each section opening with a plain-language finding:
  1. **Can we trust the data?** Duplicates, broken sequences, open cases.
  2. **How work flows:** a process map and the most common paths.
  3. **Where items stall:** waiting time by step, and who each wait is on (provider, product ops, or owner).
  4. **What chasing costs:** product ops hours on clarifications, nudges and escalations, in SGD, annualised.
  5. **Does detail level predict delay?** A verdict on intake delay with its evidence, time to resolution as context, and a toggle to rerun on the "effect off" dataset.
- The analysis lives in tested Python functions; the app only displays results.
- Process map built with pandas instead of pm4py (see design). CLAUDE.md is updated to record why.

## Who Benefits

- **Head of product ops:** evidence, not anecdote, to argue for fixing intake.
- **Product ops:** chasing work made visible and costed.
- **Owners:** waits are attributed to whoever was expected to act, so owners aren't blamed for time spent waiting on providers.

## Success Criteria

- `streamlit run app/streamlit_app.py` renders all five sections with no errors (automated smoke test).
- Effect on: the app reports a pattern. Effect off: it reports **no pattern**.
- Data quality counts match independent calculations (e.g. duplicate rows found = duplicate rows present).
- Cost of chasing reconciles exactly with summed handle time × hourly rate.
- Full analysis runs in under 5 seconds.

## Non-goals

- Public hosting (decided after review), file upload, filters beyond the readout.
- Conformance checking, forecasting, or any Jev or LLM use.
- UI polish beyond Streamlit defaults.

## Capabilities

### New Capabilities
- `discovery-app`: a readout app that analyses the event log for data quality, process flow, stalls, chasing cost and the detail-level hypothesis.

### Modified Capabilities
- None. The app reuses the generator to build the "effect off" dataset but changes none of its requirements.

## Impact

- New: `app/settings.py`, `app/analysis.py`, `app/streamlit_app.py`, tests.
- Updated: `requirements.txt`, `README.md`, CLAUDE.md (Phase 2 line).
- **New dependency (approved 2026-10-01):** `streamlit`, with no pm4py.
