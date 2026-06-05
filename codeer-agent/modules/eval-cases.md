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

After apply, refresh the server cache:

```bash
codeer eval list --agent <agent_id> --out .codeer/current/eval_cases.json
```

Then output the eval-cases server link so the user can verify.

### 2e. Optionally test this batch

Run eval on just the new cases, diagnose and fix issues before moving to
the next category. This catches problems early.

### 2f. Next category

Repeat from 2a for the next category.

---

## Step 3 — Full sweep

After all categories are covered, run eval across ALL cases as a regression
check. You must specify which evaluator to test against:

For a full-suite run with many cases, use `--out` to avoid flooding the
context window:

```bash
codeer eval run \
    --agent <agent_id> \
    --evaluators <evaluator_id> \
    --out .codeer/current/eval_results.json
```

For a full export (user review, spreadsheet analysis), run:

```bash
codeer eval export \
    --agent <agent_id> --out .codeer/current/eval_table/
```

Then hand off to **eval-debug** for any non-perfect scores.

---

## Cases from production history

When building cases from production conversations (Phase 2):

- Each failure becomes a case where the current agent should fail (and
  the fixed agent should pass).
- Each successful pattern becomes a case where the current agent should
  pass (and must keep passing after changes).
- Rewrite findings into the smallest input that makes the behavior
  objectively judgeable. Don't copy production messages verbatim — isolate
  the specific behavior being tested.
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
    --message "Follow-up user turn"
```

This writes real `History` and `Conversation` rows and returns the `history_id`
plus conversation IDs. The command uses the published agent version only; the
API-key chat flow cannot pin an unpublished draft version.

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
during the debug loop.

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
    --evaluators <evaluator_id>
```

Diagnose and fix within the batch before moving on (hand off to
**eval-debug** as usual).

### Tracking progress

Record batch status in `.codeer/current/progress.json`. Update this file
when a batch completes — record the final score and a short fix summary.

When starting a new session, read `progress.json` to understand which
batches are done and which remain. All debug-loop artifacts (rubrics,
eval results, exports) overwrite the same files in `current/` regardless
of which batch is active — `progress.json` is the only cross-batch
state.

### Full regression check

After all batches are done, run a full-suite eval as a regression check
before publishing. If the user wants to preserve the batch-level
progress, pin `current/progress.json` before the full-suite run
overwrites it.
