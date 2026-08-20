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

For channels without feedback signals, export the complete Chat V2 parts before
analyzing them. Standard output is deliberately a bounded preview and must not
be treated as the complete history:

```bash
codeer history conversations <history_id> \
    --out .codeer/current/history-<history_id>.json
```

Read the saved JSON selectively. It contains every client-visible part across
all API pages, including tool calls/results, attachments, interactions,
feedback, and passthrough metadata. Preserve the raw artifact when extracting
eval cases; summaries are navigation aids, not evidence of absence.

To continue an existing persisted history after the user approves the write:

```bash
codeer history send <history_id> --message "Follow-up question" --timeout 240
```

This uses the agent's current published version through Chat V2 structured SSE
with `stream: true`. It only reports success after `response.completed`. If it
times out, returns `response.failed`, or disconnects early, export and inspect
the history before retrying because the turn may already have been persisted.

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

### Separate evidence from diagnosis

Do not translate a finding directly into a prompt rule or other fix. Record:

- the observed behavior and its user or business consequence;
- where the behavior diverged from the intended outcome;
- related successes or failures that support or challenge the same mechanism;
- the strongest current mechanism hypothesis and meaningful uncertainty.

Group findings by shared behavioral mechanism when evidence supports it, not
only by surface topic. A single finding may still expose a structural defect;
multiple examples are useful evidence, not a prerequisite for diagnosis.

### Tool usage analysis

Look for patterns in tool behavior:

- Is a tool being called too often? (e.g. 13 KB calls for a simple question)
- Is a tool being skipped when it should be used?
- Are tool queries effective or are they missing relevant content?

### Identify unserved scenarios and useful probes

Find specific user query patterns that the current eval suite doesn't cover.
These become candidates for new eval cases. When a mechanism remains
uncertain, identify paraphrases, nearby boundaries, or successful contrasts
that could distinguish the plausible causes.

---

## Step 3 — Present and prioritize

Present observations separately from inferences. Include evidence, consequence,
mechanism hypothesis, uncertainty, and successful patterns to protect. Recommend
which categories need investigation or new cases without prescribing a settings
patch from the surface symptom. Let the user pick which categories to work on
and in what order.

---

## Step 4 — Hand off to eval cases

After the user chooses priorities, transition to **eval-cases** module:

- Each distinct failure behavior → a representative reproduction case where
  the current agent should fail
- Each successful pattern → a case that must keep passing
- Each unserved scenario → a new case for coverage
- Each uncertain mechanism → only the generalization, boundary, or contrast
  probes needed to distinguish the plausible causes

Then run baseline eval on the current published version (`--history` flag)
before changing any settings:

```bash
codeer eval run \
    --agent <agent_id> --history <published_history_id> \
    --evaluator <evaluator_id>
```

Export the baseline results and pin them so they survive the improvement cycle:

```bash
codeer eval export --agent <agent_id> --out .codeer/current/eval_table/
```

Ask the user: "Pin these baseline results before we change the agent?" If
yes, copy `current/eval_table/` to `pinned/<date>-baseline/`.

Before running the baseline, use **static-audit** to verify the exact version,
sources, settings, cases, rubrics, evaluators, and assignments. New reproduction
cases should fail; protection cases should pass. These results are evidence,
not the scope or wording of the eventual change. Then hand off to **eval-debug**
for causal diagnosis and target-state design.
