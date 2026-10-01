# Tasks

## 1. Environment setup

- [x] 1.1 Create a project-local `.venv` and install pandas, numpy and pytest (approved 2026-10-01); verify with `python -c "import pandas, numpy, pytest"` inside the venv
- [x] 1.2 Write `requirements.txt` pinned to the exact installed versions; verify that `pip install -r requirements.txt` in the venv reports nothing to change
- [x] 1.3 Create `generator/`, `tests/` and `data/` folders; verify they exist and `.venv/` is git-ignored (`git status` does not list it)

## 2. Assumptions config

- [x] 2.1 Write `generator/config.py` with every value from the design's Assumptions table, grouped and commented (seed, volume, window, working hours, mixes, probabilities, delays, handle times, noise, switch); verify it imports without error
- [x] 2.2 Add a test that the category mixes each sum to 1.0 and all probabilities lie in [0, 1]; verify `pytest` passes

## 3. Working-time clock

- [x] 3.1 Implement the helper that adds working minutes to a timestamp, skipping nights and weekends at UTC+08:00; verify with tests: Friday 17:30 + 60 min gives Monday 09:30; a start before 09:00 snaps to 09:00
- [x] 3.2 Implement sampling of submission times spread across the working day within the observation window; verify with a test that all sampled times are weekdays between 09:00 and 18:00

## 4. Case simulation

- [x] 4.1 Implement case attribute sampling (source, product area, detail level, tier) and anonymised resource pools; verify with a test that attributes and IDs use only config values and no ID contains a space or `@`
- [x] 4.2 Implement intake: submission, triage and the clarification loop (per-detail probability, repeat loops, provider no-reply leads to stale); verify with a test that every `Clarification requested` is followed by `Clarification received` or `Closed as stale`
- [x] 4.3 Implement duplicate merge, routing and reassignment; verify with a test that `Merged as duplicate` cases have no later events
- [x] 4.4 Implement the owner phase: hidden response time, nudges every N working days, stale threshold, rare escalation after K nudges, then In progress and Resolved / Won't do; verify with a test that `Escalated` always follows at least one `Nudge sent`
- [x] 4.5 Implement right-censoring at the observation end; verify with a test that no event is after the window end and censored cases have no terminal activity
- [x] 4.6 Assemble `simulate()` returning the clean log; verify with a test that every case starts with `Feedback submitted`, timestamps never decrease within a case, and at most one terminal activity appears, as the last event

## 5. Noise

- [x] 5.1 Implement `add_noise()` (random drop, then exact-row duplication, both from config); verify with a test that missing and duplicate rates are each within ±0.3 percentage points of target

## 6. Output and CLI

- [x] 6.1 Implement CSV writing (column order, sort order, ISO 8601 with `+08:00`) and the CLI flags `--seed`, `--out`, `--no-detail-effect`; verify that `python generator/generate.py` writes `data/event_log.csv` with exactly the spec's columns
- [x] 6.2 Add reproducibility tests: same seed gives byte-identical files; a different seed gives a different file
- [x] 6.3 Add switch tests: effect on gives low-detail clarification share ≥ 3× high; effect off gives shares within ±20% of each other
- [x] 6.4 Add a working-hours test on the final CSV (weekdays, 09:00–18:00, `+08:00`) and time a full run; verify all of `pytest` passes and the run takes under 30 seconds

## 7. Publish the dataset and memo

- [x] 7.1 Generate `data/event_log.csv` with default config and commit it; verify the pre-commit check passes and the file is under 5 MB
- [x] 7.2 Create `README.md` as a deployment memo (situation, approach, data so far, what's left out, next steps), covering Phase 1's assumptions, the switch and the known limitations; verify the documented commands run as written
