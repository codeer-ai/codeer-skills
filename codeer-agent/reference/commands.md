# CLI Command Reference

Use registered `codeer` domain commands only. If an operation is not supported
by the CLI, say that it is not supported by the CLI and stop for user direction.

Only `kb/` (source content for upload) stays at root level.
All working files go under **`.codeer/`** in the project root.

---

## `.codeer/` file lifecycle

The server is the source of truth for all agent, eval case, and rubric data.
Accepted Query Distribution and Behavior Contract files are persistent local
design state, not server objects. Other local files are **caches** of server
state, **drafts** staged for apply, or pinned evidence.

```
.codeer/
├── design/                             # accepted, persistent local design state
│   ├── query_distribution.csv         # descriptive demand and eval allocation
│   └── behavior_contract.md            # normative customer-guidance behavior
│
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
│   ├── local_draft_eval_cases.md       # reviewed behavior draft; may contain unresolved pairs
│   ├── local_draft_eval_cases.json     # draft:  codeer eval cases-apply
│   ├── local_draft_rubrics.json        # draft:  codeer eval rubrics-apply
│   └── progress.json                   # batch tracking across eval runs
│
└── pinned/                             # append-only baselines, pre-change evidence, saved revisions
    └── YYYY-MM-DD/                     # append -2, -3 for same-day pins
```

### Rules

1. **`design/` is persistent accepted state** — it survives cycles and is never
   auto-overwritten. Before replacing an accepted design artifact, preserve the
   prior accepted revision under `pinned/<date>-design/`.
2. **`current/` overwrites in place** — no date-stamping, no versioning.
   Refresh caches from the server at the start of each cycle.
3. **`pinned/` is append-only** — automatically pin the first full baseline
   and every required pre-change eval before a runtime change. Ask whether to
   pin other temporary debug or batch results only when preserving them would
   be useful.
4. **No files outside `design/`, `current/`, and `pinned/`** — nothing at
   `.codeer/` root.
5. **No scripts** — `.py`, `.mjs`, `.html`, `.cjs` are prohibited under
   `.codeer/`. If the CLI cannot do it, say so and stop for user direction.
6. **Drafts use `local_draft_` prefix** — distinguishes local working files
   from server caches. Delete apply-staging drafts after successful apply +
   cache refresh. Retain `local_draft_eval_cases.md` while it still records an
   unresolved case/evaluator pair or an accepted behavior that has not yet been
   transferred into the server-backed suite.
7. **ID cache files are not used** — no `kb_ids.json`, `agent_ids.json`,
   `case_ids.json`. The CLI resolves IDs from env vars or server queries.

These paths do not decide whether a customer project commits `.codeer/design/`
to Git. Treat design artifacts as potentially confidential. Use Git only in an
approved private repository or use another approved revision store; local
persistence and pinning do not by themselves authorize sharing the files.

### Cycle lifecycle

| Phase | Required handling |
| --- | --- |
| Cycle start | Preserve `design/`; refresh caches in `current/`: `codeer agent get`, `codeer eval list`, `codeer eval rubrics` |
| During cycle | Drafts created, diffs shown, applied. Eval exports overwrite `current/eval_table/`. Debug artifacts overwrite in place per batch. |
| First baseline | Automatically copy the exported results plus exact Agent/version and evaluator/judge context to `pinned/<date>-first-baseline/` before diagnosis or repair. |
| Pre-change eval | Automatically copy the focused pre-change results and context to `pinned/<date>-pre-change/` before a runtime change. |
| Other pin (optional) | Ask before copying temporary debug or batch evidence to `pinned/<date>/`. |
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
| `codeer model list` | List active cloud LLM models; use `--type text` for agent models |
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
| `codeer eval evaluator-create` | Create an evaluator, optionally with a judge model override |
| `codeer eval evaluator-update` | Update an evaluator or reset its judge model to the system default |
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
codeer model list --type text
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

## `codeer model list` and agent model selection

List the active text models before creating or updating an agent:

```bash
codeer model list --type text
codeer model list --type text --full
codeer model list --type text --out .codeer/current/models.json
```

Use the returned `model_id` verbatim as the agent payload's `llm_model`.
`--full` adds modalities, pricing, and creation metadata to stdout; `--out`
writes the complete server response while keeping stdout compact.

`codeer agent apply` also accepts a versioned agent-level handoff config:

