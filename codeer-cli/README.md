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

## Local skill management

CLI 0.1.17 adds local installation management for the three skills in this
repository. No Codeer API key or profile is needed for these commands:

```bash
codeer skill list
codeer skill list --target codex --scope project
codeer skill install codeer-agent --target codex --dry-run
codeer skill install codeer-agent --target codex
codeer skill install codeer-agent --target claude --scope project
codeer skill install codeer-presentations --target codex --ref <tag-or-commit>
codeer skill uninstall codeer-agent --target codex --dry-run
codeer skill uninstall codeer-agent --target codex
```

Supported names are `codeer-agent`, `codeer-audience-value-narrative`, and
`codeer-presentations`. Install/uninstall require `--target codex|claude`;
list shows both targets unless filtered. `--scope user` is the default:

| Target | User scope | Project scope (current directory) |
| --- | --- | --- |
| Codex | `~/.agents/skills/<name>` | `.agents/skills/<name>` |
| Claude Code | `~/.claude/skills/<name>` | `.claude/skills/<name>` |

List and uninstall are offline. Install resolves `--ref` (default `main`) to an
immutable GitHub commit, validates and copies the complete selected folder from
`skills/<name>`, and records provenance and SHA-256 hashes in
`.codeer-skill-install.json` inside the installation. The CLI package does not
bundle skill content. The selected GitHub revision must contain the `skills/`
layout; unpublished local moves and older revisions are not installable through
this command. Public GitHub access is required, and anonymous API rate limits
may apply. Install `--dry-run` reads GitHub but writes no installation files.

Install handles both first installation (`installed`) and replacement of an
unchanged managed copy (`updated`). Identical contents return `already_installed`
without writing, even if the source commit differs. Changed content is replaced
as a complete package so obsolete files do not remain. `--dry-run` reports
`would_install`, `would_update`, or `already_installed` without changing files.
Updates download and validate the new package first, recheck the old installation,
then retain a backup while replacing it. Publication failures restore the old
copy. If restoration also fails, the error gives the retained backup's path for
manual recovery. `--ref` can select an older revision as well as a newer one.

Modified, unmanaged, or symlinked directories are refused; preserve custom work
and resolve those installations manually. Uninstall checks hashes and removes
only the selected unchanged managed directory; it leaves
other skills and Codeer profiles intact. Other installers' locations and
receipts are not adopted automatically. `skill list` reports `installed`,
`modified`, `unmanaged`, or `not_installed` for each selected location; it does
not check GitHub for updates.

If discovery does not refresh, restart Codex or use `/reload-skills` in Claude
Code. These filesystem commands do not install account-level Cowork skills.

## Local Agent projects

Local Agent project continuation uses `codeer status` for recorded evidence and
an actionable `next_action` with a completion condition. It groups shared
Tester/variable gaps by affected-pair count; `status --full` includes identities
and full run details. `codeer validate` preserves combined `issues` and nonzero
exit for unresolved content, while separating `structural_issues`, `design_issues`,
`evidence_issues` and `operation_issues`. Structural validity is not complete
Eval design or apply/run readiness. Unresolved candidates stay in case drafts;
only admitted pairs enter the configured manifest. These checks do not perform
semantic review, verify live state or authorize mutations.

Agent create/update preflight accepts at most three suggested questions, each
at most 200 characters. A structured API validation 422 received before a
mutation is acknowledged is recorded as `rejected`, with safe validation
details; timeouts, unstructured errors, and readback failures remain
`outcome_unknown`. A rejected request still requires a fresh preview before retry.

For older receipts that lost the 422 details, `agent recover-rejected-create`
supports only the investigated maximum-three-question create rejection. It
requires explicit operator evidence containing `schema_version: 1`, the original
`receipt_sha256`, exact `scope` and `request_token`, observed `http_status: 422`,
`message: "Invalid request payload"`, `operator_attested_validation_rejection: true`,
and a project-relative `verification` report. The old request must contain more
than three suggested questions, the new settings must be valid, and a same-name
Agent must not exist. Listing absence alone is insufficient evidence. Review
with `codeer agent recover-rejected-create --evidence reviews/rejection.json --dry-run`,
then apply that exact preview with `--expect <token>`. Recovery performs only
server reads and a local state update, preserves the original receipt bytes,
writes a separate recovery receipt, and never retries creation itself. Known
server IDs, response-bearing receipts, other scopes and transient failures
are refused; use their existing identity-based reconciliation workflows.

