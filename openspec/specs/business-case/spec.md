# business-case Specification

## Purpose

Compares candidate fixes for stalled feedback on simulated payback and return, value against feasibility, and sensitivity to assumptions, and publishes the result as a generated exec brief and an interactive app page.

## Requirements

### Requirement: Measured baseline
The model SHALL take its baseline from the event log through the discovery analysis: annual product ops hours on `Clarification requested`, `Nudge sent` and `Escalated`, annual item volume, and annual items closed as stale after an unanswered clarification request. Annualising SHALL use the weeks the data covers.

#### Scenario: Baseline matches the readout
- **WHEN** the baseline is computed from the default dataset
- **THEN** its annual chasing hours equal the discovery readout's annual chasing hours

### Requirement: Options and assumptions
The model SHALL compare three options: AI intake clarity check, structured intake form, and owner follow-through. Each option SHALL name the effort pool it reduces. Every uncertain input SHALL be a (low, most likely, high) range defined in the assumptions file, and every feasibility score SHALL carry a written rationale.

#### Scenario: Assumptions in one place
- **WHEN** a range or score in the assumptions file changes
- **THEN** the model, brief and app page reflect it without code changes

### Requirement: Benefits and costs
Annual benefit SHALL be product ops hours saved × the hourly rate, and nothing else. Costs SHALL be one-off build cost (engineer-weeks × weekly cost) plus annual maintenance, run cost and, for the AI option, product ops time reviewing medium-confidence suggestions. Rescued items, avoided clarification rounds and avoided nudges SHALL be reported as counts with no dollar value.

#### Scenario: No hours saved, no benefit
- **WHEN** an option saves zero hours
- **THEN** its annual benefit is zero and its ROI is negative

### Requirement: Monte Carlo simulation
The model SHALL draw each range from a triangular distribution, using a seeded generator and a configured number of runs, and compute per run: annual benefit, annual cost, payback in months (build cost ÷ monthly net benefit; "never" when net benefit is not positive) and simple 3-year ROI (undiscounted). It SHALL report the 10th, 50th and 90th percentiles, the probability of payback within 12 months, and the probability of positive 3-year ROI.

#### Scenario: Reproducible
- **WHEN** the simulation runs twice with the same seed
- **THEN** the results are identical

#### Scenario: Collapsed ranges equal the hand calculation
- **WHEN** every range has low = most likely = high
- **THEN** every run equals the deterministic calculation exactly

### Requirement: Value and feasibility
Each option SHALL get a feasibility score as the weighted mean of five criteria (technical complexity, data and integration readiness, adoption, risk, time to value), each scored 1 to 5. Its value SHALL be the median 3-year net benefit. Options SHALL be ranked and shown on a value × feasibility chart.

#### Scenario: Weighted score
- **WHEN** an option scores 5 on every criterion
- **THEN** its feasibility score is 5

### Requirement: Sensitivity
For each option, the model SHALL swing each uncertain input to its low and high value while holding the others at most likely, and rank inputs by the resulting swing in 3-year net benefit.

#### Scenario: Biggest driver first
- **WHEN** the sensitivity table is produced
- **THEN** inputs are ordered by swing, largest first

### Requirement: Generated exec brief
`python business_case/brief.py` SHALL write `docs/exec_brief.md`, a one-page brief for the head of product ops: recommendation, option comparison table, value × feasibility chart, what each option rests on, what is not counted, and next steps. Every number SHALL come from the model at default settings, and the recommendation sentences SHALL follow the results rather than being fixed text.

#### Scenario: Committed brief is current
- **WHEN** the brief is regenerated
- **THEN** it is byte-identical to the committed `docs/exec_brief.md`

### Requirement: Business case page
The Streamlit app SHALL include a "Business case" page with sliders for the hourly rate, engineer weekly cost, and each option's most likely effect. It SHALL show the comparison table, the value × feasibility chart, the sensitivity ranking and the uncounted benefits, and SHALL recalculate when a slider moves.

#### Scenario: Page renders
- **WHEN** the business case page is opened
- **THEN** it renders with no errors and shows all three options

#### Scenario: Sliders change results
- **WHEN** the hourly rate slider is raised
- **THEN** every option's median annual benefit rises

### Requirement: Performance
The full model, including simulation and sensitivity, SHALL run in under 5 seconds.

#### Scenario: Timed model run
- **WHEN** the model runs with default settings
- **THEN** it finishes in under 5 seconds
