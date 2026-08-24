# Methodology

## Goal

Create the smallest distribution that can answer:

1. what customers need help with;
2. when journey state changes correct handling;
3. how consequential a mistake would be;
4. how many acceptance cases should cover each query type; and
5. what concrete customer inputs make each type recognizable.

The Query Distribution describes expected work. The Behavior Contract defines
how the Agent should handle it. The eval portfolio tests the accepted pair.

## Keep four concepts separate

### Customer task

The outcome the customer wants, such as compare, choose, book, reschedule,
check status, cancel, dispute, troubleshoot, or retrieve a record.

### Journey state

A business-state boundary that changes correct handling, such as changing an
order after shipment or rescheduling after a deadline. Leave it blank when
state does not materially matter.

### Demand band

An ordinal view of expected demand: `core`, `common`, `occasional`, `rare`, or
`unknown`. Use `unknown` instead of false precision.

### Risk level

The consequence of mishandling a query: `normal`, `elevated`, `high`, or
`critical`. Risk is independent of frequency and interaction difficulty.

## Evidence ladder

Use the strongest available evidence:

1. target first-party conversations;
2. target operational records;
3. target public surfaces;
4. close industry proxies;
5. cross-industry structural sources;
6. expert construction; and
7. synthetic expansion after a supported base pattern exists.

Evidence can establish task existence, customer wording, risk, or demand.
Do not treat support for one claim as support for all four. Public examples and
constructed cases are not evidence of target-company frequency.

## Workflow

### 1. Frame the material scope

Define the company, product, customer journeys, locale, supported Agent
actions, exclusions, and consequence owner. Persist separate notes only when
scope or evidence limits need to survive the session.

### 2. Map behaviorally distinct tasks and states

Start from customer outcomes and official workflows. Split a query type only
when the distinction changes the correct answer, next move, authority boundary,
risk policy, or necessary eval coverage.

### 3. Assign demand and risk

Use a demand band supported by available evidence. Judge risk separately using
the relevant industry consequences. Do not add provenance and confidence
columns by default; explain material uncertainty in notes or the review.

### 4. Allocate target cases

Set `target_cases` as an integer based on:

- representative core demand;
- deliberate rare-but-severe reserves;
- material journey boundaries; and
- the available review budget.

The allocation need not mirror traffic. Explain a consequential departure in
the review or optional notes; do not require a per-row rationale field.

### 5. Add concrete examples

Add representative examples first. Then add boundary or risk examples only
when they expose distinct handling or failure mechanisms. Preserve necessary
multi-turn context and deidentify observed inputs.

Use provenance labels honestly:

- `observed` for deidentified target first-party examples;
- `adapted` for examples grounded in a source but rewritten for the target;
- `constructed` for deliberately authored coverage.

### 6. Deduplicate by meaning

Retain two examples only when they differ in task, journey state, disclosure
order, consequence, or a failure mechanism that matters. Wording variation
alone is not a reason to keep another row.

### 7. Review and stop

Stop when every material query type has a representative input and additions
no longer cover a meaningful task, state, risk, or boundary gap. Report
remaining uncertainty instead of filling the table with speculative metadata
or low-value synthetic variants.

## Production evidence

Use a sufficiently broad declared history scope before changing demand bands.
One failure or negative conversation normally adds an eval probe or a
deidentified example; it does not establish distribution drift.

If first-party data later supports a numeric share, add an optional
`observed_share` column only when a current decision will use it. Do not make
that field part of the default schema.
