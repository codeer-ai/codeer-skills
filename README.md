# codeer-skills

Codex/Claude skills for building, evaluating, and managing [Codeer](https://codeer.ai) agents.

## Skills

| Skill | Description |
| --- | --- |
| [codeer-agent](skills/codeer-agent/) | Full agent lifecycle — author, knowledge base, eval, publish, post-release analysis — driven over the Codeer API from any directory. Also advises on agent design (tool selection, system prompts, composition patterns). |
| [codeer-audience-value-narrative](skills/codeer-audience-value-narrative/) | Shape audience-first Codeer narratives across decks, demos, landing pages, and substantive proposals. |
| [codeer-presentations](skills/codeer-presentations/) | Build and review prospect-facing Codeer sales and investor decks using the approved narrative and visual system. |

## Installation

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
- If a project has one default agent, provide `CODEER_AGENT_ID` as a
  non-secret environment variable.

## Prerequisites

- **Codeer CLI** — installed from PyPI or from `codeer-cli/` in editable mode
  during development.
- **Codeer session credentials** — required for Codeer API operations;
  configure them outside the skill workspace so `codeer check` succeeds.
  Local Skill installation and removal do not require these credentials.

## Repo structure

```
codeer-skills/
├── codeer-cli/               ← standalone CLI package
├── skills/
│   ├── codeer-audience-value-narrative/
│   │   ├── SKILL.md          ← cross-format audience-value contract and checks
│   │   └── references/       ← examples and regression fixtures
│   ├── codeer-presentations/
│   │   ├── SKILL.md          ← Codeer deck workflow and narrative adapter
│   │   └── references/       ← visual, layout, copy, and QA contracts
│   └── codeer-agent/
│       ├── SKILL.md          ← orientation, setup, lifecycle walkthrough
│       ├── onboarding.md     ← auth and environment setup
│       ├── modules/          ← lifecycle workflows
│       └── reference/        ← concepts, commands, errors
└── docs/
    └── customer-install/
        ├── README.md                 ← customer setup guide
        ├── customer-install-zh-TW.md ← editable Traditional Chinese guide
        ├── customer-install-zh-TW.pdf
        └── assets/                   ← screenshots used by the guide
```
