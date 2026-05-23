# CLI Command Reference

Use registered `codeer` domain commands only. If an operation is not supported
by the CLI, say that it is not supported by the CLI and stop for user direction.

All generated files go under **`.codeer/`** in the project root.
Only `kb/` (source content for upload) stays at root level.

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
codeer agent apply --payload agent.json --dry-run
codeer eval cases-apply --agent <agent-id> --cases eval_cases.json --dry-run
codeer eval rubrics-apply --rubrics rubrics.json --dry-run
codeer kb upload --dir kb --name "Product KB" --dry-run
```

Apply only after the user approves the dry-run summary.

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
