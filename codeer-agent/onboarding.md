# Codeer Agent Auth Onboarding

The `codeer` CLI uses an admin workspace API key. Keep the key outside the
repo and outside agent chat. Do not paste it into Codex, Claude Code, or Claude
cowork prompts.

## Required environment

```bash
export CODEER_API_KEY=<admin-workspace-api-key>
```

`CODEER_API_BASE` defaults to `https://api.codeer.ai`. Set it only when using
local, beta, or preview:

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
environment or secret manager. The API only returns the plain key once.
Use Codeer UI or admin tooling to create the key with the admin workspace role.

## Codex

Set `CODEER_API_KEY` in the local shell/session environment that launches
Codex. Keep the key out of the workspace. Then run:

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

Provide `CODEER_API_KEY` from the shell or a secret injection mechanism outside
the project. Avoid putting the API key in `.claude/settings.json` if that file
is visible to agents or committed.

## Claude cowork

Pass the API base, API key, workspace, and organization through the cowork
runtime environment. Each cowork shell call may be independent, so ensure the
runtime injects the variables into every call that runs `codeer`.

## Verify

```bash
codeer check
```

The command validates API-key auth, workspace scope, organization scope, and
optional agent scope.
