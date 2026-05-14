# Codeer Agent Lifecycle

Two phases: **Build** (zero to first publish) and **Improve** (continuous
iteration on a live agent). The tools are the same; the entry point and
source of truth differ.

Use registered `codeer` domain commands only. If an operation is not supported
by the CLI, say that it is not supported by the CLI and stop for user
direction.

---

## Phase 1: Build

From nothing to a publishable agent.

### Step 1 — Scope alignment

**Do this before any KB or agent work.** Pin down five things with the user:

1. **In-scope categories** — 3-6 concrete usage scenarios the agent must
   handle (e.g. "B2C consultation routing", "course recommendation",
   "enterprise intake", "card product Q&A").
2. **Out-of-scope** — what to deflect or escalate (legal advice, medical,
   competitor pricing, sensitive personal data, etc.).
3. **Conversion goals** — what counts as a successful outcome per category
   (booking link click, form submission, purchase URL, callback request).
4. **Hard rules** — anything the agent must never do (never quote a price
   not in the KB, never invent a course slug, etc.).
5. **Tools used** — which tools the agent needs and why (knowledge base,
   web search, request form, call agent, memory, http request, etc.).

Save the answers to `.codeer/scope.md`. This document feeds directly into
the system prompt (allowed outcomes + boundaries), KB content scope, and
eval case design.

### Step 2 — Prepare and upload KB

1. Crawl / write `kb/*.md` files. Keep filenames descriptive (the KB tool
   exposes them to the agent).
2. Upload to Codeer:
   ```bash
   codeer kb upload \
       --dir kb/ --name "<KB display name>" \
       --out .codeer/kb_ids.json
   ```
3. `.codeer/kb_ids.json` now contains `kb_id`, `node_ids`, `name_to_id` —
   feed these into the agent payload.

KB planning decisions to confirm with the user:
- One KB or several? (default: one per agent)
- Flat root or one level of folders? (KB UI only renders one level)
- Naming convention — descriptive `NN_topic.md` vs. opaque IDs

**KB query hints in the system prompt.** The agent queries KB content
using three tools: `list_kb_files` (regex filename search),
`retrieve_context_objs` (semantic search by question/keywords), and
`get_context_obj_lines` (read specific lines from a file). The agent's
query quality depends heavily on knowing what's in the KB and how to
find it. Include a brief topic map in the agent's system prompt that
tells the agent what content is available and how to query it. Example:

> KB contains: product specs in `01_products.md`–`05_products.md`,
> pricing in `10_pricing.md`, FAQ in `20_faq.md`, and service routing
> rules in `22_service_map.md`. Search by product name, category, or
> service type.

This dramatically improves retrieval accuracy — without it, the agent
guesses at filenames and keywords, often missing relevant content. When
filenames are opaque or the KB is large, this index is critical.

### Step 3 — Create agent

Write `.codeer/agent_payload.json`. Pull allowed outcomes and boundaries from
`.codeer/scope.md`; attach KB node IDs from `.codeer/kb_ids.json`.

```bash
codeer agent apply \
    --payload .codeer/agent_payload.json --out .codeer/agent_ids.json
```

### Step 4 — Build eval cases

This is where coverage quality is decided. Work **one category at a time**
so the user can review a manageable batch instead of being overwhelmed by
dozens of cases at once.

#### Step 4a — MECE categories

Inspect the agent's settings, system prompt, KBs, and tools. Propose a
set of mutually exclusive, collectively exhaustive categories for the
agent's expected work — for example: product Q&A, routing, ordering,
policy boundaries, tool-backed actions, and out-of-scope refusals.
Aim for 3-6 categories. **Confirm the category structure with the user
before writing any cases.**

#### Step 4b — Category loop

For each category (user picks which to tackle first, or go sequentially):

1. **Decide case count.** Judge the appropriate number of cases for this
   category based on its complexity, boundary conditions, and
   hallucination risk. State the count and rationale — the user can
   adjust.
2. **Generate cases + rubrics.** Write cases for this category only.
   Each case carries per-evaluator rubrics — Style/Tone judges *how*,
   Content Compliance judges *what*. Prioritize the **Content Compliance
   Evaluator** unless the user explicitly cares about style. Its rubrics
   must be self-sufficient: the evaluator only has its system prompt and
   the rubric, not the agent's KB or tools.
3. **Present for review.** Show the cases to the user. Keep the batch
   small enough to be mentally manageable.
4. **Apply.** After user approves (with any adjustments):
   ```bash
   codeer eval cases-apply \
       --cases .codeer/eval_cases.json --agent <agent_id> --out .codeer/case_ids.json
   ```
   Then output the eval-cases link so the user can verify on the server
   (see **Server links** section below).
5. **Optionally test this batch.** If the user wants, run eval on just
   the new cases, diagnose and fix issues before moving to the next
   category. This catches problems early without waiting for the full
   suite.
