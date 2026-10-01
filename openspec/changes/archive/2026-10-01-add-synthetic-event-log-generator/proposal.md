# Proposal

## Why

**Roadmap phase 1.** Before we can show where feedback stalls, we need an event log to analyse. In a real engagement this would be an export from the ticketing tool; here we generate a synthetic one that reproduces the problem statement: *feedback arrives unactionable, and product ops pays the cost of chasing it.* Every later phase (discovery, business case, agent, evaluation) runs on this data.

## What Changes

- A generator that simulates each feedback item through its lifecycle, from submission through clarification, routing, nudges and rare human escalation to an end state.
- All assumptions live in one config file.
- An on/off switch for the assumed link between detail level and clarification loops. With it off, the discovery tool should find no pattern, which proves the analysis is not baked in.
- Realistic noise (~1.5% missing, ~0.5% duplicated events); timestamps within Singapore working hours.
- A fixed seed, and tests for reproducibility, schema, working hours, noise and the switch.

## Who Benefits

- **Product ops:** their chasing work (clarification requests, nudges) becomes visible and costable, with handle time on every event.
- **Owners:** the data separates vague intake from slow response, so owners aren't blamed for delays caused upstream.
- **The engagement team:** known ground truth, to check the discovery tool finds what is really there.

## Success Criteria

- `python generator/generate.py` writes `data/event_log.csv` with the agreed columns.
- Two runs with the same seed produce byte-identical files.
- Missing and duplicate rates each land within ±0.3 percentage points of target.
- Switch on: low-detail items are at least 3× as likely as high-detail items to need clarification. Switch off: the rates are within ±20% of each other.
- All tests pass.

## Non-goals

- Modelling owner workload or competing priorities (a known limitation; see CLAUDE.md).
- Public holidays, time zones other than Singapore, or real integrations.
- Any analysis or charts (phase 2).

## Capabilities

### New Capabilities
- `synthetic-event-log`: generating a reproducible, configurable synthetic event log of feedback items.

### Modified Capabilities
- None.

## Impact

- New: `generator/config.py`, `generator/generate.py`, `tests/`, `requirements.txt`, `data/event_log.csv`, `README.md`.
- **New dependencies (approved 2026-10-01):** `pandas`, `numpy` and `pytest`, installed into a project-local `.venv`, not system-wide.
