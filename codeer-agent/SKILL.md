---
name: codeer-agent
description: Build, evaluate, publish, and analyze Codeer agents over the Codeer API. Use for Codeer agent design, knowledge base uploads, eval cases and rubrics, draft live tests, publishing, production history analysis, and feedback review.
---

# Codeer Agent Lifecycle — skill

Everything you need to build, evaluate, and improve a Codeer agent against
whatever files the user has in their current directory. Authenticates with a
workspace-scoped API key and calls the external Codeer API directly.

## Working pattern with the user (read this first)

This skill controls real customer agents — wrong moves cost money and trust.
The user's preference is **heavy planning, minimal execution**: invest more
in thinking, exploring, and surfacing tradeoffs *before* you act, then make
the smallest possible change once a plan is agreed.

Concretely:

- **Plan → Confirm → Act.** For any non-trivial request, state the plan
  before executing: which artifacts you will touch (file paths, case IDs,
  endpoints), what each change is, and what you expect the outcome to be.
  Wait for explicit go-ahead. Treat the user's "OK" as authorising the
  specific plan you just stated, not your interpretation of next steps.

- **Be brave during planning.** Surface alternatives, edge cases, and
  uncomfortable angles ("the rubric might be the issue, not the prompt").
  Multi-option proposals beat pre-selected ones when there's a real choice.

- **Be minimal during execution.** Smallest diff that satisfies the agreed
  plan. No bonus refactors, no helper functions added "while you're in
  there", no extra files. Stop after the minimum and report.

- **Surface sub-choices, don't answer them yourself.** If a request
  requires picking which N cases / which severity / which evaluator,
  ask — don't decide on the user's behalf.

## Setup (one time, per user)

Set external API credentials in the environment used by the model/runtime:

```bash
CODEER_EXTERNAL_API_BASE=http://localhost:8000/api/v1/external/v1  # or your staging/prod base
CODEER_API_KEY=<workspace-scoped-api-key>
```

Use API-key auth only. Do not use browser cookies, `sessionid`, `csrftoken`, or
CSRF headers for this skill.

**At the start of any Codeer-skill session, call `GET /me`** and state the
active workspace/org name to the user — this catches a missing or wrong API key
scope before any KB upload or agent edit lands in the wrong place.

## Invocation

This skill intentionally does not ship Python wrappers or reusable scripts.
When you need Codeer data or need to make a Codeer change, call the external
API directly from the current environment.

For JSON APIs, use `curl` or a short one-off HTTP request. For multipart
uploads, use `curl -F`. Keep request payloads and response snapshots in
`.codeer/` when they are useful for review.

```bash
curl -sS "$CODEER_EXTERNAL_API_BASE/me" \
  -H "X-API-Key: $CODEER_API_KEY"
```

Use `X-API-Key` as the single auth header for this external API.

## Direct API operations (use these — don't write per-customer .py files)

Common operations should be represented as JSON payloads or captured API
responses, so the customer's directory only needs **data files** (KB content,
`.codeer/agent_payload.json`, `.codeer/eval_cases.json`) — not bespoke Python.

### Output directory convention

All generated files — payloads, ID maps, eval results, ad-hoc request/response
snapshots — go under **`.codeer/`** in the customer's project root. Create the
directory at the start of a session if it doesn't exist (`mkdir -p .codeer`).
This keeps the project root clean; only `kb/` (source content for upload)
stays at root level.

