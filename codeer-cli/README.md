# codeer-cli

Standalone CLI for managing Codeer agents over the Codeer API.

## Development install

Use an editable install while the CLI is changing quickly:

```bash
cd /path/to/codeer-skills/codeer-cli
uv tool install --editable .
```

Reinstall only when dependencies, entry points, or package metadata change:

```bash
uv tool install --reinstall --editable /path/to/codeer-skills/codeer-cli
```

## Credentials

The CLI expects credentials to be configured outside any skill workspace. It
loads auth from the first available source:

1. Existing process environment:
   `CODEER_API_BASE`, `CODEER_SESSION_ID`, `CODEER_CSRF_TOKEN`
2. `$CODEER_ENV_FILE`
3. `~/.codeer/session.env`

The CLI intentionally does not read a repo-root `session.env` or caller CWD
`.env`, because those files are often visible to LLM workspace context.

Workspace scope can be passed by flags or non-secret environment variables:

```bash
CODEER_WORKSPACE_ID=<workspace-id>
CODEER_ORGANIZATION_ID=<organization-id>
CODEER_AGENT_ID=<agent-id>
```

Validate setup before API work:

```bash
codeer check
```
