# KB & Agent Setup

From scope alignment through KB upload and agent creation.

Before designing or changing the agent payload, read
[agent-settings.md](agent-settings.md). Design the target state before the
textual diff; do not treat the system prompt as the default home for every
requirement.

---

## Diff rule

**Before applying any agent changes** (create or update via `codeer agent apply`),
present the full diff to the user and wait for approval. Never apply agent
changes silently — the user must see what is being changed.

Use `codeer agent diff` to show differences between versions when updating
an existing agent.

---

## Step 1 — Scope alignment

**Do this before any KB or agent work.** For the first version, pin down six
things with the user without turning scope alignment into a scenario inventory:

1. **Core scenario** — one smallest valuable end-to-end situation that
   expresses why the Agent exists: the observable user intention or task,
   starting state, material constraint, and supported Agent role. Choose the
   central value path, not merely the easiest FAQ.
2. **Candidate core outcome and exclusions** — the user-visible result this
   version should help produce and what it deliberately defers, deflects, or
   escalates (legal advice, medical advice, competitor pricing, unsupported
   operations, etc.). The outcome remains non-normative until accepted in the
   Behavior Contract.
3. **Business or conversion goals** — candidate success signals for the core
   scenario (booking link click, form submission, purchase URL, callback
   request). At
   this stage they are non-normative business context, not accepted Agent
   outcomes; reconcile them with customer outcomes and guardrails in the
   Behavior Contract before runtime design.
4. **Hard rules** — anything the agent must never do (never quote a price
   not in the KB, never invent a course slug, etc.).
5. **Tools used** — which tools the agent needs and why (knowledge base,
   web search, request form, call agent, memory, http request, etc.).
6. **Human handoff** — whether the agent may transfer a conversation to a
   person, what should trigger the transfer, and whether an idle timeout is
   needed. Human handoff is separate from Call Agent, which delegates to
   another AI agent.

Known additional scenarios may remain explicitly deferred without being fully
specified. Add one only when it becomes part of the accepted build scope.

Keep the working answers in conversation context until the Behavior Contract is
accepted. Do not create a separate Scope Alignment artifact: the persistent
Behavior Contract owns the accepted core scenario, outcome, material
boundaries, and exclusions; Agent Settings and Eval coverage record how that
scope is implemented and tested. Assign source-of-truth facts to the KB and
operational triggers to Tool or handoff settings rather than duplicating them
in the contract.

### Route through contract and eval design before building

For a query-led customer guidance agent, stop after Scope Alignment and use
[consultative-guidance.md](consultative-guidance.md) to create the accepted
`.codeer/design/behavior_contract.md` for the one core scenario and outcome.
Then use [eval-cases.md](eval-cases.md) to design its small end-to-end acceptance
set locally. These steps happen before KB upload, Agent Settings design, or
Agent creation so intended customer behavior—not the first prompt draft—defines
what the first Agent must satisfy.

Use [query-distribution.md](query-distribution.md) before or after the contract
only when a named demand, weighted portfolio, capacity, hot-path, or drift
decision requires analysis. Keep a one-off result in the current analysis;
create the optional `.codeer/design/query_distribution.csv` and
`.codeer/design/query_examples.csv` artifacts only when the model needs reuse.
Their absence does not block a first core-scenario build.

The cases cannot be applied to the server until the Agent exists. Keep the
reviewed local manifest ready, continue with the KB and Agent steps below, and
return to Eval Case Design after creation to apply the cases using the new
`agent_id`.

---

## Step 2 — Prepare and upload KB

### KB planning decisions (confirm with user)

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

```bash
codeer kb upload \
    --dir kb/ --name "<KB display name>"
```

The CLI prints `kb_id` and `node_ids` to stdout — use these when
constructing the agent payload. Do not persist IDs to a local file;
query the server with `codeer kb list` if you need them later.

Wait for all files to reach READY status before proceeding. Files in
PROCESSING state are not yet available for retrieval.

---

## Step 3 — Create agent

Write `.codeer/current/local_draft_agent.json`. Pull stable normative customer
outcomes and guardrails from the accepted Behavior Contract; use Scope
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
    --payload .codeer/current/local_draft_agent.json
```

`codeer agent apply` always creates a new DRAFT version. The agent is not
live until explicitly published.

After a successful apply, refresh the server cache:

```bash
codeer agent get <agent_id> --full --out .codeer/current/agent.json
```

---

## Step 4 — Publish

Only after all of the following are true:

- [static-audit.md](static-audit.md) has no blockers against the exact version
  to publish;
- the final regression ran all assigned case/evaluator pairs and planned versus
  completed counts reconcile;
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
codeer agent publish --agent <agent_id> --version <version_number>
```
