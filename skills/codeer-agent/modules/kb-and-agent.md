# KB & Agent Setup

From scope alignment through KB upload and agent creation.

For portable import, original-byte verification, complete saved text/FAQ and
cross-environment FAQ rebuilding, follow
[portable KB text, originals and FAQ](../reference/project.md#portable-kb-text-originals-and-faq).
Use the integrated single-file export for the FAQ coordinate basis and revision;
website crawl settings are excluded and remain a recorded gap.

Before designing or changing the agent payload, read
[agent-settings.md](agent-settings.md). Design the target state before the
textual diff; do not treat the system prompt as the default home for every
requirement.

---

## Diff rule

Before applying Agent changes, show the concrete diff and reconcile it with
the user's authorization. Carry forward authorization for the same reviewed
content and scope; ask before applying a material new decision or scope change.
The CLI preview token identifies content and does not itself grant approval.

Use `codeer agent diff` to show differences between versions when updating
an existing agent.

---

## Step 1 — Scope alignment

Before designing a new Agent, follow the shared
[discovery and source rules](../reference/agent-design.md#discover-and-ground-the-design).
For existing Agents, recover only the scope needed for the requested work.
Read the user's material, establish intended outcomes and limits, and clarify
material gaps. Preserve explicit instructions and all tasks already in scope;
do not require a questionnaire or a separate document approval.

Connect permitted actions to available capabilities. Recommend appropriate
Tools rather than requiring the user to know their technical names. For human
handoff, establish the permitted triggers and any material idle-timeout need;
human handoff is distinct from Call Agent delegation to another AI.
Business measures such as conversion or containment are context unless clearly
established as objectives, and must be reconciled with user outcomes and
guardrails rather than optimized in isolation.

Persist established decisions and pending proposals as discovery proceeds,
using the existing Agent design/draft, source index and review/log records. Do not
create a separate Scope Alignment artifact. Product facts belong in KB;
operational configuration belongs in settings. The design records the governing
decisions without copying either implementation.

### Route through design and eval design before building

Use the shared design basis for any Agent. For query-led customer guidance,
also use [consultative-guidance.md](consultative-guidance.md) for its specialized
discovery methods. Once relevant decisions are established, use
[eval-cases.md](eval-cases.md) to design a proportionate end-to-end acceptance
set locally. These steps happen before KB upload, Agent Settings design, or
Agent creation so intended customer behavior—not the first prompt draft—defines
what the first Agent must satisfy.

Use [query-distribution.md](query-distribution.md) before or after the design
only when a named demand, weighted portfolio, capacity, hot-path, or drift
decision requires analysis. Keep a one-off result in the current analysis;
create the optional `design/query_distribution.csv` and
`design/query_examples.csv` artifacts only when the model needs reuse.
Their absence does not block a first core-scenario build.

The cases cannot be applied to the server until the Agent exists. Keep the
reviewed local manifest ready, continue with the KB and Agent steps below, and
return to Eval Case Design after creation to apply the cases using the new
`agent_id`.

---

## Step 2 — Prepare and upload KB

### KB planning decisions

Propose the organization supported by the sources and existing conventions.
Ask about unresolved content scope or material tradeoffs; reversible file layout
choices do not require a separate approval ritual.

- One KB or several? (default: one per agent)
- Flat root or one level of folders? (KB UI only renders one level)
- Naming convention — descriptive `NN_topic.md` vs. opaque IDs
- Which source content to include vs. exclude
- Whether files need postprocessing before upload (merging, splitting,
  reformatting for better chunk boundaries)

### Content preparation

1. Crawl or write `kb/*.md` files. Keep filenames descriptive — the agent
   sees filenames via `list_kb_files`.
2. Consider crawler settings if fetching from web sources.
   Use `codeer kb crawl-create --url ... --folder-name ... --dry-run`
   for website-backed KB folders. Use `--include-path` / `--exclude-path`
   with quoted clean path patterns for scope control; `*` is supported as a
   wildcard, and plain paths match that path plus children. After approval,
   create the target, then monitor with `codeer kb crawl-state --folder-id ...`
   and inspect failures with `codeer kb crawl-failures --job-id ...`.
3. Postprocess files if needed:
   - Split large files at logical boundaries (headings, topics)
   - Merge tiny files that belong together
   - Add clear headings for better chunk boundaries
   - Remove noisy footer/boilerplate content that pollutes retrieval

### Upload

In a project, use a stable local ID and review the preview before upload:

```bash
codeer kb upload --dir kb/ --name "<KB display name>" --local-id support --dry-run
codeer kb upload --dir kb/ --name "<KB display name>" --local-id support --expect <token>
```

Use `--kb-id <id>` to adopt an existing KB explicitly. Project operations persist
IDs, source directory/glob, content fingerprints and receipts in `.codeer/`;
use returned node IDs in Agent settings. If readiness polling is interrupted
after file IDs were saved, use the same upload arguments with `--reconcile` to
read back those IDs without uploading again. Unknown file identities remain
blocked. Local managed source changes invalidate prior audit/run clearance.
Existing content replacement is unsupported by this API: do
not delete/recreate nodes as a substitute. See [project KB boundaries](../reference/project.md).
Outside a project, `codeer kb upload --dir kb/ --name "<name>"` retains its
legacy name-based selection; inspect `codeer kb list` before using it.

Wait for all files to reach READY status before proceeding. Files in
PROCESSING state are not yet available for retrieval.

---

## Step 3 — Create agent

In a project, `agent/instructions.md` is the prompt authority; omit
`system_prompt` from `agent/settings.json`. Use [project apply](../reference/project.md#scope-import-and-apply)
to preserve unmodified remote settings and stable tool IDs. Preview with
`codeer agent apply --dry-run`, then use the reviewed `--expect <token>`.
Payload-only examples below describe standalone use; project operations also
require their current preview token.

Write `agent/settings.json`. Pull stable normative customer
outcomes and guardrails from the accepted Agent design; use Scope
Alignment for scope, capabilities, and operational context, and use supported
Query Distribution evidence for hot-path and capacity decisions only when that
optional analysis exists and applies. Business or conversion goals from Scope
Alignment are not independent runtime objectives.
Use the reviewed acceptance cases as verification input rather than prompt
text, and attach KB node IDs from `codeer kb list` output. Apply the target-
state gate in [agent-settings.md](agent-settings.md) before presenting the
payload diff.

Discuss with the user:

- System prompt content (stable objectives, priorities, boundaries, and
  behavioral invariants)
- Tool selection and configuration (especially `invocation_instruction` /
  "When to Use" for each tool — this controls when the agent invokes it)
- LLM model choice. Run `codeer model list --type text` and use an exact
  `model_id` returned by the server; do not guess or reuse a stale model ID.
- Human-handoff behavior, including explicit transfer conditions and an
  optional positive `idle_timeout_minutes`.

When handoff is enabled, include it in the agent payload:

```json
{
  "llm_model": "<model_id from codeer model list --type text>",
  "human_handoff": {
    "enabled": true,
    "idle_timeout_minutes": null,
    "handoff_instructions": "Hand off when the user asks to speak to a person."
  }
}
```

Human handoff is available to evaluation runs and live published-agent
conversations that have a non-empty `external_user_id`. Internal editor Live
Test does not activate human mode, so do not treat a missing handoff tool there
as a configuration failure.

Then present the full payload diff before applying:

```bash
codeer agent apply \
    --payload agent/settings.json --dry-run
```

`codeer agent apply` always creates a new DRAFT version. The agent is not
live until explicitly published.

After a successful apply, refresh the server cache:

```bash
codeer agent get <agent_id> --full --out reviews/observations/agent.json
```

---

## Step 4 — Publish

Only after all of the following are true:

- [static-audit.md](static-audit.md) has no blockers against the exact version
  to publish;
- the final regression covered the shared
  [acceptance/protection scope](../reference/project.md#regression-scope), planned
  versus completed counts reconcile, and exploratory or unresolved pairs are
  explicitly accounted for;
- any evaluator-template or judge-model change has been treated as a new
  baseline;
- the evaluated AgentHistory/version, `response_mode`, KB attachments, and
  publish target are the same effective configuration; and
- eval debugging is complete, accepted findings have a completed repair or a
  documented no-change decision, and the user gives explicit go-ahead.

Check downstream impact before publishing changes that may affect other
agents:

```bash
codeer agent impact --agent <agent_id>
```

Preview the publish target before writing server state:

```bash
codeer agent publish --agent <agent_id> --version <version_number> --dry-run
# In a project, after separate publication authorization:
codeer agent publish --agent <agent_id> --version <version_number> --expect <reviewed-token>
```
