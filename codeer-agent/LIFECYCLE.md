# Codeer Agent Lifecycle

Two phases: **Build** (zero to first publish) and **Improve** (continuous
iteration on a live agent). The tools are the same; the entry point and
source of truth differ.

For endpoint shapes and gotchas, read **API_CHEATSHEET.md**.

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
   $SKILL_DIR/scripts/codeer kb upload \
       --dir kb/ --name "<KB display name>" \
       --workspace <ws_id> --org <org_id> --out .codeer/kb_ids.json
   ```
3. `.codeer/kb_ids.json` now contains `kb_id`, `node_ids`, `name_to_id` —
   feed these into the agent payload.

KB planning decisions to confirm with the user:
- One KB or several? (default: one per agent)
- Flat root or one level of folders? (KB UI only renders one level — see
  API_CHEATSHEET.md gotcha #10)
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
$SKILL_DIR/scripts/codeer agent apply \
    --payload .codeer/agent_payload.json --out .codeer/agent_ids.json
```

### Step 4 — Build eval cases

This is where coverage quality is decided. Use MECE categorization to
ensure the eval suite covers the agent's full scope:

1. **MECE category structure.** Inspect the agent's settings, system
   prompt, KBs, and tools. Propose a set of mutually exclusive,
   collectively exhaustive categories for the agent's expected work — for
   example: product Q&A, routing, ordering, policy boundaries, tool-backed
   actions, and out-of-scope refusals. Confirm the structure with the user
   before writing cases.

2. **One case per category minimum.** Each in-scope category from the
   scope doc gets at least one eval case. Add boundary cases for hard
   rules and hallucination traps for out-of-scope categories.

3. **Per-evaluator rubrics.** Each case carries rubrics per evaluator —
   Style/Tone judges *how*, Content Compliance judges *what*. Prioritize
   the **Content Compliance Evaluator** unless the user explicitly cares
   about style. Its rubrics must be self-sufficient: the evaluator only
   has its system prompt and the rubric, not the agent's KB or tools.

```bash
$SKILL_DIR/scripts/codeer eval cases-apply \
    --cases .codeer/eval_cases.json --agent <agent_id> --out .codeer/case_ids.json
```

### Step 5 — Run eval, fix, repeat

```bash
$SKILL_DIR/scripts/codeer eval run \
    --agent <agent_id> --latest-draft --workspace <ws_id> \
    --out .codeer/eval_results.json
```

For every score < 1.0, surface the case label, evaluator, score, and
the evaluator's `reason` text. Then **stop and wait for user direction**.

The fix loop within Phase 1:
1. Diagnose each failure — agent issue (prompt/KB) or rubric issue
2. Apply the fix → re-run ALL cases with `--diff-vs <prev_history_id>`
3. Review — check that targeted cases improved without regressing others
4. Repeat until satisfied

### Step 6 — Publish

Only after explicit user go-ahead on eval results.

```bash
# Check downstream impact first if other agents call this one
$SKILL_DIR/scripts/codeer api get /agents/<agent_id>/impact
```

Use `agents.publish_version()` to promote the draft.

---

## Phase 2: Improve

The agent is live with real users. The goal is continuous improvement
driven by production data.

### Step 1 — Pull production data

Not all users or channels provide explicit feedback (thumbs up/down).
Conversation history is the primary source of truth.

```bash
# Pull conversation histories (filter by feedback if available)
$SKILL_DIR/scripts/codeer api get /histories \
    --param agent_id=<id> --param wid=<ws>
```

Use `histories.list_production()` to filter out internal testing accounts.
Use `histories.list_negative_feedback_turns()` to surface flagged turns
where feedback is available. For channels without feedback, read
conversation histories directly via `histories.get_conversations()`.

### Step 2 — Analyze

Read through production conversations and classify findings:

- **Failures** — agent gave wrong answer, hallucinated, missed a tool
  call, broke a hard rule
- **Improvement opportunities** — agent was technically correct but could
  be better (tone, clarity, conversion flow)
- **Successful patterns** — agent did something right that increased
  conversion or user satisfaction. These need protection from future
  regressions.

