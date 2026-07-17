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
│   ├── eval_results.json               # cache:  codeer eval run --out (full-suite runs)
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
| `codeer agent impact` | Check downstream agents affected by this agent |
| `codeer agent publish` | Publish an approved agent version |
| `codeer kb list` | List knowledge bases in workspace |
| `codeer kb upload` | Create/reuse KB + upload files + poll until indexed |
| `codeer kb node-rename` | Rename a KB root, folder, or file node |
| `codeer kb node-delete` | Delete a KB root, folder, or file node and descendants |
| `codeer kb crawl-create` | Create a website-crawler KB folder |
| `codeer kb crawl-update` | Update a website crawl target |
| `codeer kb crawl-state` | Read website crawl state for a crawler folder |
| `codeer kb crawl-sync` | Start a website crawl sync job |
| `codeer kb crawl-cancel` | Cancel the active website crawl job |
| `codeer kb crawl-failures` | List failed pages for a website crawl job |
| `codeer kb faq-list` | List Context Object FAQ entries |
| `codeer kb faq-get` | Read one Context Object FAQ entry |
| `codeer kb faq-create` | Create a question-to-KB-file FAQ route |
| `codeer kb faq-update` | Update a Context Object FAQ question or target file |
| `codeer kb faq-delete` | Delete a Context Object FAQ entry |
| `codeer eval list` | List eval cases for an agent |
| `codeer eval label-list` | List workspace eval case labels |
| `codeer eval label-create` | Create a reusable eval case label |
| `codeer eval label-update` | Rename or recolor an eval case label |
| `codeer eval label-delete` | Delete an eval case label and clear associations |
| `codeer eval case-update` | Update one eval case by UUID, including `input` |
| `codeer eval case-delete` | Delete one eval case by UUID |
| `codeer eval evaluators` | List evaluators in workspace |
| `codeer eval evaluator-create` | Create an evaluator in the workspace |
| `codeer eval evaluator-update` | Update a workspace-scoped evaluator |
| `codeer eval run` | Trigger assigned case/evaluator pairs, poll, print non-perfect analysis |
| `codeer eval export` | Full eval table export (CSV + JSON + summary MD) |
| `codeer eval cases-apply` | Bulk-create/update eval cases with per-evaluator rubrics |
| `codeer eval rubrics` | Read assigned per-(case, evaluator) rubrics |
| `codeer eval rubrics-apply` | Apply rubric edits (pairs with `eval rubrics`) |
| `codeer eval reconcile` | Read-only audit: compare local manifest vs server state |
| `codeer history list` | List conversation histories for an agent |
| `codeer history create` | Create a real persisted conversation history through the published agent |
| `codeer history send` | Append one or more turns to an existing persisted history |
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
codeer eval label-create --name "Routing" --color "#0969da" --dry-run
codeer kb upload --dir kb --name "Product KB" --dry-run
codeer kb node-rename --node-id <node-id> --name "New Name" --dry-run
codeer kb node-delete --node-id <node-id> --dry-run
codeer kb crawl-create --url "https://docs.example.com" --folder-name "Docs" --dry-run
codeer kb faq-create --context-object-id <snapshot-object-id> --question "..." --dry-run
codeer agent publish --agent <agent-id> --version <n> --dry-run
```

Apply only after the user approves the dry-run summary.

## KB node rename/delete

Knowledge Base roots, folders, and files are all KnowledgeNodes. Use
`node-rename` and `node-delete` when you already know the node id from
`codeer kb list` or `codeer kb files`.

```bash
codeer kb node-rename --node-id <node-id> --name "New Name" --dry-run
codeer kb node-delete --node-id <node-id> --dry-run
```

`node-delete` deletes the target node and all descendants. Always show the
dry-run output to the user and wait for approval before rerunning without
`--dry-run`.

## Eval case labels

Eval case labels are reusable workspace objects. Use them to tag cases by
coverage slice, such as `routing`, `pricing`, or `out-of-scope`. They are
separate from the manifest's legacy `label` field, which is only a local
review/display name.

Label commands always use the active API-key workspace and do not accept a
workspace override. Switch CLI profiles before running them against another
workspace.

Typical workflow:

```bash
codeer eval label-list
codeer eval label-create --name "routing" --color "#0969da" --dry-run
codeer eval case-update --case <case-id> --label-ids <label-id> --dry-run
```

For bulk case manifests, use either existing IDs:

```json
{
  "label": "routing-basic-001",
  "labels": ["routing"],
  "label_ids": ["12"],
  "input": "...",
  "rubrics": {"<evaluator-id>": "..."}
}
```

`labels` is resolved by name against workspace labels. If a manifest references
new label names, run `codeer eval cases-apply --create-labels --dry-run` to
preview creating them and assigning them to cases. After approval, rerun without
`--dry-run`.

## `codeer agent impact` and `publish`

Check downstream dependencies before publishing changes that could affect
agent-to-agent calls:

```bash
codeer agent impact --agent <agent_id>
```

Publish only after the eval loop is complete and the user approves the
specific target version:

```bash
codeer agent publish --agent <agent_id> --version <n> --dry-run
codeer agent publish --agent <agent_id> --version <n>
```

You can pass `--history <agent_history_id>` instead of `--version <n>` when
the exact `AgentHistory` UUID is known.

## `codeer kb crawl-*` commands

Website crawler commands create and manage website-backed KB folders through
the API-key external endpoints.

| Command | Purpose |
| --- | --- |
| `codeer kb crawl-create --url URL [--folder-name NAME] [crawler flags] --dry-run` | Preview crawler folder creation |
| `codeer kb crawl-update --target-id ID --url URL [crawler flags] --dry-run` | Preview crawler target update |
| `codeer kb crawl-state --folder-id UUID` | Read target/job state for a crawler folder |
| `codeer kb crawl-sync --target-id ID --dry-run` | Preview starting a sync job |
| `codeer kb crawl-cancel --target-id ID --dry-run` | Preview cancelling the active job |
| `codeer kb crawl-failures --job-id ID [--status CSV]` | Inspect failed pages |

Crawler flags for `crawl-create` and `crawl-update`:

| Flag | `crawl_config` key | Notes |
| --- | --- | --- |
| `--limit N` | `limit` | Maximum pages to crawl; backend accepts 1-5000 |
| `--max-depth N` | `maxDepth` | Maximum crawl depth; backend accepts 1-10 |
| `--include-path PATH` | `includePaths` | Repeatable clean path pattern; supports `*` wildcard |
| `--exclude-path PATH` | `excludePaths` | Repeatable clean path pattern; supports `*` wildcard |
| `--allow-subdomains` | `allowSubdomains` | Allow subdomains of the start URL host |
| `--allow-external-links` | `allowExternalLinks` | Allow links outside the start URL host |
| `--ignore-query-parameters` / `--use-query-parameters` | `ignoreQueryParameters` | Whether query strings create distinct pages |
| `--ignore-sitemap` / `--use-sitemap` | `ignoreSitemap` | Whether sitemap discovery is skipped |
| `--only-main-content` / `--include-page-chrome` | `onlyMainContent` | Whether to strip navigation/footer/page chrome |
| `--config-json JSON` | raw `crawl_config` | Advanced escape hatch; explicit flags override matching JSON keys |

For `includePaths` and `excludePaths`, pass clean path patterns rather than
raw regex. The backend encodes non-ASCII path segments and converts patterns to
Firecrawl regex. Plain paths match the exact path and children
(`/cart` matches `/cart/checkout` but not `/cartoon`). `*` matches the rest of
the encoded path, regex metacharacters are treated literally, and `\*` means a
literal star. Quote wildcard paths in the shell, e.g.:

```bash
codeer kb crawl-create \
    --url https://example.com/docs \
    --include-path "/docs*" \
    --exclude-path "/docs/private*" \
    --limit 250 \
    --max-depth 3 \
    --dry-run
