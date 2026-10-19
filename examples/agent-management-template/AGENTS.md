# Agent Development Collaboration Rules

This file covers management of multiple Agent projects. Start with the root
[README.md](README.md) ([Traditional Chinese](README.zh-TW.md)), then read the
target project's existing README, AGENTS.md and records relevant to the task.
Use the user's preferred working language. Choose the languages of project
documents, settings and the deployed Agent's customer-facing responses according
to each project's requirements.

## Scope and tools

- The management root holds shared rules and the project index. It is not an
  Agent project: do not run `codeer init`, create `project.toml`, or place an
  individual project's design or settings there.
- Each `projects/<slug>/` represents one primary Agent. Prefer stable, meaningful
  lowercase English names separated by hyphens. Keep existing directory names;
  do not rename projects merely to change their order.
- Establish the user's target project and task before acting; do not guess among
  multiple projects. Initialize only when asked to create an Agent development
  project. Creating a management folder does not imply creating an Agent.
- Use the installed `codeer-agent` skill or the checkout specified by the user.
  Read its SKILL.md, then the modules relevant to the task. The skill defines
  source analysis, design, evaluation, review and authorization workflows. The
  CLI performs initialization, structural checks, status and platform operations.
  Keep these contracts in their owning skill and CLI documentation.
- If the skill is unavailable or the CLI lacks a required command, explain the
  specific gap and consult the selected version's documentation. Do not invent
  commands or silently switch tool versions.
- Each project's local content should remain independently movable, without
  directly depending on another project's settings or local state. Manage shared
  remote resources through the skill and CLI; a new project does not automatically
  copy them.

## Create and resume

1. Inspect the destination, existing changes and relevant content before editing.
   Preserve originals and user-authored work.
2. Create a project with `codeer init projects/<slug>`. If the directory already
   contains work, inspect its purpose first. Initialization needs no credentials
   and creates no remote Agent. Run subsequent CLI commands from that project.
3. To resume, follow the skill: read existing documents relevant to the task and
   check `codeer status`, `codeer validate` and the supporting evidence. Use the
   paths in `project.toml` and existing records. Do not move files, recreate work
   or introduce a second source of truth merely to match the template.
4. When adding a project, add its purpose and README link to the root
   [project index](README.md#project-index), preserving other entries. Keep
   progress, business rules and operation results inside the project.

## Git and data preservation

- Initialize Git, commit, push and change repository settings only as requested
  by the user. These are not implicit steps in creating an Agent development
  project. Add files using explicit paths.
- Preserve CLI-generated ignore rules and check their coverage for custom paths.
  Before committing, inspect customer originals, conversations and settings for
  sensitive content. A file being unignored does not make it suitable for sharing.
- Store credentials as described by the CLI documentation, outside project files
  and chats. Keep `.codeer/` out of Git; it contains recovery information and is
  not disposable cache. Follow the skill and CLI for cleanup and evidence retention.
- Review the diff and perform the smallest meaningful validation after changes.
  Distinguish completed work from outcomes that remain unverified.
