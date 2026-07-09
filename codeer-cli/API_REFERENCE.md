# Codeer API reference — CLI maintainers

> This file is the request-shape reference for maintaining `codeer-cli`.

The 9 stages below mirror the user-docs lifecycle (`agent-creation` →
`optimization-loop` → `publish`). Every path is under `/api/v1/`. All endpoints
authenticate via `x-api-key` from `CODEER_API_KEY`.

Envelope: successful responses look like
`{"error_code": 0, "message": "", "pagination": null, "data": <payload>}`.
The client unwraps `data` automatically; errors raise `CodeerError`.

**Environment config split:**
Auth means `CODEER_API_KEY`; it comes from the process environment only.
`CODEER_API_BASE` defaults to `https://api.codeer.ai` and is only needed for
local, beta, or preview. Do not store API keys in repo files or paste them into
agent chat.

Workspace and organization scope come from the workspace API-key virtual user's
profile (`default_workspace_id` and `default_organization_id`). The CLI does
not use `--workspace`, `--org`, `CODEER_WORKSPACE_ID`, or
`CODEER_ORGANIZATION_ID`. `CODEER_AGENT_ID` is still optional for commands that
need a default agent.

**Pagination conventions:**
- `/histories` uses **`limit` + `offset`** (NOT `page` / `page_size`).
  Default in `histories.list()` is `limit=500`. Backend hard-cap may be
  lower — check the response length.
- `/agents/{id}/histories`, `/eval/agents/{id}/cases`, `/eval/evaluators` all
  return everything in one shot today (no pagination).
- `order_by` defaults to `"desc"` (most recent first) on endpoints that
  support it.

## Stage 1 — Author agent

| Method & path | Purpose |
| --- | --- |
| `POST /agents` | Create a new agent |
| `GET /agents?wid=<ws>` | List agents in a workspace |
| `GET /agents/all?wid=<ws>` or `?oid=<org>` | List across workspaces/org |
| `GET /agents/{id}` | Read current state |
| `PUT /agents/{id}` | Update — *auto-creates a new AgentHistory version* |
| `DELETE /agents/{id}` | Delete |

`unified_tools[]` fields: `type` ∈
{`knowledge_base`, `web_search`, `call_agent`, `image_generation`,
`request_form`, `payment`, `memory`, `http_request`}, plus type-specific fields
like `knowledge_node_ids`, `domain`, `agent_id`, `http_request` config.

Limits: 10 tools per agent, ≤5 `call_agent`, ≤1 `memory`.

## Stage 2 — Knowledge bases

Base path: `/organizations/{org_id}/workspaces/{ws_id}/knowledge_bases`

| Method & path | Purpose |
| --- | --- |
| `GET .../nodes` | List KB/folder/file tree (supply `parent_id` to scope) |
| `POST .../nodes` | Create a KB (type=`knowledge_base`, no parent) or folder (parent_id set) |
| `PATCH .../nodes/{node_id}` | Rename a node |
| `DELETE .../nodes/{node_id}` | Delete a node and its descendants |
| `POST .../{kb_id}/files/upload` | Upload file (multipart) — kicks off async indexing |
| `POST .../files/status` | Batch-poll indexing status by node ID |
| `GET .../{kb_id}/nodes/{node_id}/content` | Read a file's extracted content |

Attach KB files to an agent by listing their node IDs in the agent's
`unified_tools[].knowledge_node_ids`.

### Context Object FAQ

Base path: `/external/context-object-faqs`

| Method & path | Purpose |
| --- | --- |
| `GET /context-object-faqs` | List FAQ entries, optionally filtered by `context_object_id` |
| `GET /context-object-faqs/{faq_id}` | Read one FAQ entry |
| `POST /context-object-faqs` | Create an FAQ entry |
| `PATCH /context-object-faqs/{faq_id}` | Update the linked context object and/or question |
| `DELETE /context-object-faqs/{faq_id}` | Delete an FAQ entry |

Create body:

