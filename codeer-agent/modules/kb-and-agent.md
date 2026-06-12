# KB & Agent Setup

From scope alignment through KB upload and agent creation.

---

## Diff rule

**Before applying any agent changes** (create or update via `codeer agent apply`),
present the full diff to the user and wait for approval. Never apply agent
changes silently — the user must see what is being changed.

Use `codeer agent diff` to show differences between versions when updating
an existing agent.

---

## Step 1 — Scope alignment

**Do this before any KB or agent work.** Pin down five things with the user:

1. **In-scope categories** — 3–6 concrete usage scenarios the agent must
   handle (e.g. "B2C consultation routing", "course recommendation",
   "enterprise intake", "card product Q&A").
2. **Out-of-scope** — what to deflect or escalate (legal advice, medical,
   competitor pricing, sensitive personal data, etc.).
3. **Conversion goals** — what counts as a successful outcome per category
   (booking link click, form submission, purchase URL, callback request).
4. **Hard rules** — anything the agent must never do (never quote a price
   not in the KB, never invent a course slug, etc.).
5. **Tools used** — which tools the agent needs and why (knowledge base,
   web search, request form, call agent, memory, http request, etc.).

Keep the answers in conversation context — they feed directly into the
system prompt (allowed outcomes + boundaries), KB content scope, and eval
case design. Do not persist scope as a file; once the agent is on the
server, scope is captured in eval case coverage.

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

Write `.codeer/current/local_draft_agent.json`. Pull allowed outcomes and
boundaries from the scope alignment discussion; attach KB node IDs from
`codeer kb list` output.

Discuss with the user:

- System prompt content (boundaries, behavior rules, response style)
- Tool selection and configuration (especially `invocation_instruction` /
  "When to Use" for each tool — this controls when the agent invokes it)
- LLM model choice

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

Only after eval debugging is complete and the user gives explicit go-ahead.

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
