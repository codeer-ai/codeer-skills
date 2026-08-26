# Eval Case Design

Build eval cases that cover the agent's operating scope. Work one category
at a time so each review batch is mentally manageable.

For a new query-led customer guidance Agent, begin from the accepted
`.codeer/design/query_distribution.csv` in
[query-distribution.md](query-distribution.md) and
`.codeer/design/query_examples.csv`, plus the accepted
`.codeer/design/behavior_contract.md` in
[consultative-guidance.md](consultative-guidance.md). The distribution defines
the evidence-backed portfolio, the examples supply concrete customer inputs,
and the contract defines the accepted outcomes, guardrails, and correct Agent
decision policies. Design the acceptance cases locally before the Agent exists.
An `agent_id` is required to apply or run cases, not to decide the customer
behavior they should test.
Use `.codeer/current/local_draft_eval_cases.md` for this human-reviewed design
draft. It may preserve unresolved evaluator or runtime-evidence decisions that
cannot yet be represented in the apply-ready JSON manifest.
For an existing Agent, also inspect its current effective settings and relevant
production or eval evidence.

---

## Diff rule

**Before applying any eval case changes** (new cases or rubric edits),
present the full diff to the user and wait for approval. Never apply
cases or rubric changes silently.

---

## Step 1 — MECE categories

Inspect the accepted scope, Query Distribution, query examples, Behavior
Contract, and source material. When an Agent already exists, also
inspect its settings, system prompt, KBs, and tools, but do not let the current
implementation silently redefine the accepted behavior. Propose a set of
mutually exclusive, collectively exhaustive categories — for example: product
Q&A, discovery and narrowing, recommendation boundaries, transaction readiness,
tool-backed actions, handoff, and out-of-scope handling.

- Aim for 3–6 categories.
- **Confirm the category structure with the user before writing any cases.**

### Portfolio allocation

Use `target_cases` as the accepted integer portfolio allocation. Preserve the
intent of that allocation when review constraints require a smaller batch, and
propose a distribution diff when the full target should change. Allocate
coverage across representative tasks, material journey boundaries, and
intentional rare-but-high-consequence reserves.

Do not infer real-world frequency from example count. Do not drop a rare
high-risk query type merely because demand is low, and do not multiply every
task by every risk or challenge. Treat accepted examples as candidate inputs,
not automatically approved eval cases.

---

## Step 2 — Category loop

For each category (user picks order, or go sequentially):

### 2a. Decide case count

Judge the appropriate number based on complexity, boundary conditions, and
hallucination risk. State the count and rationale — the user can adjust.

### 2b. Generate cases + rubrics

Write cases for this category only. Each case carries per-evaluator rubrics.
On the server, that rubric row is also the case/evaluator assignment. A case
only runs with evaluators it is assigned to, so every manifest case needs a
`rubrics` entry for each tester that should judge it.
Use server-side eval case labels when they make later filtering or reporting
easier. Put reusable server labels in the manifest's `labels` array or
`label_ids` array; keep `label` for the local case display name.

**Evaluator priority**: Focus on the **Content Compliance Evaluator** unless
the user explicitly cares about style. Style/Tone judges _how_; Content
Compliance judges _what_.

**Evaluator-aware self-sufficiency rule**: Check the related evaluator's
system prompt/template before writing the rubric. Do not assume the evaluator
can see the agent prompt, KB files, retrieved chunks, tool traces, expected
output, or diagnosis notes unless that information is explicitly included by
the evaluator template. After accounting for the evaluator's actual inputs,
make the rubric as self-sufficient as practical.

Evaluator templates can be inspected before an Agent exists. If the required
evaluator or its evidence contract is unavailable, do not invent an ID or
claim the rubric is ready to apply. Keep the intended observable behavior in
the Markdown local draft and identify the unresolved evaluator decision. Use
the same unresolved state when the evaluator exists but a not-yet-selected or
not-yet-configured Tool makes the actual runtime evidence shape unknowable.

**Pair admission gate**: Before assigning an evaluator, be able to state all
of the following for that case/evaluator pair:

- the one material behavior or failure the pair is meant to detect;
- the exact evaluator input that carries the evidence, such as `{output}` or
  `{tool_steps}`;
- the runtime component that produces that evidence and its actual shape; and
- why an existing pair does not already cover the same decision consequence.

Inspect documented tool/runtime behavior or available capability metadata when
a tool can end generation, request interaction, replace the model response, or
validate arguments after the model call. A template containing `{output}` is
not sufficient when runtime replaces that output with a fixed or empty value.
Likewise, do not require an argument that the live schema or validator cannot
accept. Reject a pair when no plausible compliant live trace can satisfy its
rubric, when the evaluator cannot observe the required evidence, or when the
pair has no distinct material failure to catch.

**Scope matching**: For broad user questions, require only what the question
naturally asks for. Do not require prices, exhaustive lists, logistics
details, or stock confirmation unless the user asked for that dimension or
the product requirement depends on it.

For every mandatory criterion, ask: if this detail were omitted, would the
answer become wrong, produce a wrong next step, or hide a material risk? If
not, make it optional or remove it. Correct, relevant, concise answers should
not fail for omitting merely helpful detail.