The same recovery command also accepts a recorded pre-create HTTP 400 with the
exact backend message `Tool validation failed: One or more knowledge node files
are not in the workspace`; the evidence must match the receipt's retained HTTP
error. This validation happens before Agent creation. Select KB file nodes,
using `kb:<local-id>/<filename>` references, rather than the KB folder itself.
Other HTTP 400 messages remain uncertain and are not cleared by this path.

The following project commands are implemented in this checkout. This change
does not publish a new PyPI release; use the development install until a release
includes them. Initialization, status and structural validation work offline:

```bash
codeer init ./support-agent
cd support-agent
codeer status
codeer validate
```

`project.toml` describes one main Agent and supports custom paths. New schema 2
stores each deployment under `.codeer/deployments/<alias>/`; schema 1's target
and original revision reader remain supported. Child directories
discover it upward. API base, workspace and explicit Agent mismatches are
rejected; profile/connection changes invalidate previews, and legacy profile
constraints remain checked. Use global `--outside-project` only for an intentional standalone
operation. `status --refresh` explicitly queries remote configuration; offline
status reports the last observation time and cannot assert live remote validity.
Init preserves existing `.gitignore` content and appends private-output defaults
after existing rules; repeating init without further edits is idempotent.

`history negative-feedback` requires an explicit Agent or a bound project; a
missing target is rejected before querying History. Outside a project,
`eval export` and `eval reconcile` retain their `CODEER_AGENT_ID` fallback;
an explicit `--agent` takes precedence. Other commands that require an Agent
continue to require `--agent` when no project target is bound.

Original documents and extracted derivatives stay under `sources/`; curated
uploads belong in `kb/`. When working through the skill, the coding agent reads
your material, helps resolve material gaps and maintains the design record;
you need not learn its internal terminology or fill a template. Explicit
instructions are recorded with their basis without another document approval.
Unclear intent or conflicting sources still require a decision. The builder
keeps established decisions in
`design/agent-design.md`, pending decisions in its `.draft.md` counterpart,
and important milestones/reasons in `logs/YYYY-MM.md` (continue existing
`log.md`). The single prompt authority is
`agent/instructions.md`; omit `system_prompt` from `agent/settings.json`.
Structured Eval design lives in `evals/design.json`. Important understanding and
proposals are saved during discovery, so a new conversation can resume them.
Design decisions do not themselves authorize remote writes or publication.