```bash
# 1. Build KB and upload all files in a directory
curl -sS "$CODEER_EXTERNAL_API_BASE/knowledge-bases" \
  -H "X-API-Key: $CODEER_API_KEY" \
  -H "Content-Type: application/json" \
  --data '{"name":"<KB display name>"}' \
  > .codeer/kb_create_response.json

# Upload each file. Set KB_ID from the created KB root id.
for file in kb/*; do
  [ -f "$file" ] || continue
  curl -sS "$CODEER_EXTERNAL_API_BASE/knowledge-bases/$KB_ID/files:upload" \
    -H "X-API-Key: $CODEER_API_KEY" \
    -F "parent_id=$KB_ID" \
    -F "files=@$file"
done

# Poll indexing status after collecting uploaded node IDs.
curl -sS "$CODEER_EXTERNAL_API_BASE/knowledge-bases/files:status" \
  -H "X-API-Key: $CODEER_API_KEY" \
  -H "Content-Type: application/json" \
  --data @.codeer/kb_status_request.json

# Save kb_id, uploaded node_ids, and any filename-to-node mapping in
# .codeer/kb_ids.json.

# 2. Create or update an agent (PATCH auto-forks a new draft version)
curl -sS "$CODEER_EXTERNAL_API_BASE/agents" \
  -H "X-API-Key: $CODEER_API_KEY" \
  -H "Content-Type: application/json" \
  --data @.codeer/agent_payload.json

curl -sS "$CODEER_EXTERNAL_API_BASE/agents/$AGENT_ID" \
  -X PATCH \
  -H "X-API-Key: $CODEER_API_KEY" \
  -H "Content-Type: application/json" \
  --data @.codeer/agent_payload.json

# 3. Create eval cases with per-evaluator rubrics from JSON
#    Add attachments with POST /files first when any case has local attachment files.
curl -sS "$CODEER_EXTERNAL_API_BASE/eval/cases" \
  -H "X-API-Key: $CODEER_API_KEY" \
  -H "Content-Type: application/json" \
  --data @.codeer/eval_case.json

curl -sS "$CODEER_EXTERNAL_API_BASE/eval/cases/$CASE_ID/rubrics/$EVALUATOR_ID" \
  -X PUT \
  -H "X-API-Key: $CODEER_API_KEY" \
  -H "Content-Type: application/json" \
  --data '{"rubric":"<per-evaluator standard>"}'

# 4. Trigger an eval run; auto-pick the newest draft and diff vs the previous history
curl -sS "$CODEER_EXTERNAL_API_BASE/eval/runs" \
  -H "X-API-Key: $CODEER_API_KEY" \
  -H "Content-Type: application/json" \
  --data @.codeer/eval_run.json

curl -sS "$CODEER_EXTERNAL_API_BASE/eval/results:batch" \
  -H "X-API-Key: $CODEER_API_KEY" \
  -H "Content-Type: application/json" \
  --data @.codeer/eval_results_request.json

# 5. Show a system-prompt + tools diff between two AgentHistory versions
curl -sS "$CODEER_EXTERNAL_API_BASE/agents/$AGENT_ID/versions" \
  -H "X-API-Key: $CODEER_API_KEY"
# Save the two version responses under .codeer/ and compare system_prompt
# and tools / unified_tools.

# 6. Pull the whole eval table without third-party dependencies (preferred for read-only audit)
curl -sS "$CODEER_EXTERNAL_API_BASE/eval/results:batch" \
  -H "X-API-Key: $CODEER_API_KEY" \
  -H "Content-Type: application/json" \
  --data @.codeer/eval_results_request.json \
  > .codeer/eval_table/results.json

# Pull the published eval table by using the published version_id in
# .codeer/eval_results_request.json.

# 7. Read current rubrics for all (case, evaluator) pairs
curl -sS "$CODEER_EXTERNAL_API_BASE/eval/rubrics:batch" \
  -H "X-API-Key: $CODEER_API_KEY" \
  -H "Content-Type: application/json" \
  --data @.codeer/rubrics_request.json

# 8. Apply rubric edits (read → edit → apply cycle with #7)
curl -sS "$CODEER_EXTERNAL_API_BASE/eval/cases/$CASE_ID/rubrics/$EVALUATOR_ID" \
  -X PUT \
  -H "X-API-Key: $CODEER_API_KEY" \
  -H "Content-Type: application/json" \
  --data @.codeer/rubric_update.json

# 9. Reconcile local eval manifest with server state (read-only audit)
curl -sS "$CODEER_EXTERNAL_API_BASE/eval/agents/$AGENT_ID/cases" \
  -H "X-API-Key: $CODEER_API_KEY" \
  > .codeer/server_cases.json

curl -sS "$CODEER_EXTERNAL_API_BASE/eval/evaluators" \
  -H "X-API-Key: $CODEER_API_KEY" \
  > .codeer/server_evaluators.json

# Compare .codeer/eval_cases.json with .codeer/server_cases.json and save
# the read-only audit result to .codeer/eval_reconcile.json.
```

## The 9-stage lifecycle

Source of truth for endpoints: **`API_CHEATSHEET.md`** inside this skill dir.
Read it before writing payloads by hand — the **Gotchas** section at the end
captures the non-obvious traps.

