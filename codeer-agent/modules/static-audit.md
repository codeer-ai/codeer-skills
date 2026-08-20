# Static Audit

Run this read-only preflight before spending model calls on an eval. It checks
whether the KB, agent settings, eval cases, rubrics, evaluators, and version
target form one coherent test system. It reports defects and owners; it does
not diagnose an observed model failure or authorize any change.

Use [eval-debug.md](eval-debug.md) only after response, tool, retrieval, or judge
evidence exists for a specific run.

---

## When to run

Run the audit:

- before the first baseline eval;
- after KB, FAQ/routing, agent settings, cases, rubrics, evaluator templates,
  judge models, or assignments change, and before the next eval;
- before a full assigned-pair regression or publish decision; and
- whenever local manifests and server state may have drifted.

Do not run an eval or mutate server state as part of this module. Use registered
`codeer` read commands only. If required state cannot be read, record the gap in
`unresolved_questions`; do not guess.

---

## Step 1 — Pin the audited target

Record the exact target before comparing content:

- agent ID and AgentHistory/version ID;
- version number and status (`DRAFT`, `PUBLISHED`, or `ARCHIVED`);
- intended eval selection (`--latest` or a pinned `--history`);
- `response_mode`, model, system prompt, tools, handoff settings, and KB
  attachments on that version;
- published version, when different from the audited version;
- KB file/node/snapshot IDs and readiness state;
- evaluator IDs, templates, judge models, and intended case/evaluator
  assignments.

Never use *draft*, *latest*, *published*, and *response mode* as if they name the
same thing. A version mismatch is a blocker when it makes the planned eval test
a different configuration from the one under review.

---

## Step 2 — Inventory the effective system

Read the agent, KB, FAQ routes, eval cases, rubrics, and evaluators from the
server. When a local canonical manifest exists, compare it with server state
using `codeer eval reconcile` and direct reads as needed.

Build a compact dependency map:

```text
case -> assigned evaluator -> rubric -> required source/tool behavior
     -> agent version -> settings/tools -> KB attachment -> FAQ target
```

This map is evidence for the audit. It is not a proposal to change any layer.

---

## Step 3 — Audit source truth and retrieval wiring

Check all of the following:

1. Every required KB source is attached to the audited version and `READY`.
2. Each policy or fact family has a canonical owner. Flag material duplication
   across files when copies can drift or already disagree.
3. KB policy, expected outputs, and rubrics agree. Treat a direct contradiction
   or unresolved authoritative-policy ambiguity as a blocker.
4. Volatile facts are not duplicated into the system prompt. Facts that require
   current authoritative sources have a current-source path and verification
   rule.
5. FAQ/routing targets point to the current attached snapshot object and valid
   ranges. Flag stale node/snapshot IDs, cross-version targets, and routes to
   unattached or non-ready content.
6. Retrieval/routing, tool invocation, and platform behavior have distinct
   owners. Do not recommend a prompt workaround for a platform contract defect.

Absence from one retrieval result does not prove that content is absent from the
KB. This audit verifies configuration and source state, not runtime retrieval
quality.

---

## Step 4 — Audit agent settings

Read the complete relevant settings and use the ownership model in
[agent-settings.md](agent-settings.md). Check for:

- contradictory priorities, boundaries, or tool instructions;
- a tool rule that forbids deriving an input while its parameter or HTTP body
  contract requires the model to derive that input;
- duplicated facts or policies across the system prompt, tool configuration,
  KB, and handoff settings;
- handoff availability and triggers that disagree with eval expectations; and
- failure-specific or platform-bug workarounds encoded as general prompt rules.

Static contradictions are blockers when no response can reliably satisfy both
sides. Assign the finding to the component that owns the contract rather than
copying the symptom into the system prompt.

---

## Step 5 — Audit cases, rubrics, and evaluators

### Coverage and assignment integrity

Verify mechanically where possible:

- case IDs are unique and the intended case set is complete;
- every case has at least one assigned rubric/evaluator pair;
- every assignment refers to a known evaluator and a non-empty rubric;
- evaluators expected to cover a dimension have actual assignments;
- local manifest cases, labels, rubrics, and assignments match server state;
- the planned assigned-pair count equals the expected count; and
- when a completed-run claim is under review, results account for every planned
  pair.

An evaluator existing on the server is not coverage. For example, a Source
Support evaluator with zero assignments provides no Source Support coverage.
Running only Content Compliance is not a full eval when other assigned pairs
exist.

### Evaluator visibility

Inspect each evaluator template. Confirm that every rubric criterion can be
judged from the variables actually supplied, such as `{input}`, `{output}`,
`{rubric}`, `{expected_output}`, and `{tool_steps}`. Evaluators cannot be
assumed to see the agent prompt, KB, retrieved chunks, tool configuration, or
diagnosis notes.

If a criterion depends on hidden evidence, either make the criterion
self-sufficient, use an evaluator that receives the evidence, or mark the
criterion unjudgeable. Do not let the judge infer invisible source truth.

### Rubric fit and strictness

Review every mandatory criterion relative to the user's question and the
actual product risk. Ask:

> If this detail is omitted, would the answer become wrong, produce a wrong
> next step, or hide a material risk?

If not, make the detail optional or remove it. A correct, relevant, concise
answer should pass unless completeness itself is required by the question or
product contract. Flag rubrics that demand exhaustive lists, prices,
logistics, citations, handoff, or tool use without such a requirement.

Also check:

- expected output and rubric do not contradict the KB;
- criteria test observable behavior, not preferred wording;
- positive and negative handoff cases cover both *should transfer* and *should
  not transfer* boundaries; and
- different evaluators assigned to the same case do not impose incompatible
  requirements.

### Comparison validity

Record evaluator template and judge-model fingerprints with the baseline.
Scores before and after a judge/template change are not directly comparable.
Changing the agent and evaluator together also removes causal attribution;
separate those changes or explicitly declare a new baseline.

---

## Step 6 — Verdict and output contract

Use exactly one verdict:

- `PASS` — no blockers or warnings;
- `PASS_WITH_WARNINGS` — the run remains interpretable, but documented risks
  or non-blocking gaps remain; or
- `BLOCKED` — the planned eval would test the wrong target, use contradictory
  or unjudgeable truth, omit required assigned pairs, or otherwise produce
  results that cannot support the intended decision.

Return these top-level fields:

```yaml
verdict: PASS | PASS_WITH_WARNINGS | BLOCKED
blockers: []
warnings: []
observations: []
evidence: []
unresolved_questions: []
recommended_owners: []
```

Each finding should state the affected object, observed mismatch, decisive
evidence, consequence, and recommended owner. Keep direct evidence separate
from inference. `recommended_owners` names who or which component should decide
or repair the issue; it does **not** authorize an edit, server mutation, eval
run, or publish action.

---

## Mechanical checks versus human judgment

Good mechanical checks include ID uniqueness, attachment/readiness, stale FAQ
targets, missing or empty assignments, unknown evaluators, template variables,
manifest/server diffs, and planned-versus-completed pair counts.

Human judgment is required for canonical ownership, policy ambiguity, rubric
reasonableness, material-risk thresholds, instruction contradictions,
component ownership, handoff intent, source authority, and whether two
evaluator requirements truly conflict.

Do not add a script for a one-off audit. Add automation only after the same
deterministic check recurs and the available APIs expose enough data to produce
reliable results. A script may surface candidates; it must not silently resolve
policy or ownership decisions.