6. **Next category.** Repeat from step 1 for the next category.

#### Step 4c — Full sweep

After all categories are covered, run eval across ALL cases as a final
regression check:

```bash
codeer eval run \
    --agent <agent_id> --latest-draft \
    --out .codeer/eval_results.json
```

### Step 5 — Run eval, fix, repeat

```bash
codeer eval run \
    --agent <agent_id> --latest-draft \
    --out .codeer/eval_results.json
```

For every score < 1.0, surface the case label, evaluator, score, and
the evaluator's `reason` text. Then **stop and wait for user direction**.

The fix loop within Phase 1:
1. Diagnose each failure — agent issue (prompt/KB) or rubric issue
2. Apply the fix → re-run ALL cases with `--diff-vs <prev_history_id>`
3. Review — check that targeted cases improved without regressing others
4. Repeat until satisfied

#### Prompt change discipline

Do not optimize the agent prompt to make one eval case pass. Eval cases
are coverage probes, not training examples. A prompt change is acceptable
only when it fixes a general behavior that should hold across the agent's
real operating scope.

Before proposing a prompt change, compare these options:
- No change — the failure is acceptable or evaluator noise
- Rubric edit — the judge is asking for the wrong thing
- Eval case edit — the case is underspecified or not representative
- KB update — the source material is missing or stale
- KB `invocation_instruction` update — retrieval trigger/querying is the issue
- Minimal prompt edit — the agent needs a broader behavioral rule

For any prompt edit, state:
- The exact behavioral defect being fixed
- Why this is not case-specific overfitting
- The smallest prompt diff that could fix it
- Which existing categories might regress
- Which full-batch eval run will verify the change

Avoid:
- Adding phrases copied from a failing eval case
- Adding answer templates for one scenario
- Adding long new policy sections for narrow failures
- Changing unrelated style, tone, or workflow rules
- Treating eval cases as the full product requirement

### Step 6 — Publish

Only after explicit user go-ahead on eval results.

```bash
codeer agent versions --agent <agent_id>
```

Downstream impact checks are not supported by the CLI. If the user asks for
that check, say it is not supported by the CLI and stop for direction. Use the
registered publish command when available; if publishing is not exposed by the
CLI, say it is not supported by the CLI.

---

## Phase 2: Improve

The agent is live with real users. The goal is continuous improvement
driven by production data.

### Step 1 — Pull production data

Not all users or channels provide explicit feedback (thumbs up/down).
Conversation history is the primary source of truth.

```bash
codeer history list --agent <agent_id>
```

Use `codeer history negative-feedback --agent <agent_id>` to surface flagged
turns where feedback is available. For channels without feedback, use
`codeer history conversations <history_id>` after listing histories.

### Step 2 — Analyze and categorize

Read through production conversations and classify findings:

- **Failures** — agent gave wrong answer, hallucinated, missed a tool
  call, broke a hard rule
- **Improvement opportunities** — agent was technically correct but could
  be better (tone, clarity, conversion flow)
- **Successful patterns** — agent did something right that increased
  conversion or user satisfaction. These need protection from future
  regressions.

**Map each finding to an existing MECE category** from the eval suite
(the categories established in Phase 1 Step 4a). If a finding doesn't
fit any existing category, propose a new one — this is a coverage gap.

Present the categorized findings to the user with a recommendation of
which categories need new or updated cases. Let the user pick which
categories to work on and in what order.

### Step 3 — Build eval cases FIRST (one category at a time)

**Before making any fix**, turn each finding into an eval case. The eval
case defines what "fixed" or "protected" means — without it, you can't
verify the fix worked.

- Each failure becomes a case where the current agent should fail (and
  the fixed agent should pass)
- Each successful pattern becomes a case where the current agent should
  pass (and must keep passing after changes)
- Rewrite findings into the smallest input that makes the behavior
  objectively judgeable. Don't copy production messages verbatim — isolate
  the specific behavior being tested.

**Work one category at a time** — same loop as Phase 1 Step 4b:
generate cases for one category → present for review → user approves →
apply → optionally test just those cases → next category. This keeps
each review batch manageable and lets the user focus on one problem area
at a time.

```bash
codeer eval cases-apply \
    --cases .codeer/eval_cases.json --agent <agent_id> --out .codeer/case_ids.json
```

After applying, output the eval-cases link so the user can verify on
the server (see **Server links** section).

Use `meta.previous_conversations` in `codeer eval cases-apply` when the
failure requires multi-turn context.

### Step 4 — Run eval (baseline)

Run eval against the **current published version** to establish a baseline.
New failure cases should fail; protection cases should pass.

```bash
codeer eval run \
    --agent <agent_id> --history <published_history_id> \
    --out .codeer/eval_baseline.json
```