| Stage | Purpose | Primary helpers |
| --- | --- | --- |
| 0. Scope alignment | Confirm in-scope categories, out-of-scope, lead goal, hard rules with the user | `AskUserQuestion` → save to `.codeer/scope.md` |
| 1. Author | Create/update agent + tools | `POST /agents`, `PATCH /agents/{id}` |
| 2. Knowledge base | Create KB, folders, upload files | `/knowledge-bases*` external API endpoints |
| 3. Live Test (debug only) | Chat against a specific draft version — used to investigate a failing eval, not as a default validation step | `POST /chats`, `POST /chats/{id}/messages` |
| 4. Version | List/inspect `AgentHistory` snapshots | `GET /agents/{id}/versions`, `GET /agents/{id}/versions/{version_id}` |
| 5. Eval cases | Create cases with per-evaluator rubrics — **one per scope category from stage 0**, plus reverse / out-of-scope / hallucination-trap cases | `POST /eval/cases`, `PUT /eval/cases/{case_id}/rubrics/{evaluator_id}` |
| 6. Eval run | Trigger + read results per version, then **STOP and report non-perfect cases**. Compare against the previous version after every prompt change to catch regressions in unrelated cases. | `POST /eval/runs`, `POST /eval/results:batch` |
| 7. Publish | Promote a specific version (only after explicit user direction) | `POST /agents/{id}/versions/{version_id}:publish`, `GET /agents/{id}/impact` |
| 8. Post-release | Read histories + feedback. Filter to real visitors and surface flagged turns. | `GET /histories`, `GET /histories/{id}/conversations` |
| 9. Rollback | Re-publish an older version | `POST /agents/{id}/versions/{version_id}:publish` on older `version_id` |

## Top gotchas (quickref — full list in API_CHEATSHEET.md)

1. **`/agents` is published-only.** Use `/agents/all` while iterating on
   drafts.

2. **Form field `type` has a fixed enum.** Valid: `shortText`, `longText`,
   `number`, `dropdown`, `radio`, `checkbox`, `date`. There is **no** `text`,
   `email`, or `select`. The backend validator is lenient and will save broken
   tools that render as blank fields in the UI. Validate payloads before
   POST/PATCH; the backend may accept broken form config that the UI cannot
   render.

3. **The UI's `Standard` column is a per-(case, evaluator) rubric.** The
   `rubric` arg on `POST /eval/cases` is a default, not what the UI reads.
   Always set rubrics with `PUT /eval/cases/{case_id}/rubrics/{evaluator_id}` for each evaluator explicitly. Different
   evaluators should get differently-worded rubrics (Style/Tone judges **how**;
   Content Compliance judges **what**).

4. **Apply (PATCH) already forks a new version.** Every `PATCH /agents/{id}`
   creates a new draft version. Test that draft via
   chat/eval requests pinned to `version_id` / `agent_history_id` — never by mutating the live version.

5. **External API calls use API-key auth.** Send `X-API-Key: $CODEER_API_KEY` and do not send browser session or CSRF credentials.

6. **Create KB roots and folders through the external KB endpoints.**
   Use `POST /knowledge-bases` for a KB root and
   `POST /knowledge-bases/{kb_id}/folders` for folders. Files are uploaded
   through `POST /knowledge-bases/{kb_id}/files:upload`.

7. **KB upload is multipart.** Use `curl -F` with `parent_id` and file parts,
   then poll `POST /knowledge-bases/files:status` until indexing completes.

8. **A KB has exactly ONE level of folders.** KB root → files OR folders →
   files (inside folders). The backend will silently create grandchild
   folders but the UI won't render them. Always pass the **KB root id** as
   `parent_id` when creating folders. For deeply-nested source material,
   flatten first with the `kb-indexing` skill (it encodes the path into the
   filename).

## Joining an existing agent mid-flight (iteration loop)

The 9-stage lifecycle above is the greenfield path. Most real work starts
with an agent that **already exists and has production traffic**. The task
is to tighten rubrics, fix prompt regressions, or add coverage for newly
observed failures — not to build from scratch.

### Entry point: reconnaissance

1. **Read the current version.** `GET /agents/{id}` + inspect the
   `system_prompt` and `unified_tools`. Use `GET /agents/{id}/versions` and
   direct JSON comparison if you need to compare against a prior version the
   user references.
2. **Pull production feedback.** `GET /histories` with an improvement feedback
   filter, then `GET /histories/{id}/conversations`, surfaces assistant turns
   flagged for improvement — this is the fastest path to "what's failing."
   Filter out internal emails via `internal_user_emails` when the API returns
   user metadata.
3. **Read existing eval rubrics.** `POST /eval/rubrics:batch` reads the current
   (case, evaluator) rubric table. Understand what the eval suite is
   already checking before adding or changing anything.

### The iteration loop

Once you know what's failing and what the eval suite currently covers:

