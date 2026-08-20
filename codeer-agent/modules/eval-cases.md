# Eval Case Design

Build eval cases that cover the agent's operating scope. Work one category
at a time so each review batch is mentally manageable.

---

## Diff rule

**Before applying any eval case changes** (new cases or rubric edits),
present the full diff to the user and wait for approval. Never apply
cases or rubric changes silently.

---

## Step 1 — MECE categories

Inspect the agent's settings, system prompt, KBs, and tools. Propose a
set of mutually exclusive, collectively exhaustive categories — for example:
product Q&A, routing, ordering, policy boundaries, tool-backed actions, and
out-of-scope refusals.

- Aim for 3–6 categories.
- **Confirm the category structure with the user before writing any cases.**

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

Show cases to the user. Keep the batch small enough to review without fatigue.

### 2d. Apply

After user approves (with any adjustments):

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

Run eval on just the new cases, diagnose mechanisms, and improve the relevant
settings before moving to the next category. This catches problems early.

### 2f. Next category

Repeat from 2a for the next category.

---

## Step 3 — Static preflight and full sweep

Before the first baseline and after any case, rubric, evaluator, KB, FAQ, or
agent-settings change, run [static-audit.md](static-audit.md). Do not start the
full sweep while its verdict is `BLOCKED`.

After all categories are covered, run eval across ALL cases as a regression
check. The default full-suite run uses every case/evaluator pair already
assigned on the server:

For a full-suite run with many cases, use `--out` to avoid flooding the
context window:

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

Then hand off to **eval-debug** for any non-perfect scores.

---

## Cases from production history

When building cases from production conversations (Phase 2):

- Create a reproduction case for each distinct failure behavior. Deduplicate
  histories that show the same mechanism while retaining materially different
  boundaries or contexts.
- Each successful pattern becomes a case where the current agent should
  pass (and must keep passing after changes).
- Add only the paraphrase, generalization, boundary, or successful-contrast
  probes needed to test a causal hypothesis or the scope of a proposed change.
- Rewrite findings into the smallest input that makes the behavior
  objectively judgeable. Don't copy production messages verbatim — isolate
  the specific behavior being tested.
- Treat these cases as evidence and validation probes. Never copy their wording,
  entities, or answer shapes into agent settings.
- Use `meta.previous_conversations` in `codeer eval cases-apply` when the
  failure requires multi-turn context.

---

## Multi-Turn Follow-Up Cases

When a case needs previous thread context, use a real persisted history as the
source. If production traffic already has the right setup, use that history.
If not, create a seed history through the published agent:

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

Diagnose and improve the target state within the batch before moving on (hand
off to **eval-debug** as usual).

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
batch-level progress, pin `current/progress.json` before the full-suite run
overwrites it.
