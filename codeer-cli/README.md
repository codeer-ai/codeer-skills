# codeer-cli

Standalone CLI for managing Codeer agents over the Codeer API.

## User install

After the package is published to PyPI, install the CLI as an isolated command
line tool:

```bash
uv tool install codeer-cli
```

Until the package is published, install directly from this repository:

```bash
uv tool install 'git+https://github.com/<org>/codeer-skills.git#subdirectory=codeer-cli'
```

Replace `<org>` with the GitHub organization or user that hosts this repository.

Verify that the command is available:

```bash
codeer --help
```

## Credentials

The CLI expects credentials to be configured outside any skill workspace. Add a
named profile, select it, then verify the setup:

```bash
codeer profile add work
codeer profile use work
codeer check
```

`codeer profile add` prompts for the API key without echoing it. The local
project stores only the selected profile name in `.codeer/profile`; API keys
remain in the user-level config file.

For a one-off shell session, you can also export an API key directly:

```bash
export CODEER_API_KEY=<admin-workspace-api-key>
codeer check
```

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

Validate setup before API work:

```bash
codeer check
```

## Output policy for coding agents

The CLI is optimized for Codex, Claude Code, Claude Cowork, and similar coding
agents that keep command output in their LLM context. Default stdout is a
compact lifecycle summary, not the full server payload.

Use this pattern during agent lifecycle work:

```bash
codeer agent list
codeer history list --agent <agent-id> --limit 50
codeer eval run --agent <agent-id> --evaluators <evaluator-id> --out .codeer/eval_run.json
```

Flags:

- `--full` prints bounded extra detail for human inspection. It is still
  intended to be safe for LLM context.
- `--out <path>` writes complete diagnostic artifacts to a local file. Use it
  for raw eval results, full conversation turns, full rubric matrices, and
  other data that can grow with cases, versions, or turns.

Avoid piping large raw JSON directly into agent chat. Prefer `--out`, then ask
the coding agent to inspect targeted summaries, IDs, failing cases, or selected
snippets from the saved file.
