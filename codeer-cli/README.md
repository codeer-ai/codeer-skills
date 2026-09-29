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

Codeer contributors should use an editable install from this checkout, not the
PyPI package, so the `codeer` command always executes the folder being edited:

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

## HTTP input contracts

`codeer agent apply --payload` and SDK `agents.create` / `agents.update` accept
`unified_tools[].http_request.body.input_contracts`. No separate HTTP command is
needed. The target backend must have the HTTP input-contract feature deployed
(codeer-copilot #1495); installing this CLI alone does not enable runtime support.
A local dry-run cannot establish server deployment or API business-rule success.

Example payload:

```json
{
  "name": "Order helper",
  "system_prompt": "Use the configured API for approved order changes.",
  "use_search": false,
  "unified_tools": [{
    "id": "submit",
    "type": "http_request",
    "http_request": {
      "method": "POST",
      "url_template": "https://example.com/orders",
      "body": {
        "template": {
          "quantity": "{{agent[Requested quantity]}}",
          "payload": "{{agent[Order details]}}",
          "changes": "{{agent[Changes as JSON text]}}"
        },
        "input_contracts": {
          "quantity": {"type": "integer"},
          "payload": {"type": "object"},
          "changes": {"type": "string", "format": "json", "json_type": "array"}
        }
      }
    }
  }]
}
```

- `type`: `string` (default), `number`, `integer`, `boolean`, `object`, `array`.
- `format`: `text` (default) or `json`; `json` requires `type: string`.
- `json_type`: `any` (default), `object`, `array`; outside JSON format, only
  `any` is valid. API names are snake_case; the CLI rejects `inputContracts`,
  `jsonType`, and unknown fields inside individual contracts.

`type: object` / `array` sends a native JSON value. `type: string, format: json`
sends a string containing JSON. Existing valid JSON text is sent unchanged;
empty strings also pass unchanged, while non-empty text must parse and match
`json_type`. Plain strings retain existing behavior, including malformed JSON.
The backend converts supported representations before checking runtime values;
the CLI only validates configuration and never executes the configured HTTP
request. Contracts do not configure nested JSON Schema constraints or defaults.

Keys come from template paths, not instructions: `order.count` → `order_count`,
`items[0].id` → `items_0_id`, root string → `body`. Non-ASCII-alphanumeric runs
become `_`, edge underscores are removed, and keys are lowercased. Multiple
placeholders in one string add `_1`, `_2`; traversal collisions add `_2`, `_3`.
Object insertion order matters: preserve it when editing/exporting. Typed and
JSON-text placeholders must occupy the entire template value. Stale contract
keys fail validation; omitted entries remain ordinary strings.

For an existing Agent:

```bash
codeer agent get <agent-id> --out .codeer/current/agent.json
# Prepare local_draft_agent.json from current writable settings; review its diff.
codeer agent apply --agent-id <agent-id> --payload .codeer/current/local_draft_agent.json --dry-run
# After approval:
codeer agent apply --agent-id <agent-id> --payload .codeer/current/local_draft_agent.json
codeer agent get <agent-id> --out .codeer/current/agent.json
codeer agent get <agent-id> --history <history-id-from-apply> --out .codeer/current/agent-version.json
```

The external update uses PATCH, but it is **not a nested partial update**.
Preserve `name`, `system_prompt`, `use_search`, the complete `unified_tools` list
(including other tools, templates, auth and `draft_policy`), and the full desired
contract map. Also preserve description, attachments, suggested questions,
model settings, handoff and other writable settings. Sending one changed tool
replaces the list; omitting a contract entry resets that input to ordinary string.
GET responses and writable payloads have different shapes; reconstruct attachment
IDs and other absent writable fields from current version evidence as needed.
Do not apply an update if a current setting cannot be preserved by the CLI. See
[the skill workflow](../codeer-agent/reference/http-input-contracts.md) for details.

Dry-run's `http_inputs` lists tool indexes and each generated key's effective
`type` / `format` / `json_type`, with `configured: false` for defaults. It excludes
HTTP URLs, auth, headers, query values, instructions and template content.
`body_inputs_used` is false for GET/HEAD, whose body inputs are unused at runtime.
`--full` and `--out` deliberately retain complete nested content, including
credentials; metadata cleanup is limited to resource-level account fields and
workspace identity. These exports are not redacted artifacts.

Compare the fresh GET and exact version snapshot with the intended tools and
contracts; the server may materialize omitted defaults. `agent versions --out`
exports version metadata, not snapshots; use `agent get --history` for a snapshot.
Apply saves a draft. Publish the verified version separately, after approval,
using `codeer agent publish --agent <agent-id> --history <history-id>` (preview
with `--dry-run` first).

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
codeer history list --agent <agent-id> --has-ai-drafts --limit 50
codeer history conversations <history-id> --out .codeer/current/history-<history-id>.json
codeer history ai-drafts <history-id> --out .codeer/current/ai-drafts-<history-id>.json
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

- `--full` prints bounded extra detail for human inspection. Some commands,
  including `agent get`, can expose configuration credentials; `history
  ai-drafts` can expose sensitive conversation text and therefore requires
  `--out`. Use each command's flag description as the output contract, and
  inspect complete artifacts locally without flooding LLM context.
- `--out <path>` writes complete diagnostic artifacts to a local file. Use it
  for raw eval results, full conversation turns, full rubric matrices, and
  other data that can grow with cases, versions, or turns.

`history conversations` defaults to the workspace-editor management export and
follows all pages automatically. Its stdout is a bounded summary that never
prints tool arguments or results; the `--out` artifact preserves the complete
`history-parts-v1` payload, including persisted tool calls/results,
attachments, feedback, and metadata. System prompts and provider raw traces are
not part of that export contract, and a missing part does not prove that a tool
was not executed.

`history list --has-ai-drafts` narrows the history page to conversations with
at least one AI Draft and includes lifecycle counts in compact output.
`history ai-drafts` follows every server page and writes every returned draft
lifecycle record to `--out`: generated content, refinement lineage,
`generation_instruction`, `dismiss_reason`, `dismiss_feedback`, outcomes, tool
activities, proposed actions, operator attribution, and the correlated actual
delivery when one exists. Default stdout shows structural flags and counts but
no generated, operator, customer, or tool text. `--full --out <path>` explicitly
opts into bounded content previews. The endpoint has no revision token, so a
multi-page artifact is marked `snapshot_consistency: best-effort`: count changes
and duplicate IDs fail the export, but lifecycle fields can still change during
paging. Re-run when point-in-time consistency matters. These fields are evidence
for an improvement analysis; the CLI does not invent a recommended Agent change
from them.

Use the external client-owner contract only when that distinction is the point
of the test:

```bash
codeer history conversations <history-id> \
  --client-visible --user <external-user-id> \
  --out .codeer/current/client-history-<history-id>.json
```

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

## Exporting KB snapshot content

Export one file directly from the content endpoint:

```bash
codeer kb export \
  --node-id <file-node-id> \
  --file guide.md
```

Or recursively export a folder or an entire KB root:

```bash
codeer kb export \
  --node-id <folder-or-kb-root-node-id> \
  --dir kb-export \
  --out kb-export-manifest.json
```

`--file` and `--dir` are mutually exclusive. Single-file mode maps directly to
the external file-content endpoint and lets the caller choose the exact local
path. Folder mode recursively lists the node tree, calls that endpoint for each
file, and writes the extracted snapshot content as UTF-8 Markdown. Existing
`.md`/`.markdown` names are preserved; other folder-export names receive an
additional `.md` suffix (for example, `guide.pdf` becomes `guide.pdf.md`) so the
export is not mistaken for the original binary upload.

The command asks the content endpoint for every file regardless of indexing
status. If the endpoint returns text, it is exported even when the status is
not `READY`; the full manifest preserves that server status and marks the file
as `exported_while_not_ready`. If the endpoint returns `content: null`, the file
is skipped and the command exits non-zero. Existing target files block the
entire export before any content is written; pass `--overwrite` only when
replacing those local files is intended.

This is a snapshot-content export, not an original-file backup. The server API
returns processed text and does not return the original PDF, DOCX, or other
binary bytes through this endpoint.

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
