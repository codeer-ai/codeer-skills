# codeer-cli

Standalone CLI for managing Codeer agents over the Codeer API.

## User install

Install the CLI from PyPI with `pipx`:

```bash
pipx install codeer-cli
```

Verify that the command is available:

```bash
codeer --help
```

If `pipx` is not installed:

```bash
python -m pip install --user pipx
python -m pipx ensurepath
```

Then restart the terminal and run:

```bash
pipx install codeer-cli
```

As a fallback, you can install into your user Python environment:

```bash
python -m pip install --user codeer-cli
```

## Credentials

The CLI expects credentials to be configured outside any skill workspace. Add a
named profile, select it, then verify the setup:

```bash
codeer profile add work
codeer profile use work
codeer check
```

`codeer profile add` prompts for the API key without echoing it. The local
project stores only the selected profile name in `.codeer/profile`; API keys
remain in the user-level config file.

For a one-off shell session, you can also export an API key directly:

```bash
export CODEER_API_KEY=<admin-workspace-api-key>
codeer check
```

`CODEER_API_BASE` defaults to `https://api.codeer.ai`. Override it only for
local, beta, or preview environments:

```bash
export CODEER_API_BASE=http://localhost:8000
```

The CLI intentionally does not read repo-root credential files or caller CWD
`.env`, because those files are often visible to LLM workspace context. Do not
paste the API key into agent chat or commit it to the repository.

Workspace and organization scope are inferred from the workspace API-key
virtual user's profile. `--workspace`, `--org`, `CODEER_WORKSPACE_ID`, and
`CODEER_ORGANIZATION_ID` are not used by the CLI.

Agent scope is optional and can be set as a non-secret environment variable:

```bash
CODEER_AGENT_ID=<agent-id>
```

## Development install

Use an editable install while the CLI is changing quickly:

```bash
cd /path/to/codeer-skills/codeer-cli
uv tool install --editable .
```

Reinstall only when dependencies, entry points, or package metadata change:

```bash
uv tool install --reinstall --editable /path/to/codeer-skills/codeer-cli
```

Validate setup before API work:

```bash
codeer check
```

List the active cloud models without opening the Codeer web app:

```bash
codeer model list --type text
```

## Custom evaluator judge models

Custom evaluator create/update commands can select a judge LLM model by ID:

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

Omit the judge-model flags on update to leave the current setting unchanged.
Use `--clear-judge-model` to explicitly clear the override and return to the
system default:

```bash
codeer eval evaluator-update \
  --evaluator <evaluator-id> \
  --clear-judge-model \
  --dry-run
```

## Agent human handoff

`codeer agent apply` accepts the same `human_handoff` object as the Agent API.
The dry-run validates it and shows whether handoff is enabled before any server
write:

```json
{
  "name": "Support Agent",
  "system_prompt": "Help the user safely.",
  "human_handoff": {
    "enabled": true,
    "idle_timeout_minutes": null,
    "handoff_instructions": "Hand off when the user asks for a person."
  }
}
```

`idle_timeout_minutes` must be a positive integer or `null`. Human handoff only
becomes available in live published-agent conversations with a non-empty
`external_user_id`; editor Live Test conversations are internal and cannot
activate human mode.

## Upgrade and uninstall

Upgrade the CLI:

```bash
pipx upgrade codeer-cli
codeer check
```

Remove the CLI:

```bash
pipx uninstall codeer-cli
```

## Output policy for coding agents

The CLI is optimized for Codex, Claude Code, Claude Cowork, and similar coding
agents that keep command output in their LLM context. Default stdout is a
compact lifecycle summary, not the full server payload.

Use this pattern during agent lifecycle work:

```bash
codeer agent list
codeer history list --agent <agent-id> --limit 50
codeer history conversations <history-id> --out .codeer/current/history-<history-id>.json
codeer history create --agent <agent-id> --message "Review this plan" --timeout 240
codeer history send <history-id> --message "Use the recommended options" --timeout 240
codeer eval run --agent <agent-id> --cases <case-ids> --evaluator <evaluator-id> --out .codeer/eval_run.json
```

`history create` and `history send` use the agent's current published version.
They use Chat V2 structured SSE with `stream: true`; their per-message read
timeout defaults to 240 seconds. Success requires a `response.completed`
event. If the stream times out, reports `response.failed`, or disconnects
early, inspect the history before retrying: the server may already have
persisted the turn.

Eval case label commands always operate on the active API-key workspace. They
do not accept a workspace override; switch CLI profiles to target another
workspace.

Flags:

- `--full` prints bounded extra detail for human inspection. It is still
  intended to be safe for LLM context.
- `--out <path>` writes complete diagnostic artifacts to a local file. Use it
  for raw eval results, full conversation turns, full rubric matrices, and
  other data that can grow with cases, versions, or turns.

`history conversations` reads Chat V2 parts and follows all pages
automatically. Its stdout is still a bounded summary; the `--out` artifact is
the complete client-visible history, including tool calls/results,
attachments, interactions, feedback, and passthrough metadata.

Avoid piping large raw JSON directly into agent chat. Prefer `--out`, then ask
the coding agent to inspect targeted summaries, IDs, failing cases, or selected
snippets from the saved file.

## Website crawler KBs

Website-backed KB folders can be created and updated with `codeer kb crawl-*`.
Always preview crawler mutations with `--dry-run` first:

```bash
codeer kb crawl-create \
    --url https://example.com/docs \
    --folder-name "Product Docs" \
    --include-path "/docs*" \
    --exclude-path "/docs/private*" \
    --limit 250 \
    --max-depth 3 \
    --only-main-content \
    --dry-run
```

`--include-path` and `--exclude-path` are repeatable clean path patterns. Quote
paths containing `*` so the shell passes the wildcard to the CLI. Advanced
settings can still be passed through `--config-json`; explicit crawler flags
override matching JSON keys.

## KB node rename and delete

Knowledge Base roots, folders, and files are all KnowledgeNodes. Use
`codeer kb list` and `codeer kb files` to find node IDs, then preview mutations
with `--dry-run`:

```bash
codeer kb node-rename --node-id <node-id> --name "New Name" --dry-run
codeer kb node-delete --node-id <node-id> --dry-run
```

`node-delete` deletes the target node and all descendants. Review the dry-run
output before rerunning without `--dry-run`.

## Context Object FAQ

Use Context Object FAQ entries to route high-value questions to a canonical KB
file when semantic retrieval misses the right source. The FAQ target is a KB
file's `snapshot_object_id`, shown by `codeer kb files`. Add `--range` when the
route should reserve a stable passage inside that file. Ranges must include both
line and column positions so the Codeer UI can map them onto rendered Markdown.

```bash
codeer kb files --kb-id <kb-id>
codeer kb faq-list --context-object-id <snapshot-object-id>
codeer kb faq-create --context-object-id <snapshot-object-id> --question "..." --range 12:0-12:42 --dry-run
codeer kb faq-update <faq-id> --range 12:0-12:42 --dry-run
```

`--range` accepts `START_LINE:START_COLUMN-END_LINE:END_COLUMN`; repeat it to
reserve multiple passages.

After reviewing the dry-run output, rerun the create/update/delete command
without `--dry-run` to apply it.
