# codeer-skills

Codex/Claude skills for building, evaluating, and managing [Codeer](https://codeer.ai) agents.

## Skills

| Skill | Description |
| --- | --- |
| [codeer-agent](skills/codeer-agent/) | Full agent lifecycle — author, knowledge base, eval, publish, post-release analysis — driven over the Codeer API from any directory. Also advises on agent design (tool selection, system prompts, composition patterns). |
| [codeer-audience-value-narrative](skills/codeer-audience-value-narrative/) | Shape audience-first Codeer narratives across decks, demos, landing pages, and substantive proposals. |
| [codeer-presentations](skills/codeer-presentations/) | Build and review prospect-facing Codeer sales and investor decks using the approved narrative and visual system. |

## Installation

The local Agent project workflow described below is implemented in this source
checkout and has not been released by this change. Use the development install
for these commands; installing the current PyPI package does not establish that
it contains them.

For customer-facing setup docs, see
[docs/customer-install/](docs/customer-install/).

Install and authenticate the CLI separately from the skill:

```bash
pipx install codeer-cli
codeer profile add work
codeer profile use work
codeer check
```

If `pipx` is not installed, run `python -m pip install --user pipx` followed by
`python -m pipx ensurepath`, then restart the terminal.

The CLI is intentionally separate from the skill so credentials and runtime
dependencies are maintained outside the LLM-readable skill package.

### Install skills with the CLI

Skill management requires Codeer CLI 0.1.17 or newer. List the three available
skills and their local installation status without a Codeer API key:

```bash
codeer skill list
codeer skill install codeer-agent --target codex
# Or, for Claude Code:
codeer skill install codeer-agent --target claude
```

The default `--scope user` installs into `~/.agents/skills/` for Codex or
`~/.claude/skills/` for Claude Code. Use `--scope project` to install into
`.agents/skills/` or `.claude/skills/` under the current directory. The repository's
`skills/` directory contains source packages; it is not itself an auto-discovery
location. These local installs target Codex and Claude Code, not Cowork accounts.

Install the other skills when preparing audience-facing materials:

```bash
codeer skill install codeer-audience-value-narrative --target codex
codeer skill install codeer-presentations --target codex
```

Install downloads only the selected skill from this public repository, defaults
to `--ref main`, and records the resolved commit and file hashes. Use
`--ref <tag-or-commit>` for a reproducible revision. `--dry-run` downloads and
validates the source without changing installation files. Identical contents
are a no-op. If the source has changed, install updates an unchanged CLI-managed
copy, including removing obsolete files. Modified, manually installed, or
symlinked directories are refused; preserve custom work and resolve it manually.
Updates prepare the complete new package before replacing the old directory,
retain a backup during replacement, and restore it if publication fails. If
restoration also fails, the error reports the retained backup's recovery path.

To preview an update, install the desired revision, or remove the skill:

```bash
codeer skill install codeer-agent --target codex --dry-run
codeer skill install codeer-agent --target codex --ref <tag-or-commit>
codeer skill uninstall codeer-agent --target codex --dry-run
codeer skill uninstall codeer-agent --target codex
```

Uninstall checks the installation receipt and all file hashes, and leaves other
skills untouched. It also refuses symlinked installation paths. Local skill
management does not need API credentials; Codeer server operations still do.

### Native Codex installer

You can also use Codex's built-in installer with the skill's GitHub folder URL:

```text
$skill-installer install https://github.com/codeer-ai/codeer-skills/tree/main/skills/codeer-agent
```

Installations made by another installer remain unmanaged by `codeer skill`.
If Codex does not discover a newly installed skill, restart it. For Claude Code,
use `/reload-skills` if the destination skills directory was newly created.

### CLI development

Portable Agent projects preserve KB originals, exact saved text and complete FAQ
through resource-export APIs, then rebuild FAQ after target text verification.
Website crawl settings remain an explicit gap. See the
[KB/FAQ workflow](skills/codeer-agent/reference/project.md#portable-kb-text-originals-and-faq)
for API availability, ID mapping, integrity and recovery boundaries.

For CLI development, use an editable install from `codeer-cli/`:

```bash
cd /path/to/codeer-skills/codeer-cli
uv tool install --editable .
```

### Claude Cowork

Cowork should provide an installed `codeer` binary plus credentials from the
Codeer CLI profile or an external CLI credential store. Do not place
`session.env`, `.env`, or API keys in the skill workspace.

```bash
codeer check
```

Make sure:

- Code execution and file creation are enabled for Claude/Cowork.
- The external `codeer` CLI is installed and `codeer check` passes.
- Workspace and organization scope resolve from the workspace API-key virtual
  user's profile. The CLI does not use `CODEER_WORKSPACE_ID`,
  `CODEER_ORGANIZATION_ID`, `--workspace`, or `--org`.
- Bind the main Agent in `project.toml`; outside a project, `CODEER_AGENT_ID`
  remains an optional non-secret default.

## Local Agent development

The skill carries [platform basics](skills/codeer-agent/reference/platform-basics.md)
and [collaboration guidance](skills/codeer-agent/reference/collaboration.md).
It explains established behavior, concrete gaps, a recommendation and the next
completion condition in your working language. A normal Eval request includes
results and initial diagnosis; export-only requests remain bounded. Missing
policy, curation, retrieval, response and grading/execution problems need
different fixes.

Projects share navigation and editing responsibilities; KB structure and extra
analysis may differ. Material batches use one main report under
`reviews/batches/<batch-id>/`; unchanged checks do not produce more reports.
Existing projects need no reinitialization or bulk migration. Configured paths,
legacy reviews/logs and historical evidence remain readable and untouched.
Baseline evidence links include the raw-file SHA-256. Runs outside `passed`,
`failed` or `stale` may still be updated by export: save one original JSON byte
snapshot before diagnosis or repair, and reuse verified pins. See the
[batch evidence rules](skills/codeer-agent/reference/project.md#batch-reviews-and-project-entry).

```bash
codeer status --human                  # Optional readable offline guidance
codeer eval inspect-run --run-id <id>  # Read-only saved-evidence interpretation
```

Default status JSON is unchanged. Inspection does not rewrite, accept or rerun
old results. See [batch evidence](skills/codeer-agent/reference/project.md#batch-reviews-and-project-entry).

Tell the coding agent your goals and provide source files or links. It reads
the material, summarizes intended behavior, recommends how to resolve gaps and
asks only questions that change the design. It maintains the design basis and
pending decisions for you, including before discovery is complete. You need not
learn “Agent design,” fill a template or approve a clear instruction again
just to record it. The commands below support that workflow.

On continuation, it identifies established progress, the missing prerequisite,
the next action and its completion condition from project artifacts and evidence.
Case drafts can retain unknown capabilities; only admitted pairs enter the
configured Eval manifest. `codeer status` gives offline advice with grouped
contract gaps (`--full` for details); `validate` separates structural errors,
incomplete design, unverified evidence contracts and unfinished operations.
Execution errors lead to dependency diagnosis before quality judgments. Existing
acceptance scope and apply/run/publication gates remain in force.

```bash
codeer init ./support-agent
cd support-agent
codeer status
codeer validate
# When adopting an existing Agent (requires credentials):
codeer agent bind prod-customer-a-main --agent <id>
codeer agent use prod-customer-a-main
codeer agent pull --agent <id>
codeer eval pull
```

Each local project describes one Agent design with independent remote Agent bindings,
including several Agents in the same workspace or different workspaces/APIs.
Current schema 2 keeps targets/profile outside committed content. Unsupported
projects require reviewed one-time preparation; old evidence stays read-only,
while conforming data needs zero conversion. The layout grows as
work proceeds; `codeer init` creates only the initial scaffold. Paths can be
configured in `project.toml` to adopt existing files.

`agent bindings` lists saved API/workspace/Agent identities; global `--binding`
and single-invocation `--profile` choose the mapping and connection independently.
Shared Tester/KB changes require impact review; candidate separation uses
`eval tester-fork` or `kb upload --fork`, followed by appropriate reference readback.
Use `clean --dry-run`/`--expect` for completed, unreferenced machine history; preserve
unknown operations and fixed evidence. See the [binding, recovery and cleanup contract](skills/codeer-agent/reference/project.md#remote-agent-bindings-clone-and-platform-adoption).

```bash
support-agent/
├── project.toml                   # Portable project identity and paths
├── resources.json                 # Attachment originals and KB selections, when needed
├── README.md                      # Project usage and entry points
├── logs/YYYY-MM.md                # Important decisions and outcomes; old log.md continues
├── sources/
│   ├── index.md                   # Source paths, URLs and provenance
│   ├── documents/                 # Original SOPs, PDFs and customer files
│   └── history/                   # Raw conversations and AI Draft exports
├── kb/                            # Curated content prepared for upload
├── design/
│   ├── agent-design.md            # Established Agent design decisions
│   ├── agent-design.draft.md      # Pending design proposals
│   ├── acceptance.md              # Delivery scope and criteria
│   └── acceptance.json            # Confirmed evaluation scope
├── agent/
│   ├── instructions.md            # Sole editable prompt authority
│   └── settings.json              # Other Agent settings
├── evals/
│   └── design.json                # Stable Cases, Testers, Rubrics and evidence
├── reviews/                       # Audits, proposals and confirmations
├── runs/                          # Evaluation snapshots and results, per run
├── releases/                      # Unique flat JSON receipts; legacy directories also read
└── .codeer/deployments/<alias>/    # Local target, mappings, bases and receipts
```

These are new-project defaults. Existing projects keep their configured design
path (`[paths].design`, or legacy `[paths].contract`) and sibling `.draft.md`.
Without an explicit setting, an existing `design/behavior-contract.md` or its
draft keeps the old pair in use. If both naming pairs exist, select the intended
source with `[paths].design`; do not create a second design authority.

The detailed project format lives in
[`skills/codeer-agent/reference/project.md`](skills/codeer-agent/reference/project.md).
It defines file responsibilities, synchronization, evaluation evidence and
publication checks for all local projects. Keep project-specific usage and
context in each project's own `README.md`.

Keep Agent projects in your own repository, e.g. `projects/<stable-name>/`;
root README/AGENTS can provide shared guidance. `.codeer/`, raw histories and
trial runs/releases stay local. Required PDF/attachment/KB originals remain
eligible for controlled Git storage. Clone requires connection setup and explicit
resource mapping/adoption. Add `.codeer/` to the repo-root ignore for inherited
profile selection; project init preserves parent files. Clone
does not import deployment state or old local
history. Platform changes use `agent adopt`, preserving aligned/pending/undecided
fields. `eval delivery` exports/verifies selected formal evidence. Read the
project contract for logical references, unavailable original bytes, unsupported
Sub-Agent project deployment, KB replacement limits and coordinated writes.

Use ordinary requests such as “Build a support Agent from this SOP” or “Diagnose
only this failed handoff.” The builder selects **build, cases, audit, apply,
eval, improve, publish, or observe**; these internal skill modes are also available
as explicit entry points, not CLI subcommands. Existing Agents
can enter at a bounded audit or repair. Import means unvalidated current state;
it does not accept business policy. Draft apply, focused tests, covering
regression and publication are separate operations. Existing authorization
carries forward for its reviewed scope; publication needs explicit authorization.

See [CLI usage](codeer-cli/README.md#local-agent-projects) and
[reproducible synthetic journeys](examples/agent-workflow/README.md).
To create your own Agent development management folder, copy the
[Agent management template](examples/agent-management-template/README.md).
It provides shared coding-agent rules, a usage guide, an empty project index and
Git ignore defaults. Keep `AGENTS.md` and `README.md` as the standard entry points;
choose your own folder name and customize the documents for your team.

From this checkout's root, for example:

```bash
cp -R examples/agent-management-template ../my-agents
```

Choose a new destination that does not already exist. After copying, open that
folder and follow its README to initialize individual projects under `projects/`.

## Prerequisites

- **Codeer CLI** — installed from PyPI or from `codeer-cli/` in editable mode
  during development.
- **Codeer session credentials** — required for Codeer API operations;
  configure them outside the skill workspace so `codeer check` succeeds.
  Local Skill installation and removal do not require these credentials.

## Repo structure

```bash
codeer-skills/
├── codeer-cli/               # standalone CLI package
├── examples/
│   ├── agent-management-template/ # starter for your own Agent management folder
│   └── agent-workflow/       # synthetic CLI and skill scenarios
├── skills/
│   ├── codeer-audience-value-narrative/
│   │   ├── SKILL.md          # cross-format audience-value contract and checks
│   │   └── references/       # examples and regression fixtures
│   ├── codeer-presentations/
│   │   ├── SKILL.md          # Codeer deck workflow and narrative adapter
│   │   └── references/       # visual, layout, copy, and QA contracts
│   └── codeer-agent/
│       ├── SKILL.md          # eight-mode routing and shared boundaries
│       ├── onboarding.md     # auth and environment setup
│       ├── modules/          # lifecycle workflows
│       ├── workflows/        # cross-module journeys
│       └── reference/        # project contract, concepts, commands, errors
└── docs/
    └── customer-install/
        ├── README.md                 # customer setup guide
        ├── customer-install-zh-TW.md # editable Traditional Chinese guide
        ├── customer-install-zh-TW.pdf
        └── assets/                   # screenshots used by the guide
```
