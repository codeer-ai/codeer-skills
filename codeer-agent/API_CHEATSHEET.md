# Codeer API cheatsheet — agent lifecycle

> If the user is **deciding what to build** rather than executing a known
> change, read **`DESIGN_GUIDE.md`** first. This file is the external API
> request-shape reference.

All paths are relative to `CODEER_EXTERNAL_API_BASE`.

Local development currently uses:

```bash
CODEER_EXTERNAL_API_BASE=http://localhost:8000/api/v1/external/v1
```

Required auth:

```text
X-API-Key: $CODEER_API_KEY
Accept: application/json
```

For JSON writes, also send `Content-Type: application/json`.

Success responses use the external envelope:

```json
{
  "request_id": "req_...",
  "data": {}
}
```

## Sanity check

| Method & path | Purpose |
| --- | --- |
| `GET /me` | Confirm API key, organization, and workspace context |

Run this first in every Codeer task.

## Stage 1 — Author agent

| Method & path | Purpose |
| --- | --- |
| `POST /agents` | Create a new agent |
| `GET /agents` | List published agents in key workspace |
| `GET /agents/all` | List all agents, including drafts |
| `GET /agents/{agent_id}` | Read current agent state |
| `PATCH /agents/{agent_id}` | Update agent and create a new draft version |
| `DELETE /agents/{agent_id}` | Delete agent |
| `GET /agents/{agent_id}/versions` | List versions |
| `GET /agents/{agent_id}/versions/{version_id}` | Read one version |
| `GET /agents/{agent_id}/impact` | Check downstream call-agent impact |
| `POST /agents/{agent_id}/versions/{version_id}:publish` | Publish a version |
| `POST /agents/{agent_id}:set-publish-state` | Set `private`, `in_organization`, or `public` |

Agent payload fields include `name`, `description`, `system_prompt`, `model`,
`tools`, `suggested_questions`, and `use_search`. The external API maps
`tools[]` into Codeer's unified tool schema.

Tool types: `knowledge_base`, `web_search`, `call_agent`, `image_generation`,
`request_form`, `payment`, `memory`, `http_request`.

Limits: 10 tools per agent, <=5 `call_agent`, <=1 `memory`.

## Stage 2 — Knowledge bases

| Method & path | Purpose |
| --- | --- |
| `POST /knowledge-bases` | Create KB root |
| `POST /knowledge-bases/{kb_id}/folders` | Create folder under a KB root |
| `GET /knowledge-bases/nodes?parent_id=...` | List KB roots or children |
| `PATCH /knowledge-bases/nodes/{node_id}` | Rename/update node |
| `DELETE /knowledge-bases/nodes/{node_id}` | Delete node/tree |
| `POST /knowledge-bases/{kb_id}/files:upload` | Upload files (multipart) |
| `POST /knowledge-bases/files:status` | Poll indexing status |
| `GET /knowledge-bases/{kb_id}/files/{node_id}/content` | Read extracted file content |

KB folder structure should stay shallow: KB root -> files or one level of
folders -> files.

Upload example:

```bash
curl -sS "$CODEER_EXTERNAL_API_BASE/knowledge-bases/$KB_ID/files:upload" \
  -H "X-API-Key: $CODEER_API_KEY" \
  -F "parent_id=$PARENT_ID" \
  -F "files=@./kb/policy.md;type=text/markdown"
```

Attach KB files to an agent by listing their node IDs in the agent's
knowledge-base tool config.

## Stage 3 — Live test on a specific version

| Method & path | Purpose |
| --- | --- |
| `POST /chats` | Create a chat session bound to an agent |
| `GET /chats` | List chats visible to the API key scope |
| `POST /chats/{chat_id}/messages` | Send a message; can stream SSE |
| `GET /chats/{chat_id}/messages` | Read historical messages for a chat |
| `POST /chats/{chat_id}/messages/{message_id}/feedbacks` | Leave message feedback |

`POST /chats/{chat_id}/messages` accepts `version_id`, which lets the skill test
an unpublished draft version.

## Stage 4 — Version management

| Method & path | Purpose |
| --- | --- |
| `GET /agents/{agent_id}/versions` | List draft and published versions |
| `GET /agents/{agent_id}/versions/{version_id}` | Read a specific version |
| `GET /agents/{agent_id}/impact` | List downstream agents that call this one |

## Stage 5 — Evaluation cases and evaluators

