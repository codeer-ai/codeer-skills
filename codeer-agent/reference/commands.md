# CLI Command Reference

Use registered `codeer` domain commands only. If an operation is not supported
by the CLI, say that it is not supported by the CLI and stop for user direction.

Only `kb/` (source content for upload) stays at root level.
All working files go under **`.codeer/`** in the project root.

---

## `.codeer/` file lifecycle

The server is the source of truth for all agent, eval case, and rubric data.
Local files are either **caches** of server state or **drafts** staged for apply.

```
.codeer/
├── current/                            # working directory for active cycle
│   ├── agent.json                      # cache:  codeer agent get
│   ├── eval_cases.json                 # cache:  codeer eval list
│   ├── rubrics.json                    # cache:  codeer eval rubrics
│   ├── eval_table/                     # cache:  codeer eval export (on demand)
│   │   ├── eval_table_full.json
│   │   ├── eval_table_summary.md
│   │   └── eval_table.csv
│   ├── local_draft_agent.json          # draft:  codeer agent apply
│   ├── local_draft_eval_cases.json     # draft:  codeer eval cases-apply
│   ├── local_draft_rubrics.json        # draft:  codeer eval rubrics-apply
│   └── progress.json                   # batch tracking across eval runs
│
└── pinned/                             # user-triggered, auto-dated
    └── YYYY-MM-DD/                     # append -2, -3 for same-day pins
```

### Rules

1. **`current/` overwrites in place** — no date-stamping, no versioning.
   Refresh caches from the server at the start of each cycle.
2. **`pinned/` is append-only** — before overwriting something the user may
   want to keep, ask "pin these results?" and copy to `pinned/<date>/`.
3. **No files outside `current/` and `pinned/`** — nothing at `.codeer/` root.
4. **No scripts** — `.py`, `.mjs`, `.html`, `.cjs` are prohibited under
   `.codeer/`. If the CLI cannot do it, say so and stop for user direction.
5. **Drafts use `local_draft_` prefix** — distinguishes staging files from
   server caches. Delete drafts after successful apply + cache refresh.
6. **ID cache files are not used** — no `kb_ids.json`, `agent_ids.json`,
   `case_ids.json`. The CLI resolves IDs from env vars or server queries.

### Cycle lifecycle

| Phase | What happens to `current/` |
| --- | --- |
| Cycle start | Refresh caches: `codeer agent get`, `codeer eval list`, `codeer eval rubrics` |
| During cycle | Drafts created, diffs shown, applied. Eval exports overwrite `eval_table/`. Debug artifacts overwrite in place per batch. |
| Pin (optional) | Copy `current/eval_table/` (or any subset) to `pinned/<date>/` |
| Cycle end (publish) | `current/` stays as final state; next cycle start overwrites it |

### Batch progress tracking

When eval cases are split into batches, track status in `current/progress.json`:

```json
{
  "total_cases": 120,
  "batches": [
    {
      "batch": 1,
      "label": "books-pricing",
      "case_ids": ["uuid1", "uuid2"],
      "status": "done",
      "final_score": 0.92,
      "fix_summary": "relaxed price-optional rubric"
    },
    {
      "batch": 2,
      "label": "routing",
      "case_ids": ["uuid3"],
      "status": "in-progress"
    }
  ]
}
```

All debug-loop artifacts (rubrics before/after, rerun results) overwrite the
same files in `current/` regardless of which batch is active. When a batch
completes, record the summary in `progress.json` and move to the next batch.

---

## Commands

| Command | Purpose |
| --- | --- |
| `codeer check` | Validate auth, workspace, and agent config |
| `codeer agent list` | List agents in workspace |
| `codeer agent get` | Get agent details |
| `codeer agent apply` | Create or update agent (always creates a new DRAFT version) |
| `codeer agent diff` | Show diff between versions |
| `codeer agent versions` | List agent version history |
| `codeer kb list` | List knowledge bases in workspace |
| `codeer kb upload` | Create/reuse KB + upload files + poll until indexed |
| `codeer kb faq-list` | List Context Object FAQ entries |
| `codeer kb faq-get` | Read one Context Object FAQ entry |
| `codeer kb faq-create` | Create a question-to-KB-file FAQ route |
| `codeer kb faq-update` | Update a Context Object FAQ question or target file |
| `codeer kb faq-delete` | Delete a Context Object FAQ entry |
| `codeer eval list` | List eval cases for an agent |
| `codeer eval evaluators` | List evaluators in workspace |
| `codeer eval evaluator-create` | Create an evaluator in the workspace |
| `codeer eval evaluator-update` | Update a workspace-scoped evaluator |
| `codeer eval run` | Trigger eval, poll, print non-perfect analysis |
| `codeer eval export` | Full eval table export (CSV + JSON + summary MD) |
| `codeer eval cases-apply` | Bulk-create/update eval cases with per-evaluator rubrics |
| `codeer eval rubrics` | Read per-(case, evaluator) rubrics |
| `codeer eval rubrics-apply` | Apply rubric edits (pairs with `eval rubrics`) |
| `codeer eval reconcile` | Read-only audit: compare local manifest vs server state |
| `codeer history list` | List conversation histories for an agent |
| `codeer history create` | Create a real persisted conversation history through the published agent |
| `codeer history negative-feedback` | Surface turns with negative feedback |
| `codeer history conversations` | Read a specific conversation history |

