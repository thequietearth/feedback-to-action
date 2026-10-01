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
| 2. Discovery app | Where do items stall, and what does chasing cost? | Next |
| 3. Business case | Which fix is worth funding, and what's the ROI range? | Planned |
| 4. Prototype agent | Can an agent check intake clarity, route confidently and follow through, without escalating on its own? | Planned |
| 5. Evaluation | Does the agent reduce time to resolution, chases and misroutes? | Planned |

Each phase is planned as an [OpenSpec](https://github.com/Fission-AI/OpenSpec) change (proposal, spec, design, tasks) under `openspec/`, so the reasoning behind every decision is recorded next to the code.

## Phase 1: the event log

In a real engagement, we'd start from an export of the ticketing tool. Here, `generator/` produces an equivalent log: one row per event, one case per feedback item, 2,000 items over January to June 2026.

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1      # Windows PowerShell; macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python generator/generate.py    # writes data/event_log.csv
pytest                          # 53 tests
```

**What each item goes through:** submission → triage → clarification loops if the item is vague → merged as a duplicate, or routed (sometimes to the wrong owner first) → owner acknowledgement, with product ops nudging every 3 working days of silence → in progress → resolved, won't do, or closed as stale.

**Design choices worth knowing:**

- **Every assumption is in one file.** [`generator/config.py`](generator/config.py) holds all numbers: volumes, probabilities, delays, effort per step, noise. None are measured; they are plausible starting points to be replaced by a real export.
- **The key assumption has an off switch.** Vague items are assumed to need clarifying far more often (70% for low detail vs 10% for high). Running `python generator/generate.py --no-detail-effect --out data/event_log_no_effect.csv` removes that link while keeping total clarification workload the same. Phase 2's discovery app must then report "no pattern". That shows the analysis finds what is in the data rather than what we expected.
- **Code owns timers.** Nudges follow from how long an owner actually takes, as a real chaser's would. Escalation is a single, rare human decision (about 5% of routed items), never automatic.
- **Realistic mess.** 1.5% of events are missing and 0.5% duplicated, all timestamps fall within Singapore working hours, and items still open on 30 June are left open, just as in a live export.
- **Reproducible.** The same seed produces a byte-identical file, and a test checks it.

**Verified against the spec (seed 42):** low-detail items need clarifying 6.4× as often as high-detail ones; with the switch off, the three levels are within 10% of each other. Missing and duplicate rates came out at 1.51% and 0.51%. A full run takes under a second.

## What was left out

- **The owners' side.** We model only the chaser's view. Owners' competing priorities and workload aren't simulated, and in a real engagement they'd be the first people to interview.
- **Capacity effects.** Items are independent; a busy week doesn't slow anyone down.
- **Calendars.** No public holidays, leave, or teams in other time zones.
- **Feedback text.** The log holds metadata only. That also matches how we'd handle customer data in a real deployment.

## What I'd do next

Phase 2: a Streamlit discovery app that checks data quality, maps the process, finds where items stall, puts a cost on chasing, and tests whether detail level predicts delay (with the switch both on and off).

In a real deployment, before any of that, I'd ask for a read-only, pseudonymised export from the ticketing tool. I'd also interview product ops (to validate the lifecycle), two or three owners (on competing priorities), and a support lead (on what makes feedback vague at intake).