```
  ┌─────────────────────────────────────────────────────┐
  │  Diagnose: for each failing case, classify          │
  │    agent issue → fix system_prompt or KB             │
  │    rubric issue → fix rubric (`PUT /eval/cases/{case_id}/rubrics/{evaluator_id}`) │
  │    judge noise → refine rubric wording or re-run     │
  ├─────────────────────────────────────────────────────┤
  │  Apply the fix (smallest diff)                       │
  │    prompt change → `PATCH /agents/{id}` (forks new draft)  │
  │    rubric change → rubric endpoint             │
  │    new case → `POST /eval/cases`                    │
  ├─────────────────────────────────────────────────────┤
  │  Re-run ALL cases and compare with the previous version │
  │    catches regressions in unrelated cases             │
  ├─────────────────────────────────────────────────────┤
  │  STOP and report — user decides next move            │
  └─────────────────────────────────────────────────────┘
```

**Key differences from the greenfield path:**

- You skip stages 0–2 (scope, KB, author) — those are done.
- You start at stage 8 (post-release analysis), then loop through
  stages 6 → 1 → 6 until the user is satisfied.
- New eval cases come from **production failures**, not from the scope
  doc. Each `sys_improve`-flagged turn is a candidate eval case. Use
  `POST /eval/cases` with `meta.previous_conversations` when the
  failure requires multi-turn context (see DESIGN_GUIDE.md §8.5).
- Rubric edits are the most common change — more common than prompt
  edits. Use `POST /eval/rubrics:batch` → edit → rubric update endpoint
  cycle instead of writing one-off scripts.
- The per-case diagnosis (agent vs rubric vs judge) is mandatory before
  any fix. See the `feedback_eval_diagnosis` methodology.

## Customer-materials workflow

The default flow when the user drops you in a directory of customer files.
**Confirm with the user at every "→ ASK" gate before continuing — don't
race past these into implementation.**

### Stage 0 — Scope alignment (→ ASK)

**Do this before any KB or agent work.** Use `AskUserQuestion` to nail
down four things:

1. **In-scope categories** — 3–6 concrete categories the agent must handle
   (e.g. "B2C consultation routing", "course recommendation", "enterprise
   intake", "card product Q&A"). Each becomes an eval case in stage 5.
2. **Out-of-scope** — what to deflect or escalate (legal advice, medical,
   competitor pricing, sensitive personal data, etc.). Each becomes a
   reverse / hallucination-trap eval case.
3. **Lead-capture goal** — what counts as a successful conversion per
   category (booking link click, form submission, purchase URL, callback
   request). This shapes `system_prompt` allowed-outcomes.
4. **Hard rules** — anything the agent must never do (never quote a price
   not in the KB, never give a counsellor's personal contact, never
   invent a course slug, etc.).

Save the answers to `.codeer/scope.md` in the customer's directory.
Reference it when writing the `system_prompt` and the eval rubrics —
those are the two artifacts that have to embody scope.

### Stage 1 — KB plan (→ ASK)

Before crawling or writing any content files, confirm:

- **One KB or several?** Default is one per agent. Multiple KBs make sense
  only when the user has truly distinct knowledge domains AND wants
  separate `invocation_instruction` triggers per domain.
- **Folder layout** — flat root, or one level of folders? (KB UI only
  renders one level; see gotcha #10.)
- **Source coverage** — which URLs / docs / sources are in, which are out
  (out-of-scope from stage 0 should map to KB exclusions too).
- **Naming convention** — descriptive `NN_topic.md` filenames vs. opaque
  IDs. If sources are a deep tree of opaque names, use the `kb-indexing`
  skill's `flatten` + `enrich` + `index` modes.

### Stage 2 — Prep KB content

Crawl / write `kb/*.md` files. Keep filenames descriptive (the KB tool
exposes them to the agent). Include a `22_服務地圖` style file that maps
visitor categories from stage 0 → KB content → next-step URL or tool —
this is the agent's decision aid.

### Stage 3 — Build KB in Codeer

```bash
curl -sS "$CODEER_EXTERNAL_API_BASE/knowledge-bases" \
  -H "X-API-Key: $CODEER_API_KEY" \
  -H "Content-Type: application/json" \
  --data '{"name":"<KB display name>"}'

curl -sS "$CODEER_EXTERNAL_API_BASE/knowledge-bases/$KB_ID/files:upload" \
  -H "X-API-Key: $CODEER_API_KEY" \
  -F "parent_id=$KB_ID" \
  -F "files=@kb/example.md;type=text/markdown"
```

`.codeer/kb_ids.json` now contains `kb_id`, `node_ids`, `name_to_id` —
feed those into the agent payload.

### Stage 4 — Build agent

Write `.codeer/agent_payload.json` (see `examples/donation_agent.json`
for the shape). Pull `system_prompt` allowed-outcomes and boundaries from
`.codeer/scope.md`; copy the KB node_ids from `.codeer/kb_ids.json`.

```bash
curl -sS "$CODEER_EXTERNAL_API_BASE/agents" \
  -H "X-API-Key: $CODEER_API_KEY" \
  -H "Content-Type: application/json" \
  --data @.codeer/agent_payload.json
```

### Stage 5 — Build eval cases (one per scope category)

Write `.codeer/eval_cases.json` with **one case per in-scope category**
from stage 0, plus boundary cases for each hard rule and a
hallucination-trap case for each out-of-scope category. Each case carries
per-evaluator rubrics — Style/Tone judges *how*, Content Compliance
judges *what*.

Use `POST /eval/cases` and `PUT /eval/cases/{case_id}/rubrics/{evaluator_id}` from the external API, then save created case IDs to `.codeer/case_ids.json`.

### Stage 6 — Run evals → STOP and report

**Do not run live test chats as a default validation step.** Skip
straight from build → eval. Run:

Use `POST /eval/runs` to trigger, then `POST /eval/results:batch` for each evaluator/version pair and save results to `.codeer/eval_results.json`.

Then:
1. Print the per-(case, evaluator) score table.
2. For every score < 1.0, surface the case label, evaluator name, score,
   and the evaluator's `reason` text.
3. **Stop. Wait for explicit user direction** before iterating the prompt,
   editing the KB, or publishing. Do not assume the next move; the user
   may want to fix the prompt, fix the KB, edit the rubric, or accept
   the score as-is.

Live Test is for *debugging a specific failing case after eval* — not for
"sanity-checking" an agent before evals. Use `POST /chats/{chat_id}/messages`
only when you've identified a case to investigate.

### Stage 7+ — Publish, monitor, rollback

Only after the user gives an explicit go on stage 6 results.

## What lives in this skill dir

```
codeer-agent/
├── SKILL.md                  ← you are here — orientation + lifecycle
├── DESIGN_GUIDE.md           ← read when designing/brainstorming an agent (now includes §0 scope alignment)
├── API_CHEATSHEET.md         ← endpoint reference + gotchas (the "how")
└── examples/                 ← reusable JSON payloads (donation_agent.json, eval cases)
```

**Pick which doc to read based on what's happening:**
- User is brainstorming an agent ("what should it do? which tools?") → **DESIGN_GUIDE.md**
- User wants to execute a specific change (create, upload, update, eval) → **API_CHEATSHEET.md** + this file's lifecycle table
- Either way, **DESIGN_GUIDE.md** owns the wisdom on tool choice, instruction-writing, and composition patterns; the cheatsheet owns the request shapes.

## Parsing return shapes

The external API returns JSON directly. Prefer reading only the fields needed for the task and store useful snapshots under `.codeer/` when they help the user review results.

For eval analysis, preserve raw `reasoning_steps` / tool-call fields from `POST /eval/results:batch` instead of summarizing them too early. If you create a local table, include `score`, `reason`, `output`, and any tool-call timing fields returned by the API.

## Keeping this skill accurate

The canonical reference for Codeer's API and capabilities is the public
documentation at **https://docs.codeer.ai**. Check it when this skill's
cheatsheet feels out of date.

If you have access to the `codeer-copilot` source repo (ask the user),
the backend + frontend enums this skill validates against live in:
- `codeer/agents/types.py` — `UnifiedToolType`, `PublishState`, `HttpRequestConfig`.
- `web/src/types/requestForm.ts` — `FormFieldType`, `FormField`.
- `codeer/eval/types.py` — eval case/evaluator/rubric schemas.
- `codeer/config/urls.py` + per-app `api.py` — routes.
- `codeer/agents/api.py` — agent CRUD endpoint implementations.
- `codeer/eval/api.py` — eval trigger/results/rubric endpoint implementations.
- `codeer/knowledge/api.py` — KB node/file endpoints.

**When uncertain about an API shape, parameter name, enum value, or
backend behavior, check docs.codeer.ai or read the actual source file
before guessing.** The cheatsheet and this skill doc are summaries that
can lag behind the code. For example, if you're unsure whether
`POST /eval/results:batch` takes `evaluator_id` (singular) or
`evaluator_ids` (plural), check `codeer/eval/api.py` — the function
signature is the ground truth.

When a new tool type or field type is added, update `API_CHEATSHEET.md` if the
backend and frontend disagree (they have before).