---

## Safe CLI-first workflow

When the repository source is unavailable, use the installed CLI as the full
interface contract:

```bash
codeer check --json
codeer agent list
codeer agent get <agent-id> --full
codeer kb list
codeer eval list --agent <agent-id>
codeer eval evaluators
```

Before any server mutation, preview the intended write:

```bash
codeer agent apply --payload .codeer/current/local_draft_agent.json --dry-run
codeer eval cases-apply --agent <agent-id> --cases .codeer/current/local_draft_eval_cases.json --dry-run
codeer eval rubrics-apply --rubrics .codeer/current/local_draft_rubrics.json --dry-run
codeer kb upload --dir kb --name "Product KB" --dry-run
codeer kb faq-create --context-object-id <snapshot-object-id> --question "..." --dry-run
```

Apply only after the user approves the dry-run summary.

## `codeer kb faq-*` commands

Context Object FAQ links a representative question to a canonical KB file.
Use it only after confirming the file is uploaded, attached, and `READY`, and
semantic retrieval is missing that file despite a reasonable query.

The FAQ target is the file node's `snapshot_object_id`, shown by:

```bash
codeer kb files --kb-id <kb-id>
```

Commands:

| Command | Purpose |
| --- | --- |
| `codeer kb faq-list [--context-object-id ID]` | List FAQ routes |
| `codeer kb faq-get <faq-id>` | Inspect one FAQ route |
| `codeer kb faq-create --context-object-id ID --question TEXT --dry-run` | Preview creation |
| `codeer kb faq-update <faq-id> [--context-object-id ID] [--question TEXT] --dry-run` | Preview update |
| `codeer kb faq-delete <faq-id> --dry-run` | Preview deletion |

After user approval, rerun the same mutation command without `--dry-run`.

---

## `codeer history create` flags

Creates a real persisted chat history by calling the API-key external chat
endpoints. This uses the agent's **published** version. It cannot pin an
unpublished draft `AgentHistory` unless the server API gains support for that.

| Flag | Type | Default | Purpose |
| --- | --- | --- | --- |
| `--agent` | string | `CODEER_AGENT_ID` | Agent ID |
| `--title` | string | first message prefix | Conversation title |
| `--user` | string | — | `external_user_id` to associate with the history |
| `--message` | string, repeatable | **required** | User turn to send, in order |

Example:

```bash
codeer history create \
    --agent <agent_id> \
    --title "Seed conversation" \
    --user "eval-seed@example.com" \
    --message "First user turn" \
    --message "Follow-up user turn"
```

The output includes `history_id`, conversation IDs, and a history URL. Keep
those IDs when turning a real conversation into follow-up eval cases later.

---

## `codeer eval run` flags

| Flag | Type | Default | Purpose |
| --- | --- | --- | --- |
| `--agent` | string | **required** | Agent ID |
| `--history` | string | — | Pin eval to a specific version (AgentHistory UUID) |
| `--latest` | flag | **default behavior** | Auto-select newest version |
| `--cases` | string | all | Comma-separated case UUIDs to run |
| `--evaluators` | string | **required** | Comma-separated evaluator UUIDs to use |
| `--poll-timeout` | int | 900 | Polling timeout in seconds |
| `--out` | string | — | Write results JSON to this path |

`--history` and `--latest` are mutually exclusive. If neither is passed,
`--latest` behavior applies automatically.

---

## Server links

After any step that creates or modifies server state, output the relevant
Codeer web link so the user can verify visually. Construct URLs from
`CODEER_API_BASE` (the same origin as the API).

| After | Link |
| --- | --- |
| Creating or updating an agent | `{CODEER_API_BASE}/workspaces/{workspace_id}/agents/{agent_id}` |
| Applying eval cases or rubrics | `{CODEER_API_BASE}/workspaces/{workspace_id}/agents/{agent_id}?tab=evaluation` |
| Running eval | `{CODEER_API_BASE}/workspaces/{workspace_id}/agents/{agent_id}?tab=evaluation` |
| Viewing a conversation history | `{CODEER_API_BASE}/workspaces/{workspace_id}/histories/{history_id}` |
| Listing agents in workspace | `{CODEER_API_BASE}/workspaces/{workspace_id}?tab=edit-agents` |
| KB uploads | `{CODEER_API_BASE}/knowledge-base` |