These are new-project defaults. Override the design path with `[paths].design`;
the older `[paths].contract` key remains supported. Explicit settings take
precedence; if both keys are present they must resolve to the same path. Without
either key, an existing `design/behavior-contract.md` or its `.draft.md` selects
the old pair. If both naming pairs exist, set `[paths].design` to resolve the
ambiguity. Pending proposals use the selected file's sibling `<stem>.draft.md`.
Existing files are never automatically renamed. Updating the CLI or renaming
only the design file without changing content preserves its revision; changes
to content or dependent Eval references still require renewed validation. See
[the path rules](../skills/codeer-agent/reference/project.md#agent-design-paths-and-existing-projects).

To adopt an existing Agent without overwriting local work:

```bash
codeer agent bind --alias prod --agent <id>
codeer agent use prod
codeer agent pull --agent <id>
codeer eval pull
codeer agent diff --local
```

Import preserves raw editable/Published snapshots and marks them unvalidated.
KB import/export is separate. Agent and Eval apply compare base/local/current
remote fields and preserve stable server IDs. Arrays require explicit conflict
resolution. Missing local files do not delete resources. KB project upload
requires `--local-id`; existing targets require explicit `--kb-id`, never a name
match. The existing API supports new files, not safe in-place content replacement.

```bash
codeer agent apply --dry-run
codeer agent apply --expect <preview-token>
codeer eval cases-apply --dry-run
codeer eval cases-apply --expect <preview-token>
codeer kb upload --dir kb --name Support --local-id support --dry-run
codeer kb upload --dir kb --name Support --local-id support --expect <preview-token>
```

Tokens bind the reviewed preview to content, API, workspace and selected profile;
Agent update previews also include `--note`. They are not user approval. Partial
success and unknown outcomes retain receipts. Reconcile unknown identities before
retrying; client preflight/readback provides neither a transaction nor atomic CAS.
Separate local and remote checkpoints preserve web-only changes across repeated
apply without rewriting authored files. Resource commands retain reviewed local
proposals even when a later resource fails. Case attachment/label response objects
are compared as ID lists; Rubrics belong to Tester pairs, so project mode rejects
legacy `case-update --rubric`.
Project `cases-apply --cases` must resolve to the configured `[paths].evals`
file. Change that setting to adopt another design before preview/apply; default
and explicit applies then share one local authority.
Project `case-delete` requires a unique imported Case mapping, matching scope and
fresh remote ownership by the bound Agent, for both preview and deletion.
Intentional operations on another Agent use global `--outside-project`.
Explicit deletion journals intent before writing and retires the Case/pair mappings
only after reading back absence. It preserves authored design and historical IDs.
Remove the retired Case from the design before applying again; an intentional
replacement needs a new local ID and changed acceptance coverage needs review.
Unknown deletion outcomes block retry until `eval pull --reconcile` observes the
known ID: absence retires it, while presence restores checkpoints for fresh review.
Recovery never repeats DELETE or treats an unrecorded missing Case as authorization.
Retired mappings do not block other resources' recovery; original receipt evidence
remains available alongside reconciliation observations.

Status only reports a recorded release as current when its exact history, revision
and remote configuration fingerprint match the current passing run. A newer passing
configuration still requires publication review.

`agent pull --agent <known-id> --reconcile` and `eval pull --reconcile` read back
known identities, including a newly created Tester not yet assigned to any Case.
For an upload interrupted after file IDs were saved:

```bash
codeer kb upload --dir kb --name Support --local-id support --reconcile
```

This reads saved IDs without uploading again. A lost upload response with unknown
file IDs remains blocked. Managed KB bindings retain their source directory/glob;
added, changed or missing source files affect revision and offline dirty status.
Run/publish reject unapplied changes in referenced managed KBs. Missing files do
not authorize remote deletion; existing bindings cannot silently switch source
directories or globs.
Upload stages private temporary copies while computing the content hashes;
multipart requests use those exact bytes and original filenames even if source
files change during a request. Temporary copies are removed when the command ends.

Tester means the existing Evaluator/Judge. Select/reuse/design it, verify its
evidence producer and delivery, author Case/Rubric pairs, then review. Case local
IDs survive wording changes. Verified local source/report references must exist;
their content participates in revision identity. Structural validity does not
establish semantic correctness or evidence completeness.

```bash
codeer eval snapshot --history <exact-history-id> --out reviews/anchor.json
# Skill authors a scope-bound semantic audit; CLI cannot create this clearance.
codeer eval run --history <exact-history-id>
codeer eval export --run-id <saved-run-id> --out-dir reviews/export
codeer agent publish --history <exact-history-id> --dry-run
codeer agent publish --history <exact-history-id> --expect <preview-token>
```

Runs retain exact trigger result IDs, configuration, evidence requirements and
thresholds. Old results do not satisfy new runs; missing evidence, skipped pairs,
errors and failed behavior remain distinct. A Judge score is not independent
proof of a tool call or external completion. Publication checks a current audit,
confirmed `design/acceptance.json` scope and a passing covering run, then records
actual Published-history readback separately. `--reconcile` resolves publication
observations after unknown or mismatched outcomes; both block another preview or
publish until reconciled. The receipt retains the original readback alongside
the later observation. KB dependencies include search tools' `knowledge_node_ids`
and tabular tools' single `knowledge_node_id`, with the same readiness and source
freshness checks. Current KB/Tester state and `use_search`
cannot all be fixed by AgentHistory; fingerprints record observations, not
reproducibility guarantees.

See [schema, audit and acceptance formats](../skills/codeer-agent/reference/project.md)
and [local end-to-end fixtures](../examples/agent-workflow/README.md).

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
[the skill workflow](../skills/codeer-agent/reference/http-input-contracts.md) for details.

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

`history conversations` reads `/api/v1/external/histories/{id}/messages`
using a workspace admin API key and follows all pages automatically. Member
keys retain existing History visibility but are intentionally rejected by this
complete tool-payload export. This requires a server supporting
`history-parts-v1`; it never falls back to a
different authorization contract. Stdout shows at most 20 part summaries (50
with `--full`) and omits tool payload previews. `--out` retains native tool
args/results/outcomes, group/part IDs, attachments, feedback, and metadata.
Attachment URLs remain permission-checked History download endpoints rather
than direct storage/source URLs.
Legacy projections have `source: legacy-adapter`; tool outcomes absent from
the original records are omitted and marked `outcome_not_recorded`. System
prompts and provider raw traces are not included. Missing parts do not prove a tool never ran. Keep export files private.

`--client-visible --user <external-user-id>` explicitly selects the existing
Chat V2 owner/allowlist contract. No external identity is inferred from History
metadata. `history get` and the low-level legacy `get_conversations` reader
remain compatible. Management exports do not hydrate display-only tool payloads.

Release order: deploy the backend supporting `history-parts-v1` first, verify
an authorized management export across multiple pages, then release/install
this CLI. Existing CLI versions retain their previous behavior until upgraded.
If the backend endpoint is unavailable, the new CLI fails explicitly with no
fallback; keep the previous CLI installed until backend verification passes.
The management endpoint can remain available if the CLI release is rolled back.

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

## Portable KB originals and FAQ

In a schema 2 project, `codeer kb import --local-id manual --kb-id <id>` saves
originals, exact saved text and complete FAQ, with a provenance/integrity manifest.
Run `--dry-run`, then repeat with the reviewed `--expect <token>`. The first
portable `agent pull` also imports referenced KB resources when no Agent definition
exists. Existing definitions and originals are preserved. `kb export` remains
the separate legacy text export.

Knowledge definitions may declare a `faq_file` and `manifest` path in
`resources.json`. For the format and complete workflow, see
[portable KB/FAQ](../skills/codeer-agent/reference/project.md#portable-kb-text-originals-and-faq).
After target KB upload/binding, use `kb faq-sync --local-id manual --keep-local`
with preview/expect to keep a pending proposal; then preview/expect the same command
with `--apply` to rebuild. `--remote` adopts target text/FAQ locally without remote
writes. Existing target FAQ need explicit `--ids` mappings; questions are never
matched. Target saved text must match before recreating ranges. Reconcile known
interrupted operations with `--reconcile`; unknown creates need investigated IDs,
never a blind retry. Recovery uses the recorded identities even if newer local
proposals remove a FAQ. Unrelated platform changes remain undecided and do not
advance recovery bases; compare and choose again before applying.

The CLI uses conditioned same-service resource downloads and the single-file
text/FAQ export, staging and checking bytes before saving. Export API absence,
missing originals and permission failures remain explicit gaps; no `source_url`
fallback is used. A missing server digest is recorded separately from verified
hashes. Website crawl settings are excluded and recorded as a gap. Export
revisions identify environment observations; portable definitions use local hashes.
Partial imports retain available files and per-resource gaps. Direct file
references reuse covering folder mappings when available. FAQ definitions/manifests
enter immutable run inputs and selected delivery bundles; declared files must
exist, and resolved input paths must remain outside deployment state and inside
the project. Offline bundle verification checks those declared dependencies too.

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
