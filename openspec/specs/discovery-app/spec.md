# discovery-app Specification

## Purpose

A discovery readout that analyses the feedback event log and presents, in order, whether the data can be trusted, how work flows, where items stall, what chasing costs, and whether low-detail feedback predicts delay.

## Requirements

### Requirement: Readout layout
The app SHALL start with `streamlit run app/streamlit_app.py` and show five sections in this order: data quality, process flow, stalls, cost of chasing, detail level and delay. Each section SHALL open with a one-sentence finding computed from the data, not fixed text.

#### Scenario: App renders
- **WHEN** the app is run with the default dataset
- **THEN** all five sections render in order with no errors

#### Scenario: Findings follow the data
- **WHEN** the dataset changes
- **THEN** the opening findings change to match the new numbers

### Requirement: Dataset selection
The app SHALL load `data/event_log.csv` by default. It SHALL offer a second dataset, "detail effect off", produced by the generator with the same seed and the detail-level effect switched off. All sections SHALL use the selected dataset.

#### Scenario: Switching dataset
- **WHEN** the user selects "detail effect off"
- **THEN** every section recalculates on that dataset

### Requirement: Data quality report
The app SHALL report: event and case counts, exact duplicate rows, cases not starting with `Feedback submitted`, sequence breaks (a `Clarification received` with no earlier request, or an `Owner acknowledged` with no earlier routing), open cases with no end state, and timestamps outside working hours. Later sections SHALL use the log with exact duplicates removed.

#### Scenario: Duplicates counted exactly
- **WHEN** the log contains N exact duplicate rows
- **THEN** the report shows N duplicates and later sections count each of those events once

#### Scenario: Sequence breaks flagged
- **WHEN** a case contains `Clarification received` with no earlier `Clarification requested`
- **THEN** that case is counted as a sequence break

### Requirement: Process flow
The app SHALL show a directly-follows process map: each activity as a node and each "A is directly followed by B within a case" pair as an edge labelled with its count. Edges below a user-adjustable minimum count SHALL be hidden. The app SHALL list the most common paths (variants) with case counts and shares.

#### Scenario: Edge counts are exact
- **WHEN** a small log has two cases that each go `Feedback submitted` → `Triaged`
- **THEN** that edge has count 2

### Requirement: Stall analysis
The app SHALL measure the wait before each event as working hours since the previous event in the same case. It SHALL rank transitions by total and median wait, and attribute each wait to the party expected to act next (provider, product ops or owner) using a mapping in settings. It SHALL show each party's share of total waiting time and how long open items have been waiting.

#### Scenario: Waits exclude nights and weekends
- **WHEN** one event is at 17:00 on a Friday and the next at 10:00 on the following Monday
- **THEN** the wait is 2 working hours

#### Scenario: Shares add up
- **WHEN** waiting time is attributed by party
- **THEN** the parties' shares sum to 100%

### Requirement: Active work is not a stall
Time after `In progress` is the owner actively working, not waiting. The app SHALL report it separately as active work and SHALL exclude it from the stall ranking and the party shares.

#### Scenario: Working time excluded from stalls
- **WHEN** a case goes `In progress` → `Resolved`
- **THEN** that time appears in the active-work figure and not in the stall ranking or party shares

### Requirement: Cost of chasing
The app SHALL compute product ops chasing effort as the summed `handle_time_min` of `Clarification requested`, `Nudge sent` and `Escalated` events, in hours. Cost SHALL be hours × an hourly rate (default SGD 60, adjustable). It SHALL show an annualised figure, scaled by the weeks the data covers, and show misrouting rework (`Reassigned`) separately.

#### Scenario: Cost reconciles
- **WHEN** chasing events total M minutes of handle time and the rate is R per hour
- **THEN** the reported cost is exactly (M / 60) × R

### Requirement: Detail-level verdict
The app SHALL measure intake delay as working hours from `Feedback submitted` to the first `Routed to owner` or `Merged as duplicate`. It SHALL compare low- and high-detail cases with a one-sided, seeded permutation test on the difference in median delay. The verdict SHALL be "pattern" only when p is below the threshold (default 0.05) **and** low-detail median delay is at least the minimum ratio (default 1.5×) of high-detail; otherwise "no pattern". It SHALL also show the clarification rate per detail level.

#### Scenario: Effect on
- **WHEN** the default dataset is analysed
- **THEN** the verdict is "pattern"

#### Scenario: Effect off
- **WHEN** the "detail effect off" dataset is analysed
- **THEN** the verdict is "no pattern"

#### Scenario: Significant but small or reversed is not a pattern
- **WHEN** p is below the threshold but the low/high ratio is under the minimum
- **THEN** the verdict is "no pattern"

### Requirement: Resolution time as context
Alongside the verdict, the app SHALL show median time to resolution per detail level: working hours from `Feedback submitted` to the case's end state, for closed cases only. It SHALL show how many open cases were left out at each level, and label the figures as context that does not affect the verdict.

#### Scenario: Open cases disclosed
- **WHEN** some cases have no end state
- **THEN** the resolution figures exclude them and the number excluded is shown for each detail level

#### Scenario: Context never changes the verdict
- **WHEN** resolution times differ by detail level
- **THEN** the verdict is still decided by intake delay alone

### Requirement: Explicit analysis assumptions
Every number the analysis uses (hourly rate, currency, working hours, chasing activities, waiting-on mapping, test threshold, minimum ratio, permutation count and seed) SHALL be defined in the app settings file, not in analysis or display code.

#### Scenario: Changing an assumption
- **WHEN** a value in the settings file changes
- **THEN** the app reflects it without code changes

### Requirement: Performance
The full analysis of the default dataset SHALL complete in under 5 seconds.

#### Scenario: Timed analysis
- **WHEN** every analysis step runs on the default dataset
- **THEN** it finishes in under 5 seconds
