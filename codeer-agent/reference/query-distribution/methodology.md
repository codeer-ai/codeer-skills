# Methodology

## Goal

Construct an eval portfolio that can explain:

1. which customer tasks matter;
2. which failures have serious industry consequences;
3. why the selected cases receive their allocation;
4. which challenge mechanisms are intentionally tested;
5. how strong the supporting evidence is.

The persistent Query Distribution records two related but distinct views:

- an evidence-bounded estimate of real customer demand; and
- a designed eval portfolio that combines representative demand with deliberate
  risk coverage.

The test set is not a claim that it mirrors production traffic. Keep the Query
Distribution separate from the Behavior Contract: the former describes what is
expected to arrive, while the latter defines how the Agent should behave.

## Keep four concepts separate

### Base task

The outcome the customer wants, such as book, reschedule, check status, cancel, dispute, diagnose, or retrieve a record.

### Task-specific complication

A business-state boundary that only makes sense in the task lifecycle, such as changing an order after shipment or rescheduling after the cancellation deadline.

### Industry risk

The consequence of mishandling the case, such as delayed medical care, financial loss, privacy exposure, loss of legal rights, or service interruption.

### Challenge pattern

The communication or state-management mechanism that makes the same underlying task harder, such as contradiction, late disclosure, missing attachment, abuse, or fragmented multi-turn input.

## Evidence ladder

Use the strongest available evidence and label its limits.

1. **Target first-party conversations**: strongest evidence for language and demand within the target organization.
2. **Target operational records**: tickets, dispositions, search logs, escalation reasons, call categories, or CRM fields.
3. **Target public surfaces**: official FAQ, help center, forms, policies, reviews, complaints, and public Q&A.
4. **Close industry proxies**: comparable organizations, professional forums, regulator complaints, court cases, and incident reports.
5. **Cross-industry structural sources**: useful for task or challenge mechanisms, not target frequency.
6. **Expert construction**: useful for rare high-risk coverage; label as constructed.
7. **Synthetic expansion**: useful only after a real base pattern exists; never frequency evidence.

Record `evidence_tier`, `source_population`, `adaptation_distance`, and `confidence`.

## Research and distribution workflow

### 1. Frame

Define company scope, operating models, customer journeys, channels, geography, language, Agent actions, exclusions, and risk owner.

### 2. Map base tasks

Use official workflows and customer-facing surfaces first. Model lifecycle transitions instead of relying on a flat intent list.

### 3. Find friction and unmet states

Use public questions, reviews, complaint records, and project data to find:

- failed or blocked transitions;
- repeated contacts;
- missing prerequisites;
- exception requests;
- handoff and ownership gaps;
- common task combinations.

### 4. Build an industry-risk register

For each task or transition, ask what happens if the Agent:

- gives incorrect information;
- fails to escalate;
- takes an unauthorized action;
- discloses protected information;
- creates false certainty;
- delays a time-sensitive next step.

Keep severity independent from prevalence.

### 5. Estimate observed demand

Estimate `estimated_real_world_share` only when evidence permits. Prefer ranges or ordinal bands over false precision. Set the field blank when the evidence only proves existence.

### 6. Design the eval allocation

Set `eval_target_share` using:

- representative coverage;
- intentional rare-but-severe risk reserves;
- operating-model breadth;
- channel and language requirements;
- review budget.

Record `overweight_reason` whenever allocation exceeds the estimated real-world share.

### 7. Generate base inputs

Generate plain inputs before adversarial variants. Preserve source meaning without copying copyrighted text. Keep full multi-turn context in `input_display` and the latest evaluand in `target_user_query`.

### 8. Add challenge variants selectively

Use challenges that plausibly change the Agent's failure probability. Prefer one mechanism per diagnostic variant. Combine two only when the interaction is realistic or the risk demands stress testing.

### 9. Deduplicate and cluster

Exact uniqueness is insufficient. Assign:

- `cluster_id` for semantically similar scenarios;
- `variant_family_id` for the same base situation expressed through different challenge mechanisms.

Do not delete a variant merely because wording overlaps; retain it only when it tests a distinct state, disclosure order, channel, or failure mechanism.

### 10. Review in stages

Distinguish:

- generated candidate;
- evidence-checked candidate;
- domain-reviewed candidate;
- approved eval case;
- empirically validated eval case.

Schema validity does not prove domain correctness or representative value.

## Coverage saturation

Do not stop at an arbitrary row count. Stop when proposed additions no longer cover a meaningful gap across:

- operating model and task lifecycle;
- representative demand;
- industry risk;
- channel and language;
- relevant challenge mechanism;
- evidence confidence.

Report unresolved gaps instead of filling them with low-value synthetic variations.

## Empirical difficulty

Keep designed challenge separate from observed model difficulty:

- `designed_challenge_level`: structural expectation before testing;
- `empirical_failure_rate`: measured across runs or models;
- `observed_failure_modes`: actual errors.

Use empirical results to improve pattern knowledge, not to rewrite historical evidence.
