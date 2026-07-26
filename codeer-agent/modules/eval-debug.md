# Eval Debugging

Use eval results to diagnose behavior and leave the whole agent configuration
in a better state. Passing the affected case is necessary but not sufficient.
This module covers both scores < 1.0 and spot-checking scores = 1.0.

Before proposing any agent-settings change, read
[agent-settings.md](agent-settings.md) and apply its target-state gate.

---

## Entry point

For every non-perfect score, surface: case label, evaluator, score, and
the evaluator's `reason` text. Then **stop and wait for user direction**.

Also review score = 1.0 cases when asked — the evaluator might not be
checking what you think it's checking.

---

## Evidence triage

Inspect evidence in this order. These observations narrow the mechanism and
component owner; they do not prescribe a fix by themselves.

### 1. Is the agent's response actually good?

Read the response yourself before looking at tool calls or KB content.

- **Response is good, score is low** → investigate the rubric, case, or
  evaluator before changing the agent.
- **Response is wrong** → continue to step 2.

### 2. Rubric / source-of-truth check

Compare the rubric against KB facts before inspecting the agent's behavior.

- If the rubric contradicts the KB → resolve the source-of-truth conflict
  before changing the agent.
- If the rubric assumes hidden context (KB content, retrieved chunks, tool
  config, diagnosis notes) → make it self-sufficient.
- For broad user questions, do not require unnecessary details the user
  did not ask for.

### 3. Tool-use check

Did the agent call the right tool at all?

- **Agent skipped KB lookup** (answered from training data) → inspect the
  complete decision policy, tool availability, and KB `invocation_instruction`
  / "When to Use" before deciding which component owns the defect.
- **Agent made excessive tool calls** (e.g. 13 calls for a simple question) →
  inspect whether the cause is query strategy, weak stop conditions, unclear
  tool boundaries, or inadequate retrieval results.

### 4. Retrieval check

The agent called KB but the key information is missing from results.
Walk through these sub-cases in order:

**4a. Canonical file not in the uploaded KB.**
The authoritative file is not part of the KB files attached to the agent,
or is not indexed (status != READY). No prompt edit or Context Object FAQ
can retrieve what doesn't exist.

→ Fix: add the file to KB, attach correct node IDs, wait for indexing.

**4b. Canonical file exists but retrieval never reached it.**
The retrieved sources don't include the authoritative file.

- If the agent's query is clearly wrong/too narrow/too general → identify
  whether the general decision policy or the tool-specific invocation/query
  contract owns the behavior.
- If the query is reasonable but semantic search misses the file →
  **add Context Object FAQ**: pair representative question variants with
  the canonical file. The FAQ embedding reserves the linked file during
  `retrieve_context_objs`.

→ Fix: usually Context Object FAQ; prompt/`invocation_instruction` only
when the query itself is wrong.

**4c. Retrieval reached an adjacent chunk within the correct file.**
The right file was found but the wrong chunk was returned.

- If the file's internal structure is weak (bad headings, unclear
  boundaries) → improve file structure / headings / chunk boundaries.
- If structure is clear but the agent asked for the wrong part → inspect the
  owning decision policy, invocation instruction, and query hints.

**4d. Information missing AND agent hallucinated.**
The agent fabricated an answer instead of admitting the gap.

This may indicate a missing or unclear evidence boundary in the agent's stable
behavioral policy, even when a KB fix (4a/4b) is also needed. Read the complete
settings before deciding whether to remove, consolidate, replace, or add an
instruction.

### 5. Content check (retrieval was correct)

The agent got the right KB content but the response is still wrong.

**5a. KB contradicts the rubric.**
The KB says one thing, the rubric expects another.

→ Flag to user: "The KB and rubric disagree on X — which is the source
of truth?" This requires human judgment.

**5b. Agent embellished or distorted KB content.**
The agent had the right data but added unsupported claims or its own
interpretation.

