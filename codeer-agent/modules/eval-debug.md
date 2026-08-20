# Eval Debugging

Use this module after an eval or live test has produced dynamic evidence: a
response, tool trace, retrieval trace, evaluator result, or platform error. It
diagnoses the strongest supported causal mechanism and defines the smallest
coherent correction and regression set.

If no dynamic evidence exists yet, use [static-audit.md](static-audit.md)
instead. Do not mix a whole-system preflight into the diagnosis of one run.
Before proposing an agent-settings change, read
[agent-settings.md](agent-settings.md) and apply its target-state gate.

---

## Entry point and evidence packet

For each result under review, capture:

- case ID/label, input, expected output, evaluator ID, rubric, score, and
  evaluator reason;
- exact agent ID and AgentHistory/version, status, `response_mode`, and model;
- generated response and completion/error state;
- tool calls, arguments, results, and ordering;
- retrieval queries, files/chunks/routes returned, and KB snapshot IDs;
- evaluator template and judge-model fingerprint; and
- planned assigned-pair count versus completed result count for the run.

Surface non-perfect results to the user before changing anything. Also inspect
selected perfect scores when needed: a false pass can reveal a coverage gap.
Missing evidence lowers confidence; it does not license a guessed diagnosis.

---

## Dynamic causal chain

Inspect evidence in this order and stop at the earliest component that fully
explains the observation:

```text
response quality -> rubric/source truth -> tool use -> retrieval
                 -> KB content -> evaluator/judge noise -> platform defect
```

The nearest visible symptom is not necessarily the owner. Do not paste failure
wording into settings; identify the owning component first.

### 1. Response quality

Read the response against the user's question before trusting the score.

- Good response, low score: investigate rubric, source truth, or evaluator.
- Bad response: state what is wrong and continue down the chain.
- Good response, perfect score: no fix unless other evidence exposes a gap.

### 2. Rubric and source truth

For the specific pair, determine whether the rubric is correct, observable, and
proportionate to the question.

- If KB, expected output, and rubric disagree, surface the exact conflict for
  human resolution before changing the agent.
- If the evaluator lacks required KB or tool evidence, the pair is unjudgeable
  as written.
- If a correct concise answer failed because the rubric demands details whose
  omission would not cause a wrong answer, wrong next step, or material risk,
  classify evaluator strictness rather than agent failure.

If the evidence suggests suite-wide drift, route that broader check to
[static-audit.md](static-audit.md); keep this diagnosis tied to the observed
pair.

### 3. Tool use

Compare actual tool actions with the tool contract, not with prose claims in
the final answer.

- skipped required tool;
- called the wrong tool;
- passed invalid, invented, or improperly derived arguments;
- repeated calls because stop conditions or tool boundaries were unclear; or
- behaved correctly and should proceed to retrieval/content analysis.

Read the complete system and tool settings before assigning ownership. A tool
contract, handoff setting, or platform behavior may own the defect instead of
the system prompt.

### 4. Retrieval

When a KB tool ran, distinguish these cases:

1. **Required source unavailable** — canonical content was not attached or
   `READY`; runtime retrieval cannot reach it.
2. **Canonical file not reached** — source exists, but the query or route did
   not select it.
3. **Correct file, wrong passage** — file was selected, but chunking, range, or
   query specificity missed the relevant content.
4. **Correct evidence retrieved** — move to KB content or response-use policy.

A missing retrieval hit is not proof that the fact does not exist anywhere in
the KB. Verify the source inventory before making that claim.

### 5. KB content and response use

Determine whether the retrieved source is missing, ambiguous, duplicated,
stale, or internally contradictory. If the source is sound but the response
embellished or distorted it, inspect source-use priorities and evidence
boundaries in the complete settings.

Do not add an FAQ to compensate for missing content, and do not add a prompt
rule when the source itself owns the error.

### 6. Evaluator and judge

Classify false fail, false pass, ambiguous rubric, evaluator visibility gap,
and stochastic judge noise separately.

- A false pass is a coverage defect, not proof of agent quality.
- Inconsistent repeat scores may justify clearer criteria or calibrated
  pass/fail examples.
- A judge model or template change creates a new baseline; do not compare its
  scores directly with the prior baseline.