**Rubric quality standard**: Good rubrics should be easy to maintain:

- Use short bullet points instead of dense prose.
- Use positive criteria when unacceptable answers form an open-ended or
  infinite set.
- Use negative criteria when the prohibited behavior is narrow and concrete.

Common check patterns:

- **Content Accuracy Check**: Prefer positive expectations for what the answer
  should include. Use "must not" only for specific known errors.
- **Source Support Check**: Do not hard-code stale facts. Specify which claims
  need source support and which sources count as valid.
- **Tool Use Check**: Negative lists are acceptable because tool-call rules are
  usually a finite set, e.g. "must not call request_form".
- **Style & Format Check**: Positive or negative framing can both work; choose
  whichever is clearer and easier to maintain.

### 2c. Present for review

Show the Markdown draft cases to the user. Keep the batch small enough to
review without fatigue. Acceptance at this point covers the case input,
intended behavior, prohibited outcome, and observable success; it does not
pretend that an unresolved evaluator ID or runtime evidence shape is final.

### 2d. Apply

After the user approves the cases and the Agent has been created, read the
DRAFT Agent and Tools with `codeer agent get --full` and read evaluator
templates with `codeer eval evaluators --full`. Resolve every intended pair
through the Pair Admission Gate, then convert the admitted cases into
`.codeer/current/local_draft_eval_cases.json`. If the conversion changes the
accepted behavior rather than only its evaluator/evidence binding, return the
semantic change to the user for review. Cases with no admitted pair remain in
the Markdown draft and do not count as applied coverage.

Present the server diff and obtain the mutation approval required by the parent
skill. Then apply the admitted cases using the new `agent_id`:

```bash
codeer eval cases-apply \
    --cases .codeer/current/local_draft_eval_cases.json --agent <agent_id>
```

If the manifest references new server label names, preview label creation and
case assignment first:

```bash
codeer eval cases-apply \
    --cases .codeer/current/local_draft_eval_cases.json \
    --agent <agent_id> \
    --create-labels \
    --dry-run
```

After apply, refresh the server cache:

```bash
codeer eval list --agent <agent_id> --out .codeer/current/eval_cases.json
```

Then output the eval-cases server link so the user can verify.

### 2e. Optionally test this batch

After a complete Agent version exists and Static Audit has passed, run eval on
just the new cases and use **eval-debug** to diagnose any dynamic findings.
When a finding warrants a change, use **repair-planner** to design and review
the target state before the owning module applies it. Do not describe a local
draft or an unevaluated case batch as a baseline.

### 2f. Next category

Repeat from 2a for the next category.

---

## Step 3 — Static preflight and full sweep

Before the first baseline and after any case, rubric, evaluator, KB, FAQ, or
agent-settings change—and after an accepted Query Distribution update—run
[static-audit.md](static-audit.md). Do not start the full sweep while its verdict
is `BLOCKED`. Include both distribution-to-portfolio alignment and the Behavior
Contract's semantic alignment with acceptance cases in the audited scope.

For a new Agent, after all categories are covered, cases are applied, and the
first full DRAFT Agent passes Static Audit, run every assigned case/evaluator
pair. This is the first baseline: the pre-repair dynamic evidence for the
complete first Agent. On later iterations, the same full sweep is a regression
check. The default full-suite run uses every case/evaluator pair already
assigned on the server. For a full-suite run with many cases, use `--out` to
avoid flooding the context window:

```bash
codeer eval run \
    --agent <agent_id> \
    --out .codeer/current/eval_results.json
```

Supplying `--evaluator`/`--evaluators` intentionally narrows the run. Use that
for a focused impact set, not for a completion claim. Reconcile the planned
assigned-pair count with completed results; a Content-only run is not full
coverage when other evaluator assignments exist.

For a full export (user review, spreadsheet analysis), run:

```bash
codeer eval export \
    --agent <agent_id> --out .codeer/current/eval_table/
```

After the first baseline completes, automatically copy the exported results
plus exact Agent/version, evaluator-template, and judge-model context to
`.codeer/pinned/<date>-first-baseline/` before any diagnosis or repair.

Then hand off to **eval-debug** for any non-perfect scores. Findings that
warrant a change go to **repair-planner** before any diff is drafted or applied.

---

## Cases from production history

When building cases from production conversations (Phase 2):

- Start from the accepted analysis outcome and the production finding's
  treatment candidate. Identify the observable entry context, the Agent
  decision being tested, the expected action policy, the prohibited or unsafe
  alternative, the immediate observable outcome, and material guardrails.
  Do not require a rigid case schema when the same meaning is clear in the
  input, expected behavior, rubric, and metadata.
- Create a reproduction case for each distinct failure mechanism. Deduplicate
  histories that show the same decision-policy defect while retaining
  materially different boundaries or contexts.
- Each successful pattern becomes a case where the current agent should
  pass (and must keep passing after changes).
- Add only the paraphrase, generalization, boundary, or successful-contrast
  probes needed to test a causal hypothesis or the scope of a proposed change.