```

After user approval, rerun the same mutation command without `--dry-run`.

## `codeer kb faq-*` commands

Context Object FAQ links a representative question to a canonical KB file, with
optional line ranges for routing to a stable passage inside that file.
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
| `codeer kb faq-create --context-object-id ID --question TEXT [--range START_LINE:START_COLUMN-END_LINE:END_COLUMN] --dry-run` | Preview creation |
| `codeer kb faq-update <faq-id> [--context-object-id ID] [--question TEXT] [--range START_LINE:START_COLUMN-END_LINE:END_COLUMN] --dry-run` | Preview update |
| `codeer kb faq-delete <faq-id> --dry-run` | Preview deletion |

After user approval, rerun the same mutation command without `--dry-run`.
Repeat `--range` to reserve multiple passages. Ranges must include both line and
column positions so the Codeer UI can map them onto rendered Markdown. On
update, supplied ranges replace the FAQ's existing ranges.

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
| `--timeout` | float | `120` | Per-message response timeout in seconds |
| `--out` | path | — | Write complete message and conversation details to a file |

Example:

```bash
codeer history create \
    --agent <agent_id> \
    --title "Seed conversation" \
    --user "eval-seed@example.com" \
    --message "First user turn" \
    --message "Follow-up user turn" \
    --timeout 120
