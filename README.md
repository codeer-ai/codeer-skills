# codeer-skills

Codex/Claude skills for building, evaluating, and managing [Codeer](https://codeer.ai) agents.

## Skills

| Skill | Description |
| --- | --- |
| [codeer-agent](codeer-agent/) | Full agent lifecycle — author, knowledge base, eval, publish, post-release analysis — driven over the Codeer API from any directory. Also advises on agent design (tool selection, system prompts, composition patterns). |

## Installation

Install and authenticate the CLI separately from the skill. After the CLI is
published to PyPI, install it as an isolated command line tool:

```bash
uv tool install codeer-cli
codeer profile add work
codeer profile use work
codeer check
```

Until the package is published, install directly from this repository:

```bash
uv tool install 'git+https://github.com/<org>/codeer-skills.git#subdirectory=codeer-cli'
codeer check
```

The CLI is intentionally separate from the skill so credentials and runtime
dependencies are maintained outside the LLM-readable skill package.

For CLI development, use an editable install from `codeer-cli/`:

```bash
cd /path/to/codeer-skills/codeer-cli
uv tool install --editable .
```

### Claude Cowork

Cowork should provide an installed `codeer` binary plus credentials from the
runtime environment or an external CLI credential store. Do not place
`session.env` or `.env` files in the skill workspace.

```bash
codeer check
```

Package the skill folder itself:

```bash
zip -r codeer-agent.zip codeer-agent
```

Then open Cowork and go to **Customize > Skills**. Click the **+** button,
choose **Create skill**, select **Upload a skill**, and upload
`codeer-agent.zip`.

For Team or Enterprise accounts, you can also share the uploaded skill with
specific colleagues or publish it to your organization's skill directory if
skill sharing is enabled by an owner.

After uploading, make sure:

- Code execution and file creation are enabled for Claude/Cowork.
- The external `codeer` CLI is installed and `codeer check` passes.
- Workspace and organization scope resolve from the workspace API-key virtual
  user's profile. The CLI does not use `CODEER_WORKSPACE_ID`,
  `CODEER_ORGANIZATION_ID`, `--workspace`, or `--org`.
- If a project has one default agent, provide `CODEER_AGENT_ID` as a
  non-secret environment variable.

### Claude Code

Install a skill into Claude Code by running:

```bash
claude install-skill /path/to/codeer-skills/<skill-name>
```

Or, if this repo is hosted on GitHub:

```bash
claude install-skill https://github.com/anthropics/codeer-skills/tree/main/<skill-name>
```

Once installed, Claude Code will automatically invoke the skill when your request matches its trigger phrases. You can also invoke it explicitly with `/<skill-name>`.

## Prerequisites

- **Codeer CLI** — installed from PyPI, from the repository subdirectory, or
  from `codeer-cli/` in editable mode during development.
- **Codeer session credentials** — configured outside the skill workspace so
  `codeer check` succeeds.

## Repo structure

```
codeer-skills/
├── codeer-cli/               ← standalone CLI package
└── codeer-agent/
    ├── SKILL.md              ← orientation, setup, lifecycle walkthrough
    ├── onboarding.md         ← auth and environment setup
    ├── modules/              ← lifecycle workflows
    └── reference/            ← concepts, commands, errors
```
