# Preview Environment Guide

This guide covers the explicit raw session-cookie path for Codeer PR preview
environments. Use it when the normal API-key commands do not expose the
platform endpoint you need.

The normal lifecycle commands still use API-key auth:

```bash
codeer check
codeer agent list
codeer kb list
codeer eval list --agent <agent_id>
```

The raw platform path is separate and opt-in:

```bash
codeer api --env-file preview_session.env get /accounts/me
```

## Production vs preview

| | Production | Preview |
| --- | --- | --- |
| Frontend | `https://app.codeer.ai` | `https://pr<N>.preview.codeer.ai` |
| API | `https://api.codeer.ai` | `https://pr<N>.api.preview.codeer.ai` |
| Cookie source | `app.codeer.ai` devtools | `pr<N>.preview.codeer.ai` devtools |
| Database | Production DB | Per-PR ephemeral DB |

The common mistake is using the preview frontend host as the API base. The API
host has an extra `api.` segment:

```text
https://pr<N>.api.preview.codeer.ai
```

## Env files

Keep env files local. The repository `.gitignore` ignores `session.env`,
`preview_session.env`, and other `*.env` files.

Production:

```env
CODEER_API_BASE=https://api.codeer.ai
CODEER_APP_BASE=https://app.codeer.ai
CODEER_SESSION_ID=<production sessionid>
CODEER_CSRF_TOKEN=<production csrftoken>
```

Preview:

```env
CODEER_API_BASE=https://pr<N>.api.preview.codeer.ai
CODEER_APP_BASE=https://pr<N>.preview.codeer.ai
CODEER_SESSION_ID=<preview sessionid>
CODEER_CSRF_TOKEN=<preview csrftoken>
```

Replace `<N>` with the PR number.

## Get preview cookies

1. Open `https://pr<N>.preview.codeer.ai` in a browser and log in.
2. Open DevTools, then Application, Cookies, `pr<N>.preview.codeer.ai`.
3. Copy `sessionid` into `CODEER_SESSION_ID`.
4. Copy `csrftoken` into `CODEER_CSRF_TOKEN`.

Sessions expire. If requests start returning 401 or 403, refresh both cookie
values from the browser.

## Basic checks

Production:

```bash
codeer api --env-file session.env get /accounts/me
```

Preview:

```bash
codeer api --env-file preview_session.env get /accounts/me
```

If you prefer an environment variable:

```bash
CODEER_ENV_FILE=preview_session.env codeer api get /accounts/me
```

## Raw API examples

List draft and published agents:

```bash
codeer api --env-file preview_session.env get /agents/all --param wid=<workspace_id>
```

Read one agent:

```bash
codeer api --env-file preview_session.env get /agents/<agent_id>
```

Create or update with JSON:

```bash
codeer api --env-file preview_session.env post /agents --json-file agent.json
codeer api --env-file preview_session.env put /agents/<agent_id> --json-file agent.json
```

Upload multipart data:

```bash
codeer api --env-file preview_session.env post /some/upload/path \
  --form name="Example" \
  --file file=./payload.pdf
```

Stream an SSE endpoint:

```bash
codeer api --env-file preview_session.env stream post /chats/<chat_id>/messages \
  --json-file message.json
```

Paths beginning with `/api/` are used unchanged. Other relative paths are
prefixed with `/api/v1`, so `/accounts/me` becomes `/api/v1/accounts/me`.
