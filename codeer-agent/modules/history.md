# History Analysis

Analyze production conversations to drive continuous improvement. This module
is the entry point for Phase 2 (Improve).

Before analyzing behavior or demand, read the accepted
`.codeer/design/query_distribution.csv`,
`.codeer/design/query_examples.csv`, and
`.codeer/design/behavior_contract.md`. They answer different questions: what
customer work was expected, what concrete inputs represent it, and how the
Agent was intended to handle it. For a legacy Agent without these artifacts,
surface the missing design evidence and reconstruct it with user acceptance
before making strong claims about contract divergence or distribution drift.

---

## Step 0 — Define the improvement outcome

Before broad sampling or coding, establish from the request, accepted design
evidence, and available operational context what outcome this analysis is meant
to improve. Reuse stable journey outcomes and guardrails from the accepted
Behavior Contract, but do not assume that they fully specify the current
research question. Ask the user only about unresolved choices that would
materially change the analysis. Define only what the current decision needs:

- the primary outcome and any secondary outcomes or guardrails;
- the customer intention, population, or entry-condition stratum in scope;
- the observation horizon, such as one response, one task, multiple Histories,
  a work object, or a longitudinal user outcome;
- observable success, failure, acceptable alternative, and missing-evidence
  handling;
- the decision this analysis must inform and what result could change it; and
- whether the work is descriptive, diagnostic, predictive, or intended to
  support a later causal test.

Choose the analysis unit after defining the outcome. Conversation, exchange,
semantic Episode, customer task, History, work object, user, and cohort are
candidate units rather than one mandatory hierarchy. Use the minimum unit that
can observe both the outcome and the Agent decisions that may affect it. When a
semantic Episode boundary is itself inferred, keep the underlying messages and
Tool events available so uncertain segmentation does not become hidden fact.

Apply an outcome-relevance gate before adding a field, profile, category, or
coding dimension. Keep it only when it helps select an Agent decision, measure
or explain an outcome, support a fair comparison, protect a material
guardrail, or drive a named Contract, Eval, settings, Tool, KB, handoff, or
experiment decision. Otherwise omit it.

---

## Step 1 — Pull production data

Not all channels provide explicit feedback (thumbs up/down). Conversation
history is the primary source of truth.

```bash
codeer history list --agent <agent_id> --limit 50 --offset 0
```

Treat this as the first page, not automatically as the complete result set. Do
not fetch every page by default. Continue only when the task needs broader
coverage—for example, a complete audit, a frequency/distribution estimate, a
specified time window, or enough examples to support a conclusion.

If the page contains exactly `limit` histories and broader coverage is still
needed, request the next page by increasing `offset` by `limit`:

```bash
codeer history list --agent <agent_id> --limit 50 --offset 50
```

Repeat as needed. Stop when a page contains fewer than `limit` histories or
when the evidence scope is sufficient for the task. Never treat absence from
the first page as absence from all history. When reporting findings, state how
many histories and pages were inspected and, when relevant, the covered date
range.

### Negative feedback first

Start with flagged turns where feedback is available:

```bash
codeer history negative-feedback --agent <agent_id>
```

Negative feedback and other failure signals provide an enriched diagnostic
sample, not a representative denominator. When the analysis claims demand,
frequency, ordinary success, or association with an outcome, also define a
representative or explicitly stratified sample and state its selection frame.
Use failure and protection cases in parallel for mechanism discovery and Eval
creation without presenting their share as the production rate.

### Then browse conversations

For channels without feedback signals, export the complete Chat V2 parts before
analyzing them. Standard output is deliberately a bounded preview and must not
be treated as the complete history:

```bash
codeer history conversations <history_id> \
    --out .codeer/current/history-<history_id>.json
```

Read the saved JSON selectively. It contains every client-visible part across
all API pages, including tool calls/results, attachments, interactions,
feedback, and passthrough metadata. Preserve the raw artifact when extracting
eval cases; summaries are navigation aids, not evidence of absence.

To continue an existing persisted history after the user approves the write:

```bash
codeer history send <history_id> --message "Follow-up question" --timeout 240
```

This uses the agent's current published version through Chat V2 structured SSE
with `stream: true`. It only reports success after `response.completed`. If it
times out, returns `response.failed`, or disconnects early, export and inspect
the history before retrying because the turn may already have been persisted.

---

## Step 2 — Analyze entry conditions and Agent decisions

Use two explanatory axes around the accepted analysis outcome:

1. **Observable user entry condition** — the current intention, stated goal
   specificity, supplied context, existing work object, journey or readiness
   state, urgency, constraints, risk, authority, and only evidence-supported
   operational profiles that can change correct handling.