```json
{
  "human_handoff": {
    "enabled": true,
    "idle_timeout_minutes": null,
    "handoff_instructions": "Hand off when the user asks to speak to a person."
  }
}
```

`idle_timeout_minutes` must be a positive integer or `null`. Human handoff is
available in evaluation runs and live published-agent conversations with a
non-empty `external_user_id`; internal editor Live Test does not activate it.

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

## Custom evaluator judge models

Use a model ID from `codeer model list --type text` to override the system
default judge model for a custom evaluator. Preview each mutation first:

```bash
codeer eval evaluator-create \
    --name "Correctness" \
    --system-prompt-template-file evaluator-prompt.txt \
    --judge-model <model-id> \
    --dry-run

codeer eval evaluator-update \
    --evaluator <evaluator-id> \
    --judge-model <model-id> \
    --dry-run
```

On update, omitting both judge-model flags leaves the current override
unchanged. To clear the override and return to the system default, explicitly
use:

```bash
codeer eval evaluator-update \
    --evaluator <evaluator-id> \
    --clear-judge-model \
    --dry-run
```

Dry-run output reports `judge_model.action` as `set`, `unchanged`,
`use_system_default` (create without an override), or
`clear_to_system_default`. `--judge-model` and `--clear-judge-model` are
mutually exclusive on update.

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

## `codeer history list` flags

| Flag | Type | Default | Description |
|---|---|---|---|
| `--agent` | string | — | Filter by agent ID. |
| `--user` | string | — | Filter by external user ID. |
| `--feedback` | string | — | Filter by feedback state (`positive`, `negative`, or `any`). |
| `--exclude-users` | string | — | Comma-separated external user IDs to exclude. |
| `--version` | integer | — | Filter by agent version. |
| `--limit` | integer | `50` | Maximum histories returned in this page. |
| `--offset` | integer | `0` | Histories to skip before returning this page. |
| `--full` | flag | false | Print the full response instead of the compact view. |
| `--out` | path | — | Write JSON to a file. |

Pagination is caller-controlled. Start with `--limit 50 --offset 0`; if the
page contains 50 histories and the task needs broader coverage, continue with
`--offset 50`, then `100`, and so on. Stop on a page shorter than `limit` or
when the evidence scope is sufficient. Do not fetch all pages by default, and
do not interpret a first-page miss as proof that no matching history exists.

## `codeer history conversations` flags

Reads persisted content from `GET /api/v2/chats/{id}/messages` and follows all
pages automatically. Standard output is a bounded part summary for coding-agent
context safety; use `--out` whenever completeness matters.

| Flag | Type | Default | Purpose |
| --- | --- | --- | --- |
| `history_id` | integer | **required** | Persisted history ID |
| `--out` | path | — | Write every unmodified client-visible Chat V2 part |
| `--full` | boolean | false | Require `--out` and include longer stdout previews |

```bash
codeer history conversations <history_id> \
    --out .codeer/current/history-<history_id>.json
```

The artifact includes tool-call/tool-return payloads, metadata, attachments,
interactions, and feedback. It intentionally does not include server-side
`system-prompt` or `console_only` parts hidden from workspace API keys.

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
| `--timeout` | float | `240` | Per-message Chat V2 SSE read timeout in seconds |
| `--out` | path | — | Write complete message and conversation details to a file |

Example:

```bash
codeer history create \
    --agent <agent_id> \
    --title "Seed conversation" \
    --user "eval-seed@example.com" \
    --message "First user turn" \
    --message "Follow-up user turn" \
    --timeout 240
```

The command uses Chat V2 with `stream: true`. The output includes `history_id`,
conversation group/part IDs, and a history URL. Keep those IDs when turning a
real conversation into follow-up eval cases later.

Success requires `response.completed`. If the stream times out, reports
`response.failed`, or disconnects before completion, read the history before
retrying. The server may already have persisted the turn.

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
| `--timeout` | float | `240` | Per-message Chat V2 SSE read timeout in seconds |
| `--out` | path | — | Write complete message and conversation details to a file |

```bash
codeer history send <history_id> \
    --message "Use the recommended options" \
    --timeout 240
```

The command sends each turn with `stream: true` and requires
`response.completed`. On a timeout, `response.failed`, or early disconnect,
inspect `codeer history conversations <history_id>` before retrying. The write
may already have created the turn.

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