```

The output includes `history_id`, conversation IDs, and a history URL. Keep
those IDs when turning a real conversation into follow-up eval cases later.

If the request times out, read the history before retrying. The server may have
persisted the turn after the CLI stopped waiting.

## `codeer history send` flags

Appends turns to an existing persisted history. It resolves the agent and
external user from history metadata unless explicitly overridden. Like
`history create`, it uses the agent's **current published version**; it does not
continue with an older or unpublished `AgentHistory` version.

| Flag | Type | Default | Purpose |
| --- | --- | --- | --- |
| `history_id` | integer | **required** | Existing persisted history ID |
| `--agent` | string | history metadata, then `CODEER_AGENT_ID` | Agent ID fallback/override |
| `--user` | string | history metadata | `external_user_id` fallback/override |
| `--message` | string, repeatable | **required** | User turn to append, in order |
| `--timeout` | float | `120` | Per-message response timeout in seconds |
| `--out` | path | — | Write complete message and conversation details to a file |

```bash
codeer history send <history_id> \
    --message "Use the recommended options" \
    --timeout 120
```

On a timeout, inspect `codeer history conversations <history_id>` before
retrying. A timed-out write may already have created the turn.

---

## `codeer eval run` flags

| Flag | Type | Default | Purpose |
| --- | --- | --- | --- |
| `--agent` | string | **required** | Agent ID |
| `--history` | string | — | Pin eval to a specific version (AgentHistory UUID) |
| `--latest` | flag | **default behavior** | Auto-select newest version |
| `--cases` | string | all | Comma-separated case UUIDs to run |
| `--evaluator` | string | assigned pairs | One evaluator UUID; common path for many cases with one tester |
| `--evaluators` | string | assigned pairs | Comma-separated evaluator UUIDs |
| `--poll-timeout` | int | 900 | Polling timeout in seconds |
| `--out` | string | — | Write results JSON to this path |

`--history` and `--latest` are mutually exclusive. If neither is passed,
the CLI uses the newest AgentHistory.

If `--evaluator` or `--evaluators` is supplied, the CLI runs the requested
cases with those evaluator IDs. If no evaluator is supplied, the CLI uses
external rubric batches to find case/evaluator pairs with configured rubrics.
Internally, runs should be triggered through the external eval runs endpoint
and grouped by evaluator. Do not call legacy internal trigger endpoints from
the public CLI.

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
