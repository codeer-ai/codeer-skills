# Codeer Skill Customer Install Guide

This guide helps you set up the Codeer CLI and Codeer Agent Skill for Claude
Code or Codex.

Use this guide if you want Claude Code or Codex to help with the Codeer Agent
lifecycle: planning agents from your files and KB, analyzing production
histories, designing behavior eval cases, debugging failed behaviors, and
showing proposed changes before anything is applied.

## What You Will Install

There are two separate pieces:

1. **Codeer CLI**: the local `codeer` command-line tool. It signs in to Codeer,
   calls the Codeer API, and runs commands such as `codeer agent`,
   `codeer eval`, `codeer history`, and `codeer kb`. CLI 0.1.17 or newer also
   installs and removes Codeer Skills locally without an API key.
2. **Codeer Agent Skill**: the workflow instructions Claude Code or Codex uses
   to understand the Codeer Agent lifecycle: how to plan an agent, prepare KB,
   design behavior cases, analyze production histories, and ask before making
   changes.

The Skill does not include your API key. Keep API keys outside chats, prompts,
and shared project files.

## What You Can Do With This Skill

Use your preferred collaboration language; it can differ from the Agent's customer
language. The builder explains known behavior, concrete gaps and a recommended
next action. Cases combine authoritative facts, real questions and labeled
synthetic/public analogies; other companies' policies do not become yours.
Useful worker perspectives are optional, not required for every change.

A normal test request includes results and initial diagnosis. Missing sources,
retrieval, Instructions, grading and execution gaps need different fixes. You can
request export only or bounded diagnosis. Suggestions grant no new apply/publish
authorization. Existing projects continue with configured files and evidence;
`codeer status --human` and `codeer eval inspect-run --run-id <id>` offer offline
guidance/inspection without reinitialization or bulk migration.
For baseline comparisons, fixed `passed`/`failed`/`stale` runs use a link and
raw-file SHA-256. Other run records may change during export: the builder saves
one original JSON byte snapshot and hash before diagnosis or repair, reusing
verified pins. It does not copy whole run trees or rewrite historical evidence.

- Plan and create an Agent v0 from a folder of KB, product docs, SOPs, or other
  source files.
- Select or design a Tester, verify evidence delivery, then design cases,
  Rubrics and pairs before applying them. Tester means the existing Evaluator/Judge.
- Use failed behavior cases to decide whether to adjust KB, the Agent, retrieval,
  or Standard / Rubric.
- Analyze production histories and negative feedback to find failure patterns
  and coverage gaps.
- Help you start the next iteration with evidence and a preview of proposed
  changes before anything is applied.

## Requirements

- Python 3.11 or newer
- Claude Code or Codex
- A Codeer account with access to the target workspace
- Permission to issue an Admin workspace API key

## 1. Create a Codeer API Key

1. Open your Codeer dashboard.
2. In the left sidebar, open **API Keys**.
3. Click **Issue New Key**.
4. Enter a key name, such as `Claude Code` or `Codex`.
5. Choose **Admin** access.
6. Optionally set an expiration date.
7. Click **Issue Key**.
8. Copy the full API key immediately and store it securely.

The full API key is shown only once. If you close the dialog before saving it,
revoke that key and issue a new one.

Use **Admin** for this setup because the Codeer Agent Skill can create or update
agents, knowledge base resources, and eval resources. **Member** keys are only
for lower-risk chat, read, and list use cases.

## 2. Install the Codeer CLI

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

If your shell cannot find `codeer`, restart the terminal and try again. If it
still cannot find the command, run:

```bash
pipx ensurepath
```

As a fallback, you can install into your user Python environment:

```bash
python -m pip install --user codeer-cli
```

## 3. Configure Codeer CLI Credentials

Create a local CLI profile. The profile name `work` is only an example. You can
choose any name that is easy to recognize, such as `codeer`, `prod`,
`client-a`, or `support-agent`. If you choose a different name, use the same
name in the later `codeer profile use ...` command.

```bash
codeer profile add work
```

The command will ask for the API key. Paste the key you created in Codeer. The
key is not echoed back on screen.

Select the profile:

```bash
codeer profile use work
```

Verify the setup:

```bash
codeer check
```

`codeer check` should confirm authentication, workspace scope, and organization
scope. If you already know the default agent ID for this project, you can also
set it as a non-secret environment variable:

```bash
export CODEER_AGENT_ID=<agent-id>
```

Do not put `CODEER_API_KEY` into `.claude/settings.json`, project `.env` files,
Git commits, or agent chat messages.