2. **Agent decision policy** — the decision point, evidence available at that
   point, missing information and consequence of error, chosen answer, question,
   retrieval, recommendation, draft, Tool, validation, action, or handoff
   policy, and a plausible alternative policy.

Entry conditions are context the Agent must adapt to, not a way to assign the
Agent's responsibility back to the user. Separate what existed before the
Agent acted from what the Agent could observe and from what happened afterward.
Do not infer personality, motivation, sophistication, or another latent profile
from wording unless the evidence supports it and the distinction has a named
decision use.

Action verbs such as `answer`, `ask`, `retrieve`, `draft`, `execute`, or
`handoff` are useful trace labels but not complete improvement findings. Analyze
the policy at the level that can guide a later change: under what observable
condition the Agent chose the move, why an alternative may have been more
appropriate, what immediate state changed, and which accepted outcome or
guardrail the difference may affect.

Treat user correction, continuation, abandonment, reuse, feedback, and return
as observed behavior, outcome evidence, mediators, or sampling signals. Do not
equate them with quality or stop the diagnosis there. Trace backward to the
Agent decision that may have enabled or impeded the target outcome, while
preserving meaningful alternative explanations.

Classify outcome-anchored findings as:

- **Failures** — an Agent decision or result violated the accepted outcome,
  guardrail, source truth, Tool contract, or hard boundary;
- **Improvement opportunities** — the Agent may have chosen a less effective
  policy despite remaining technically acceptable; and
- **Successful patterns** — an Agent decision appears to advance or protect
  the outcome and needs protection from regressions.

### Map findings to MECE categories

For each actionable Agent improvement that proceeds to Eval coverage, map the
finding to an existing category from the eval suite (established during
initial eval case design). If it does not fit, propose a new category as a
coverage gap. Do not force descriptive demand, outcome, fairness, selection,
or product observations into the Agent Eval taxonomy when they have not passed
the Actionability Gate.

### Separate evidence from diagnosis

Do not translate a finding directly into a prompt rule or other fix. Record:

- the observed behavior and its user or business consequence;
- where the behavior diverged from the intended outcome;
- related successes or failures that support or challenge the same mechanism;
- the strongest current mechanism hypothesis and meaningful uncertainty.

Group findings by shared behavioral mechanism when evidence supports it, not
only by surface topic. A single finding may still expose a structural defect;
multiple examples are useful evidence, not a prerequisite for diagnosis.

When an accepted Behavior Contract is available, distinguish two decisions:

- **Implementation divergence** — the desired behavior is already clear, but
  the current settings, KB, Tools, handoff, retrieval, or platform behavior did
  not implement it.
- **Contract improvement** — the current implementation may match the accepted
  contract, but the evidence suggests a different customer-guidance behavior
  would create a materially better experience, or the contract is too
  ambiguous to decide.

Do not infer the contract from current settings or eval rubrics when the
accepted design context is unavailable. Surface the gap for user confirmation.

### Actionability gate

Before presenting an item as an Agent improvement finding, make the following
ideas reviewable in the clearest format for the task:

- the target outcome, relevant population or intention, and guardrails;
- the observable entry condition and Agent decision point;
- the action policy the Agent followed and the successful, failed, or
  counterfactual alternative;
- the immediate observed effect and meaningful alternative explanations;
- the strongest mechanism hypothesis and its evidence limits;
- a modifiable behavioral treatment candidate stated at a reusable policy
  level rather than as production wording;
- the likely owner, such as the Behavior Contract, system prompt, Tool policy,
  KB, retrieval, handoff, evaluator, UI, or platform; and
- the reproduction, generalization, boundary, protection, production, or
  experimental evidence needed next.

This is a coverage lens, not a required report schema. If the evidence does not
identify a decision point, alternative policy, treatment candidate, or
testable downstream use, retain the observation as descriptive product,
demand, or selection evidence rather than calling it an Agent improvement.
The likely owner is provisional until Eval Debug or Repair Planner reads the
complete evidence and configuration.

### Query-distribution analysis

Use [query-distribution.md](query-distribution.md) when the selected history
scope is broad enough to inform demand. Treat the conversation or customer task
as the unit rather than counting messages. State the inspected channels, date
range, population, selection criteria, and material sampling limits in the
analysis or optional notes rather than adding them to every distribution row.

Compare observed customer tasks, journey states, demand, and risks with the
accepted distribution and examples. Distinguish:

- **distribution drift** — meaningful new evidence changes a customer task,
  journey state, demand band, risk level, or target case allocation;
- **example gap** — a meaningful customer input is missing from the accepted
  examples without changing the underlying distribution;
- **eval-portfolio gap** — the accepted distribution already contains the
  query type, but reviewed cases do not cover it adequately; and
