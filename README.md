# codeer-skills

Claude Code skills for building, evaluating, and managing [Codeer](https://codeer.ai) agents.

## Skills

| Skill | Description |
| --- | --- |
| [codeer-agent](codeer-agent/) | Full agent lifecycle — author, knowledge base, eval, publish, post-release analysis — driven over the Codeer API from any directory. Also advises on agent design (tool selection, system prompts, composition patterns). |

## Installation

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

### Claude Cowork

1. Mount this repo as a **workspace folder** in Cowork (select the
   `codeer-skills/` directory).
2. Create `session.env` at the repo root (`codeer-skills/session.env`):
   ```
   CODEER_API_BASE=https://api.codeer.ai
   CODEER_SESSION_ID=<from browser devtools>
   CODEER_CSRF_TOKEN=<from browser devtools>
   ```
3. The skill scripts auto-detect `session.env` from the repo root — no
   manual `export` needed.
4. In Cowork, use the sandbox bash tool with absolute paths to invoke
   scripts. Example:
   ```bash
   /sessions/<id>/mnt/codeer-skills/codeer-agent/scripts/codeer get /accounts/me
   ```

## Prerequisites

- **[uv](https://docs.astral.sh/uv/)** on PATH — the skills resolve Python dependencies through uv's cache, no manual installs needed. (Cowork's sandbox has `uv` pre-installed.)
- **Codeer session credentials** — in `~/.codeer/session.env` (Claude Code) or `<repo-root>/session.env` (Cowork). See each skill's `SKILL.md` for setup details.

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
