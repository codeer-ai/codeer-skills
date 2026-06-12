# Eval Debugging

Diagnose eval results and apply the smallest correct fix. This module
covers both scores < 1.0 and spot-checking scores = 1.0.

---

## Entry point

For every non-perfect score, surface: case label, evaluator, score, and
the evaluator's `reason` text. Then **stop and wait for user direction**.

Also review score = 1.0 cases when asked — the evaluator might not be
checking what you think it's checking.

---

## Triage ladder

Diagnose in this order. Do not skip ahead.

### 1. Is the agent's response actually good?

Read the response yourself before looking at tool calls or KB content.

- **Response is good, score is low** → the rubric is too strict. Fix the
  rubric, not the agent.
- **Response is wrong** → continue to step 2.

### 2. Rubric / source-of-truth check

Compare the rubric against KB facts before inspecting the agent's behavior.

- If the rubric contradicts the KB → fix the rubric.
- If the rubric assumes hidden context (KB content, retrieved chunks, tool
  config, diagnosis notes) → make it self-sufficient.
- For broad user questions, do not require unnecessary details the user
  did not ask for.

### 3. Tool-use check

Did the agent call the right tool at all?

- **Agent skipped KB lookup** (answered from training data) →
  fix system prompt (make tool-use rule clearer) or KB
  `invocation_instruction` / "When to Use" (make trigger more specific).
- **Agent made excessive tool calls** (e.g. 13 calls for a simple
  question) → improve system prompt: tighten query strategy, add soft
  limits on retrieval rounds, or improve "When to Use" specificity.

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

- If the agent's query is clearly wrong/too narrow/too general →
  fix system prompt or `invocation_instruction`.
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
- If structure is clear but the agent asked for the wrong part →
  improve prompt / `invocation_instruction` / query hints.

**4d. Information missing AND agent hallucinated.**
The agent fabricated an answer instead of admitting the gap.

→ Fix: strengthen system prompt to refuse or admit lack of information.
This applies even when a KB fix (4a/4b) is also needed.

### 5. Content check (retrieval was correct)

The agent got the right KB content but the response is still wrong.

**5a. KB contradicts the rubric.**
The KB says one thing, the rubric expects another.

→ Flag to user: "The KB and rubric disagree on X — which is the source
of truth?" This requires human judgment.

**5b. Agent embellished or distorted KB content.**
The agent had the right data but added unsupported claims or its own
interpretation.

→ Fix: tighten system prompt — be more explicit about sticking to KB
content and not embellishing.

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

## Diagnosis summary

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Good response, low score | Rubric too strict | Fix rubric |
| Agent didn't use tool | Weak tool trigger | Fix prompt or invocation_instruction |
| Excessive tool calls | Inefficient query strategy | Fix prompt (query hints, soft limits) |
| Canonical file not in KB | KB gap | Add file, attach node IDs, wait for indexing |
| File in KB but never reached | Semantic search miss | Add Context Object FAQ |
| Adjacent chunk only | Wrong chunk in right file | Improve file structure or query hints |
| Missing info + hallucination | No refusal guardrail | Fix prompt to refuse |
| KB contradicts rubric | Source-of-truth conflict | Human decision needed |
| KB correct, response wrong | Agent embellishing | Fix prompt |
| Score 1.0, answer wrong | Rubric coverage gap | Tighten rubric |
| Inconsistent scores | Ambiguous rubric | Add pass/fail examples |

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
   Add `--range START_LINE:END_LINE` when the route should reserve a specific passage.
3. Show the dry-run output and wait for user approval.
4. Apply by rerunning without `--dry-run`.
5. Re-run the affected eval case first, then the broader batch if it passes.

---

## Prompt change discipline

Do not optimize the agent prompt to make one eval case pass. Eval cases
are coverage probes, not training examples. A prompt change is acceptable
only when it fixes a general behavior that should hold across the agent's
real operating scope.

### Before proposing a prompt change, compare these options

1. No change — the failure is acceptable or evaluator noise
2. Rubric edit — the judge is asking for the wrong thing
3. Eval case edit — the case is underspecified or not representative
4. KB update — the source material is missing or stale
5. KB `invocation_instruction` update — retrieval trigger/querying is the issue
6. Context Object FAQ — reasonable query, semantic search misses the file
7. Minimal prompt edit — the agent needs a broader behavioral rule

### For any prompt edit, state

- The exact behavioral defect being fixed
- Why this is not case-specific overfitting
- The smallest prompt diff that could fix it
- Which existing categories might regress
- Which full-batch eval run will verify the change

### Avoid

- Adding phrases copied from a failing eval case
- Adding answer templates for one scenario
- Adding long new policy sections for narrow failures
- Changing unrelated style, tone, or workflow rules
- Treating eval cases as the full product requirement

---

## Fix loop

1. Diagnose using the triage ladder above.
2. Apply the smallest agreed fix.
3. Re-run impacted cases first (`--latest` for newest draft).
4. Run the full suite when the change has cross-category regression risk.
5. Review — targeted cases improved without regressing others.
6. Repeat until satisfied.

For rubric edits, always show before/after text and explain which KB fact
or eval-design issue motivated the change.
