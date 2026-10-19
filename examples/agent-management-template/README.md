# Agent Development Management

English | [繁體中文](README.zh-TW.md)

Use this folder with the `codeer-agent` skill and Codeer CLI to manage multiple
Agent development projects. Shared collaboration rules live in
[AGENTS.md](AGENTS.md). Each project keeps its own sources, design, settings,
evaluations and verification evidence.

## Set up your management folder

Copy the whole template to your preferred location and choose a name such as
`my-agents/` or `team-agents/`. After copying:

1. Adapt this README's title and introduction to your team or personal use.
   Keep the project index as the entry point.
2. Review `AGENTS.md` for your collaboration language, data retention and team
   rules. Keep the standard filename so coding agents can discover it.
3. Install Codeer CLI 0.1.17 or newer and a compatible `codeer-agent` skill. Use
   PyPI for the CLI by default; follow the selected version's CLI documentation
   if a source installation is needed. Check `codeer init --help` before starting.
   This template contains neither tools nor credentials.
4. Create your first project as needed. Initialize Git separately if you want
   version control.

The initial layout contains only `.gitkeep` under `projects/`:

```text
my-agents/                  # Choose your own management folder name
  README.md                 # English guide and shared project index
  README.zh-TW.md           # Traditional Chinese guide
  AGENTS.md                 # Shared rules for coding agents
  .gitignore                # Default protection for local state and raw data
  projects/                 # Create individual Agent projects as needed
```

The management root holds shared documents and the index. Keep each project's
content under `projects/`, without creating a root-level `project.toml`.
Each `projects/<slug>/` represents one primary Agent; prefer stable, meaningful
lowercase English names separated by hyphens. Local project content should remain
independently movable. Manage shared remote resources through the skill and CLI.

## Document and tool responsibilities

| Entry point | Responsibility |
| --- | --- |
| Management README and AGENTS.md | Navigation, project index and collaboration across projects |
| `codeer-agent` skill | Source analysis, design, evaluation, review, remote workflows and authorization boundaries |
| Codeer CLI | Initialization, structural checks, status and evidence records, platform commands and readback |

Platform commands, acceptance criteria and evidence formats belong to the skill
and CLI documentation for the versions in use. Project paths come from
`project.toml`.

## Add a project

Open a coding agent in the management root and provide the project name, goal
and source location. For example:

```text
Use the codeer-agent skill to create a support Agent development project at
projects/support-agent. The sources are in the folder I specify. Read them,
record the understood design, open questions and next step. Work locally only
for this request.
```

To initialize it yourself, run these commands from the management root, replacing
`support-agent` with your project name. Resume existing work instead of starting
it again:

```bash
codeer init projects/support-agent
cd projects/support-agent
codeer status
codeer validate
```

These commands work offline without an API key and create no remote Agent.
After initialization, add the project's purpose and README link to the
[project index](#project-index). Originals default to the project's `sources/`;
the source index can also record explicitly supplied external locations.
Other content grows as work proceeds; there is no need to complete every template
in advance.

## Project index

No projects have been created yet. Add each project's relative README link and
purpose below. Both language guides use this shared index. Project documents and
CLI evidence determine actual status; keep progress records inside each project.

| Project | Purpose |
| --- | --- |

## Resume work

Specify `projects/<slug>/` and the current goal. The coding agent follows the
skill's continuation workflow, reads existing documents relevant to the task,
then checks `codeer status`, `codeer validate` and supporting evidence. A design
or record that has not yet been produced is not a reason to recreate the project.
`validate` runs local checks; the skill guides semantic review.

These are common default locations. Content appears as work proceeds; existing
projects retain their configured paths and records:

| Location | Responsibility |
| --- | --- |
| `project.toml`, project README | One primary Agent's local configuration and navigation |
| `sources/` | Originals, source index, History and AI Draft exports |
| `design/` | Accepted behavior, pending drafts and acceptance scope |
| `kb/`, `agent/`, `evals/` | Knowledge, Instructions/settings and Case/Tester/Rubric design |
| `reviews/`, `logs/YYYY-MM.md` | Reviews, confirmations, reasons and outcomes; continue an existing `log.md` |
| `runs/`, `releases/` | Recorded evaluation and publication evidence |
| `.codeer/` | Local bindings, sync bases and recovery receipts; keep out of Git |

## Remote operations and data retention

For remote work, follow the skill's connection, binding, import and authorization
workflows. Local organization does not require a remote Agent. Store credentials
in user settings as described by the CLI documentation, outside project files.

The root `.gitignore` excludes personal environment files, `.codeer/` at any depth,
and default raw History, runs and releases under `projects/*/`. These match the
CLI's private-output defaults. Check coverage for custom paths or team sharing;
a file being unignored does not make it suitable for sharing.

`.codeer/` contains recovery information. Do not delete it as cache or assume a
clone restores all operation state. Follow the skill and CLI to select evidence
for controlled sharing.