- **individual behavior evidence** — a conversation exposes a failure or
  success without supporting a frequency conclusion.

One failure, negative conversation, or first-page sample normally creates an
eval probe or deidentified example, not a distribution revision. Never copy raw
sensitive conversations into either canonical CSV.

### Tool usage analysis

Separate trace facts from normative judgments. Trace facts include the Tool
selected, arguments, result, error, latency, repetition, and whether the result
was referenced. Judgments such as whether the Agent should have called the
Tool, chose the best route, stopped at the right time, used the result
correctly, or advanced the task require a policy, reference trajectory,
external end state, or explicit human rubric.

Look for decision-policy patterns in tool behavior:

- Is a tool being called too often? (e.g. 13 KB calls for a simple question)
- Is a tool being skipped when it should be used?
- Are tool queries effective or are they missing relevant content?
- What observable evidence gap justified the call, what decision or work
  object did the result change, and what stopping condition applied?

### Identify unserved scenarios and useful probes

Find specific user query patterns that the current eval suite doesn't cover.
These become candidates for new eval cases. When a mechanism remains
uncertain, identify paraphrases, nearby boundaries, or successful contrasts
that could distinguish the plausible causes.

---

## Step 3 — Present and prioritize

Present observations separately from inferences. Include evidence, consequence,
mechanism hypothesis, uncertainty, successful patterns to protect, and any
Actionability Gate treatment candidate. Make clear whether each item is a
description, selection or demand signal, Agent improvement hypothesis,
supported implementation divergence, or causal conclusion. Recommend which
categories need investigation or new cases without prescribing a settings
patch from the surface symptom. When distribution drift is proposed, show the
sample scope, evidence limits, and before/after distribution separately from
behavioral findings. Let the user pick which categories to work on and in what
order.

---

## Step 4 — Choose the follow-on path

After the user chooses priorities, keep distribution, contract, and
implementation decisions distinct.

### Meaningful Query Distribution update

Use [query-distribution.md](query-distribution.md) to present the complete
revision and obtain user acceptance before replacing
`.codeer/design/query_distribution.csv` or
`.codeer/design/query_examples.csv`. Then:

1. update target case allocation and example coverage when warranted;
2. revise `.codeer/design/behavior_contract.md` only when the new demand model
   changes the appropriate customer experience or a stable risk policy; and
3. change Agent Settings, KB, or Tools only after any contract revision is
   accepted and expressed in eval cases.

A distribution-only update may end with eval-portfolio maintenance and no
runtime Agent change.

### Implementation divergence against an unchanged contract

Transition to **eval-cases**:

- Each distinct failure behavior → a representative reproduction case where
  the current agent should fail
- Each successful pattern → a case that must keep passing
- Each unserved scenario → a new case for coverage
- Each uncertain mechanism → only the generalization, boundary, or contrast
  probes needed to distinguish the plausible causes

Run Static Audit, then run a focused pre-change eval on the current published
version (`--history` flag) before changing any settings:

```bash
codeer eval run \
    --agent <agent_id> --history <published_history_id> \
    --evaluator <evaluator_id>
```

Export the pre-change results and pin them so they survive the improvement
cycle:

```bash
codeer eval export --agent <agent_id> --out .codeer/current/eval_table/
```

Automatically copy `.codeer/current/eval_table/` plus the exact Agent/version,
evaluator-template, and judge-model context to
`.codeer/pinned/<date>-pre-change/` before changing the Agent. This is a required
comparison point, not an optional pin prompt. Ask about pinning only for other
temporary debug or batch evidence.

The audit must verify the exact version, sources, settings, cases, rubrics,
evaluators, and assignments. New reproduction cases should fail; protection
cases should pass. These results are evidence, not the scope or wording of the
eventual change. Then hand off to **eval-debug** for causal findings and to
**repair-planner** when accepted findings warrant an implementation or eval
change.

### Intentional Behavior Contract improvement

Before drafting a runtime repair:

1. Use [consultative-guidance.md](consultative-guidance.md) to compare the
   accepted and proposed customer behavior, recommend the suitable dialogue or
   discovery strategy, and obtain user acceptance.
2. Persist the accepted `.codeer/design/behavior_contract.md`, then update or
   add acceptance cases and rubrics. They should express the revised behavior
   and protect still-valid successful patterns.
3. Run Static Audit, then run the focused cases against the current published
   Agent. Expected failures make the intended behavioral delta visible; they
   are not proof that the current Agent was defective under the old contract.
4. Hand the accepted contract and pre-change evidence to **repair-planner**,
   then use the owning modules for Agent Settings, KB, Tools, handoff, or other
   approved changes.
5. Re-run Static Audit, the focused impact set, and the required full
   assigned-pair regression before any publish decision.
