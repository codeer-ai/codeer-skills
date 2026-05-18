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

The CLI expects credentials to be configured outside any skill workspace. For a
one-off shell session, export an API key directly:

```bash
export CODEER_API_KEY=<admin-workspace-api-key>
```

For persistent local use, store named profiles in `~/.codeer/profiles.json`:

```bash
codeer profile add work
codeer profile use work
codeer profile current
```

`codeer profile add` prompts for the API key without echoing it. The local
project stores only the selected profile name in `.codeer/profile`; API keys
remain in the user-level config file.

`CODEER_API_BASE` defaults to `https://api.codeer.ai`. Override it only for
local, beta, or preview environments:

```bash
export CODEER_API_BASE=http://localhost:8000
```

The CLI intentionally does not read repo-root credential files or caller CWD
`.env`, because those files are often visible to LLM workspace context. Do not
paste the API key into agent chat or commit it to the repository.

Workspace and organization scope are inferred from the workspace API-key
virtual user's profile. `--workspace`, `--org`, `CODEER_WORKSPACE_ID`, and
`CODEER_ORGANIZATION_ID` are not used by the CLI.

Agent scope is optional and can be set as a non-secret environment variable:

```bash
CODEER_AGENT_ID=<agent-id>
```

Validate setup before API work:

```bash
codeer check
```
