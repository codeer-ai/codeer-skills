# codeer-skills

Codex/Claude skills for building, evaluating, and managing [Codeer](https://codeer.ai) agents.

## Skills

| Skill | Description |
| --- | --- |
| [codeer-agent](codeer-agent/) | Full agent lifecycle — author, knowledge base, eval, publish, post-release analysis — driven over the Codeer API from any directory. Also advises on agent design (tool selection, system prompts, composition patterns). |

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

### Claude Code

Install the Codeer Agent skill from the public GitHub folder URL:

```bash
claude install-skill https://github.com/codeer-ai/codeer-skills/tree/main/codeer-agent
```

Use the `codeer-agent` folder URL, not the repository root.

### Codex

Install the Codeer Agent skill through Codex's built-in skill installer:

```text
$skill-installer install https://github.com/codeer-ai/codeer-skills/tree/main/codeer-agent
```

Restart Codex if the skill does not appear after installation.

### CLI development

For CLI development, use an editable install from `codeer-cli/`:

```bash
cd /path/to/codeer-skills/codeer-cli
uv tool install --editable .
```

### Claude Cowork

Cowork should provide an installed `codeer` binary plus credentials from the
Codeer CLI profile or an external CLI credential store. Do not place
API keys in the skill workspace.

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

For platform debugging or PR preview work, the CLI also provides an explicit
raw session-cookie mode. It is opt-in and does not affect `codeer check`,
`codeer agent`, `codeer kb`, `codeer eval`, or `codeer history`:

```bash
codeer api --env-file session.env get /accounts/me
codeer api --env-file preview_session.env get /accounts/me
```

See [codeer-agent/PREVIEW_ENV.md](codeer-agent/PREVIEW_ENV.md) for preview
domain and credential details.

## Prerequisites

- **Codeer CLI** — installed from PyPI or from `codeer-cli/` in editable mode
  during development.
- **Codeer session credentials** — configured outside the skill workspace so
  `codeer check` succeeds.

## Repo structure

```
codeer-skills/
├── codeer-cli/               ← standalone CLI package
├── codeer-agent/
│   ├── SKILL.md              ← orientation, setup, lifecycle walkthrough
│   ├── onboarding.md         ← auth and environment setup
│   ├── modules/              ← lifecycle workflows
│   └── reference/            ← concepts, commands, errors
└── docs/
    └── customer-install/
        ├── README.md                 ← customer setup guide
        ├── customer-install-zh-TW.md ← editable Traditional Chinese guide
        ├── customer-install-zh-TW.pdf
        └── assets/                   ← screenshots used by the guide
```
