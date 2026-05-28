# Codeer Agent Onboarding

The Codeer Agent Skill works through the installed `codeer` CLI. Install the
CLI, store the Codeer API key in a local CLI profile, then install this skill in
Codex or Claude Code.

Keep API keys outside the repo and outside agent chat. Do not paste API keys
into Codex, Claude Code, `.claude/settings.json`, project `.env` files, or Git
commits.

## Recommended setup

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

Install this skill from the public GitHub folder URL, not the repository root.

## Codex

Use Codex's built-in skill installer:

```text
$skill-installer install https://github.com/codeer-ai/codeer-skills/tree/main/codeer-agent
```

Then verify the selected CLI profile:

```bash
codeer check
```

## Claude Code

Install from the same public GitHub folder URL:

```bash
claude install-skill https://github.com/codeer-ai/codeer-skills/tree/main/codeer-agent
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
