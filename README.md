# codeer-skills

Claude skills for building, evaluating, and managing [Codeer](https://codeer.ai) agents.

## Skills

| Skill | Description |
| --- | --- |
| [codeer-agent](codeer-agent/) | Full agent lifecycle — author, knowledge base, eval, publish, post-release analysis — driven over the Codeer API from any directory. Also advises on agent design (tool selection, system prompts, composition patterns). |

## Installation

### Claude Cowork

To use this skill in Claude Cowork, package the skill folder itself and upload
it in Claude:

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
- `~/.codeer/session.env` exists on the computer where Cowork is running.
- The relevant project provides `CODEER_WORKSPACE_ID` and
  `CODEER_ORGANIZATION_ID`. In Claude Code this is usually done with
  `.claude/settings.json`; in Cowork, provide those values in the working
  project context or ask Cowork to use them before running Codeer API actions.

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

- **Python 3 with venv support** — skill wrappers create and reuse their own
  virtualenv under `${TMPDIR:-/tmp}/codeer-skills/`.
- **Codeer session credentials** in `~/.codeer/session.env` — see each skill's `SKILL.md` for setup details.

## Repo structure

```
codeer-skills/
└── codeer-agent/
    ├── SKILL.md              ← orientation, setup, lifecycle walkthrough
    ├── DESIGN_GUIDE.md       ← agent design advice (tools, prompts, patterns)
    ├── API_CHEATSHEET.md     ← endpoint reference + gotchas
    ├── examples/             ← reusable JSON payloads
    └── scripts/              ← CLI wrapper + reusable Python scripts
```