```json
{
  "context_object_id": 123,
  "question": "How do I reset billing?",
  "ranges": [
    {
      "start_line": 12,
      "start_column": 0,
      "end_line": 12,
      "end_column": 42
    }
  ]
}
```

Update body accepts any of these fields:

```json
{
  "context_object_id": 456,
  "question": "How do I update billing?",
  "ranges": [
    {
      "start_line": 20,
      "start_column": 0,
      "end_line": 20,
      "end_column": 39
    }
  ]
}
```

`context_object_id` is the KB file's `snapshot_object_id` from the KB node
listing. `ranges` is optional; use it when the FAQ route should reserve chunks
overlapping a stable passage inside that file. Include both line and column
positions so the Codeer UI can map the range onto rendered Markdown. The compact
CLI output includes the target id:

```bash
codeer kb files --kb-id <kb-id>
codeer kb faq-create --context-object-id <snapshot-object-id> --question "..." --range 12:0-12:42 --dry-run
```

## Stage 3 — Live Test on a specific version

| Method & path | Purpose |
| --- | --- |
| `POST /chats` | Create a new chat session bound to an agent |
| `POST /chats/{chat_id}/messages` | Send a message; **SSE stream** of tool calls + reasoning + final text |
| `GET /chats/{chat_id}/messages` | Read historical messages for a chat |
| `POST /chats/{chat_id}/regenerate` | Re-run the last turn |
| `POST /chats/{chat_id}/messages/{msg_id}/feedbacks` | Thumbs up/down on a reply |

`POST /chats/.../messages` requires `agent_history_id` — this is the key hook
for the apply → test → publish workflow. Pass the draft `AgentHistory.id` from
`PUT /agents/{id}` to test an unpublished version.

## Stage 4 — Version management

| Method & path | Purpose |
| --- | --- |
| `GET /agents/{id}/histories` | List every AgentHistory version, with `was_published` flags |
| `GET /agents/{id}/histories/{history_id}` | Read a specific version |
| `GET /agents/{id}/impact` | List downstream agents that `call_agent` this one |

## Stage 5 — Evaluation

| Method & path | Purpose |
| --- | --- |
| `GET /eval/workspaces/{workspace_id}/case-labels` | List reusable eval case labels |
| `POST /eval/workspaces/{workspace_id}/case-labels` | Create reusable eval case label (`name`, `color?`) |
| `PUT /eval/case-labels/{label_id}` | Update eval case label name/color |
| `DELETE /eval/case-labels/{label_id}` | Delete eval case label and clear associations |
| `POST /eval/cases` | Create case (`input`, `expected_output?`, `rubric?`, `label_ids?`); rubric = user-docs "Standard" |
| `GET /eval/agents/{agent_id}/cases` | List cases for an agent |
| `GET /eval/cases/{case_id}` | Read one |
| `PUT /eval/cases/{case_id}` | Update, including replacing labels via `label_ids` |
| `DELETE /eval/cases/{case_id}` | Delete |
| `POST /eval/cases/upload-csv` | Bulk import |
| `POST /eval/cases/bulk` | Bulk delete |
| `POST /eval/evaluators` | Create evaluator (LLM-judge via `system_prompt_template`) |
| `GET /eval/evaluators?wid=<ws>` | List evaluators |
| `PUT /eval/evaluators/{id}` | Update |
| `DELETE /eval/evaluators/{id}` | Delete |
| `POST /eval/case-evaluator-infos:batch` | Read assigned evaluators/rubrics for cases |
| `PUT /eval/cases/{case_id}/case-evaluator-infos` | Replace assigned evaluators/rubrics for one case |
| `POST /eval/trigger` | Run explicit assigned `case_evaluator_pairs` pinned to `agent_history_id` |
| `POST /eval/stop` | Cancel running case+evaluator combo |
| `POST /eval/rubric` | Set/override the rubric for one (case, evaluator); also creates assignment |
| `POST /eval/rubrics/batch` | **Read** rubrics for a batch of (case, evaluator) pairs |

