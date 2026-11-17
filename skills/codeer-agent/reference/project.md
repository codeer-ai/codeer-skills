# Local Agent project contract

This reference is bundled with the `codeer-agent` skill and defines the shared
contract for local Agent projects. The repository README's **Local Agent
development** section provides the directory overview; see
[onboarding](../onboarding.md) for setup and first steps.
Each project's own `README.md` holds its specific usage and context.

`project.toml` is portable configuration for one primary Agent, not a remote
Codeer Project. Skill modes compose resource commands; there is no `codeer
project`, `codeer build` or `codeer audit` command.

## Files and offline work

```toml
schema_version = 2
name = "Support"
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
The current project contract is schema 2, without `[target]` or personal profile.
Target/state/resources/FAQ objects have their own schema 1 contracts; those numbers
do not make them old projects. Additional optional diagnostic fields are ignored.
Unsupported project formats fail before authentication and remain untouched; there
is no runtime migration command. Follow the [one-time preparation runbook](one-time-preparation.md)
on a reviewed copy when needed. Conforming projects need zero conversion. Fixed
history, embedded project.toml and old evidence are never rewritten or upgraded.

## Remote Agent bindings, clone and platform adoption

Keep projects in your own repository, e.g. `projects/<stable-name>/`. Recommend a
root README linking projects and common AGENTS maintenance rules; do not create a
workspace registry, rewrite the root index or commit for the user automatically.
Recommend `.codeer/` in the repository-root `.gitignore` too, protecting inherited
profile selection at every level. Preserve authored rules; project init does not
rewrite the parent repository's files.
Each project is discovered independently from its nearest `project.toml`.

Use an existing explicit environment, nearest parent/project `.codeer/profile`
or global profile. `.codeer/` missing after clone is normal, not proof of missing
credentials. Run `profile current` and `check`; only missing configuration calls
for explicit `profile add <name>` (other platform: `--api-base`). Unselected
profiles need `profile use`; an unknown name must be selected or added explicitly.
Missing/rejected keys need the actual setting corrected and `check` repeated;
environment overrides must be corrected/removed themselves. Network/timeouts/5xx
mean connection unverified. Explicit permission errors differ from uncertain
401/403 rejection; do not infer expiration from HTTP status alone. Never scan
files for keys or persist environment credentials. Interactive `profile add`
alone may save secure input to the user's config, with restricted permissions.

```bash
# Both configure local state; --new-agent does not create a remote Agent yet.
codeer --profile beta-a agent bind beta-customer-a-main --agent <id>
codeer --profile beta-a agent bind beta-customer-a-candidate --new-agent
codeer --profile beta-b agent bind beta-customer-b-main --agent <id>
codeer agent use beta-customer-a-main
codeer agent bindings
codeer --binding beta-customer-a-candidate --profile beta-a status
```

Each binding names one remote Agent mapping in this project, not an environment.
Names are project-unique, 1–64 letters/digits/underscores/hyphens, starting with a
letter or digit. Same environment/workspace may have many Agents and a workspace
may have several keys. Names such as `beta` are allowed when unambiguous; examples
include workspace/customer and Agent role to make multi-Agent work clear.
The physical paths remain `.codeer/deployments/<name>/target.json`, `state.json`, `imports/`
and `receipts/`; `.codeer/deployment` stores the local selection. `--deployment`,
`bind --alias` and `--new` are low-cost command aliases using the same handlers.
`agent bindings` is offline and shows saved API, workspace/Agent names and IDs,
selection, creation intent and unresolved operations. Saved names may be stale.
`known_agent_id` shows an acknowledged create ID even before it can be bound;
`creation_unresolved` means investigate/reconcile that operation, not create again.
Binding/profile names are not platform identity. API/workspace/Agent
must match actual scope. Profile/environment changes after a preview invalidate
that preview. Content revision excludes deployment and personal profile; runs
and releases still bind actual scope and exact remote content. Do not copy state
from another computer. Shared production writes require operator coordination;
there is no server CAS or concurrent-writer guarantee.

Global `--profile <name>` selects credentials/API for one invocation, including
`check`, first bind, previews and `status --refresh`, without changing the default
or saving credentials. An explicit profile rejects any `CODEER_API_KEY` override
and a different nonempty `CODEER_API_BASE` before client creation/authentication;
a trailing slash is equivalent. Without the flag, existing env/directory/global
priority remains. `agent use` changes only the binding. Profiles are not pinned
or enumerated in bindings: any valid key for the same API/workspace may be used,
but a key/profile change requires a fresh mutation preview.

### Shared resources and candidate separation

Sharing a Tester/KB is valid; a new Agent binding does not imply dependency copies.
A Rubric belongs to one Case/Tester pair. Editing that Rubric with `rubrics-apply`
does not update the shared Tester or another Agent's pairs. Updating a shared
Tester previews the readable Agent/Case users (`shared_impact`); explain that this
is the accessible workspace scope, not proof that all external consumers are known.
Review the actual shared settings and impact. A change in readable users invalidates
the preview. Historical runs keep captured settings/results and are not rescored.

For candidate-only changes to the Tester itself:

```bash
codeer --binding beta-customer-a-candidate --profile beta-a eval tester-fork --tester tools --dry-run
# Repeat with --expect <token>; use --reconcile after a known-ID interruption.
```

`tools` is a local Tester ID. The command creates one new Tester from reviewed
local settings, reconnects only this Agent's mapped Cases while retaining their
Rubrics, reads back, then updates this binding's mapping. The shared source and
other bindings remain untouched. Changing an `env:` model value invalidates its
preview, just as for ordinary Agent/Eval apply. An interrupted create without a returned ID is
never repeated; investigate the actual server identity. Partial reconnection keeps
its receipts and known new Tester ID. Reconcile those reads, review a fresh preview
and finish reconnection before another fork or edit to that created Tester.

For separate KB files, use `kb upload --fork --local-id faq --dir kb --glob '*.md'
--name 'Candidate FAQ' --dry-run`, then reviewed `--expect`. It creates new KB/file
IDs and changes only this binding's local mapping after original-byte verification.
Before starting or finishing the mapping switch, reconcile unfinished FAQ operations
for this KB and unfinished Agent writes in this binding. Their recovery depends on
the existing mapping; a paused fork retains its known new IDs for later reconnection.
The output still has `references_pending: true`: upload does not switch the Agent
or copy FAQ. Review/rebuild FAQ against the new saved snapshots, then use
`agent diff --local`, `agent adopt --resource agent --fields unified_tools
--keep-local` with preview/expect, and `agent apply` with fresh preview/expect.
Only the Agent readback establishes the completed reference switch. Original
sources and other Agents' old KB nodes remain. For partial uploads use the same
`--fork ... --reconcile`; unknown file identities block any repeat create/upload.
The visible source users come from readable Agent knowledge-tool references;
hidden/non-Agent consumers and server transactions are outside this guarantee.

### Machine records and safe cleanup

`imports/` holds observations, not a second editable Agent definition. Unchanged
Agent/Eval pulls reuse one snapshot and update state's observation time. `receipts/`
holds request/identity/readback and recovery evidence; it is more than an activity
log. Current sync receipts omit derived base/local-base/remote/comparison copies;
state keeps checkpoints. FAQ replay still needs its full preimage. Existing optional
extra fields remain readable without another format reader.

Never remove `.codeer/`, state or whole record directories to resolve an unknown
operation. For a receipt cited by fixed project evidence, recovery creates a live
derivative with original path/SHA-256 instead of rewriting the pinned source.

```bash
codeer --binding beta-customer-a-main clean --dry-run
codeer --binding beta-customer-a-main clean --older-than 30d --dry-run
# Repeat the same selection/age with --expect <token>.
codeer clean --keep .codeer/deployments/beta-customer-a-main/receipts/example.json --reason 'Investigation baseline'
```

Cleanup is explicit, offline and project-local; there is no background retention
job. Preview writes nothing, lists exact files/bytes and retention reasons. Only
recognized, completed, unreferenced receipt/import history in the selected binding
is eligible. Current state from every binding, JSON/path/Markdown/SHA-256 references,
manual `.codeer/keep.json`, unresolved outcomes, source files, runs, releases and
fixed history protect content. An unrecognized history contract/scope retains that
binding; corrupt global roots refuse cleanup. Cyclic dependencies are retained.
Deletion removes referrers before their dependencies, so interruption can resume
with a fresh preview. Symlinks are refused rather than followed.

Apply takes `.codeer/project.lock` and rechecks candidates/protection roots/token.
Current CLI project writers use the same exclusive local process lock, including
pull/apply/reconcile/refresh/run/export/publish/delivery and FAQ preview observations.
This provides no remote CAS and no protection against older CLI, direct file
tools, skill audit/pin writes, or standalone/outside-project writers. Stop those
writers during cleanup and one-time preparation; do not claim they inherit a lock.
Manual keep is persistent; removing a keep entry requires deliberate local review.

`resources.json` contains originals and KB source selections:

```json
{
  "schema_version": 1,
  "attachments": {"manual": {"path": "sources/documents/manual.pdf"}},
  "knowledge": {"faq": {"directory": "kb", "glob": "*.md"}}
}
```

Agent/Case attachments use `attachment:manual`; knowledge tools use `kb:faq` or
`kb:faq/faq.md`. Model/HTTP URL/credential values can use `env:VARIABLE` referencing
an explicitly supplied environment variable. Sensitive HTTP auth/header values
must use these references; resolved values stay at the HTTP boundary. Check
available models in each deployment. Context/label environment IDs require
explicit environment references, not committed platform IDs. Upload originals
with `agent attachment --local-id manual --dry-run`, then the reviewed `--expect`;
bytes are downloaded and checked after upload. Unknown upload identity blocks
retry. KB upload must match its declared directory/glob/local ID. Its new node
IDs are mapped locally. The API cannot replace existing KB file content in place.
Create-only API omissions (`response_mode`/output policy) are listed as deferred;
after create readback, review a second apply without changing portable content.

After clone, map an existing attachment explicitly with `agent attachment
--local-id manual --remote-id <uuid> --dry-run`, then the matching `--expect`.
The ID must occur in the selected Agent/Eval and downloaded bytes must match the
local original; no upload occurs. If identity/bytes cannot be proven, retain the
gap. On an already deployed/takeover target, genuinely new attachments or KB
uploads require explicit `--new`; missing mappings cannot create replacements.

Takeover is explicit: pull records Draft/Published observations, then compare
and decide with the same adoption core used for ongoing platform changes:

```bash
codeer agent pull
codeer agent adopt --resource agent --fields description --remote --dry-run
codeer agent adopt --resource agent --fields description --remote --expect <token>
codeer agent adopt --resource agent --fields human_handoff --keep-local --dry-run
# Repeat that reviewed choice with --expect <token>.
codeer agent adopt --resource tester:tools --remote-id <uuid> --remote --dry-run
codeer agent adopt --resource case:handoff --remote-id <uuid> --keep-local --dry-run
codeer agent adopt --resource pairs:handoff --remote-id <case-uuid> --remote --dry-run
```

Never match names or case text. Map Testers before pair adoption. For a genuinely
new Case/Tester on takeover, explicitly declare `--remote-id new --keep-local`
and confirm its preview; missing state alone never authorizes creation. `eval
pull` preserves existing design and observations, without silently mapping clone
resources. KB takeover uses `kb bind --local-id faq --kb-id <id> --files <json>`
where JSON maps each source path to an exact node ID. Review with `--keep-local`
or `--remote-text` and `--expect`. Binding verifies original bytes using the
conditioned download API. Text adoption is limited to text files whose saved
text equals the downloaded original; other representations stay separate.

Each independent field is `aligned`, `pending_apply` or `undecided`. Equality or
verified adoption advances only that field's bases. Keeping local 30 against
remote 14 retains a pending 30 proposal; it aligns only after successful apply
and readback of 30. Adopting 14 updates local bytes, verifies them and aligns with
zero remote mutations. Partial adoption preserves all other conflicts. Prompt,
Rubric and arrays remain indivisible. An unresolved field blocks the resource's
whole replacement payload; independent resources may proceed when their own
dependencies are satisfied. Confirmation is tied to both current values; either
side changing requires comparison again. `--reconcile` resolves interrupted
operations only when readback proves the recorded expected payload; it cannot
accept a conflicting platform edit or clear unknown results by observation alone.

No-original-project imports can obtain settings/Eval, attachment bytes and referenced
KB originals/text/FAQ through the resource-export APIs. Record missing-original,
capability and permission gaps with source/time. Legacy `kb export` remains a
UTF-8 text operation. Unavailable design rationale,
confirmations and old local history cannot be reconstructed. Sub-Agent references
are preserved for read-only diagnosis and block project deployment; do not recurse,
remove them or offer remote-ID-only deployment. Imports are not complete backups,
accepted business design, passing evaluation or publication authorization.

Formal delivery uses `eval delivery --run-id <id> --release-id <id> --out-dir
<fresh-directory>`, then `eval delivery --verify <directory>`. It exports selected
run/results/traces, audit/confirmation evidence and release readback with hashes
and exact IDs. Missing evidence remains incomplete; summaries cannot replace it.
No `.codeer/`, other trials or all conversation history are exported. Share raw
evidence under appropriate access controls; verification is offline integrity
and identity, not live verification or proof of authenticity.

### Portable KB text, originals and FAQ

Use the single-file resource export for unchanged saved text, the complete FAQ
collection, metadata and `export_revision`. It avoids mixing independently read
text/FAQ and detects FAQ-only changes. Each file is consistent; walking a KB is
not a cross-resource transaction. Do not replace this read with paginated FAQ
queries or refreshed `/content` text when preserving FAQ coordinates.

```bash
codeer kb import --local-id manual --kb-id <root-or-file-id> --dry-run
codeer kb import --local-id manual --kb-id <root-or-file-id> --expect <token>
```

Import writes originals under `sources/knowledge/manual/originals/`, an exact
saved-text/FAQ definition at `kb/manual-faqs.json`, and provenance/download
evidence in `sources/knowledge/manual/manifest.json`. Existing destinations are
refused. Imported FAQ IDs are deployment mappings; portable FAQ values contain
stable local IDs, questions and ranges. Agent import is observation, not accepted
design or quality validation. Website crawl settings are excluded and recorded
as `website_crawl_settings_excluded`; saved page text does not recreate crawling.

A knowledge declaration can add `faq_file` and `manifest` relative paths:

```json
{"schema_version":1,"files":{"001-guide.pdf":{"content":"Exact saved text\n","faqs":{"opening-hours":{"question":"Opening hours?","ranges":[]}}}}}
```

This is the FAQ file's format. Questions are trimmed, nonempty and at most 100
characters. Ranges use the existing API's one-based lines, zero-based columns,
optional character offsets and text; saved CRLF/whitespace must remain unchanged.
Original PDFs are never overwritten by text snapshots. Source IDs/revisions stay
in the provenance manifest and local mappings, not portable FAQ values. Remote
`export_revision` is an opaque deployment identity, not a portable content hash.

After target KB upload/readiness or explicit `kb bind`, map each original path
to a target node. FAQ synchronization compares the entire collection for each
file. Use explicit IDs for existing target FAQ; never match questions/names:

```bash
codeer kb faq-sync --local-id manual --ids faq-ids.json --remote --dry-run
# faq-ids.json: {"001-guide.pdf":{"opening-hours":123}}
# Repeat with --expect <token> to adopt target text/FAQ locally; no remote writes.
codeer kb faq-sync --local-id manual --keep-local --dry-run
# Repeat with --expect <token> to preserve a pending local proposal.
codeer kb faq-sync --local-id manual --keep-local --apply --dry-run
# Repeat with --expect <token> only within authorization for those FAQ mutations.
codeer kb faq-sync --local-id manual --reconcile
```

New target FAQ require a reviewed keep-local decision, then a separate apply.
Apply requires exact target saved-text equality before recreating ranges; changed
extraction is a review gap, never an automatic coordinate rewrite. Unmapped target
FAQ block writes. Only explicitly mapped FAQ can be updated/deleted; removing a
managed local definition previews deletion. Platform deletions are visible and
may be adopted; missing IDs never silently create replacements. For deliberate
new identities, provide a reviewed complete mapping with those entries omitted.

Previews bind local bytes, mappings, current export revisions and connection.
Successful readback alone advances bases; partial/unknown writes retain receipts.
Known update/delete identities reconcile without another write. Unknown create
identities block retry; after external investigation supply a complete `--ids`
mapping with `--reconcile` to verify exact snapshot/content, without creating.
Recovery uses recorded file/snapshot identities even if a newer local proposal
removed the FAQ. It confirms only recorded operations: additional platform changes
remain `conflict`/`undecided`, with the prior bases retained and a fresh explicit
choice required. Batch readback also checks that only the reviewed FAQ changed.
Direct file references reuse a covering KB's exact file mapping; a single-file
import keeps its file reference distinct from the owning KB root.
Automatically imported overlapping folders retain their root references and
originals, while shared exact file IDs reuse one canonical file reference.
Explicitly configured ambiguous aliases still require resolution.
Reconciliation preserves newer local proposals as pending. Pure preview/read
never advances bases or accepts design. Pending local FAQ or unresolved writes
block run/publish for referenced managed KB. Run inputs and selected delivery
include FAQ definitions/manifests; the run records complete observed FAQ/revisions.

Original downloads use authenticated same-service endpoints with snapshot/revision
conditions, staged bytes, response identity, size and available SHA-256 checks.
`files:status` establishes readiness; snapshot identity comes from metadata,
conditioned downloads and complete exports. KB binding rechecks the export
revision before recording its baseline; status need not contain a snapshot ID.
Null server digest is recorded as `no_server_digest`, not two-sided hash proof.
409/interruption/mismatch cannot finalize a successful original. Missing export
APIs report capability gaps; no internal-route or `source_url` fallback. Saved
representations, text, media URLs and external references do not become uploaded
originals automatically. Required missing originals prevent complete deployment.
Import preserves available files/text/FAQ when another node is not ready or
unavailable, recording per-node server reasons and marking the KB incomplete.
An entirely unavailable KB leaves a gap receipt so the same local ID can be retried.
Declared manifests are required run/delivery inputs; missing references invalidate
both new runs and offline delivery checks. Collected paths resolve symlinks before
checking project and machine-state boundaries.

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

The older name was Behavior Contract. Naming compatibility preserves its content
responsibility. Revision hashing retains its legacy field identity:
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
| `runs/<run-id>/`, `releases/<UTC-timestamp>-<id>.json` | Actual operation evidence, including pending/unknown; legacy `releases/<id>/release.json` is also read without double counting |
| `.codeer/` | Profile name and selected alias; each deployment owns target, mappings, bases, observations and receipts |
| `logs/YYYY-MM.md` | Important reasons, status, evidence links and unresolved steps; continue an existing `log.md` without splitting/copying it |

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

### Batch reviews and project entry

Use the project README as navigation to goals, primary artifacts, unresolved
decisions and the latest material batch/run, not another hand-maintained status
database. Actual receipts/runs take precedence over stale prose. Existing authored
README and configured/legacy paths remain in use; no reinitialization is needed.
Extension analysis is welcome when it states purpose, source and relationship to
the primary artifact. Derive admitted Case/Rubric reading copies from the configured
manifest when needed; only unresolved proposals remain separately editable drafts.

For a material batch use `reviews/batches/<batch-id>/report.md` for findings,
decisions, scope and evidence links, with necessary attachments alongside it.
Continue an existing relevant report within the batch. Do not create a report for
every command, ordinary query or unchanged validation; the monthly log links
milestones. Workers return findings to the parent instead of independent files.
Keep confirmation source and the exact reviewed content recoverable.

For per-run conclusions, readable reports, necessary customer questionnaires
and returned answers, follow [assessment and clarification](../modules/eval-review.md).
Do not append follow-up findings to a report fingerprinted by an audit or fixed
delivery: keep it intact and continue in a sibling document with current
README/log navigation. Preserving old bytes does not establish that a contradicted
semantic conclusion remains valid for the next gated operation.

Active audit metadata may live at `reviews/*.audit.json` (legacy) or
`reviews/batches/<batch-id>/*.audit.json`. Both use the same matching rules in
status, run and publish. Other nested archives, especially `reviews/evidence/`,
are historical observations and do not grant active clearance. Reports may be
linked inside the project; fingerprints and scope still determine validity.
Do not relocate old evidence or rewrite its references as an upgrade side effect.

Pin first-baseline evidence before diagnosis or repair, and any focused run used
as a pre-change comparison. An existing `runs/<id>/` is not necessarily fixed:
`eval export --run-id` can resume and overwrite its `run.json` unless the recorded
status is `passed`, `failed` or `stale`. This rule applies to current contract-2 runs;
having answers or a `finished_at` timestamp does not make an `incomplete` run fixed.

- For `passed`, `failed` or `stale`, link the existing run and record its raw-file
  SHA-256 in the batch report; do not duplicate the run tree.
- For `incomplete`, `triggering`, `polling`, `outcome_unknown` or an unrecognized
  status, first read the original `run.json` bytes once, compute their SHA-256 and
  save those same bytes at a fresh path such as
  `reviews/batches/<batch-id>/baseline/<run-id>-<sha256>.json`. Do not reserialize
  or overwrite them. Reuse an existing pin only after verifying identical bytes
  and hash. Later observations belong at separate paths, not over this baseline.
- In the existing batch report, link the evidence and record its SHA-256, run,
  history and result IDs, recorded status and comparison purpose. A pinned partial
  observation is still partial, not acceptance or a completed baseline. Check
  the hash on resume before relying on the comparison.

For old runs without evidence contract 2, every status is historical and read-only;
`inspect-run` reports stored status/counts/hash only. Current export/refresh,
publication and new delivery do not accept them. A pinned old CLI may inspect old
semantics offline; it must not act on current projects or grant current clearance.

The JSON preserves its captured snapshot, results and context; retain referenced
inputs in their original run directory and copy only missing or mutable supporting
evidence needed by the diagnosis. Generic `--out` paths may be reused by later
runs and are not pins. Saving a pin makes no network call, changes no canonical
run or recovery receipt, and does not change publication clearance. Unchanged
reads need no new pin or report. Formal delivery still needs a self-contained,
verified bundle. Preserve existing archives and `.codeer/` recovery receipts.

`codeer status --human` is opt-in readable offline guidance; default JSON remains
unchanged. `codeer eval inspect-run --run-id <id>` reads captured evidence offline,
showing current recorded outcomes separately from derived evidence interpretation with
source hash. It does not refresh, rewrite, rerun, accept or authorize publication.
New runs (evidence contract 2) resolve input/rubric from the bound snapshot and
output/tool_steps from results; wrong version/pair/result IDs or snapshot bytes
cannot supply static evidence. Legacy run/export classification remains intact;
use inspect-run for a separately attributable interpretation of old evidence.

New init ignore defaults exclude all `.codeer/`, raw histories, runs and releases;
required PDF/attachment/KB originals remain eligible for controlled Git storage.
Legacy ignore rules are preserved; review broad historical PDF rules explicitly
before sharing needed originals. Init appends defaults after existing rules, preserving
their content; repeating init without further edits leaves the file unchanged.
Review confidentiality before sharing other sources/design; location
does not grant publication rights. Legacy `.codeer/design/current/pinned`
content is only adopted after explicitly selecting files, preserving originals.
Input-based manifests remain usable outside project mode. To adopt them, pull
server IDs, then match explicitly; duplicate text or differing prior context is
ambiguous and must never auto-map by name/input.

## Scope, import and apply

A build's first remote resource write, including KB upload, requires the
[local alignment review](../modules/static-audit.md#local-alignment-before-first-apply)
across sources, design, KB, Instructions and acceptance cases. Its report in
`reviews/` records scope, reviewed identities, findings and dispositions. Reuse
unchanged covered inputs on resume; changes require only the affected relations
to be checked and linked to retained conclusions. This is a skill-level semantic
prerequisite, not something `validate`, preview tokens or the offline status
recommendation can certify. It does not replace later readback/audit/Eval.

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
reads an interrupted operation's recorded identity; local drafts remain intact.
The current reader advances the local checkpoint only when
readback proves the receipt's payload, preserving proposals edited after that
operation. Eval recovery includes known unassigned Testers. Unknown create identity cannot be recovered
by guessing a matching name: identify it from actual server evidence first.
The first portable Agent pull imports referenced KB originals/text/FAQ and attachments
without overwriting existing definitions. Eval import remains separate. A repeated
pull preserves local proposals and bases.
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
removal lists IDs with `--remove-tools`; pair removal lists `tester:<local-id>` references in
the case's `remove_tester_ids`. No transaction, server CAS or automatic rollback
is promised. Successful resource receipts survive a later failure; unknown
outcomes require reconciliation before retry.
Successful apply and no-op synchronization store separate local and remote
checkpoints. Changed remote fields require explicit adoption or keep-local decisions.
Resource commands persist reviewed
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
then design Case/Rubric and pair them. Drafts need no server IDs.
Keep unresolved candidates in the Markdown draft; the configured manifest holds
admitted pairs. Use the shared [completion meanings](../workflows/lifecycle.md#completion-meanings):
authoring is not complete Eval design, and declared evidence verification is
not observed runtime delivery. Existing unresolved manifests must be corrected
through review without silently dropping managed pairs or acceptance requirements.
The following synthetic example is a format illustration, not an accepted SOP:

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
the selected binding's `state.json` scoped to
API base/Workspace/Agent. Renaming input retains
the case; identical input may represent distinct initial conditions. Tester
updates preview all accessible Workspace pair usage, including other Agents.
One Tester can cover many cases; new Testers need a distinct evidence/judgment
reason. Validate reports unresolved references/evidence; it cannot approve SOP
semantics or prove that a producer really supplies the claimed evidence.

`codeer validate` separates `structural_issues`, `design_issues`, `evidence_issues` and
`operation_issues`, preserving the combined `issues` and nonzero exit for unresolved
content. `eval_design.evidence_gaps` groups each Tester/variable's reasons and
affected pairs; the full per-pair `unresolved` remains available. A structurally
valid manifest may still have `design_complete: false` / `apply_ready: false`.
These machine checks never replace semantic review or waive existing gates.
`codeer status` summarizes shared gaps with affected-pair counts and returns
`next_action` (evidence, action, completion condition and limits); `next_step`
retains the action text. `status --full` includes per-pair issues and identities
plus the full recorded run; `validate` retains all unresolved details.
Offline status checks the current values of explicitly referenced `env:` variables
against the last snapshot, reporting `environment` in `local_changes` when they
differ. The derived `latest_run.environment_stale` separately compares against
the run's saved environment fingerprint, so refresh cannot make an old run current
for different settings. Status exposes no resolved values and rewrites no run,
outcome or content revision. Restoring the reviewed settings permits reuse of
otherwise unchanged evidence; unreferenced variables do not invalidate it.
Advice is derived from recorded operations, changes, audit and runs, not a manual
phase field. Offline status does not check live dependencies or infer an execution
error's root cause. Check the artifacts and current task before acting.
For an unchanged passing run awaiting publication, `renew_audit` identifies
missing/invalid current audit evidence. Retain the run/results and renew the
semantic clearance; audit evidence repair alone does not require another Eval.
Status checks the same confirmed acceptance scope as publication, falling back
to the latest run's planned pairs when acceptance is not yet confirmed. The
`audit.valid_for_acceptance_at_last_query` and
`valid_for_latest_run_at_last_query` fields distinguish these scopes from
`valid_at_last_remote_query` (all snapshot pairs); exploratory pairs outside
confirmed acceptance do not force audit renewal. All remain cached checks.
Configuration changes, new findings or missing coverage still follow existing
stale/run/publication gates. An already verified release remains an observation
entry rather than a request to publish again.

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
and `reviews/<id>.audit.json` (legacy) or
`reviews/batches/<batch-id>/<id>.audit.json` using the same schema:

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
