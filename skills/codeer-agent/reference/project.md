# Local Agent project contract

This reference is bundled with the `codeer-agent` skill and defines the shared
contract for local Agent projects. The repository README's **Local Agent
development** section provides the directory overview; see
[onboarding](../onboarding.md) for setup and first steps.
Each project's own `README.md` holds its specific usage and context.

`project.toml` is local configuration for one primary Agent, not a remote
Codeer Project. Skill modes compose resource commands; there is no `codeer
project`, `codeer build` or `codeer audit` command.

## Files and offline work

```toml
schema_version = 1
name = "Support"
[target]
# Filled by pull/create; no credentials.
agent_id = "<remote-agent-id>"
api_base = "https://api.codeer.ai"
workspace_id = "<workspace-id>"
# Optional profile constraint. Selection remains in .codeer/profile.
profile = "work"
[paths]
agent = "agent/settings.json"
instructions = "agent/instructions.md"
evals = "evals/design.json"
sources = "sources/index.md"
design = "design/agent-design.md"
acceptance = "design/acceptance.json"
```

Initialize with `codeer init customer-project`; `status` and `validate` work
without auth or a bound Agent. Init creates README, log, source index and
documents entry, preserving existing content. Other directories appear on
demand. Paths are relative to project root and must stay inside it. Override
paths to adopt existing files; do not move/delete legacy data automatically.
Only a literal `[target]` table with simple one-line basic strings supports
comment-preserving automated binding; exotic TOML is rejected for manual review.

### Agent design paths and existing projects

Resolve the Agent design source before reading or saving it. `[paths].design`
is the preferred setting; `[paths].contract` remains a supported legacy alias.
An explicit setting wins even when its file does not exist yet. If both keys
are set, they must resolve to the same path inside the project; otherwise fix
the conflicting settings before continuing.

Without either setting, use `design/agent-design.md` for new projects. If only
the old `design/behavior-contract.md` or `design/behavior-contract.draft.md`
exists, continue using that old pair. If either member of both the new and old
pairs exists, `status`/`validate` stop with an ambiguity error: establish the
intended source and set `[paths].design`. Never create a second design authority
or move customer files just to follow the new naming.

Pending proposals belong beside the selected design as `<stem>.draft.md`, e.g.
`notes/policy.md` uses `notes/policy.draft.md`. The paths below and in other skill
modules are new-project defaults; always substitute the selected path and its
draft. Both must stay inside the project. Init preserves existing authored
files; updating the CLI does not rename them or rewrite historical references.

The older name was Behavior Contract. Its content responsibilities and project
schema have not changed. Revision hashing retains its legacy field identity:
an upgrade, alias change, or rename of the design file with identical content
alone does not invalidate audit/run/release evidence. Changes to content or
other dependencies still do. If Eval source references point to a moved file,
update those references and revalidate the affected evidence. Pending drafts
are not accepted design and are not hashed as the established design file.

| Location | Authority / purpose |
| --- | --- |
| `sources/index.md` | Original path/URL, purpose, version/date, authority, gaps, derivative/KB mapping |
| `sources/documents/` | Original SOP/PDF/customer material; extracts are separate files with provenance |
| `sources/history/<collection-id>/` | Raw History/AI Draft exports and collection scope; never public fixtures |
| `kb/` | Curated upload content and source mapping; remote-only references need no local copy |
| `design/agent-design.md` / `.draft.md` | Builder-maintained established design basis / pending proposal; instruction or confirmation evidence lives in `reviews/` |
| `design/acceptance.md` / `.json` | Human delivery scope and gaps / machine acceptance pairs and scope-bound confirmation |
| `agent/settings.json`, `agent/instructions.md` | Writable settings and the sole editable prompt; omit `system_prompt` from JSON when Instructions exists |
| `evals/design.json` | Stable Case/Tester design, Rubrics, evidence requirements and pairs |
| `reviews/` | Semantic audit, repair/Tester decisions, confirmation evidence, immutable observations |
| `runs/<run-id>/`, `releases/<release-id>/` | Actual operation evidence; never overwrite a prior run |
| `.codeer/` | Profile name, state, remote imports, ID mappings, sync bases and operation receipts |
| `log.md` | Short dated reason, decision/status, evidence links and next unresolved step; never machine truth |

