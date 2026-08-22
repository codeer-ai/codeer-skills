# Repair Planner

Use this module after Static Audit or Eval Debug has produced one or more
evidence-backed findings and the user wants to decide what, if anything, should
change. It turns findings into a coherent target state, reviewable diffs, and a
proportionate verification plan. It does not treat the closest symptom as the
owner and does not apply a change merely because it can propose one.

Planning is read-only. Before any later server mutation, follow the skill's
mutation and diff guardrails, use the module that owns the affected component,
show the complete diff, and wait for explicit user approval.

---

## Flexible entry point

Accept findings in the form available: a natural-language report, bullets, a
table, selected objects, or another review artifact. Do not require issue codes,
a fixed taxonomy, JSON, or a rigid input/output schema.

The planner still needs enough meaning to recover:

- what was observed and why it matters;
- the evidence supporting the finding;
- the likely owner and material uncertainty; and
- the current objects that would be affected by a change.

Read current affected state before drafting a diff. A finding is evidence about
the system, not a command to preserve its wording or proposed remedy. If the
finding and current state disagree, surface the mismatch and return it to
Static Audit or Eval Debug instead of planning against stale evidence.

---

## Step 1 — Establish the repair set

Review all findings in scope together. Combine findings that share one causal
owner, separate similar symptoms with different causes, and preserve successful
behavior that the change must not regress.

Distinguish:

- direct observations;
- supported causal findings;
- unresolved source-truth or ownership decisions;
- hypotheses that still require static context or dynamic evidence; and
- findings for which no change is the best outcome.

Do not plan an exact repair when source truth is unresolved or the available
evidence cannot distinguish plausible owners. In those cases, recommend the
smallest decision, read, trace, or probe needed to unblock planning.

---

## Step 2 — Confirm component ownership

Read the complete relevant configuration, not only the line nearest the
symptom. Use the ownership model in [agent-settings.md](agent-settings.md):

- system prompt for stable operational invariants and cross-component choices;
- tool configuration for tool purpose, invocation, inputs, and limits;
- KB for authoritative domain content and evidence;
- file structure, retrieval routes, and Context Object FAQ for routing to
  existing canonical content;
- model selection for capability, latency, and cost;
- handoff settings for transfer availability and operational triggers;
- evaluator and rubric for observable pass/fail criteria; and
- eval cases for reproduction, boundary, and regression probes.

When an agent-settings change is in scope, read
[agent-settings.md](agent-settings.md) in full and apply every section relevant
to the affected settings, including its full target-state gate, before
presenting a diff. Do not copy failure wording into the system prompt or use one
component to conceal a contract defect owned by another.

---

## Step 3 — Design the target state

Describe the simplest coherent state that resolves the accepted findings while
preserving required behavior. Prefer the earliest adequate intervention:

1. make no change when the behavior is acceptable or the finding does not
   justify a repair;
2. remove a contradiction, obsolete instruction, or unnecessary constraint;
3. consolidate, clarify, or reorder existing information;
4. move responsibility to the component that should own it;
5. replace a narrow workaround with a stable invariant at the broadest scope
   supported by evidence;
6. add a new rule only when the requirement is genuinely absent; and
7. use a case-specific exception or temporary containment only as a labeled
   last resort.

Consider genuinely different repair approaches when ownership, maintenance,
latency, context cost, evaluator visibility, or regression risk creates a real
tradeoff. State the recommendation, decisive reasons, rejected alternatives,
and remaining uncertainty. Optimize the resulting system, not the number of
changed lines or the pass rate of one case.

---

## Step 4 — Plan by affected owner

### Rubric, expected output, case, or evaluator

For a rubric edit, show the before/after text, relevant source truth, evaluator
visibility, and why each mandatory criterion is necessary. A correct, relevant,
concise answer should not fail for omitting merely helpful detail.

If the evaluator cannot see the evidence required by a criterion, compare at
least the plausible choices: make the rubric self-sufficient, assign an
evaluator that receives the evidence, change the criterion to something
observable, or mark the requirement unsuitable for automated judgment. Do not
silently copy volatile source content into a rubric.

Changing an evaluator template or judge model establishes a new baseline.
Changing the agent and evaluator together removes causal attribution; separate
those changes or explicitly declare the new baseline.

### KB, file structure, retrieval, and routing

Fix missing, ambiguous, duplicated, stale, or contradictory canonical content
at the source. Do not add a route to content that does not exist, and do not add
a prompt rule when the source itself owns the error.

Use a Context Object FAQ only when the finding establishes that:

- the canonical file is uploaded, attached, and `READY`;
- the agent issued a reasonable query;
- semantic retrieval missed or under-ranked that source; and
- the platform's FAQ/filter contract works for the relevant snapshot.

Do not use it when content is missing, the agent never queried, the target is a
stale or cross-version snapshot, file structure is the real defect, source
truth is unresolved, or platform filtering blocks the route.

When justified, read the current canonical file and `snapshot_object_id`, then
preview the representative question and target with `codeer kb faq-create ...
--dry-run` or `faq-update ... --dry-run`. Use a line range only when the passage
is stable and the question should land on that specific section. Present the
preview and wait for explicit approval before applying it.

### Agent settings, tools, handoff, or model

Apply [agent-settings.md](agent-settings.md) to the complete resulting
configuration. Explain information removed, merged, moved, replaced, or added;
why the chosen component owns it; and why the result is simpler or more
coherent. Label urgent workarounds as containment and state the design debt.

### Platform defects

Prefer a platform correction backed by reproduction evidence. Do not encode a
platform bug as an agent prompt rule. If the user explicitly chooses temporary
containment, label its scope, expiry or removal condition, known limitations,
and the regression risk it introduces.

---

## Step 5 — Present the repair proposal

Use the clearest format for the decision; prose, bullets, a table, or a diff are
all acceptable. Do not force a machine-readable envelope. A complete proposal
should make these ideas reviewable when they are material:

- the findings being addressed and any findings intentionally left unchanged;
- the proposed target state and component ownership;
- the recommended changes, grouped so their combined effect is visible;
- before/after diffs for every object that would change;
- alternatives, tradeoffs, uncertainty, and containment debt;
- successful behavior and compatible baselines to protect; and
- the verification and rollback or stop conditions.

A repair proposal is not approval. Do not call a mutating command until the
user has seen the complete diff and explicitly approved the change.

---

## Step 6 — Plan impact-based verification

Every proposed repair needs, where applicable:

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

Use dependency labels when they reliably identify a local impact set. Missing
or untrusted dependency metadata expands the set; it does not justify testing
less. For stochastic P0/P1 behavior, plan multiple trials and report the
distribution; one passing trial is not completion.

After an approved KB, settings, case, rubric, evaluator, assignment, or routing
change is applied, run [static-audit.md](static-audit.md) before the next full
regression. Before publish, run all assigned case/evaluator pairs and reconcile
planned versus completed counts. A Content-only sweep is not a full regression
when other assignments exist.

---

## Execution handoff

After the user approves the proposal, use the module and registered CLI command
that own each change. Read back the effective state, run the planned focused
checks, re-audit changed static state, and then run the required regression.
Publish remains a separate action requiring explicit user confirmation. A
completed plan, approved diff, or passing reproduction does not authorize
publish.
