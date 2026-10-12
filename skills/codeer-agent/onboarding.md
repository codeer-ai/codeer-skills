# Codeer Agent Onboarding

The Codeer Agent Skill works through the installed `codeer` CLI. Install the
CLI, store the Codeer API key in a local CLI profile, then install this skill in
Codex or Claude Code.

Keep API keys outside the repo and outside agent chat. Do not paste API keys
into Codex, Claude Code, `.claude/settings.json`, project `.env` files, or Git
commits.

## Recommended setup

Start by telling the coding agent what you want and where the source material
is, for example: “Use these SOPs to build a support Agent; it may look up orders
but refund decisions belong to staff.” The builder reads the material, explains
its understanding and asks only material unresolved questions. It maintains
the design and pending decisions for you; you do not need to learn mode names,
fill an Agent design template or reapprove a clear instruction to save it.
Commands below can be run by the coding agent as part of that work.

Project commands below are available in the development source checkout. This
change does not release them to PyPI; verify `codeer init --help` on the installed
CLI and use the repository's development install if unavailable.

You can first run `codeer init <customer-directory>`, `codeer status` and
`codeer validate` without credentials. Put original SOP/PDF files in
`sources/documents/` and list paths or external URLs in `sources/index.md`.
Read [project mechanics](reference/project.md) for the file contract and existing
Agent adoption. Select a profile only when server reads/writes are needed.

Install the CLI from PyPI with `pipx`:

```bash
pipx install codeer-cli
```

If `pipx` is not installed:

```bash
python -m pip install --user pipx
python -m pipx ensurepath
```

Then restart the terminal and run `pipx install codeer-cli` again.

Create a named CLI profile. The profile stores the selected profile name in the
project and keeps the API key in the user-level Codeer CLI config. The name
`work` is only an example; users can choose any recognizable name, such as
`codeer`, `prod`, `client-a`, or `support-agent`:

```bash
codeer profile add work
codeer profile use work
codeer check
```

`codeer profile add` prompts for the API key without echoing it.

Workspace and organization scope come from the workspace API-key virtual user's
profile. The CLI does not use `--workspace`, `--org`, `CODEER_WORKSPACE_ID`, or
`CODEER_ORGANIZATION_ID`.

Agent scope is optional:

```bash
export CODEER_AGENT_ID=<agent-id>
```

`CODEER_AGENT_ID` is optional unless the command needs a default agent.

## Create the API key

Create an admin workspace API key from Codeer, then store the key in your local
Codeer CLI profile. The API only returns the plain key once. Use the Codeer UI
to create the key with the admin workspace role.

## Install the skill

Use Codeer CLI 0.1.17 or newer to install the complete Skill from this public
repository. Local Skill management does not need an API key.

## Codex

Install into the user skill directory:

```bash
codeer skill install codeer-agent --target codex
```

This uses `~/.agents/skills/codeer-agent`. Codex's built-in installer is also
available, using the source folder URL:

```text
$skill-installer install https://github.com/codeer-ai/codeer-skills/tree/main/skills/codeer-agent
```

## Claude Code

Install into `~/.claude/skills/codeer-agent`:

```bash
codeer skill install codeer-agent --target claude
```

If a project has one default agent, you may set only `CODEER_AGENT_ID` in the
project `.claude/settings.json` `env` block:

```json
{
  "env": {
    "CODEER_AGENT_ID": "<agent-id>"
  }
}
```

Keep the API key in the Codeer CLI profile or another secret mechanism outside
the project. Avoid putting the API key in `.claude/settings.json` if that file
is visible to agents or committed.

## Installation scope and maintenance

Both CLI targets default to `--scope user`. Add `--scope project` to install
under the current directory's `.agents/skills/` or `.claude/skills/`. Use
`codeer skill list` to inspect status. Install defaults to `--ref main`; select
`--ref <tag-or-commit>` when a fixed revision is needed. The revision must use
the repository's `skills/codeer-agent` layout. `--dry-run` validates the remote
source without changing installation files.

Install again to update an unchanged CLI-managed copy; no uninstall is needed.
Preview with `codeer skill install codeer-agent --target codex --dry-run`, then
run without `--dry-run`. Identical contents return `already_installed`; changed
contents return `updated` after full-package replacement, removing obsolete
files. Previews return `would_install`, `would_update`, or `already_installed`.
The new package is downloaded and validated before replacement, with a backup
retained until publication succeeds. Failed publication restores the old copy;
if restoration also fails, the error gives the retained backup's recovery path.
Modified, unmanaged, or symlinked installations are not overwritten.
Keep the same target and scope throughout. Preserve local customizations and
resolve modified or unmanaged directories manually. Installs made with the
native Codex installer remain managed by that installer.

To remove an unchanged CLI-managed copy, preview `codeer skill uninstall
codeer-agent --target codex --dry-run`, then run without `--dry-run`.

Restart Codex if discovery does not refresh; use `/reload-skills` in Claude
Code when necessary. These local filesystem installs do not configure Cowork
account-level Skills.

## Verify the CLI and API

```bash
codeer check
codeer agent list
```

These commands validate API-key auth, workspace scope, organization scope, and
optional agent scope. They do not prove the skill is loaded.

## Verify the skill

Ask Codex or Claude Code:

```text
Please confirm whether the Codeer Agent Skill is loaded. Explain how you can
help me plan an Agent from KB/files, create behavior cases, analyze production
history, and show me proposed changes before applying them.
```

The answer should mention the Codeer Agent lifecycle, behavior cases,
production history, and asking for confirmation before creating, updating, or
publishing Codeer resources.