The builder follows the shared [discovery and source rules](agent-design.md#discover-and-ground-the-design)
to maintain this design from user goals, clear instructions, designated source
rules and confirmed choices. Users need not know the internal file names or
approve a document merely to make their explicit instructions effective.
Persist important understanding and open proposals during discovery; keep
unresolved assumptions in the draft. Record actual instruction/confirmation
evidence and link it from the established design. Missing legacy design files
do not block a bounded diagnosis or clearly specified repair. This does not
change remote-operation authorization or machine evidence requirements below.

Local `source.document` and evidence `verification` paths must exist within the
project. Their bytes participate in revision identity; changing a report makes
prior audit evidence stale. External HTTP(S) references are recorded, not fetched
or semantically verified by offline validation. A verified flag and an existing
file are structural checks; audit must still inspect actual producer/delivery
evidence and challenge Judge scores contradicted by tool traces.

Init ignore defaults exclude local state, raw histories, runs, PDF and raw release
evidence. Init appends these defaults after existing `.gitignore` rules, preserving
their content; repeating init without further edits leaves the file unchanged.
Review confidentiality before sharing other sources/design; location
does not grant publication rights. Legacy `.codeer/design/current/pinned`
content is only adopted after explicitly selecting files, preserving originals.
Input-based manifests remain usable outside project mode. To adopt them, pull
server IDs, then match explicitly; duplicate text or differing prior context is
ambiguous and must never auto-map by name/input.

## Scope, import and apply

Explicit Agent arguments, environment Agent, bound profile, API base and
Workspace must agree. A different operation requires an explicit
`codeer --outside-project …` invocation; this does not rebind the project or
claim project acceptance. Do not use it to bypass a project conflict.

```bash
codeer agent pull --agent <agent-id>
codeer eval pull
codeer kb export --node-id <kb-node-id> --dir kb/imported --out reviews/kb-import.json
codeer status
```

Pull saves raw editable/Published/version observations separately from writable
files, retains remote/shared identities, and never modifies existing local work.
A repeated pull observes without advancing established sync bases. `--reconcile`
explicitly accepts observed remote baselines after inspecting an interrupted
receipt; local drafts remain intact. It advances the local checkpoint only when
readback proves the receipt's payload, preserving proposals edited after that
operation. Eval recovery includes known unassigned Testers. Unknown create identity cannot be recovered
by guessing a matching name: identify it from actual server evidence first.
Agent pull does not import KB/Eval; the skill coordinates those separate commands.
Current KB/Rubric/Tester reads are not historical snapshots of an old Agent version.
Record gaps in sources/reviews and append an import milestone to the log.

```bash
codeer agent diff --local
codeer agent apply --dry-run
codeer agent apply --expect <reviewed-token>
codeer eval cases-apply --dry-run
codeer eval cases-apply --expect <reviewed-token>
```

Dry-run tokens cover exact current base/local/remote changes, API, workspace and
selected profile. Agent apply also binds its `--note`; preview with the same note.
Present the diff
and obtain or carry forward authorization before mutation; tokens do not grant
approval. Apply rereads before each mutation and reads back afterward. Disjoint
top-level changes can form a proposal; same-field edits conflict. Prompt,
Rubric, tools and ordered arrays are indivisible. Omitted local fields retain
remote values; missing files/resources never authorize deletion. Explicit tool
removal lists IDs with `--remove-tools`; pair removal lists server Tester IDs in
the case's `remove_tester_ids`. No transaction, server CAS or automatic rollback
is promised. Successful resource receipts survive a later failure; unknown
outcomes require reconciliation before retry.
Successful apply and no-op synchronization store separate local and remote
checkpoints. A web-only value retained remotely does not become a new local
overwrite proposal on the next apply. Resource commands persist reviewed
proposals before writes so a partial failure cannot turn old authored values into
rollback intent. Confirmed pair removals are idempotent; remote readdition needs
review, and an explicitly accepted readdition clears the earlier removal marker.

Case responses expose `attachments` and `labels` objects; imports, snapshots,
preflight and readback compare their ID lists. Rubrics belong to Case/Tester pairs.
Project mode rejects the legacy Case-level `rubric`/`case-update --rubric` path;
use `pairs` or `rubrics-apply`. Agent comparison expands documented nested schema
defaults while retaining tool IDs/order and arbitrary HTTP template values/nulls.

KB upload in a project requires `--local-id`, and `--kb-id` to reuse an existing
KB. It creates new file nodes and stores readiness/snapshot evidence; it cannot
replace existing file content in place. A replacement proposal must name new
nodes and review Agent/FAQ reference changes. Never delete/recreate silently.
The binding also retains its source directory/glob. New, changed and missing
local files affect revision and dirty status; referenced managed KBs must be
current before run/publish. A legacy binding missing source metadata cannot
assert freshness; explicitly reselect the original source files to adopt it.
Changing a binding's directory/glob requires a separate stable local ID.
Upload hashes and sends the same privately staged bytes, preserving original
filenames/MIME types. Source edits during the request remain local unapplied
changes. Temporary content is removed when the command ends; receipts store hashes.

If polling failed after file IDs were saved, run
`codeer kb upload --dir kb --name Support --local-id support --reconcile`.
It queries saved file IDs without another upload. A root ID alone or a lost
upload response cannot establish file membership and stays blocked for recovery.

## Complete evaluation design

Choose/review the Tester first, identify evidence producer and actual delivery,
then design Case/Rubric and pair them. Drafts need no server IDs. The following
synthetic example is a format illustration, not an accepted SOP:

```json
{
  "schema_version": 1,
  "testers": [{
    "local_id": "tools", "name": "Tool behavior",
    "rationale": "Reuse one common tool judge for distinct case Rubrics",
    "system_prompt_template": "Judge {tool_steps} against {rubric}",
    "evidence": [{"variable": "tool_steps", "producer": "reasoning_steps",
      "availability": "verified", "verification": "reviews/tool-evidence.md"}]
  }],
  "cases": [{
    "local_id": "request-human", "input": "Human please",
    "source": {"document": "sources/documents/sop.md"},
    "meta": {}, "attachment_ids": [], "label_ids": [],
    "pairs": [{"tester": "tools", "rubric": "Actually call the handoff tool",
      "required_evidence": ["tool_steps"]}]
  }]
}
```

`meta` retains supported prior-state/conversation references; never invent a new
backend context field. Keep source provenance outside API payload. Review
Judge model omission versus explicit `null` (system default). IDs live in
`.codeer/state.json` scoped to API base/Workspace/Agent. Renaming input retains
the case; identical input may represent distinct initial conditions. Tester
updates preview all accessible Workspace pair usage, including other Agents.
One Tester can cover many cases; new Testers need a distinct evidence/judgment
reason. Validate reports unresolved references/evidence; it cannot approve SOP
semantics or prove that a producer really supplies the claimed evidence.

Existing `case-update`, `evaluator-create/update`, `rubrics-apply` and `reconcile`
share mappings, differences and receipts in project mode. Tester creation needs
`--local-id` already in design. Per-resource updates retain their bounded scope.
New pairs require design/evidence first; rubric apply cannot invent a pair.
`cases-apply` reads the configured `[paths].evals` file (default `evals/design.json`).
An explicit `--cases` must resolve to that same file. Adopt another file through
`[paths].evals` before previewing; alternate proposals cannot silently diverge
from the design used by the next default apply.
Project `case-delete` checks the unique imported mapping, saved scope and current
remote Case ownership before preview or deletion. Use global `--outside-project`
for intentional standalone deletion. It saves a pending deletion receipt before
writing, then checks the exact ID for absence. Only verified absence retires the
Case and its pair mapping; local design and historical IDs remain intact.
Remove the retired Case from the design before applying again, and review changed
acceptance coverage. An intentional replacement needs a new `local_id`.
Timeouts, interruptions and failed readback remain unresolved and block repeating
the deletion. `eval pull --reconcile` reads known IDs without deleting again:
absence retires the mapping; presence records the observation and restores the
previous checkpoints for fresh review. Ordinary pull does not resolve unknown
deletions, and an unrecorded missing Case never authorizes retirement. Retired
mappings do not block recovery of other resources. Receipts retain original
responses/readback/errors alongside later reconciliation observations.

## Audit, runs and publication

### Regression scope

Full regression covers the confirmed acceptance pairs and the declared protection
pairs for the current change. Establish that set before running; account for
exploratory and unresolved assignments separately. Server assignment alone does
not make a pair a release requirement. Do not omit affected protection pairs or
shrink the agreed scope merely to obtain a pass.

For project publication, include every required acceptance and protection pair in
the confirmed `acceptance.json`. Outside a project, record the agreed pair IDs
before execution. A focused run supports full clearance only if it covers the
entire required set. Unfiltered CLI runs default to all assigned pairs; use an
explicit selection for a smaller agreed scope without deleting assignments.

### Audit and run evidence

Use `codeer eval snapshot --history <history-id> --out reviews/anchor.json` to
read exact AgentHistory and current cases, pairs, Tester/Judge model, KB status,
snapshot IDs and FAQ dependencies, including `knowledge_base.knowledge_node_ids`
and `tabular_data.knowledge_node_id`. Both shapes participate in readiness,
managed source freshness and run/publication evidence. Perform semantic audit using the relevant
module. A local design review is not remote clearance. Save the readable report
and `reviews/<id>.audit.json`:

```json
{
  "schema_version": 1, "conclusion": "pass", "history_id": "<exact-history-id>",
  "revision": "<anchor revision>", "remote_fingerprint": "<anchor remote_fingerprint>",
  "pairs": [{"case_id": "<server-case-id>", "evaluator_id": "<server-tester-id>"}],
  "report": "reviews/audit.md", "report_fingerprint": "<fingerprint of report text>"
}
```

Use `codeer_cli.project.fingerprint` for machine hashes; never hand-invent them.
The metadata states a scope-bound review conclusion, not an automatic semantic
decision. Never copy a passing conclusion after content changes without review.
Use `conclusion: "pass"` only when the selected scope has no blockers; keep any
non-blocking warnings in the readable report. Project runs require this current
clearance even for an authorized exploratory request. The CLI has no blocked-run
override; resolve blockers and re-audit rather than rewriting the verdict or
using `--outside-project` to bypass it. See the
[audit verdict rules](../modules/static-audit.md#step-6--report-the-findings).

```bash
codeer eval run --history <history-id> --cases <optional-case-ids>
codeer eval export --run-id <run-id> --out-dir reviews/export
codeer status --refresh
```

Run persists inputs before triggering, then trigger responses and result IDs.
Only those IDs count. `missing`, `unjudgeable`, `skipped`, `error`, `failed` and
`passed` remain distinct. Empty tool evidence can prove no call; absent evidence
cannot prove success. A claimed handoff differs from a call, which differs from
external completion. Unsupported evidence variables remain unjudgeable. Export
with `--run-id` reads the saved run's identities without triggering. The API returns
only the latest result per pair, so export retains already captured exact rows
when a newer run hides them; `refresh_observation` records IDs absent from the
latest query. Missing historical rows remain incomplete and newer result IDs
cannot fill them. Passed/failed historical outcomes remain distinct. Exact-run
export keeps completed `run.json` unchanged so release fingerprints remain
verifiable; refresh details go to the exported copy. Incomplete runs with saved
IDs can resume readback and update their record. Version-only
export is historical analysis and is not a newly executed acceptance run.
An interrupted trigger with no returned identity remains outcome unknown; the
API cannot reconstruct its membership reliably, so do not blindly retrigger.

For publication, save `design/acceptance.json` with stable pair IDs and an actual
confirmation record:

```json
{
  "pairs": [{"case": "request-human", "tester": "tools", "minimum_score": 1.0}],
  "confirmation": {
    "source": "reviews/acceptance-decision.md",
    "source_fingerprint": "<fingerprint of actual confirmation record text>",
    "scope_fingerprint": "<fingerprint of this object without confirmation>"
  }
}
```

Passing requires every required pair to meet its confirmed `minimum_score`
(default 1.0) with complete necessary evidence. A lower score threshold changes
the measurement standard and must be included in the reviewed acceptance scope;
it cannot waive missing evidence, errors or skipped pairs. A focused run cannot satisfy
a larger acceptance set. Changes to Agent/KB/FAQ/Case/Rubric/Tester invalidate
dependent evidence. Status explicitly marks its last remote observation;
offline status cannot prove live remote validity. Comparison separates Agent/KB
changes from measurement changes and does not infer score causality.
Status reports a recorded release as current only when its exact history, local
revision and remote configuration fingerprint match the current passing run.
A newer passing configuration still requires publication review.

```bash
codeer agent publish --history <history-id> --dry-run
codeer agent publish --history <history-id> --expect <reviewed-token>
# After an unknown or mismatched publication outcome: readback only, no new publish.
codeer agent publish --history <history-id> --reconcile
```

Publish remains separately authorized. It requires current audit, confirmed
pair set, passing covering run and exact version. Release records preserve
expected/actual Published identity and unknown/mismatch outcomes. Unresolved
outcomes block another preview or publication until reconciled. Reconciliation
preserves the original readback and records the later observation separately;
it does not establish the intervening publication sequence. These
fingerprints identify observed configuration; they do not freeze KB contents,
tool external state, or concurrent web edits. Local fixtures do not establish
deployment readiness.