Eval case labels are workspace-scoped reusable objects. The case create/update
payload uses `label_ids` (stringified label IDs), not freeform label names:

```json
{
  "agent_id": "<agent_uuid>",
  "input": "How do I return an item?",
  "expected_output": "Explain the return policy.",
  "label_ids": ["12", "13"]
}
```

Send `label_ids: []` on update to clear all labels from a case. The
`codeer eval cases-apply` manifest can resolve label names through a separate
`labels` array; the legacy `label` field remains a local review/display label.

## Stage 6 — Diagnose + update

| Method & path | Purpose |
| --- | --- |
| `POST /eval/results/batch` | Read per-case scores + `reason` + generated `output` + persisted tool trace for one `agent_history_id` |
| `PUT /agents/{id}` | Apply the fix — creates the next AgentHistory draft |

Iterate: trigger → results → PUT → trigger again, staying on drafts.

`POST /eval/results/batch` body shape:

```json
{
  "agent_history_id": "<uuid>",
  "workspace_id":     "<uuid>",
  "case_ids":         ["<uuid>", ...],
  "evaluator_id":     "<uuid>",      // singular — NOT evaluator_ids
  "include_output":   true,           // optional, default true
  "include_reasoning_steps": true      // include persisted tool args/results/timing
}
```

Both `agent_history_id` and `workspace_id` are required at the body level
(passing `wid=...` as a query param doesn't count). Cases that haven't been
evaluated yet on that history come back with `score=null` rather than being
omitted, so use `null`-checks instead of length comparisons.

Pass `include_reasoning_steps=true` to include persisted tool/reasoning steps.
The rows then include `reasoning_steps[]` with `id`, `type`, `args`, `result`,
`start_at`, and `end_at` when available. The skill preserves these as
normalized `tool_calls`, `tool_calls_summary`, and `tool_total_duration_ms`;
`codeer eval export` also writes `tool_calls_json` and keeps untouched rows
in `eval_table_full.json`. Per-tool time is computed from `start_at/end_at`.

**`evaluator_id` is singular — one call returns results for one evaluator
only.** Cases are also bound to specific evaluator assignments. To see the
full picture for a case, first read the case/evaluator assignments, then call
results once per assigned evaluator. `codeer eval run` and
`codeer eval rubrics` handle this automatically; if calling the API directly,
prefer `eval_mod.get_case_evaluator_infos(case_ids=[...])` as the source of
truth for which pairs should run.

Regression workflow (apply prompt change → re-run all assigned pairs → spot
side effects): `codeer eval run --agent <agent_id>` runs the latest
AgentHistory by default. For the common "many cases, one tester" flow, use
`codeer eval run --agent <agent_id> --cases <ids> --evaluator <evaluator_id>`.

## Stage 7 — Publish

| Method & path | Purpose |
| --- | --- |
| `POST /agents/{id}/publish-history` | Make a specific AgentHistory version the public one (also used for rollback) |
| `POST /agents/{id}/publish` | Change `publish_state` (`private` / `in_organization` / `public`) |
| `GET /agents/{id}/impact` | Always worth running first if other agents `call_agent` this one |

## Stage 8 — Post-release analysis

| Method & path | Purpose |
| --- | --- |
| `GET /histories?agent_id=X&feedback_filter=improve_feedback&external_user_id=…` | List conversations with filters |
| `GET /histories/{id}` | Read one history's metadata |
| `GET /histories/{id}/conversations` | Full conversation turns incl. tool calls |
| `POST /histories/{hid}/conversations/{cid}/feedbacks` | Leave freeform improvement feedback |
| `POST /histories/{hid}/conversations/{cid}/score` | Numeric score |

`feedback_filter` accepts the `FeedbackFilterType` enum values:
`no_feedback`, `with_feedback`, `helpful_feedback`, `improve_feedback`.

No built-in filter for "histories where tool X was called" — walk the
conversations and inspect tool-call messages yourself.

## Stage 9 — Rollback

Reuse `POST /agents/{id}/publish-history` with an older `history_id`.
Non-destructive: older versions stay in `GET /agents/{id}/histories`.

## Other useful endpoints

| Method & path | Purpose |
| --- | --- |
| `GET /accounts/me` | Sanity-check session, read workspace_organization_map |
| `GET /organizations` | List orgs visible to the user |
| `GET /llm/models` | List available LLM model IDs to use as `llm_model` |
| `GET /retrieval/...` | Shared retrieval helpers (file upload for attachments, markdown conversion) |

---

## Gotchas (read this before your first dogfood run)

These are traps we hit in practice; `codeer-cli/src/codeer_cli/_validate.py`
catches most of them client-side, but they're worth knowing when you're
writing payloads by hand.

### 1. `/agents` returns published only; `/agents/all` returns drafts too

`GET /agents?wid=<ws>` filters to **published** agents. While iterating on a
draft, use `GET /agents/all?wid=<ws>&oid=<org>` — **both** params are required,
or the server returns `400 Organization ID is required`. Map workspace → org via
`/accounts/me` → `profile.workspace_organization_map`.

### 2. Form field `type` has a fixed enum — backend doesn't enforce it

Valid values:
`shortText`, `longText`, `number`, `dropdown`, `radio`, `checkbox`, `date`.

There is **no** `"text" | "email" | "select"`. The backend validator accepts
anything (`extra="allow"`) so the agent saves, but the form builder renders
blank fields because none of the renderers match. Use:

- `"email"` → `shortText` + `placeholder`/`helpText` hint
- `"text"` → `shortText` (single-line) or `longText` (multi-line)
- `"select"` → `dropdown` with `options: [{value, label}]`

Every field also requires `id`, `type`, `name`, `label`, `question`, `required`
all present and non-empty. `name` is the submission key, `label` is the
analytics/column name, `question` is the user-facing prompt.

### 3. The `Standard` shown in Test Suite is a per-(case, evaluator) rubric

`POST /eval/cases` has a `rubric` field — this is NOT what the Test Suite's
`Standard` column reads. That column is populated by `CaseEvaluatorInfo` keyed
on `(evaluation_case_id, evaluator_id)`. The same row is also the assignment
that makes the pair eligible to run. Set it explicitly for each
(case, evaluator) pair, or use the eval helpers in
`codeer-cli/src/codeer_cli/eval_.py` which create assignments and rubrics
together.

To **read** rubrics back, use `POST /eval/rubrics/batch` with
`{case_ids: [...], evaluator_id}` — it returns the raw rubric strings out of
`CaseEvaluatorInfo`, no `agent_history_id` required since rubrics are
version-independent. Don't try to scrape rubrics out of past
`/eval/results/batch` `reason` text: the judge paraphrases them, and a case
with a rubric set but never evaluated is indistinguishable from one with no
rubric. Use the eval helpers in `codeer-cli/src/codeer_cli/eval_.py`.

Different evaluators should usually get differently-worded rubrics: a
Style/Tone evaluator should judge **how** the agent responded (language,
tone, format), while a Content Compliance evaluator should judge **what** it
said (scope, factuality, tool-use rules).

### 4. Agent version pinning works everywhere — use it

Both `POST /chats/{id}/messages` (`agent_history_id` required) and
`POST /eval/trigger` (`agent_history_id` optional, null = live state) accept
the draft history id. The apply-→-test-→-publish loop:

1. `PUT /agents/{id}` with your change → new `AgentHistory` with status=`draft`.
2. Find its id in the response (`latest_version_number` + `histories`).
3. Live-test and/or eval against that draft id.
4. Only `POST /agents/{id}/publish-history` when you're happy.

Never test a change on the currently-published version by mutating it — every
PUT already forks a new version for you.

### 5. API-key auth is required for every request

The `codeer` wrapper sends `CODEER_API_KEY` as `x-api-key`. If you curl by
hand, include that header and never print or paste the key into agent-visible
logs.

### 6. KB `POST /nodes` has no `type` field — and only ever creates folders

`CreateNodeSchema` is `{parent_id?, name, description?}`. There's no `type` /
`node_type` field; the server infers **KB root** when `parent_id` is null and
**folder** when it's set. This endpoint **cannot create files** — files only
come through `/files/upload`. Backend is lenient (`extra="allow"`), so a
`type: "knowledge_base"` or `type: "folder"` field gets silently dropped —
misleading but harmless.

Prefer `kb.create_kb()` / `kb.create_folder()` in new code over the generic
`create_node()`.

### 7. KB upload form is a single JSON-encoded field named `form`

Django Ninja serializes a `Schema`-typed form param as one form field whose
value is the JSON-stringified body — it is NOT flattened into top-level form
fields. So the multipart body looks like:

```
form:  {"parent_id": "<folder-or-kb-root-id>"}
files: <file-1>
files: <file-2>
```

Sending `parent_id=...` as a top-level form field returns HTTP 422 with
`{"loc": ("body","form"), "msg": "Field required"}`. `kb.upload_file()` /
`kb.upload_files()` handle this; if you roll your own, replicate the shape.

### 8. KB upload needs an explicit `Content-Type` per file

`common/files.py :: validate_uploaded_file` rejects when `file.content_type`
is missing or unrecognized — and httpx's default for multipart uploads is
`application/octet-stream`, which is unrecognized. The response comes back
with `status: "FAILED"` and `node_id: null` with no `error_message`
populated, making this hard to debug.

Always pass `(name, file_handle, content_type)` as a 3-tuple. The helper uses
`mimetypes.guess_type` with overrides for `.md`/`.txt`/`.csv` (the stdlib
returns `None` for those on older systems). Accepted MIMEs: any `text/*`,
plus `application/pdf`, DOCX/DOC/PPTX, Google Docs/Slides, and HTML.
**Image files (JPEG, PNG, GIF, WEBP) are NOT accepted for KB uploads** —
the upload endpoint explicitly rejects them with "Image files are not
supported in knowledge base", even though `BASE_ALLOWED_CONTENT_TYPES`
includes image MIMEs (that set is shared with other upload paths like
eval-case attachments, where images are allowed).

### 9. KB upload response shape + enum casing

- Response envelope: `{"nodes": [{"node_id": "...", "status": "PENDING", "original_name": "...", ...}]}` — NOT `{files: [...]}` or a flat list.
- `node_type` in list responses is **uppercase** (`FOLDER`, `FILE`); the frontend / ingestion code often uses lowercase. Normalize with `.upper()` before comparing.
- Indexing status transitions: `PENDING` → `INDEXING` → `READY`, or `FAILED` / `ERROR`. Poll `/files/status` with `{"node_ids": [...]}` until terminal. Small text files usually hit `READY` within 1–2 polls.

### 12. Eval-case attachments come from `/retrieval/upload-file`; the id is `data.uuid`

To attach an image / PDF to an eval case (e.g. "owner uploaded a cat selfie
instead of a report"):

1. **Upload** via `POST /retrieval/upload-file` (multipart):
   ```
   file: (filename, bytes, content_type)
   data: {"workspace_id": "...", "scope": "persistent", "is_evaluation_context": true}
   ```
   `data` must be a **JSON-encoded string** (same Django Ninja quirk as KB
   upload — see Gotcha #7).

2. **Response**:
   ```json
   {"data": {
     "original_name": "cat.jpg", "content_type": "image/jpeg", "size": 43853,
     "file_url": "https://codeer-media.s3.amazonaws.com/.../cat.jpg?...",
     "uuid": "ab155432-5119-4070-bc12-65794ecef970",
     "scope": "persistent"
   }}
   ```
   **The attachment id is `data.uuid`** — there is no `data.attachment_id`
   or `data.id` field. Looking up either of those wastes a debugging round.

3. **Attach** to the case:
   ```python
   eval_mod.update_case(c, case_id, attachment_ids=[uuid])
   ```

For bulk creation, `codeer eval cases-apply --attachments-dir <dir>` reads
each case's `attachment_files: ["x.jpg"]` array, uploads, and attaches in one
pass. Workspace scope is inferred from the API-key virtual user profile.

### 11. Tool args + outputs are NOT persisted in history reads

Conversations have only three roles (`OpenAIChatRole = system | user | assistant`)
— there is no `tool` role row. When you read a history, here's what you can
and can't recover from each assistant turn:

| Recoverable | Where |
| --- | --- |
| Tool name + call_id | regex over `content`: `<tool id=call_xxx>name</tool>` |
| Per-call token usage | `meta.token_usage.tool_calls[]` (positional match to tags) |
| Sequenced tool order within a turn | the order of `<tool …>` tags in `content` |
| Retrieved primary sources | top-level `primary_sources[]` on the assistant turn |
| Final answer text (no tool markers) | `strip_tool_markers(content)` |

| NOT recoverable | Why |
| --- | --- |
| Tool **arguments** (e.g. the regex passed to `list_kb_files`, the question/keywords passed to `retrieve_context_objs`) | flow over the WebSocket during execution, not stored on Conversation |
| Tool **outputs** (raw JSON returned by the tool) | same — stored only as derived `primary_sources` for retrieval tools |
| Reasoning steps mid-turn | `meta.reasoning_steps` is currently always `null` |

If you need full tool I/O, capture it at execution time via the chat SSE
stream (`POST /chats/{id}/messages`), not from history reads. For after-the-
fact analysis, the persisted shape is sufficient to surface tool-selection
patterns, token costs, and which sources the agent ended up citing.

### 10. A KB has exactly ONE level of folders — no nesting

The file-manager UI only renders a single layer of folders inside a KB:

```
KB root
├── file.md                    ← files at root are fine
├── file2.md
└── Folder/                    ← one level of folders is the max
    ├── another.md             ← files inside a folder are fine
    └── one-more.md
```

The backend will happily accept a folder id as `parent_id` on `POST /nodes`
and create a grandchild folder, but the UI won't render it and retrieval
tooling treats KBs as flat. **Always pass the KB root id as `parent_id`
when creating folders**, not another folder's id.

If the user's source tree has deeper nesting, flatten it first with the
`kb-indexing` skill — it encodes the original path into the filename (e.g.
`products／a.md` using `／` U+FF0F as separator) so `list_kb_files` regex
can still recover structure. That skill's docs explain the full flow.

### 13. Eval results and rubrics are **per assigned case/evaluator pair**

Both `POST /eval/results/batch` and `POST /eval/rubrics/batch` take a
**singular** `evaluator_id`, not a list. Each call returns data for one
evaluator only. A case only runs with evaluators it is assigned to through
`CaseEvaluatorInfo`.

When pulling eval data manually, always:
1. Read assignments with `eval_mod.get_case_evaluator_infos(case_ids=[...])`.
2. Call `get_results()` or `get_rubrics_batch()` once per assigned evaluator.
3. Join the results by `(case_id, evaluator_id)`.

The CLI commands (`codeer eval run`, `codeer eval rubrics`,
`codeer eval rubrics-apply`) and the `get_case_rubrics()` helper all handle
this iteration automatically. Use `codeer eval rubrics --all-pairs` only when
you intentionally want the old full matrix scan.

---

## Keeping this reference accurate

The canonical reference for Codeer's API and capabilities is the public
documentation at **https://docs.codeer.ai**. When uncertain about an API
shape, parameter name, or enum value, check docs.codeer.ai first — this
cheatsheet is a summary that can lag behind.

The enums and limits this skill validates against are mirrored in
`codeer-cli/src/codeer_cli/constants.py`. When a new tool type or field type is
added, update that file and add a Gotcha note here if behavior is surprising.
