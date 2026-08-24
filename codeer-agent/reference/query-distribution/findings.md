# Curated findings

Record generalized, reusable findings only. Keep raw dialogue and project-specific distributions in their original projects.

## Finding template

- **ID**
- **Status**: observed fact, reasonable inference, or proposal
- **Applicable operating models**
- **Observation**
- **Design implication**
- **Evidence and checked date**
- **Confidence**
- **Limitations or counterexamples**

## F-ABCD-001 — Model workflows, not only intents

- **Status**: observed fact plus reasonable inference
- **Applicable operating models**: order, account, subscription, billing, technical support
- **Observation**: ABCD v1.1 contains 10,042 conversations across 10 broad flows and 96 subflows. The dialogues interleave 89,372 customer turns, 95,129 agent turns, and 36,482 action records. Many outcomes depend on ordered verification, policy checks, state checks, and permitted actions.
- **Design implication**: represent support as lifecycle states, prerequisites, branches, and tool actions. Treat blocked transitions and policy branches as task-specific complications rather than generic linguistic challenges.
- **Evidence**: https://github.com/asappresearch/abcd, local v1.1 analysis, checked 2026-07-23
- **Confidence**: high
- **Limitations**: retail-oriented and deliberately balanced; do not infer another industry's frequency.

## F-ABCD-002 — The same request changes with business state

- **Status**: observed fact plus reasonable inference
- **Applicable operating models**: transaction, order, subscription, appointment
- **Observation**: ABCD workflow instructions condition actions on membership, purchase validation, shipment state, deadlines, and prior action completion.
- **Design implication**: create eval cells around consequential state boundaries, such as before versus after fulfillment, eligible versus ineligible, or reversible versus irreversible.
- **Evidence**: https://github.com/asappresearch/abcd, workflow guidelines, checked 2026-07-23
- **Confidence**: high
- **Limitations**: exact policy branches are dataset-specific.

## F-SGD-001 — State mutation is cross-task challenge

- **Status**: observed fact plus reasonable inference
- **Applicable operating models**: appointment, travel, order, account, advice, multi-service support
- **Observation**: the Schema-Guided Dialogue dataset contains 22,825 dialogues and 231,642 user turns across 20 service families. User actions include 15,926 negations, 7,373 intent negations, and 14,776 requests for alternatives.
- **Design implication**: model correction, negation, alternative requests, and constraint changes as reusable cross-task challenges. Preserve the base task while checking whether the Agent updates state instead of retaining stale values.
- **Evidence**: https://github.com/google-research-datasets/dstc8-schema-guided-dialogue, checked 2026-07-23
- **Confidence**: high
- **Limitations**: the dialogues are schema-guided and may overrepresent structured slot behavior.

## F-SGD-002 — Composite journeys deserve explicit coverage

- **Status**: observed fact plus reasonable inference
- **Applicable operating models**: multi-service and multi-party support
- **Observation**: 15,255 of 22,825 SGD dialogues contain more than one service; 16,331 user turns contain multiple frames.
- **Design implication**: add composite task cells only when customer journeys realistically cross services. Distinguish a new task from a modification of the current task.
- **Evidence**: https://github.com/google-research-datasets/dstc8-schema-guided-dialogue, checked 2026-07-23
- **Confidence**: high
- **Limitations**: multi-service prevalence is a property of SGD construction, not a target-industry frequency estimate.

## F-CONVABUSE-001 — Separate substantive task from hostility

- **Status**: observed fact plus reasonable inference
- **Applicable operating models**: all customer-facing support
- **Observation**: ConvAbuse annotates contextual user turns by explicit versus implicit abuse, target, and abuse type rather than treating all negative language as one class.
- **Design implication**: keep the underlying customer task and abuse challenge as separate labels. Test whether the Agent can preserve task resolution and safety boundaries without mirroring hostility or abandoning the legitimate request.
- **Evidence**: https://aclanthology.org/2021.emnlp-main.587/, checked 2026-07-23
- **Confidence**: high
- **Limitations**: chatbot context and English language; do not infer target-customer prevalence.

## F-CONVABUSE-002 — Target and directness change the response problem

- **Status**: reasonable inference grounded in dataset annotations
- **Applicable operating models**: complaint, escalation, public-facing chat
- **Observation**: hostility can be explicit or implicit and can target the system, an individual, or a generalized group.
- **Design implication**: vary target and directness only when they change escalation, safety, or response-boundary requirements. Do not inflate the eval with synonymous insults.
- **Evidence**: https://aclanthology.org/2021.emnlp-main.587/, checked 2026-07-23
- **Confidence**: medium
- **Limitations**: local annotation exports contain multiple annotator rows; counts require aggregation before use.

## F-METHOD-001 — Keep observed demand and eval allocation separate

- **Status**: proposal derived from the veterinary eval attempt
- **Applicable operating models**: all
- **Observation**: public and adapted sources can establish task existence and risk without supporting precise target-company traffic shares.
- **Design implication**: record `estimated_real_world_share` separately from `eval_target_share`, evidence confidence, and intentional risk overweighting.
- **Evidence**: veterinary candidate-pool retrospective, checked 2026-07-23
- **Confidence**: high
- **Limitations**: allocation still requires reviewer judgment when first-party frequency is absent.
