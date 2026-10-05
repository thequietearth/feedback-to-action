# Feedback to Action

*A deployment memo from a mock discovery engagement. All data is synthetic; the company is fictional.*

## Situation

Tessellate is a mid-sized B2B software company. Customer feedback reaches it through support tickets, sales call notes, surveys and in-app forms. A small product ops team triages each item and routes it to a product or engineering owner. Then the team spends much of its week chasing.

**Problem statement:** feedback stalls because it arrives unactionable, and the cost falls on whoever has to chase it.

## Approach

The engagement runs in five phases:

| Phase | Question | Status |
|---|---|---|
| 1. Synthetic event log | What would the ticket history look like? | **Done** |
| 2. Discovery app | Where do items stall, and what does chasing cost? | **Done** |
| 3. Business case | Which fix is worth funding, and what's the ROI range? | Next |
| 4. Prototype agent | Can an agent check intake clarity, route confidently and follow through, without escalating on its own? | Planned |
| 5. Evaluation | Does the agent reduce time to resolution, chases and misroutes? | Planned |

Each phase is planned as an [OpenSpec](https://github.com/Fission-AI/OpenSpec) change (proposal, spec, design, tasks) under `openspec/`, so the reasoning behind every decision is recorded next to the code.

## Phase 1: the event log

In a real engagement, we'd start from an export of the ticketing tool. Here, `generator/` produces an equivalent log: one row per event, one case per feedback item, 2,000 items over January to June 2026.

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows PowerShell; macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python generator/generate.py        # writes data/event_log.csv
streamlit run app/streamlit_app.py  # opens the discovery readout in your browser
pytest                              # 83 tests
```

**What each item goes through:** submission → triage → clarification loops if the item is vague → merged as a duplicate, or routed (sometimes to the wrong owner first) → owner acknowledgement, with product ops nudging every 3 working days of silence → in progress → resolved, won't do, or closed as stale.

**Design choices worth knowing:**

- **Every assumption is in one file.** [`generator/config.py`](generator/config.py) holds all numbers: volumes, probabilities, delays, effort per step, noise. None are measured; they are plausible starting points to be replaced by a real export.
- **The key assumption has an off switch.** Vague items are assumed to need clarifying far more often (70% for low detail vs 10% for high). Running `python generator/generate.py --no-detail-effect --out data/event_log_no_effect.csv` removes that link while keeping total clarification workload the same. Phase 2's discovery app must then report "no pattern". That shows the analysis finds what is in the data rather than what we expected.
- **Code owns timers.** Nudges follow from how long an owner actually takes, as a real chaser's would. Escalation is a single, rare human decision (about 5% of routed items), never automatic.
- **Realistic mess.** 1.5% of events are missing and 0.5% duplicated, all timestamps fall within Singapore working hours, and items still open on 30 June are left open, just as in a live export.
- **Reproducible.** The same seed produces a byte-identical file, and a test checks it.

**Verified against the spec (seed 42):** low-detail items need clarifying 6.4× as often as high-detail ones; with the switch off, the three levels are within 10% of each other. Missing and duplicate rates came out at 1.51% and 0.51%. A full run takes under a second.

## Phase 2: the discovery readout

`app/` is a Streamlit readout written for Tessellate's head of product ops. It tells one story top to bottom, and each section opens with a finding computed from the data. The analysis is a set of tested functions in [`app/analysis.py`](app/analysis.py); every assumption (hourly cost, working calendar, thresholds) is in [`app/settings.py`](app/settings.py).

### Findings (2,000 items, January to June 2026)

1. **The data is usable.** 77 duplicate rows were removed, 37 items (1.8%) have a gap from a missing event, and 311 were still open at export. Missing events are counted, never filled in.
2. **No two journeys look alike.** The ten most common paths cover only 40% of items; clarification loops, nudges and reassignments make each one different.
3. **Owners hold most of the wait, but providers hold a fifth of it.** Of all waiting time, 70% is on owners, 20% on feedback providers answering clarification questions, and 9% on product ops. The biggest stall is a nudge followed by another nudge: owners staying silent through repeated chasing (1,931 times, 52,643 working hours). Separately, **108 items were lost outright** because a clarification question was never answered.
4. **Chasing costs about SGD 62,000 a year.** Product ops spent 504 hours in 25 weeks on nudges (298h), clarification requests (175h) and escalations (31h). That is about 1,040 hours a year at an assumed SGD 60/hour. Misrouting rework adds a further 27 hours.
5. **Vague feedback does cause delay.** Low-detail items take 2.4× as long to reach an owner (16.4 vs 6.9 working hours, median; one-sided permutation test p = 0.0002), and 69% need clarifying against 11% of high-detail items.

### How we know the verdict isn't wishful thinking

The generator can switch the detail effect off. On that dataset, the readout reports **no pattern** (0.85×, p = 0.975). But a plain two-sided significance test on the same data gave p = 0.041, which looks like a finding and points the wrong way: low-detail items were slightly *faster*. So the verdict requires three things together: the expected direction, p < 0.05, and at least a 1.5× gap. The dataset selector in the sidebar reruns every section on the effect-off data, so this can be shown live.

### Two analysis choices worth knowing

- **Each wait is charged to whoever was expected to act next,** not to whoever logged the next event. The wait before a nudge counts against the owner, even though product ops sends the nudge.
- **Active work is not a stall.** The first build counted time after "In progress" as owner waiting, which made "In progress → Resolved" the headline stall. That time is the owner actually working (28% of all measured time), so it is now reported separately.

The verdict uses intake delay (submission to routing) rather than time to resolution. Resolution time is shown as context: low-detail items take 1.3× as long to resolve, a smaller gap because owner waits dominate, and 311 open items have no resolution time at all.

## What was left out

- **The owners' side.** We model only the chaser's view. Owners' competing priorities and workload aren't simulated, and in a real engagement they'd be the first people to interview.
- **Capacity effects.** Items are independent; a busy week doesn't slow anyone down.
- **Calendars.** No public holidays, leave, or teams in other time zones.
- **Feedback text.** The log holds metadata only. That also matches how we'd handle customer data in a real deployment.
- **Process-mining libraries.** The process map is built in pandas rather than pm4py, which is licensed AGPL-3.0 (often blocked by client legal teams) and heavier than a directly-follows graph needs.
- **Finer analysis.** The verdict compares low against high detail only, waits ignore public holidays, and the annual cost assumes steady volume.

## What I'd do next

Phase 3: a business case. The readout points to two levers: catching vague feedback at intake (20% of waiting, 108 lost items, 175 hours of clarification requests in 25 weeks) and reducing owner silence (the nudge-after-nudge stall). Phase 3 scores each on value and feasibility and puts an ROI range on them with Monte Carlo simulation.

In a real deployment, before any of that, I'd ask for a read-only, pseudonymised export from the ticketing tool. I'd present the readout live to the head of product ops, confirm the hourly cost with finance, and interview two or three owners about the waits charged to them, which is the view this analysis can't see.