| Method & path | Purpose |
| --- | --- |
| `POST /files` | Upload eval/chat attachment |
| `POST /eval/cases` | Create case |
| `GET /eval/agents/{agent_id}/cases` | List cases for an agent |
| `GET /eval/cases/{case_id}` | Read one case |
| `PUT /eval/cases/{case_id}` | Update case |
| `DELETE /eval/cases/{case_id}` | Delete case |
| `POST /eval/cases:bulk-delete` | Bulk delete cases |
| `POST /eval/evaluators` | Create evaluator |
| `GET /eval/evaluators` | List evaluators |
| `GET /eval/evaluators/{evaluator_id}` | Read evaluator |
| `PUT /eval/evaluators/{evaluator_id}` | Update evaluator |
| `DELETE /eval/evaluators/{evaluator_id}` | Delete evaluator |
| `PUT /eval/cases/{case_id}/rubrics/{evaluator_id}` | Set rubric for one case/evaluator pair |
| `POST /eval/rubrics:batch` | Read rubrics for many cases under one evaluator |

The UI's `Standard` column is the per-(case, evaluator) rubric. Set it
explicitly for each evaluator.

## Stage 6 — Eval run, results, and diagnosis

| Method & path | Purpose |
| --- | --- |
| `POST /eval/runs` | Trigger eval cases and evaluators, optionally pinned to `version_id` |
| `POST /eval/runs:stop` | Cancel one running case/evaluator job |
| `POST /eval/results:batch` | Read per-case scores, reasons, output, and tool trace |
| `PATCH /agents/{agent_id}` | Apply a fix and create the next draft version |

`POST /eval/runs` does not create or return a first-class `run_id` resource in
current backend semantics. Treat it as an accepted trigger for the selected
case/evaluator/version combinations, then read results with
`POST /eval/results:batch`.

`POST /eval/results:batch` body shape:

```json
{
  "case_ids": ["case_1", "case_2"],
  "evaluator_id": "ev_1",
  "version_id": "agv_...",
  "include_output": true,
  "include_reasoning_steps": true
}
```

`evaluator_id` is singular. To see the full picture for a case, call this once
per evaluator. Cases that have not finished may return empty/null result fields,
so check result state instead of relying only on row count.

Regression workflow: apply prompt change -> re-run all cases on the new version
-> compare against previous version -> report every case whose score moved.

## Stage 7 — Publish

| Method & path | Purpose |
| --- | --- |
| `POST /agents/{agent_id}/versions/{version_id}:publish` | Make a version the published one |
| `POST /agents/{agent_id}:set-publish-state` | Change `publish_state` |
| `GET /agents/{agent_id}/impact` | Check downstream dependency impact first |

## Stage 8 — Post-release analysis

| Method & path | Purpose |
| --- | --- |
| `GET /histories?agent_id=...&feedback_filter=...` | List conversations with filters |
| `GET /histories/{history_id}` | Read one history metadata object |
| `GET /histories/{history_id}/conversations` | Full conversation turns, including tool calls |
| `POST /histories/{history_id}/conversations/{conversation_id}/feedbacks` | Leave textual feedback |
| `POST /histories/{history_id}/conversations/{conversation_id}/score` | Set numeric score |
| `DELETE /histories/{history_id}` | Delete one history record |

`feedback_filter` accepts `no_feedback`, `with_feedback`, `helpful_feedback`,
and `improve_feedback`.

## Stage 9 — Rollback

Reuse `POST /agents/{agent_id}/versions/{version_id}:publish` with an older
`version_id`. Older versions remain available through
`GET /agents/{agent_id}/versions`.

## Gotchas

### 1. Use API-key auth only

Do not send browser cookies, `sessionid`, `csrftoken`, or CSRF headers from this
skill. If a request fails with auth/scope errors, re-run `GET /me` before making
any changes.

### 2. `/agents` returns published only

Use `GET /agents/all` when iterating on drafts. Use `GET /agents` only when you
specifically want the published list.

### 3. Form field `type` has a fixed enum

Valid values: `shortText`, `longText`, `number`, `dropdown`, `radio`,
`checkbox`, `date`. There is no `text`, `email`, or `select`.

Every field also requires `id`, `type`, `name`, `label`, `question`, and
`required`. The backend may accept broken form config that the UI cannot render,
so validate request payloads before calling `POST /agents` or
`PATCH /agents/{agent_id}`.

### 4. The `Standard` shown in Test Suite is per-(case, evaluator)

The case-level `rubric` field is not enough. Use
`PUT /eval/cases/{case_id}/rubrics/{evaluator_id}` for each evaluator and use
`POST /eval/rubrics:batch` to read rubrics back.

### 5. Version pinning is the safe loop

`PATCH /agents/{agent_id}` creates a new draft version. Test that version via
chat/eval requests pinned to `version_id`, then publish only after the user
approves results.

### 6. KB structure is shallow

Use one KB root, optionally one folder level, then files. Flatten deeply nested
source material before upload.