### Step 5 — Apply the fix

Make the smallest change that addresses the findings:
- Prompt change → `codeer agent apply` (auto-forks a new draft)
- KB update → `codeer kb upload`
- Rubric edit → `codeer eval rubrics-apply`

For prompt changes, use the **Prompt change discipline** from Phase 1.
The target is better general behavior across the coverage map, not a
case-specific patch that only improves the current eval failures.

### Step 6 — Re-run ALL eval cases

```bash
codeer eval run \
    --agent <agent_id> --latest-draft \
    --diff-vs <prev_history_id> --out .codeer/eval_results.json
```

`--diff-vs` prints a regression table — every case whose score moved up
or down vs the previous version. Check that:
- Targeted failure cases now pass
- Protection cases still pass
- No unrelated cases regressed

### Step 7 — Review and decide

**Stop and report results to the user.** They decide:
- Publish the new version
- Iterate more (back to step 5)
- Roll back if regressions are unacceptable

### Step 8 — Publish or roll back

Publish promotes a draft. Rollback re-publishes an older version.
Both are non-destructive; older versions are preserved.

Then loop back to Step 1 with new production data.

---

## Debugging eval results

Eval has two sides: the **agent** (calls tools, produces a response) and
the **evaluator** (an LLM judge with a system prompt template containing
`{input}`, `{output}`, `{rubric}`, `{expected_output}`, `{tool_steps}`).

Even when a case scores 1.0, the evaluator might not be checking what you
think it's checking. But most debugging focuses on cases scoring < 1.0.

### Start here: is the agent's response actually good or bad?

**If the response is actually good** — the rubric is too strict. Fix the
rubric, not the agent.

**If the response is wrong** — check what tool calls the agent made and
what data it got back. The diagnostic tree below walks through the
possibilities.

### Agent didn't call the right tool

The agent skipped the KB lookup entirely (or called the wrong tool) and
answered from its own training data. The response may sound plausible but
isn't grounded in KB content.

**Fix**: system prompt (make the tool-use rule clearer) or KB
`invocation_instruction` / "when to use" (make the trigger more specific).

### Agent called KB but the key information is missing from query results

**1. The information is not in the KB at all.**
The KB simply doesn't contain the answer. No prompt fix will help.

Fix: enhance the KB content — add or update the relevant file.

**2. The information IS in the KB but the query didn't retrieve it.**
The agent asked the wrong question or the KB's trigger didn't fire on
the right content.

Fix: improve the agent's system prompt (guide how it formulates queries)
and/or the KB's `invocation_instruction` to improve retrieval quality.

**2.5. The information is missing from query results AND the agent made
something up instead of admitting the gap.**
The agent hallucinated rather than saying "I don't have that information."

Fix: strengthen the system prompt to refuse or admit lack of information
rather than fabricate answers. This applies even when the KB fix from #1
or #2 also needs to happen.

### Agent got the right KB content but the response is still wrong

**3. The KB content contradicts the rubric.**
The KB says one thing, the rubric expects another. Someone needs to decide
which is correct — this requires human judgment.

Flag to user: "The KB and rubric disagree on X — which is the source of
truth?"

**4. The KB content is correct but the agent answered wrong or added its
own interpretation.**
The agent had the right data but distorted it, added unsupported claims,
or mixed in its own reasoning.

Fix: tighten the system prompt — be more explicit about sticking to KB
content and not embellishing.

### Evaluator-side issues

**5. Score = 1.0 but the answer is actually wrong.**
The rubric has a coverage gap — it doesn't test the dimension that's
actually broken. The judge scores 1.0 because nothing in the rubric
catches the real problem.

Fix: tighten the rubric to cover the missed failure mode.

**6. Judge noise — same case scores differently on re-run.**
The evaluator LLM interprets the rubric inconsistently because the
wording is ambiguous.

Fix: make the rubric more deterministic. Add concrete pass/fail examples
inline so the judge has anchors:
```
- PASS example: "目前沒有看到您附上的檔案，請您再上傳一次"
- FAIL example: "我已收到您的報告，正在為您辨識"
```

### Diagnosis summary

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Good response, low score | Rubric too strict | Fix rubric |
| Agent didn't use tool | Weak tool trigger | Fix prompt or invocation_instruction |
| Info not in KB | KB gap | Add KB content |
| Info in KB, not in query results | Bad retrieval | Fix prompt / KB when-to-use |
| Missing info + hallucination | No refusal guardrail | Fix prompt to refuse |
| KB contradicts rubric | Source of truth conflict | Human decision needed |
| KB correct, response wrong | Agent embellishing | Fix prompt |
| Score 1.0, answer wrong | Rubric coverage gap | Tighten rubric |
| Inconsistent scores across runs | Ambiguous rubric | Add pass/fail examples |

