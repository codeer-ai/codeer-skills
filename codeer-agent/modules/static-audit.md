# Static Audit

Use this module to inspect static configuration evidence before spending model
calls on an eval. A review may be narrow (for example, one rubric and its
evaluator) or a full pre-eval gate across persistent design artifacts, the KB,
agent settings, cases, rubrics, evaluators, assignments, and version target.
State the audited scope so a narrow review is never mistaken for whole-system
clearance.

The audit produces evidence-backed findings and likely owners. It does not
diagnose an observed runtime failure, design the resulting repair, or authorize
any change. Send findings that need a change to
[repair-planner.md](repair-planner.md).

Use [eval-debug.md](eval-debug.md) only after response, tool, retrieval, or judge
evidence exists for a specific run.

---

## When to run

Run a full audit:

- before the first baseline eval;
- after Query Distribution, Behavior Contract, KB, FAQ/routing, agent settings,
  cases, rubrics, evaluator templates, judge models, or assignments change, and
  before the next eval;
- before a full assigned-pair regression or publish decision; and
- whenever local manifests and server state may have drifted.

Before implementation, this module may also perform a local-only scoped review
of Query Distribution against the draft case portfolio and Behavior Contract
against the draft cases. Server target pinning and runtime checks are not
applicable to that limited review. State the limited scope explicitly; it is
not a full Static Audit clearance.

Run a scoped audit when the user asks about one rubric, evaluator, case,
assignment, source relationship, or other bounded static concern. Read the
smallest evidence set that can support the requested conclusion, but expand the
scope when the local object cannot be interpreted without its evaluator,
source truth, assignment, or version context.

For a maintained query-led customer guidance Agent, read the persistent
`.codeer/design/query_distribution.csv` and
`.codeer/design/behavior_contract.md`. Include distribution-to-eval-portfolio
and contract-to-acceptance-eval alignment in a full audit. For a legacy Agent,
do not fabricate either artifact; record missing design evidence and limit the
conclusion accordingly.

Do not run an eval or mutate server state as part of this module. Use registered
`codeer` read commands only. If required state cannot be read, record the gap in
`unresolved_questions`; do not guess.

---

## Finding method

Use the same evidence discipline for both scoped and full audits. A useful
finding communicates, in whatever prose, bullets, table, or other format best
fits the task:

- what was observed and which object is affected;
- the decisive static evidence;
- why the mismatch matters and what consequence it can cause;
- the component or person most likely to own the decision; and
- material uncertainty or missing context.

Do not require issue codes, a fixed taxonomy, confidence percentages, JSON, or
another rigid input/output schema. Add labels, severity, or structure only when
they help the current review. Keep direct evidence distinct from inference,
and do not turn a repair idea into evidence that the finding is true.

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
  assignments;
- Query Distribution revision, evidence window, sampling scope, confidence,
  open gaps, and intended eval allocation, when applicable; and
- Behavior Contract revision and applicable Agent/version, and whether the
  cases are intended to express that contract.

For a local-only pre-implementation review, record the accepted design files
and reviewed draft-case revision; mark server version, runtime, Tool, and
assignment evidence as not applicable rather than inventing it.

Never use *draft*, *latest*, *published*, and *response mode* as if they name the
same thing. A version mismatch is a blocker when it makes the planned eval test
a different configuration from the one under review.

---

## Step 2 — Inventory the effective system

Read the persistent design artifacts locally and the agent, KB, FAQ routes,
eval cases, rubrics, and evaluators from the server. When a local canonical
manifest exists, compare it with server state using `codeer eval reconcile` and
direct reads as needed.

Build a compact dependency map:

```text
accepted Query Distribution -> eval portfolio allocation -> acceptance cases
  (when applicable)            -> assigned evaluator -> observable evidence
accepted Behavior Contract (outcomes, guardrails, decision policies)
  -> acceptance case -> assigned evaluator -> rubric -> observable evidence
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

Read the complete relevant settings and read [agent-settings.md](agent-settings.md)
in full so the audit uses its current design principles, ownership model, and
prompt-residency criteria. Apply only the sections that define the expected
configuration; do not perform the repair-planning work owned by Repair Planner.
Check for:

- contradictory priorities, boundaries, or tool instructions;
- a tool rule that forbids deriving an input while its parameter or HTTP body
  contract requires the model to derive that input;
- duplicated facts or policies across the system prompt, tool configuration,
  KB, and handoff settings;
- handoff availability and triggers that disagree with eval expectations;
- failure-specific or platform-bug workarounds encoded as general prompt rules;
  and
- any setting, KB content, or Tool instruction directing the Agent to assert
  scarcity, urgency, authority, social proof, price, eligibility, or a Tool
  outcome that the available source or actual Tool response cannot substantiate.

Static contradictions are blockers when no response can reliably satisfy both
sides. Assign the finding to the component that owns the contract rather than
copying the symptom into the system prompt.

---

## Step 5 — Audit cases, rubrics, and evaluators

### Query Distribution and eval-portfolio alignment

When the accepted distribution is available, compare it with the designed case
portfolio and intended run. Confirm that:

- each material core/common query type and intentionally reserved
  high-consequence query type has meaningful coverage;
- case counts align with `target_cases` or have an accepted, explicit
  departure;
- every covered query type has a concrete linked example;
- example count, constructed variants, and public evidence are not used as
  unsupported prevalence evidence; and
- material document-level scope or evidence limitations remain visible when
  they affect the audit conclusion.

Treat omission of a material high-consequence query type required for the
intended decision as a blocker. Treat an interpretable small-portfolio
allocation difference as a warning unless it invalidates the intended gate.
Static Audit assesses the accepted model and portfolio; it does not estimate a
new distribution or choose the repair.

### Behavior Contract and acceptance-eval alignment

When the accepted contract is available, first check the contract itself
against the canonical Evidence and autonomy boundaries in
[consultative-guidance.md](consultative-guidance.md). Verified scarcity,
urgency, authority, social proof, prices, eligibility, and Tool outcomes are
allowed; a contract requiring fabrication, exaggeration, or unsupported claims
is a blocker even when the cases, rubrics, settings, KB, and Tools all agree
with it. The contract inherits these canonical boundaries without restating
them; missing duplicated boundary prose is not a contract-coverage gap.

Then compare the contract semantically with the cases, expected outputs, and
rubrics. Use a simple judgment review. Confirm that:

- each material journey's accepted customer or task outcome, acceptable
  alternative outcome, and guardrails are represented by observable decision
  coverage where the intended gate requires it;
- no case or mandatory criterion demands behavior absent from or contradictory
  to the contract;
- answer-versus-question initiative, consent before consequential actions,
  recommendation boundaries, and handoff expectations agree with the material
  decisions in the contract, while truthfulness and uncertainty also satisfy
  the canonical boundaries;
- an optional discovery strategy has not become a mandatory script or fixed
  wording requirement;
- material high-consequence behaviors and nearby boundaries have some
  observable coverage; and
- expected outputs and rubrics test decisions and outcomes without
  over-specifying phrasing.

Where the contract uses an entry condition or operational profile to select a
different policy, confirm that the distinction is observable in the case and
actually changes correct handling. Do not require a Persona taxonomy or a
separate operational case for profile variation that leaves the decision
policy unchanged. A fairness, outcome-comparison, or heterogeneous-effect
stratum may still belong in production analysis or sampling metadata without
becoming a Query Type, contract branch, or runtime Persona inference.

Assess decision coverage, not document length or one-to-one rule/case mapping.
One contract principle may govern several journeys and cases; concrete variants
belong in the eval portfolio unless they expose a distinct material decision.

Treat an explicit contradiction or violation of a hard contract boundary as a
blocker. Treat a material but still interpretable coverage omission as a gap or
warning unless the intended decision requires that behavior to be tested in
the current run. Leave the exact case, rubric, contract, or implementation
change to the appropriate follow-on module.

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

If a criterion depends on hidden evidence, identify whether the static defect
is an evaluator-visibility gap, a non-self-sufficient rubric, or an
unjudgeable requirement. Do not choose or draft the repair here, and do not let
the judge infer invisible source truth.

### Runtime observability and satisfiability

Evaluator placeholders describe what the judge receives, not whether runtime
can produce meaningful evidence in those fields. For criteria involving tools
that end generation, request interaction, replace the model response, or
validate arguments after the model call, inspect documented runtime behavior,
tool capability metadata, or another read-only source of the execution
contract.

Confirm that a plausible compliant live trace can both satisfy the rubric and
reach the evaluator in the expected evidence shape. In particular, flag:

- content criteria whose `{output}` is fixed, suppressed, or replaced by the
  runtime path being tested;
- tool-argument criteria that the live schema or validator cannot accept;
- source-truth criteria assigned to an evaluator that cannot see the relevant
  retrieval evidence; and
- multiple pairs that catch no distinct material failure beyond an existing
  assignment.

Treat an impossible or runtime-unobservable requirement as a blocker for that
pair. Missing runtime metadata is unresolved evidence, not permission to assume
that the evaluator can observe the behavior.

### Rubric fit and strictness

Review every mandatory criterion relative to the user's question and the
actual product risk. Ask:

> If this detail is omitted, would the answer become wrong, produce a wrong
> next step, or hide a material risk?

If not, flag it as an unnecessary mandatory criterion. A correct, relevant,
concise answer should pass unless completeness itself is required by the
question or product contract. Flag rubrics that demand exhaustive lists,
prices, logistics, citations, handoff, or tool use without such a requirement.
Leave the exact rewrite or evaluator reassignment to the Repair Planner.

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

## Step 6 — Report the findings

For a full pre-eval gate, use one verdict:

- `PASS` — no blockers or warnings;
- `PASS_WITH_WARNINGS` — the run remains interpretable, but documented risks
  or non-blocking gaps remain; or
- `BLOCKED` — the planned eval would test the wrong target, use contradictory
  or unjudgeable truth, omit required assigned pairs, or otherwise produce
  results that cannot support the intended decision.

Report the verdict first, followed by the evidence-backed findings, unresolved
questions, and likely owners. State when a material category has no findings.

For a scoped audit, state the scope and report the findings without implying
that the rest of the test system passed. A scoped verdict is optional; use it
only when it makes the bounded decision clearer.

No report format is mandatory. The content must remain reviewable and preserve
the finding method above. A likely owner identifies who or which component
should decide the issue; it does **not** authorize an edit, server mutation,
eval run, or publish action. When a change is warranted, hand the findings to
[repair-planner.md](repair-planner.md) rather than drafting local patches in
the audit.

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
