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
| 3. Business case | Which fix is worth funding, and what's the ROI range? | **Done** |
| 4. Prototype agent | Can an agent check intake clarity, route confidently and follow through, without escalating on its own? | Next |
| 5. Evaluation | Does the agent reduce time to resolution, chases and misroutes? | Planned |

Each phase is planned as an [OpenSpec](https://github.com/Fission-AI/OpenSpec) change (proposal, spec, design, tasks) under `openspec/`, so the reasoning behind every decision is recorded next to the code.

## Phase 1: the event log

In a real engagement, we'd start from an export of the ticketing tool. Here, `generator/` produces an equivalent log: one row per event, one case per feedback item, 2,000 items over January to June 2026.

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows PowerShell; macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python generator/generate.py        # writes data/event_log.csv
streamlit run app/streamlit_app.py  # opens the readout; the business case is a second page
python business_case/brief.py       # regenerates docs/exec_brief.md
pytest                              # 110 tests
```

If PowerShell refuses to run the activation script, skip it and call the environment's Python directly, e.g. `.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py`.

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

## Phase 3: the business case

**[Read the one-page exec brief →](docs/exec_brief.md)**

The readout pointed to two levers: vague feedback at intake and owner silence. The business case compares three ways to pull them against the measured baseline (about 1,040 product ops hours a year spent chasing):

- **AI intake clarity check:** asks the provider for missing details at submission.
- **Structured intake form (no AI):** mandatory fields. It's there to answer the question a client will ask: do we need AI at all?
- **Owner follow-through:** digests and an ageing view instead of one-off nudges.

Every uncertain input (effect size, build effort, engineer cost, maintenance, review time) is a range, not a number. A seeded Monte Carlo simulation runs each option 10,000 times. **The ROI counts product ops hours saved only**; rescued items and avoided nudges are reported as counts without a dollar value, because pricing them would rest on assumptions finance would rightly challenge.

### Findings

| Option | 3-year net (median) | Chance ROI > 0 | Payback |
|---|---|---|---|
| Owner follow-through | SGD 31k | 100% | ~13 months |
| Structured intake form | SGD 11k | 100% | ~12 months, and the cheapest build |
| AI intake clarity check | −SGD 11k | 13% | ~68 months |

**Recommendation:** fund owner follow-through first, and run the intake form alongside it, because they target different work. **The AI intake check does not pay back on hours saved alone.** Its case rests on outcomes the ROI doesn't count: about 111 lost items rescued a year and faster intake. Phase 4 prototypes it and Phase 5 tests whether those outcomes are real before anyone funds a full build.

That result goes against the AI option this project is about to prototype. That's deliberate: the model has to be able to say no, and the assumptions are visible enough for anyone to argue with. The app's "Business case" page has sliders for the hourly rate, engineer cost and each option's effect, and the sensitivity view shows the AI option's result swings most with build effort.

### Choices worth knowing

- **One function does all the money arithmetic.** The simulation, the sensitivity view and the tests all call `evaluate()`. A test collapses every range to a single value and checks the simulation matches the hand calculation exactly.
- **The brief is generated, and a test fails if it is stale.** Change an assumption without regenerating, and the build breaks rather than a number drifting.
- **The value axis is fixed,** not rescaled per option, so the weakest option isn't automatically drawn at zero.

## What was left out

- **The owners' side.** We model only the chaser's view. Owners' competing priorities and workload aren't simulated, and in a real engagement they'd be the first people to interview.
- **Capacity effects.** Items are independent; a busy week doesn't slow anyone down.
- **Calendars.** No public holidays, leave, or teams in other time zones.
- **Feedback text.** The log holds metadata only. That also matches how we'd handle customer data in a real deployment.
- **Process-mining libraries.** The process map is built in pandas rather than pm4py, which is licensed AGPL-3.0 (often blocked by client legal teams) and heavier than a directly-follows graph needs.
- **Finer analysis.** The verdict compares low against high detail only, waits ignore public holidays, and the annual cost assumes steady volume.
- **Business case scope.** Costs are estimates, not quotes; provider and owner time isn't counted; the ROI is undiscounted; options are compared, not combined; and the intake form's effect on submission volume isn't modelled.

## What I'd do next

Phase 4: prototype the agent. The business case shapes its priorities: owner follow-through (digests, an ageing view, no auto-escalation) is the proven case, and the AI intake check is an experiment whose outcomes Phase 5 must measure, starting with items rescued and intake delay.

In a real deployment, I'd first get a read-only, pseudonymised export from the ticketing tool, present the readout and brief live to the head of product ops, replace assumed costs with engineering estimates, and run a short workshop to challenge the feasibility scores. Then I'd pilot the cheapest option and measure its real effect before funding the next.
