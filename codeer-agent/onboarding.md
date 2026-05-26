# Codeer Agent Auth Onboarding

The `codeer` CLI uses an admin workspace API key. Keep the key outside the repo
and outside agent chat. Do not paste it into Codex, Claude Code, or Claude
cowork prompts.

## Recommended setup

Use a named CLI profile. The profile stores the selected profile name in the
project and keeps the API key in the user-level Codeer CLI config.

```bash
codeer profile add work
codeer profile use work
codeer check
```

`codeer profile add` prompts for the API key without echoing it.

## API base

`CODEER_API_BASE` defaults to `https://api.codeer.ai`. Override it only when
using local, beta, or preview:

```bash
export CODEER_API_BASE=http://localhost:8000
```

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
Codeer CLI profile or secret manager. The API only returns the plain key once.
Use Codeer UI or admin tooling to create the key with the admin workspace role.

## Codex

Install the skill, then make sure the `codeer` CLI is installed and the selected
profile works:

```bash
codeer check
```

## Claude Code

If a project has one default agent, set only `CODEER_AGENT_ID` in the project
`.claude/settings.json` `env` block:

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

## Claude cowork

Make sure every cowork shell call can access the installed `codeer` binary and
the selected CLI profile. If cowork shells do not share user-level CLI config,
inject credentials through the runtime secret mechanism instead.

## One-off environment fallback

For a temporary shell session, you can still provide an API key directly:

```bash
export CODEER_API_KEY=<admin-workspace-api-key>
codeer check
```

Use this only when a CLI profile is not practical.

## Verify

```bash
codeer check
```

The command validates API-key auth, workspace scope, organization scope, and
optional agent scope.
