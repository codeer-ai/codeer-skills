# codeer-skills

Claude Code skills for building, evaluating, and managing [Codeer](https://codeer.ai) agents.

## Skills

| Skill | Description |
| --- | --- |
| [codeer-agent](codeer-agent/) | Full agent lifecycle — author, knowledge base, eval, publish, post-release analysis — driven over the Codeer API from any directory. Also advises on agent design (tool selection, system prompts, composition patterns). |

## Installation

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

- **[uv](https://docs.astral.sh/uv/)** on PATH — the skills resolve Python dependencies through uv's cache, no manual installs needed.
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
