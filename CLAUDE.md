# CLAUDE.md

## What this project is

A portfolio project run as a mock discovery engagement. It shows the full arc of
a deployment: find where value lives, build a business case, prototype an AI
solution, and evaluate it.

**Problem statement:** Feedback stalls because it arrives unactionable, and the
cost falls on whoever has to chase it.

**Setting (fictional):** Tessellate, a mid-sized B2B software company. Feedback
arrives from support tickets, sales call notes, surveys and in-app forms. A small
product ops team triages it and routes it to product and engineering owners, then
spends much of its week chasing those owners.

## Hard rules

- All data is synthetic. Never add real company, customer or employer data.
- No government, defence or employer names, terminology, categories or screenshots
  anywhere in code, data, comments, commits or docs. The setting is a generic
  commercial software company only.
- Secrets go in `.env` (git-ignored). Never commit API keys.
- Ask before adding a new dependency.
- Explain what you changed and why after each task. I need to understand every
  line, because I will be asked about it in interviews.

## Key design decisions (and why)

1. **Intake clarity comes first.** Most chasing happens because owners receive
   vague feedback and someone must go back to the provider for details. Checking
   completeness at submission, while the provider is still engaged, is the
   highest-value fix.
2. **The agent never escalates on its own.** Escalation carries relationship cost.
   The agent uses soft levers instead: actionable items, context (how many
   customers raised it), owner digests and an ageing view. Escalation is always a
   human decision.
3. **Code owns arithmetic, timers and dates.** Classification models (Jev) make
   narrow judgements; a generative LLM writes text (clarifying questions, nudges).
4. **Assumptions are explicit.** Every number in the generator lives in
   `generator/config.py`. The link between detail level and clarification loops is
   an assumption with an on/off switch, so the discovery tool can be shown to
   report "no pattern" when the effect is turned off.
5. **Known limitation:** we only model the chaser's view. In a real engagement,
   owners would be interviewed about competing priorities.

## Event log design (phase 1)

One case = one feedback item. Columns: `case_id, activity, timestamp, channel,
role, resource, handle_time_min, source, product_area, detail_level,
customer_tier`.

Lifecycle (with loops):
- Feedback submitted (source: support_ticket / sales_call / survey / in_app;
  detail_level: low / medium / high)
- Triaged
- Clarification requested -> Clarification received (repeatable; the provider
  can be slow; low detail makes this far more likely)
- Merged as duplicate (ends the case)
- Routed to owner -> Reassigned (misrouted, occasional)
- Owner acknowledged
- Nudge sent (chasing; repeatable)
- Escalated (rare, human-initiated)
- In progress
- Ends as: Resolved / Won't do / Closed as stale (lost items with no activity)

Include realistic noise: ~1.5% missing events, ~0.5% duplicated events.
Timestamps stay within working hours (Singapore time), spread across the day.

## Roadmap

- [x] Phase 1: Synthetic data generator (adapt the freight generator's structure:
      config.py for assumptions, generate.py for case simulation, fixed seed)
- [ ] Phase 2: Discovery app (Streamlit): data quality, process map (pm4py),
      where items stall, cost of chasing, does detail level predict delay?
- [ ] Phase 3: Business case: value x feasibility scoring, Monte Carlo ROI,
      exec brief
- [ ] Phase 4: Prototype agent: intake clarity check, confident routing,
      follow-through (nudges, digests), no auto-escalation
      - First: synthetic feedback text per case, built from templates in code
        (seeded, offline), saved to `data/feedback_items.csv`. Its true product
        area and detail level are the answer key. The event log stays metadata only.
      - Jev makes three narrow judgements: intake clarity (Score + Nouls for
        missing details), routing (Choice over product areas) and duplicate
        check (same issue as a recent item?). A generative LLM writes text.
      - Confidence gates every action: >0.9 act, 0.5-0.9 suggest to product
        ops, <0.5 hand to a human. Escalation stays human whatever the score.
      - `typesafe-sdk` needs approval; `TYPESAFE_API_KEY` lives in `.env`.
- [ ] Phase 5: Evaluation: replay items, measure time to resolution, human
      chases, wrong routings
      - Measure Jev's accuracy against the answer key and its calibration
        (is it right ~90% of the time when confidence is 0.9?).
      - Note: template text is more uniform than real feedback, so accuracy
        here is an upper bound.

## Out of scope

User accounts, a database, real integrations (Slack, Jira), arbitrary file
upload formats, UI polish beyond clean defaults.

## Conventions

- Python 3.11+, pandas, numpy. Small functions, type hints, docstrings on
  anything non-obvious.
- Reproducible: fixed random seed; same config gives the same data.
- README is written as a deployment memo: situation, approach, findings, what was
  left out, what I'd do next.

## Commands

```bash
pip install -r requirements.txt
python generator/generate.py      # writes data/event_log.csv
```