---

## Command reference

All generated files go under **`.codeer/`** in the project root.
Only `kb/` (source content for upload) stays at root level.

| Command | Purpose |
| --- | --- |
| `codeer check` | Validate auth, workspace, and agent config |
| `codeer agent list\|get\|apply\|diff\|versions\|publish` | Agent CRUD, versioning, publishing |
| `codeer kb list` | List knowledge bases in workspace |
| `codeer kb upload` | Create/reuse KB + upload files + poll until indexed |
| `codeer eval list` | List eval cases for an agent |
| `codeer eval evaluators` | List evaluators in workspace |
| `codeer eval run` | Trigger eval, poll, print non-perfect analysis, `--diff-vs` regression |
| `codeer eval export` | Full eval table export (CSV + JSON + summary MD) |
| `codeer eval cases-apply` | Bulk-create eval cases with per-evaluator rubrics |
| `codeer eval rubrics` | Read per-(case, evaluator) rubrics |
| `codeer eval rubrics-apply` | Apply rubric edits (pairs with `eval rubrics`) |
| `codeer eval reconcile` | Read-only audit: compare local manifest vs server state |

All commands run via the separately installed `codeer` CLI.

Workspace and organization scope come from the workspace API-key virtual user's
profile. The optional `CODEER_AGENT_ID` can live in `.claude/settings.json`
when a project has one default agent.

### Common helpers (for ad-hoc Python)

Only fall back to these when the CLI commands above can't express what you need:

- `histories.list_production(agent_id, internal_user_emails=...)` — filter
  out internal testing accounts.
- `histories.list_negative_feedback_turns(agent_id, ...)` — surface
  assistant turns flagged with `sys_improve`.
- `eval_mod.list_runs_for_case(case_id, agent_id, workspace_id, evaluator_id)`
  — score history of one case across every version.
- `agents.get_latest_draft_history_id(agent_id)` — find the newest
  unpublished draft version.

---

## Server links

After any step that creates or modifies server state, output the relevant
Codeer web link so the user can verify visually. Construct URLs from
`CODEER_API_BASE` (the same origin as the API).

| After… | Link |
| --- | --- |
| Creating or updating an agent | `{CODEER_API_BASE}/workspaces/{workspace_id}/agents/{agent_id}` |
| Applying eval cases or rubrics | `{CODEER_API_BASE}/workspaces/{workspace_id}/agents/{agent_id}?tab=evaluation` |
| Running eval | `{CODEER_API_BASE}/workspaces/{workspace_id}/agents/{agent_id}?tab=evaluation` |
| Viewing a conversation history | `{CODEER_API_BASE}/workspaces/{workspace_id}/histories/{history_id}` |
| Listing agents in workspace | `{CODEER_API_BASE}/workspaces/{workspace_id}?tab=edit-agents` |
| KB uploads | `{CODEER_API_BASE}/knowledge-base` |

---

## Common errors and recovery

Run `codeer check` first — it catches most setup
problems. For errors that happen during work:

| Error | Cause | Fix |
| --- | --- | --- |
| HTTP 401 or 403 | API key missing, invalid, expired, revoked, or under-scoped | Create an admin workspace API key and export `CODEER_API_KEY`. Run `codeer check`. |
| HTTP 400 "Organization ID is required" | API-key virtual user profile did not expose `default_organization_id` | Run `codeer check`; the API key may not be a workspace API key. |
| KB upload returns `status: FAILED`, `node_id: null`, no error message | Wrong or missing Content-Type on the uploaded file | The `kb.upload_file()` helper handles this. If uploading manually, pass `(filename, file_handle, content_type)` as a 3-tuple. Image files (JPEG, PNG, etc.) are not accepted for KB uploads. |
| KB upload returns HTTP 422 `"Field required"` on `form` | `parent_id` sent as a top-level form field instead of JSON-encoded `form` field | Use `kb.upload_files()` which handles the Django Ninja quirk. If calling manually, the multipart body needs `form: {"parent_id": "..."}` as a single JSON-encoded field. |
| Agent saves but form fields render blank in UI | Invalid form field `type` value (e.g. `"text"`, `"email"`, `"select"`) | Valid types: `shortText`, `longText`, `number`, `dropdown`, `radio`, `checkbox`, `date`. Use `shortText` for email/text, `dropdown` for select. |
| Eval results show `score: null` for some cases | Cases haven't been evaluated on that agent version yet | `null` means "not yet run", not "failed". Trigger eval for those cases, or check that the correct `agent_history_id` was passed. |
| Changes land in the wrong workspace | Wrong API key is active in the runtime environment | Export the API key for the intended workspace and run `codeer check`. |
| `codeer check` can't find credentials | `CODEER_API_KEY` is missing from the process environment | Export it outside the workspace. See `onboarding.md`. |
