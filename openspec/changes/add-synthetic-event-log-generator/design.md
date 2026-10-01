# Design

## Context

Greenfield: the repo holds only OpenSpec scaffolding and CLAUDE.md. Python 3.12 is installed; pandas, numpy and pytest are not. CLAUDE.md asks us to reuse the structure of an earlier freight generator (a config file for assumptions, a generate script, a fixed seed). That code is not in this repo, so we take the structure only. See proposal.md for motivation and specs/synthetic-event-log/spec.md for requirements.

## Goals / Non-Goals

**Goals:**
- A readable simulation that can be explained line by line in an interview.
- A clean separation: `config.py` holds every number, `generate.py` holds only logic.
- Ground truth we control, including a switch to turn the key effect off.

**Non-Goals:**
- Queueing or capacity effects (owners never get "busier").
- Statistical realism beyond plausible shapes; the numbers are assumptions, not estimates.

## Layout

```
generator/config.py      all assumptions, as plain constants and dicts
generator/generate.py    simulate cases, add noise, write CSV; small CLI
tests/test_generator.py  pytest tests mapped to the spec scenarios
data/event_log.csv       committed output (synthetic, small)
requirements.txt         pinned versions
```

## Decisions

**1. Simulate each case independently, step by step.**
Each case walks through the lifecycle, sampling what happens next and how long it takes.
- *Alternative:* a discrete-event simulation library such as SimPy, which models shared queues.
- *Rejected because:* it adds a dependency and a concept (resource contention) the analysis doesn't need, and it's harder to explain. The cost is a known limitation (see below).

**2. Work in "working minutes", then map to the calendar.**
Delays are sampled as working minutes. One helper adds working minutes to a timestamp, skipping nights and weekends. That single function is how every timestamp stays within working hours.
- *Alternative:* sample calendar times, then shift any out-of-hours time forward.
- *Rejected because:* shifting distorts delays (a 1-hour wait at 17:30 would become 16 hours), and it spreads the rule across many places.

**3. Use a fixed UTC+08:00 offset, not a named time zone.**
- *Alternative:* `zoneinfo("Asia/Singapore")`.
- *Rejected because:* on Windows that needs the extra `tzdata` package. Singapore has no daylight saving time, so a fixed offset is exactly correct.

**4. Owner timers are code, not chance.**
We sample how long an owner will take to respond (hidden from the log). Product ops sends a `Nudge sent` every N working days while waiting. The number of nudges therefore follows from the wait, which is how a real chaser behaves. If the wait passes the stale threshold, the case is `Closed as stale`.
- *Alternative:* sample the number of nudges directly.
- *Rejected because:* nudges would be disconnected from delay, and Phase 2's "cost of chasing" would be meaningless.

**5. Escalation is rare and follows nudges.**
It can only happen after a configured number of nudges, and even then only with a small probability. After escalation, the remaining owner wait is shortened. This mirrors CLAUDE.md decision 2: escalation is a human last resort.

**6. The switch keeps volume constant.**
When the detail effect is off, every detail level uses the *weighted average* of the per-level clarification probabilities, not an arbitrary value. The total number of clarification loops stays about the same, so turning the effect off removes the *pattern* without changing the *workload*. This isolates the one thing the switch is meant to test.

**7. Delays are lognormal.**
Waits are right-skewed (most are quick, a few are very long). The config states each wait as a median in working hours plus a spread.
- *Alternative:* exponential distributions.
- *Rejected because:* they have too many near-zero waits and too thin a long tail for human response times.

**8. Noise is applied after simulation, to a copy.**
`simulate()` returns a clean log; `add_noise()` drops and duplicates rows. Tests check lifecycle rules on the clean log and noise rates by comparing clean against noisy.
- *Alternative:* inject noise during simulation.
- *Rejected because:* then no test could separate "the simulation is wrong" from "noise removed the event".

**9. Right-censoring at the end of the window.**
Cases submitted near the end of the observation window are cut at the window's end and left open, as in a real export. Phase 2 must handle open cases rather than treating them as fast.

**10. Anonymised resources.**
People are identified by role-based IDs (`OPS-01`, `OWN-12`, `SUP-04`), never names or emails. This avoids any resemblance to real people, keeps the pre-commit email check clean, and matches how a real export would be pseudonymised.

**11. Commit the generated CSV.**
It's small (about 2 MB) and synthetic. Committing it lets the Phase 2 app run without a generation step.
- *Alternative:* git-ignore it and generate on demand.
- *Rejected because:* reviewers browsing GitHub can see the data directly, and reproducibility is still guaranteed by the seed test.

**12. A CLI with three optional flags:** `--seed`, `--out`, `--no-detail-effect`. This lets Phase 2 produce the "no pattern" dataset without editing config. The defaults all come from config.

## Assumptions

All values below are starting points and will live in `generator/config.py`. That file, not this table, is the source of truth.

| Assumption | Starting value |
|---|---|
| Random seed | 42 |
| Cases | 2,000 |
| Observation window | 2026-01-05 to 2026-06-30 |
| Working hours | Mon–Fri, 09:00–18:00, UTC+08:00 |
| Source mix | support 45%, sales 20%, survey 15%, in-app 20% |
| Detail mix | low 35%, medium 40%, high 25% |
| Tier mix | enterprise 20%, mid-market 45%, SMB 35% |
| Product areas | billing, reporting, integrations, permissions, onboarding, mobile |
| P(needs clarification) by detail, effect on | low 0.70, medium 0.35, high 0.10 |
| P(still unclear after a reply) | 0.25, at most 3 loops |
| P(provider never replies) | internal submitters 0.05, customers 0.25 |
| P(duplicate) | 0.12 |
| P(misrouted) | 0.10 |
| Nudge interval | every 3 working days |
| Stale after | 20 working days with no activity |
| Escalation | possible after 3 nudges, P = 0.15 |
| Outcome after acknowledgement | resolved 70%, won't do 20%, no progress (stale) 10% |
| Missing / duplicated events | 1.5% / 0.5% |
| `channel` meaning | the medium of the event: `tracker`, `email`, `chat`, `call` |

CLAUDE.md lists `channel` but doesn't define it. We confirmed it means the medium of each event, because `source` already records where the feedback came from. This also lets Phase 2 compare, for example, nudge response by chat versus email.

## Risks / Trade-offs

- **[Numbers look like findings]** → The README and app will label them as assumptions, and the switch shows the analysis responds to them.
- **[numpy's random streams can change between versions]** → Pin exact versions in `requirements.txt`; the reproducibility test catches drift.
- **[Circular logic: we find the effect we planted]** → That is the point of the switch. Phase 2 must report "no pattern" with the effect off.
- **[Too slow for the app]** → 2,000 cases in pure Python should take a few seconds; we'll check this during apply.

## Known limitations

- Only the chaser's view is modelled; owners' competing priorities and capacity are not (CLAUDE.md decision 5).
- No public holidays, leave or time-zone differences between teams.
- Cases are independent: a wave of similar feedback doesn't create correlated duplicates.
- Handle times are rough effort estimates, not measured.

## In a real deployment

- **Data access:** request a read-only export of ticket history from the tracking tool, with names replaced by stable pseudonymous IDs before it leaves the customer's environment.
- **Integrations:** map the tool's status changes onto our activity names. Expect to derive `Nudge sent` from comment history, because no tool logs chasing explicitly.
- **Privacy:** feedback text may contain customer personal data. Keep text out of the log and work with metadata only.
- **Who to interview:** product ops, to validate the lifecycle and where time goes; two or three owners, on competing priorities (our biggest blind spot); a support lead, on what makes feedback vague at intake.
