# Eval Debugging

Use this module after an eval or live test has produced dynamic evidence: a
response, tool trace, retrieval trace, evaluator result, or platform error. It
diagnoses the strongest supported causal mechanism and produces evidence-backed
findings. It does not design or apply the correction. Send findings that need a
change to [repair-planner.md](repair-planner.md).

If no dynamic evidence exists yet, use [static-audit.md](static-audit.md)
instead. Do not mix a whole-system preflight into the diagnosis of one run.

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

## Failure-cluster orchestration

When a run contains several independent failure groups, the parent Agent may
delegate clusters to read-only sub-agents. If a prior comparable run or planned
Agent change exists, use [regression-triage.md](regression-triage.md) first to
match pairs, organize deltas, and preserve the Agent-version diff. Triage does
not assign the causal owner; every non-perfect result still enters this module.

Build provisional work units from a shared failure signature or decision
mechanism, such as the same rubric conflict, Tool path, retrieval route, source
family, handoff boundary, or evaluator visibility problem. Do not cluster only
by topic, numeric score, or similar evaluator wording. Do not assign one worker
per case unless a unique high-consequence trace requires independent review.

The parent must pin the complete run evidence and static anchors before
delegation. Give each worker the relevant cases and traces, the accepted
Behavior Contract, exact Agent/version and KB snapshot, evaluator template and
judge fingerprint, plus selected passing controls or successful contrasts.
Withhold a proposed repair or preferred owner when independent diagnosis is the
point of the delegation.

Each worker applies the full dynamic causal chain to its cluster and returns
the observation, decisive evidence, earliest supported mechanism, consequence,
likely owner, alternative explanations, uncertainty, and smallest
discriminating evidence needed. The parent then checks whether apparently
separate clusters share an earlier common owner, whether one cross-cutting eval
defect explains both failures and false passes, and whether passing controls
contradict the proposed mechanism. Resolve conflicts from the underlying traces
rather than averaging worker confidence or taking a majority vote.

---

## Behavior Contract decision boundary

Read the accepted `.codeer/design/behavior_contract.md` and use it as the
design anchor for diagnosis without treating it as hidden evaluator evidence.

- If the response violates a clear contract behavior and the case accurately
  tests that behavior, continue diagnosing the implementation owner.
- If the case, expected output, rubric, or evaluator demands behavior that the
  contract does not require or contradicts, classify an eval-system defect.
- If the contract is materially ambiguous, or faithfully implementing it would
  still produce a worse customer experience, identify a contract decision for
  [consultative-guidance.md](consultative-guidance.md) and human acceptance.

Eval Debug does not silently rewrite the Behavior Contract. It is used for all
non-perfect dynamic evidence, not only when the eval itself may need to change;
its job is to determine the strongest supported owner. If the contract is not
available, do not infer it from one rubric or the current Agent settings.
For a legacy Agent without the persistent artifact, surface the missing design
evidence and obtain user confirmation before classifying a finding as contract
divergence or contract improvement.

---

## Finding method

Dynamic evidence must remain anchored to the static configuration that produced
it. A score or tool trace without the corresponding case, rubric, evaluator,
agent version, and relevant source context is not enough to assign a cause.

A useful finding communicates, in whatever prose, bullets, table, or other
format best fits the task:

- the observed runtime behavior and affected object;
- the decisive dynamic evidence and necessary static anchors;
- the earliest mechanism that explains the observation;
- the user, product, or evaluation consequence;
- the component or person most likely to own the cause; and
- plausible alternatives, uncertainty, or missing evidence.

Do not require issue codes, a fixed taxonomy, confidence percentages, JSON, or
another rigid input/output schema. Add labels or structure only when they help
the current diagnosis. Keep observations, inference, and unresolved hypotheses
distinct. A proposed repair is not evidence that the diagnosis is correct.

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
- Good response, perfect score: no defect finding unless other evidence exposes
  a gap.

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

Classify an imperfect score as evaluator strictness when the response is
correct and the available evidence does not support an agent defect. Whether to
accept or change it is a Repair Planner decision.

### 7. Platform defect

Use this classification only when evidence shows a contract-level failure
outside the configured agent, such as a valid FAQ/filter target being ignored,
the wrong snapshot being queried, or required trace data not reaching an
evaluator despite the documented template contract.

Record reproduction evidence, expected versus actual platform behavior, and
affected scope. Do not encode a platform bug as a prompt workaround unless the
user explicitly approves a labeled temporary containment.

---

## Stop and hand off

Stop when the strongest supported mechanism, evidence, consequence, likely
owner, alternatives, and uncertainty are clear enough for the requested
decision. If the evidence cannot distinguish plausible mechanisms, name the
smallest additional trace, probe, or comparison needed; do not plan speculative
repairs.

If a finding appears suite-wide, route the broader static consistency question
to [static-audit.md](static-audit.md). When the user wants to change the system,
hand accepted implementation or eval findings to
[repair-planner.md](repair-planner.md). Route a contract decision to
[consultative-guidance.md](consultative-guidance.md) first; after the revised
contract is accepted, update eval cases before planning runtime changes. Eval
Debug does not choose the target state, draft the diff, define the impact
regression, or apply server changes.