## 4. Install the Skill

### Claude Code

Install with Codeer CLI 0.1.17 or newer:

```bash
codeer skill install codeer-agent --target claude
```

The default installation is `~/.claude/skills/codeer-agent`.

### Codex

Install into Codex's user skill directory:

```bash
codeer skill install codeer-agent --target codex
```

The default installation is `~/.agents/skills/codeer-agent`. Add
`--scope project` to either command to install under the current directory
instead. Skill installation does not need a Codeer API key. `--dry-run`
previews the selected source and destination without changing files;
`--ref <tag-or-commit>` selects a revision instead of the default `main`.
The source revision must contain `skills/codeer-agent`.

Check installation status with `codeer skill list`. Restart Codex if the skill
does not appear; in Claude Code, use `/reload-skills` when needed.

Codex's built-in installer remains an alternative:

```text
$skill-installer install https://github.com/codeer-ai/codeer-skills/tree/main/skills/codeer-agent
```

That installation is managed by its original installer, not `codeer skill`.

## 5. Verify the CLI and API Setup

First verify the local CLI and Codeer API credentials:

```bash
codeer check
```

Then list the workspace agents:

```bash
codeer agent list
```

If both commands work, the CLI credentials are ready.

## 6. Verify the Skill

Open Claude Code or Codex in the project where you want to manage the Codeer
agent, then ask:

```text
Please confirm whether the Codeer Agent Skill is loaded. Explain how you can
help me plan an Agent from KB/files, create behavior cases, analyze production
history, and show me proposed changes before applying them.
```

The answer should mention the Codeer Agent lifecycle, Tester/Case/Rubric pairs,
production history, concrete change previews and scoped authorization. Previously
confirmed scope carries forward; publication is separately authorized.

## Local Project Workflow

Describe the Agent you want and provide files or links. For example: “Use these
SOPs to build a support Agent. It can look up orders; staff decide refunds.”
The coding agent reads first, explains what it understands and recommends how
to resolve material gaps. It asks about unclear intent, source conflicts and
new tradeoffs, without asking you to repeat clear instructions. It saves the
design and pending decisions as work proceeds so another conversation can resume.
You do not need to learn internal mode names, fill an Agent design template
or approve a document merely to record an explicit instruction.

The workflow is: understand requirements → design behavior and tests → preview
and apply the authorized Draft changes → read back and audit → evaluate the
specified version → diagnose and repair when needed → publish only with explicit
authorization. The coding agent can operate the commands below for you. An
established design decision does not by itself authorize a remote write.

