# Proposal

## Why

**Roadmap phase 3.** The readout found what chasing costs (about SGD 62,000 a year) and why items stall. The head of product ops now needs to know which fix to fund, what it returns, and how sure we are. That decision also sets Phase 4's priorities.

## What Changes

- A business case model comparing three options against the measured baseline:
  - **AI intake clarity check:** asks providers for missing details at submission.
  - **Structured intake form (no AI):** mandatory fields, as the cheap baseline.
  - **Owner follow-through:** digests and an ageing view instead of one-off nudges.
- Each option's uncertain inputs are ranges, not single numbers. A seeded Monte Carlo simulation turns them into ranges for payback months and 3-year ROI.
- **ROI counts product ops hours saved only.** Rescued items and avoided nudges are quantified alongside, without a dollar value.
- Value × feasibility scoring, with a written rationale for every feasibility score, and a sensitivity view showing which assumption moves each result most.
- A one-page exec brief (`docs/exec_brief.md`), generated from the model so its numbers always match, plus a "Business case" page in the app with sliders.

## Who Benefits

- **Head of product ops:** a defensible recommendation with ranges, not one optimistic number.
- **Finance:** every assumption visible and adjustable.
- **Product ops, providers and owners:** the fix chosen is the one that removes the most chasing for the least disruption.

## Success Criteria

- `python business_case/brief.py` regenerates the brief byte-for-byte (a test checks the committed copy is current).
- Same seed gives identical results; with every range collapsed to one value, the simulation equals the hand calculation exactly.
- The app page renders with no errors.
- The model runs in under 5 seconds.

## Non-goals

- Building any option (Phase 4).
- Dollar values for outcomes, discounting or NPV.
- AI routing and duplicate checks: excluded, as misrouting cost only 27 hours in the period.
- Real vendor or salary quotes; costs are labelled assumptions.

## Capabilities

### New Capabilities
- `business-case`: comparing fix options on simulated payback and ROI, value × feasibility, and sensitivity, published as a brief and an app page.

### Modified Capabilities
- None. The model reads the baseline through the existing analysis functions.

## Impact

- New: `business_case/` (assumptions, model, brief), `app/pages/`, `docs/exec_brief.md`, tests.
- Updated: `pytest.ini`, README, CLAUDE.md.
- No new dependencies.