- Rewrite findings into the smallest input that makes the behavior
  objectively judgeable. Don't copy production messages verbatim — isolate
  the decision context and behavior being tested. A case that passes only on
  the original wording does not establish a reusable policy.
- Treat these cases as evidence and validation probes. Never copy their wording,
  entities, or answer shapes into agent settings.
- Use `meta.previous_conversations` in `codeer eval cases-apply` when the
  failure requires multi-turn context.

An offline acceptance Eval verifies that the Agent reliably implements the
intended decision policy and produces evidence visible to its evaluator. It
does not by itself establish a delayed or longitudinal outcome such as
retention, implementation, revenue, classroom change, or long-term time saved.
Use an immediate observable outcome or faithful proxy in the case, then name
the production measurement needed to see whether the real outcome moves. A
causal improvement claim additionally requires an appropriate controlled or
credible quasi-experimental design; uncontrolled monitoring can support trend
or association claims only. Never require an evaluator to judge an outcome
that its input contract cannot observe.

---

## Multi-Turn Follow-Up Cases

When a case needs previous thread context, use a real persisted history as the
source. If production traffic already has the right setup, use that history.
For an existing Agent with a suitable published version, obtain explicit user
approval immediately before creating or continuing a seed history, because
these commands persist conversation state. Then create the seed through the
published Agent:

```bash
codeer history create \
    --agent <agent_id> \
    --title "Seed conversation" \
    --user "eval-seed@example.com" \
    --message "First user turn" \
    --timeout 240

codeer history send <history_id> \
    --message "Follow-up user turn" \
    --timeout 240
```

This uses Chat V2 structured SSE to write real persisted conversation parts
and returns the `history_id` plus conversation group/part IDs. The command uses
the published agent version only; the API-key Chat V2 flow cannot pin an
unpublished draft version.

For a brand-new Agent with no suitable persisted history, this limitation makes
an authentic multi-turn pair unresolved before first publish. Do not seed it
through a different Agent or publish merely to create the prerequisite. Keep
the case in `.codeer/current/local_draft_eval_cases.md`, report the coverage
blocker, and do not claim a complete multi-turn baseline or publish readiness.
A deliberately limited first publish requires separate, explicit user risk
acceptance. Full pre-publish coverage requires Codeer support for
DRAFT-compatible history seeding or supported inline prior-turn replay.

If either stream times out, reports `response.failed`, or disconnects before
`response.completed`, inspect the history before retrying. The server may
already have persisted the turn.

For the eval case, set `meta.previous_conversations` to replay prior turns from
the source history before the target conversation:

```json
{
  "previous_conversations": {
    "source_history_id": 123,
    "target_conversation_id": 456,
    "previous_conversation_count": 2
  }
}
```

The eval case `input` should be the follow-up user message being judged. The
server uses the current eval run's agent version for the system prompt and
replays only the prior user/assistant turns from `source_history_id`.

---

## Custom evaluators

When the existing evaluators don't cover a needed dimension, create or
modify an evaluator. Common reasons:

- Need to evaluate tool-use behavior (requires `{tool_steps}` variable)
- Need a domain-specific scoring rubric structure
- Need a different scoring scale or pass/fail threshold

Use `codeer eval evaluators` to list available evaluators. If the CLI
supports evaluator creation/update, use it; otherwise say it is not
supported by the CLI.

---

## Batch workflow

When the eval suite has many cases (50+), split them into batches and
work through one batch at a time. This keeps each review cycle
manageable and avoids running expensive full-suite evals repeatedly
during the improvement loop.

During Phase 1, batches may organize case authoring, review, and apply, but do
not repair the Agent between dynamic batches before the first full baseline.
The batch → diagnose → repair loop below is for Phase 2 after the first baseline
has been preserved. Otherwise the eventual full sweep is post-repair evidence,
not the pre-repair first baseline defined by the parent skill.

### Splitting into batches

Use the MECE categories as the natural batch boundaries. Each batch
should be small enough to review without fatigue (typically 10–20 cases).

### Running a batch

Run eval on only the batch's case IDs. For small batches (≤20 cases),
stdout is fine — the non-perfect analysis fits in context:

```bash
codeer eval run \
    --agent <agent_id> \
    --cases <comma-separated-case-ids> \
    --evaluator <evaluator_id>
```

Diagnose findings within the batch before moving on (hand off to
**eval-debug**, then to **repair-planner** when a change is warranted).

### Tracking progress

Record batch status in `.codeer/current/progress.json`. Update this file
when a batch completes — record the final score and a short change summary.

When starting a new session, read `progress.json` to understand which
batches are done and which remain. All debug-loop artifacts (rubrics,
eval results, exports) overwrite the same files in `current/` regardless
of which batch is active — `progress.json` is the only cross-batch
state.

### Full regression check

After all batches are done, re-run [static-audit.md](static-audit.md), then run
all assigned case/evaluator pairs as a regression check before publishing.
Reconcile planned and completed pair counts. If the user wants to preserve the
batch-level progress beyond the active cycle, pin
`.codeer/current/progress.json` before it is replaced during later work.
