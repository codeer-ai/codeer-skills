# History Analysis

Analyze production conversations to drive continuous improvement. This module
is the entry point for Phase 2 (Improve).

---

## Step 1 — Pull production data

Not all channels provide explicit feedback (thumbs up/down). Conversation
history is the primary source of truth.

```bash
codeer history list --agent <agent_id>
```

### Negative feedback first

Start with flagged turns where feedback is available:

```bash
codeer history negative-feedback --agent <agent_id>
```

### Then browse conversations

For channels without feedback signals, read conversations directly:

```bash
codeer history conversations <history_id>
```

---

## Step 2 — Analyze and categorize

Read through production conversations and classify findings:

- **Failures** — agent gave wrong answer, hallucinated, missed a tool
  call, broke a hard rule
- **Improvement opportunities** — agent was technically correct but could
  be better (tone, clarity, conversion flow)
- **Successful patterns** — agent did something right that increased
  conversion or user satisfaction (these need protection from regressions)

### Map findings to MECE categories

Map each finding to an existing category from the eval suite (established
during initial eval case design). If a finding doesn't fit any existing
category, propose a new one — this is a coverage gap.

### Tool usage analysis

Look for patterns in tool behavior:

- Is a tool being called too often? (e.g. 13 KB calls for a simple question)
- Is a tool being skipped when it should be used?
- Are tool queries effective or are they missing relevant content?

### Identify unserved scenarios

Find specific user query patterns that the current eval suite doesn't cover.
These become candidates for new eval cases.

---

## Step 3 — Present and prioritize

Present the categorized findings to the user with a recommendation of
which categories need new or updated cases. Let the user pick which
categories to work on and in what order.

---

## Step 4 — Hand off to eval cases

After the user chooses priorities, transition to **eval-cases** module:

- Each failure → a case where the current agent should fail
- Each successful pattern → a case that must keep passing
- Each unserved scenario → a new case for coverage

Then run baseline eval on the current published version (`--history` flag)
before making any fix:

```bash
codeer eval run \
    --agent <agent_id> --history <published_history_id> \
    --out .codeer/eval_baseline.json
```

New failure cases should fail; protection cases should pass. Then hand off
to **eval-debug** for the fix cycle.