### Step 3 — Build eval cases FIRST

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

```bash
$SKILL_DIR/scripts/codeer eval cases-apply \
    --cases .codeer/eval_cases.json --agent <agent_id> --out .codeer/case_ids.json
```

Use `meta.previous_conversations` in `codeer eval cases-apply` when the
failure requires multi-turn context.

### Step 4 — Run eval (baseline)

Run eval against the **current published version** to establish a baseline.
New failure cases should fail; protection cases should pass.

```bash
$SKILL_DIR/scripts/codeer eval run \
    --agent <agent_id> --history <published_history_id> --workspace <ws_id> \
    --out .codeer/eval_baseline.json
```

### Step 5 — Apply the fix

Make the smallest change that addresses the findings:
- Prompt change → `codeer agent apply` (auto-forks a new draft)
- KB update → `codeer kb upload`
- Rubric edit → `codeer eval rubrics-apply`

### Step 6 — Re-run ALL eval cases

```bash
$SKILL_DIR/scripts/codeer eval run \
    --agent <agent_id> --latest-draft --workspace <ws_id> \
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
Both use the same endpoint — non-destructive, older versions are preserved.

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
| `codeer api get\|post\|put\|patch\|delete\|stream` | Raw API escape hatch |

All commands run via `$SKILL_DIR/scripts/codeer <noun> <verb>`.

Per-project env (set in `.claude/settings.json` `env` block) makes
workspace and agent IDs injectable: `CODEER_WORKSPACE_ID`,
`CODEER_ORGANIZATION_ID`, `CODEER_AGENT_ID`. In Cowork, pass these as CLI
flags, add them to `session.env` for a single-workspace session, or export
them in the bash call.

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

## Common errors and recovery

Run `codeer check` first — it catches most setup
problems. For errors that happen during work:

| Error | Cause | Fix |
| --- | --- | --- |
| HTTP 401 or 403 | Session cookie expired | Re-grab `sessionid` and `csrftoken` from Codeer UI -> devtools -> Application -> Cookies. Update `~/.codeer/session.env` or repo-root `session.env`. |
| HTTP 403 "CSRF Failed" | CSRF token missing or mismatched | Ensure `CODEER_CSRF_TOKEN` in `session.env` matches the `csrftoken` cookie. Both must be the same value. |
| HTTP 400 "Organization ID is required" | Using `/agents/all` without `oid` param | Pass both `wid` and `oid`. Look up org for workspace via `GET /accounts/me` -> `profile.workspace_organization_map`. |
| KB upload returns `status: FAILED`, `node_id: null`, no error message | Wrong or missing Content-Type on the uploaded file | The `kb.upload_file()` helper handles this. If uploading manually, pass `(filename, file_handle, content_type)` as a 3-tuple. Image files (JPEG, PNG, etc.) are not accepted for KB uploads. |
| KB upload returns HTTP 422 `"Field required"` on `form` | `parent_id` sent as a top-level form field instead of JSON-encoded `form` field | Use `kb.upload_files()` which handles the Django Ninja quirk. If calling manually, the multipart body needs `form: {"parent_id": "..."}` as a single JSON-encoded field. |
| Agent saves but form fields render blank in UI | Invalid form field `type` value (e.g. `"text"`, `"email"`, `"select"`) | Valid types: `shortText`, `longText`, `number`, `dropdown`, `radio`, `checkbox`, `date`. Use `shortText` for email/text, `dropdown` for select. |
| Eval results show `score: null` for some cases | Cases haven't been evaluated on that agent version yet | `null` means "not yet run", not "failed". Trigger eval for those cases, or check that the correct `agent_history_id` was passed. |
| Changes land in the wrong workspace | `CODEER_WORKSPACE_ID` not set or wrong for this project | Set per-project in `.claude/settings.json`, pass `--workspace`, or set it in the current Cowork bash environment. Run `codeer check` to verify. |
| `codeer check` can't find credentials | `~/.codeer/session.env` and repo-root `session.env` are missing or empty | Create a credential file with `CODEER_API_BASE`, `CODEER_SESSION_ID`, `CODEER_CSRF_TOKEN`. See SKILL.md setup section. |