Inspect the complete source-use policy for conflicts, missing priorities, or
unnecessary complexity. Do not automatically append a scenario-specific
instruction.

### 6. Evaluator-side issues

**6a. Score = 1.0 but the answer is actually wrong.**
The rubric has a coverage gap — it doesn't test the broken dimension.

→ Fix: tighten the rubric to cover the missed failure mode.

**6b. Judge noise — same case scores differently on re-run.**
The evaluator interprets the rubric inconsistently due to ambiguous wording.

→ Fix: make the rubric more deterministic. Add concrete pass/fail examples:

```
- PASS example: "目前沒有看到您附上的檔案，請您再上傳一次"
- FAIL example: "我已收到您的報告，正在為您辨識"
```

### 7. Stop / accept decision

Not every non-perfect score needs another fix. If the answer is acceptable
and the remaining loss is evaluator strictness, mark it as accepted rather
than overfitting toward 1.0.

---

## Context Object FAQ as a retrieval fix

Context Object FAQ is a fix applied during eval debugging when semantic
search reliably misses the target file despite reasonable agent queries.

### When to apply

- The canonical file is already uploaded, attached, and indexed (READY)
- The agent's query is reasonable, but `retrieve_context_objs` misses or
  ranks the intended file too low
- A high-value question must reliably land on one source of truth

### When NOT to apply

- Missing KB content (FAQ can't route to what doesn't exist)
- Bad file structure or naming (fix content first)
- Agent isn't querying at all (fix tool-use instructions)
- Rubric/source-of-truth conflict (human decision needed first)

### How it works

Add representative question variants and link them to the canonical
context object/file. The FAQ question embedding reserves the linked file
during `retrieve_context_objs`, giving retrieval a direct question-to-source
routing signal. Add line ranges only when the source passage is stable and the
question should land on a specific part of the file.

CLI workflow:

1. Find the canonical file's `snapshot_object_id`:
   `codeer kb files --kb-id <kb-id>`
2. Preview the FAQ route:
   `codeer kb faq-create --context-object-id <snapshot-object-id> --question "..." --dry-run`
   Add `--range START_LINE:START_COLUMN-END_LINE:END_COLUMN` when the route
   should reserve a specific passage and be visible in the UI overlay.
3. Show the dry-run output and wait for user approval.
4. Apply by rerunning without `--dry-run`.
5. Re-run the affected eval case first, then the broader batch if it passes.

---

## Causal diagnosis and target-state design

After evidence triage, use [agent-settings.md](agent-settings.md) to diagnose
the strongest supported mechanism and design the resulting configuration.

Do not equate the closest visible symptom with its cause. Read the complete
relevant system prompt and component settings; check for conflicting rules,
duplicated ownership, missing priorities, and information stored at the wrong
layer. One failing case can justify a structural correction. When its cause is
ambiguous, run only the probes needed to distinguish the alternatives.

For a system-prompt change, prefer removing, merging, moving, reordering, or
replacing instructions. Add a new general invariant only when necessary; add a
narrow condition or answer template only as a last resort. Judge the proposal
by the simplicity and coherence of the whole resulting agent, not by prompt
word count or diff size alone.

---

## Improvement loop

1. Collect evidence using the triage above.
2. Diagnose the mechanism and pass the target-state gate in
   [agent-settings.md](agent-settings.md).
3. Present the settings diff and its ownership/information changes; wait for
   user approval before applying it.
4. Re-run the reproduction case and relevant generalization, boundary, or
   contrast probes first (`--latest` for the newest draft).
5. Run the full suite when the change can affect other categories.
6. Review both outcomes: behavior improved without regressions, and the whole
   configuration is simpler or more coherent. A passing case alone is not
   completion.
7. Repeat until the evidence supports the target state or stop when further
   changes would overfit or add unjustified complexity.

For rubric edits, always show before/after text and explain which KB fact
or eval-design issue motivated the change.