Accept an imperfect score when the response is correct and further changes
would only overfit evaluator preference.

### 7. Platform defect

Use this classification only when evidence shows a contract-level failure
outside the configured agent, such as a valid FAQ/filter target being ignored,
the wrong snapshot being queried, or required trace data not reaching an
evaluator despite the documented template contract.

Record reproduction evidence, expected versus actual platform behavior, and
affected scope. Do not encode a platform bug as a prompt workaround unless the
user explicitly approves a labeled temporary containment.

---

## Context Object FAQ as a retrieval fix

Use a Context Object FAQ only when:

- the canonical file is uploaded, attached, and `READY`;
- the agent issued a reasonable query;
- semantic retrieval missed or under-ranked that source; and
- the platform's FAQ/filter contract is working for the relevant snapshot.

Do not use it when content is missing, the agent never queried, the target is a
stale or cross-version snapshot, file structure is the real defect, source
truth is unresolved, or platform filtering blocks the route.

When justified:

1. Read the current canonical file and `snapshot_object_id`.
2. Preview the representative question and target with
   `codeer kb faq-create ... --dry-run` or `faq-update ... --dry-run`.
3. Show the diff and wait for explicit user approval.
4. Apply, then read the FAQ back and confirm its target/range.
5. Re-run the reproduction and the impact-based regression set below.

Use line ranges only when the passage is stable and the intended question
should land on that specific section.

---

## Target-state design

State the strongest supported mechanism, alternatives considered, uncertainty,
and component owner before drafting a change. Prefer, in order:

1. no change when the response is acceptable or the defect is elsewhere;
2. remove a contradiction or obsolete constraint;
3. consolidate, clarify, reorder, or move existing information;
4. replace a narrow rule with a stable invariant; and
5. add a new rule only when the requirement is genuinely absent.

For any agent-settings diff, use the full gate in
[agent-settings.md](agent-settings.md). For rubric edits, show before/after
text, source truth, evaluator visibility, and why the criterion is necessary.
Changing the evaluator establishes a new baseline.

---

## Impact-based regression strategy

Fast iteration must test more than the failing case. Every proposed correction
needs, where applicable:

- the exact reproduction;
- a paraphrase or generalization;
- a nearby boundary;
- a negative control; and
- impacted cases that previously passed.

Choose the additional impact set from the changed owner:

| Changed owner | Minimum impact set |
| --- | --- |
| One case rubric | The pair plus calibration examples and adjacent cases using the same criterion |
| FAQ/routing target | Reproduction, same-source variants, similar routes, boundary, negative control |
| One KB policy/file | Dependent Content/Source pairs and routes to that source |
| Handoff policy/settings | Should-transfer, should-not-transfer, boundary, and affected Content pairs |
| Global KB/tool configuration | All KB/tool-backed cases; full regression is usually required |
| System prompt or model | Full assigned-pair regression |
| Evaluator template or judge model | All pairs assigned to it and a new baseline |
| Retrieval/platform contract | All cases using the affected KB, FAQ, filter, source, or evaluator trace; then full regression before release |

Use dependency labels when they reliably identify a local impact set. Missing or
untrusted dependency metadata expands the set; it does not justify testing less.

For stochastic P0/P1 behavior, run multiple trials and report the distribution.
One passing trial is not completion. After a root-cause batch completes and
before publish, run all assigned case/evaluator pairs. A Content-only sweep is
not a full regression when other assignments exist.

---

## Improvement loop

1. Assemble the evidence packet and classify the earliest supported cause.
2. Define the target state, owner, regression risk, and impact set.
3. Present every proposed server-state diff and wait for user approval.
4. Apply the approved change, then read back the effective state.
5. Re-run reproduction, generalization, boundary, negative control, and
   previously-passing impacted cases.
6. After any KB/settings/case/rubric/evaluator state change, run
   [static-audit.md](static-audit.md) before the next full regression.
7. Run the required full assigned-pair regression and compare only compatible
   baselines.
8. Stop when evidence supports the target state, or accept/flag the remaining
   issue when another change would overfit or add unjustified complexity.

Publish remains a separate action requiring explicit user confirmation. A
passing reproduction or completed batch does not authorize publish.
