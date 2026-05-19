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

**Rubric self-sufficiency rule**: The evaluator only has its system prompt
and the rubric — not the agent's KB, retrieved chunks, tools, settings, or
diagnosis notes. Rubrics must carry all criteria the judge needs.

**Scope matching**: For broad user questions, require only what the question
naturally asks for. Do not require prices, exhaustive lists, logistics
details, or stock confirmation unless the user asked for that dimension or
the product requirement depends on it.

### 2c. Present for review

Show cases to the user. Keep the batch small enough to review without fatigue.

### 2d. Apply

After user approves (with any adjustments):

```bash
codeer eval cases-apply \
    --cases .codeer/eval_cases.json --agent <agent_id> --out .codeer/case_ids.json
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

```bash
codeer eval run \
    --agent <agent_id> \
    --evaluators <evaluator_id> \
    --out .codeer/eval_results.json
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