These commands are implemented in the development source checkout. This change
does not release a new PyPI package. Check `codeer init --help`; until released,
use the [development install](../../codeer-cli/README.md#development-install).

```bash
codeer init ./support-agent
cd support-agent
codeer status
codeer validate
```

These three commands work without credentials or network access. When adopting
an existing Agent, select the correct profile, then run:

```bash
codeer agent bind --alias prod --agent <id>
codeer agent use prod
codeer agent pull --agent <id>
codeer eval pull
codeer agent diff --local
```

The project targets one main Agent; it is not a new remote Project. Original
SOPs/PDFs belong in `sources/documents/`, indexed in `sources/index.md`; curated
KB content belongs in `kb/`. The coding agent keeps established design decisions in
`design/agent-design.md`, pending proposals in
`design/agent-design.draft.md`, and milestone reasons/evidence links in
`logs/YYYY-MM.md` (continue an existing `log.md`). Keep the prompt in `agent/instructions.md`, other settings in
`agent/settings.json`, and stable Tester/Case/Rubric pairs in `evals/design.json`.

These are new-project defaults. Existing projects keep the file selected by
`[paths].design` or legacy `[paths].contract`. Without either setting, an existing
`design/behavior-contract.md` or its draft keeps the old location. If both naming
pairs exist, select the intended source with `[paths].design`. Pending proposals
use the selected file's sibling `<stem>.draft.md`; do not create a second design.
Updating the CLI never moves existing files. Naming changes alone do not stale
evidence; changed design content or other dependencies still need validation.

Use ordinary language; the coding agent selects **build, cases, audit, apply,
eval, improve, publish or observe**. These Skill modes can also be named
explicitly. For example: “Diagnose only this failed
handoff case,” “Apply the already confirmed batch and test it; do not publish,”
or “Use last week's AI Draft feedback to propose test candidates.” Existing
Agents can start with a bounded diagnosis; an imported configuration does not
establish accepted policy or quality.

Project apply requires a current `--dry-run` preview and its `--expect <token>`.
The token identifies content; it does not grant authorization. Local/web
conflicts and unknown outcomes remain visible for reconciliation. Applying a
Draft does not publish it. Runs save exact result IDs under `runs/`; publication
checks current semantic audit, confirmed acceptance scope and a covering passing
run, and saves readback evidence under `releases/`. Missing tool evidence and
old test results cannot establish success. A Judge score alone cannot prove
that an operation occurred.

See the [project contract](../../skills/codeer-agent/reference/project.md) for
formats, legacy-project adoption and API limits. Original History/AI Draft exports
stay private under `sources/history/<collection-id>/`; proposed tests retain
source references and require review before application.

### Portable projects, clone and platform changes

Keep Agent projects in your own repo, e.g. `projects/<stable-name>/`; a root
README can link them and shared AGENTS can record maintenance rules. A new
project init preserves parent files; add `.codeer/` to the repo-root ignore too,
protecting inherited profile selection. New
`project.toml` uses schema 2 without targets/personal profiles. Legacy schema 1
still reads original hashes; explicitly use `agent migrate --alias <name>` to
retain originals and move tracking into a local deployment. Migration does not
renew old evaluation evidence or resolve environment IDs automatically.

After clone, missing `.codeer/` is normal. Reuse explicitly configured environment
variables, nearest parent/project profile or global default. Run `profile current`
and `check`; only missing configuration needs explicit `profile add <name>`
(another platform: `--api-base`), while unselected profiles need `profile use`.
Correct missing/rejected keys at their source; environment overrides remain
effective after profile switching. Interactive add saves secure input with
restricted permissions. No automatic key collection/persistence occurs.
Network/timeouts/5xx mean connection unverified. Permission errors and uncertain
401/403 rejections do not establish expiration.

Explicitly configure a new deployment with `agent bind --alias dev --new`, or
take over with `--agent <id>`. Select with `agent use <alias>` or global
`--deployment <alias>`. Each deployment has its own target/mappings/bases/receipts;
profile names are not identity. Operators coordinate shared production writes;
there is no concurrent-writer guarantee or state handoff package.

Declare required originals/KB selections in `resources.json`. Agent/Case settings
use `attachment:<local-id>` and knowledge tools use `kb:<local-id>[/path]`.
Explicit `env:<VARIABLE>` references supply environment values/credentials at the
HTTP boundary; do not commit credentials. Upload originals with `agent attachment`
and KB with their declared selections; each uses reviewed `--dry-run`/`--expect`.
Keep needed PDFs/attachments in controlled Git/storage. Raw histories and trial
runs/releases stay local; no broad PDF ignore is added to new projects.

Portable imports use resource-export APIs to preserve KB originals, exact saved
text and complete FAQ. `kb import --local-id <id> --kb-id <id>` uses preview/expect
and writes separate originals, FAQ definitions and provenance evidence. After
target KB upload/binding, `kb faq-sync --remote` adopts platform FAQ locally;
`--keep-local` saves a pending proposal, then a separately reviewed `--apply`
rebuilds it. Existing FAQ need explicit ID mappings; target text must match before
ranges are recreated. Unknown creates block retry; an investigated ID can recover
the recorded operation even if a newer local proposal removed it. Reconcile does
not accept unrelated platform changes: they require a fresh comparison and choice.
Partial KB imports retain available files and record each unavailable resource;
declared FAQ/manifests must be present for validation and delivery.
Website crawl settings are
excluded and recorded as a gap. Missing APIs/originals remain gaps; text or source
URLs do not substitute for verified originals. See the
[KB/FAQ workflow](../../skills/codeer-agent/reference/project.md#portable-kb-text-originals-and-faq).

For platform edits, pull observations, then use `agent adopt --resource agent
--fields description --remote --dry-run` and repeat the reviewed command with
`--expect <token>`. `--keep-local` preserves the proposal as pending apply; map
Case/Tester/pairs by explicit IDs, never names. `kb bind` maps source files to
node IDs and can adopt text snapshots. Aligned, pending_apply and undecided fields
remain distinct. Adoption writes no platform resources; unresolved fields block
the entire replacement payload. Local/remote changes invalidate the preview.
Unknown operations must reconcile first; another deployment is never pushed.
Existing attachment takeover uses `agent attachment --local-id <id> --remote-id
<uuid>` with preview/expect and matching downloaded bytes, without upload.
Genuinely new attachments/KB after deployment or takeover require explicit `--new`.

Release receipts use unique flat JSON names, retaining pending/unknown/readback
states; legacy release directories remain readable. For formal controlled sharing,
run `eval delivery --run-id <id> --release-id <id> --out-dir <fresh-directory>` and
`eval delivery --verify <directory>`. It preserves exact result IDs, target/content
fingerprints and necessary audit/result/trace/release evidence. Missing files
remain incomplete; a summary is insufficient. It excludes `.codeer/` and other
trials. Verification proves offline integrity/identity, not live platform status.

Without original local files, import is a current-state project: attachments may
be downloaded and checked, but expired/unavailable originals remain gaps. KB
export is Markdown, not original PDF bytes. Design rationale/confirmed requirements
and previous local history cannot be reconstructed. Sub-Agent references stay
read-only and block project deployment. These imports are not complete backups,
accepted policy or validated quality; existing KB content has no in-place
replacement API.

## 7. What To Do Next

If you do not have an agent yet, point Claude Code or Codex at your KB folder,
product docs, SOPs, or source files and ask it to discuss what Agent v0 should
be built.

If you have an agent but no behavior cases yet, ask it to select/design a Tester,
verify available evidence, and propose Case/Rubric pairs before applying them.

If you have behavior cases but some are failing, ask it to analyze whether the
fix belongs in the KB, the Agent instructions, retrieval, or the Standard /
Rubric.

If the agent is already in production, ask it to analyze production histories
and negative feedback to find patterns and coverage gaps.

If you are preparing the next version, ask it to propose changes and show a
preview. Authorization for the same reviewed batch carries forward; material new
decisions require confirmation, and publication requires separate authorization.

## Common Issues

### `codeer` Command Not Found

The CLI installed, but your shell cannot find the executable. Run:

```bash
pipx ensurepath
```

Then restart the terminal. If you used the fallback pip install, make sure your
Python user scripts directory is on `PATH`.

### `codeer check` Shows 401 or 403

401/403 alone does not identify expiration or distinguish rejected credentials
from insufficient access. Inspect the selected source, API/workspace and
permissions. If the key is confirmed invalid, explicitly update its profile with
`codeer profile add <name>`, then check again. If `CODEER_API_KEY` or
`CODEER_API_BASE` overrides the profile, correct/remove that variable; profile
switching alone cannot repair it. Network/timeouts/5xx mean unverified connection,
so keep existing credentials while checking the service.

```bash
codeer profile current
codeer check
```

### The Wrong Workspace Appears

Verify the API base and effective key's workspace. Correct environment overrides
or select a profile with the intended workspace key, then check. Never rebind a
deployment automatically:

```bash
codeer profile use <profile-name>
codeer check
```

### The Agent Is Not Found

If you set `CODEER_AGENT_ID`, make sure that agent belongs to the same workspace
as the API key. You can unset the default and list available agents:

```bash
unset CODEER_AGENT_ID
codeer agent list
```

### The API Key Was Lost

Codeer only shows the full key once. Revoke the lost key in **API Keys**, then
issue a new Admin key and update your CLI profile.

## Maintenance

Upgrade the CLI:

```bash
pipx upgrade codeer-cli
codeer check
```

Run install again to update an unchanged CLI-managed Skill. Preview with
`--dry-run`, then install the default `main` revision or choose `--ref`.
Use `--target claude` for Claude Code or `--target codex` for Codex, and keep
the same `--scope` used during installation:

```bash
codeer skill install codeer-agent --target claude --dry-run
codeer skill install codeer-agent --target claude
codeer skill install codeer-agent --target claude --ref <tag-or-commit>
```

Identical contents are left unchanged. Updates validate the full new package
before replacing the old copy, remove obsolete files, and restore the old copy
if publication fails. If restoration also fails, the error reports the retained
backup's location. Modified, manually installed, or symlinked directories are
never overwritten or removed; preserve custom files and resolve them manually.

Remove an unchanged CLI-managed Skill separately:

```bash
codeer skill uninstall codeer-agent --target claude --dry-run
codeer skill uninstall codeer-agent --target claude
```

Removing the CLI does not remove Skills.

### Regenerate the Traditional Chinese PDF

The Markdown guide is the editable source. The checked-in builder uses ReportLab,
matching the existing PDF producer, and preserves its screenshots:

```bash
python build_pdf.py --font /path/to/traditional-chinese.ttf
```

Run from this directory in an environment with `reportlab`. On macOS the default
font is Arial Unicode. Render the resulting PDF with `pdftoppm` and inspect every
page before delivery; text extraction alone does not verify layout.

Remove the CLI:

```bash
pipx uninstall codeer-cli
```
