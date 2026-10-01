# Spec Delta

## Purpose

Produces a reproducible, configurable synthetic event log of customer feedback items moving through triage, clarification, routing and follow-up, so later phases can analyse where feedback stalls against a known ground truth.

## ADDED Requirements

### Requirement: Event log output
The generator SHALL write a CSV event log where each row is one event and each case is one feedback item. The file SHALL contain exactly these columns, in this order: `case_id, activity, timestamp, channel, role, resource, handle_time_min, source, product_area, detail_level, customer_tier`. Rows SHALL be sorted by `case_id`, then `timestamp`.

#### Scenario: Default run
- **WHEN** the user runs `python generator/generate.py` with no arguments
- **THEN** the file `data/event_log.csv` is written with exactly the listed columns in order

#### Scenario: Case attributes are consistent
- **WHEN** the log is read
- **THEN** `source`, `product_area`, `detail_level` and `customer_tier` have a single value per `case_id`

### Requirement: Allowed values
Each categorical column SHALL only contain its allowed values:
- `activity`: Feedback submitted, Triaged, Clarification requested, Clarification received, Merged as duplicate, Routed to owner, Reassigned, Owner acknowledged, Nudge sent, Escalated, In progress, Resolved, Won't do, Closed as stale
- `source`: support_ticket, sales_call, survey, in_app
- `detail_level`: low, medium, high
- `customer_tier`: enterprise, mid_market, smb
- `product_area`, `channel`, `role`: the values listed in the generator config

`resource` SHALL be an anonymised identifier (for example `OPS-03`), never a personal name or email address.

#### Scenario: No unexpected values
- **WHEN** the log is read
- **THEN** every value in `activity`, `source`, `detail_level` and `customer_tier` belongs to its allowed set

#### Scenario: No personal identifiers
- **WHEN** the log is read
- **THEN** no `resource` value contains a space or an `@` character

### Requirement: Case lifecycle
Before noise is applied, every case SHALL start with `Feedback submitted` and end with exactly one terminal activity: `Merged as duplicate`, `Resolved`, `Won't do` or `Closed as stale`. The exception is a case still open at the end of the observation window, which SHALL have no terminal activity. `Clarification requested` SHALL always be followed by `Clarification received` or `Closed as stale`. `Escalated` SHALL only occur after at least one `Nudge sent`.

#### Scenario: Valid clean case
- **WHEN** the noise-free log is generated
- **THEN** every case begins with `Feedback submitted` and has at most one terminal activity, which is its last event

#### Scenario: Escalation is never the first lever
- **WHEN** a case contains `Escalated`
- **THEN** at least one `Nudge sent` precedes it in that case

### Requirement: Working hours
Every timestamp SHALL fall on a Monday to Friday, between 09:00 and 18:00 Singapore time (UTC+08:00), and SHALL be written in ISO 8601 format with the `+08:00` offset. Within a case, timestamps SHALL never decrease.

#### Scenario: Timestamps within working hours
- **WHEN** the log is read
- **THEN** every timestamp is a weekday between 09:00 and 18:00 at `+08:00`

### Requirement: Reproducibility
Given the same config and seed, the generator SHALL produce a byte-identical file. A different seed SHALL produce a different file.

#### Scenario: Same seed, same file
- **WHEN** the generator runs twice with the same seed
- **THEN** the two output files are byte-identical

#### Scenario: Different seed, different file
- **WHEN** the generator runs with two different seeds
- **THEN** the output files differ

### Requirement: Detail-level effect switch
The config SHALL include an on/off switch for the assumed link between `detail_level` and clarification loops. When on, low-detail cases SHALL need clarification at least 3 times as often as high-detail cases. When off, all detail levels SHALL share one clarification probability, so their observed rates differ by no more than 20%.

#### Scenario: Effect on
- **WHEN** the log is generated with the switch on
- **THEN** the share of low-detail cases with any `Clarification requested` is at least 3× the share for high-detail cases

#### Scenario: Effect off
- **WHEN** the log is generated with the switch off
- **THEN** the clarification shares for low, medium and high detail are within ±20% of each other

### Requirement: Realistic noise
After simulation, the generator SHALL remove a configured share of events at random (target 1.5%) and duplicate a configured share of events (target 0.5%). A duplicated event is an exact copy of an existing row.

#### Scenario: Noise rates on target
- **WHEN** the log is generated with default config
- **THEN** the share of missing events and the share of duplicated rows are each within ±0.3 percentage points of target

### Requirement: Explicit assumptions
Every number the generator uses (volumes, probabilities, delay parameters, handle times, noise rates, dates, working hours, seed) SHALL be defined in the generator config, not in simulation code.

#### Scenario: Changing an assumption
- **WHEN** a user changes a value in the config and reruns the generator
- **THEN** the output reflects the new value without any change to simulation code
