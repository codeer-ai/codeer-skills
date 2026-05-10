"""HTTP client for the Codeer API.

Auth is session-cookie based: we ride the same sessionid + csrftoken a browser
would send after logging in. For every non-GET request, Django's CSRF middleware
requires the csrftoken cookie to be echoed in an X-CSRFToken header.

Credentials come from environment variables (CODEER_SESSION_ID, CODEER_CSRF_TOKEN,
CODEER_API_BASE). Resolution order for a dotenv file:

  1. $CODEER_ENV_FILE (explicit override)
  2. ~/.codeer/session.env (user-level, permission-locked — recommended)

Skip the file entirely by exporting the vars directly. The CLI intentionally
does not read repo-root session.env or caller CWD .env files, because those
locations are commonly visible to LLM workspace context.
"""

from __future__ import annotations

import json as json_lib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Optional

import httpx


class CodeerError(RuntimeError):
    """Raised when the server returns a non-2xx response or an error envelope."""

    def __init__(self, status: int, message: str, body: Any = None):
        super().__init__(f"HTTP {status}: {message}")
        self.status = status
        self.body = body


class AuthError(CodeerError):
    """Raised when the session cookie is missing, expired, or rejected."""


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _candidate_env_files() -> list[Path]:
    """Return dotenv candidates in preferred order; first that exists wins."""
    out: list[Path] = []
    explicit = os.environ.get("CODEER_ENV_FILE")
    if explicit:
        out.append(Path(explicit).expanduser())
    out.append(Path.home() / ".codeer" / "session.env")
    return out


@dataclass
class CodeerClient:
    """Thin wrapper around httpx.Client with Codeer auth + CSRF handling.

    Construct via ``CodeerClient.from_env()`` so your script picks up credentials
    from the process environment or a CLI-owned credential file without
    hardcoding them.
    """

    base_url: str
    session_id: str
    csrf_token: str
    workspace_id: Optional[str] = None
    organization_id: Optional[str] = None
    agent_id: Optional[str] = None
    timeout: float = 30.0

    def __post_init__(self) -> None:
        self._client = httpx.Client(
            base_url=self.base_url.rstrip("/"),
            timeout=self.timeout,
            cookies={"sessionid": self.session_id, "csrftoken": self.csrf_token},
            headers={
                "X-CSRFToken": self.csrf_token,
                "Referer": self.base_url,
                "Accept": "application/json",
            },
        )

    @classmethod
    def from_env(cls, dotenv_path: Optional[Path] = None, **overrides: Any) -> "CodeerClient":
        if dotenv_path is not None:
            _load_dotenv(dotenv_path)
        else:
            for candidate in _candidate_env_files():
                if candidate.exists():
                    _load_dotenv(candidate)
                    break

        try:
            base_url = overrides.pop("base_url", None) or os.environ["CODEER_API_BASE"]
            session_id = overrides.pop("session_id", None) or os.environ["CODEER_SESSION_ID"]
            csrf_token = overrides.pop("csrf_token", None) or os.environ["CODEER_CSRF_TOKEN"]
        except KeyError as e:
            raise AuthError(
                0,
                f"Missing required env var {e.args[0]}. Expected ~/.codeer/session.env, "
                "$CODEER_ENV_FILE, or exported CODEER_API_BASE / "
                "CODEER_SESSION_ID / CODEER_CSRF_TOKEN.",
            ) from None

        return cls(
            base_url=base_url,
            session_id=session_id,
            csrf_token=csrf_token,
            workspace_id=overrides.pop("workspace_id", None) or os.environ.get("CODEER_WORKSPACE_ID") or None,
            organization_id=overrides.pop("organization_id", None) or os.environ.get("CODEER_ORGANIZATION_ID") or None,
            agent_id=overrides.pop("agent_id", None) or os.environ.get("CODEER_AGENT_ID") or None,
            **overrides,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "CodeerClient":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        json: Any = None,
        files: Any = None,
        data: Any = None,
    ) -> Any:
        url = path if path.startswith("http") else f"/api/v1{path if path.startswith('/') else '/' + path}"
        r = self._client.request(method, url, params=params, json=json, files=files, data=data)
        return self._parse(r)

    def get(self, path: str, **kwargs: Any) -> Any:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> Any:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> Any:
        return self.request("PUT", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> Any:
        return self.request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Any:
        return self.request("DELETE", path, **kwargs)

    def stream_sse(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        json: Any = None,
    ) -> Iterator[dict]:
        """Yield parsed SSE events from a streaming endpoint (e.g. POST /chats/{id}/messages).

        Each event is a dict like ``{"event": "message", "data": <parsed-json-or-str>}``.
        """
        url = path if path.startswith("http") else f"/api/v1{path if path.startswith('/') else '/' + path}"
        with self._client.stream(method, url, params=params, json=json) as r:
            if r.status_code >= 400:
                body = r.read().decode("utf-8", "replace")
                self._raise_for_error(r.status_code, body)
            event = "message"
            buf: list[str] = []
            for line in r.iter_lines():
                if line == "":
                    if buf:
                        raw = "\n".join(buf)
                        yield {"event": event, "data": _maybe_json(raw)}
                        buf = []
                        event = "message"
                    continue
                if line.startswith(":"):
                    continue
                if line.startswith("event:"):
                    event = line[len("event:"):].strip()
                    continue
                if line.startswith("data:"):
                    buf.append(line[len("data:"):].lstrip())
            if buf:
                yield {"event": event, "data": _maybe_json("\n".join(buf))}

    def _parse(self, r: httpx.Response) -> Any:
        text = r.text
        try:
            payload = r.json() if text else None
        except ValueError:
            payload = text

        if r.status_code >= 400:
            self._raise_for_error(r.status_code, payload)

        # Ninja responses follow {error_code, message, data, pagination}. Unwrap `data`
        # when present and the envelope indicates success, but return the full envelope
        # if callers need the pagination cursor or error_code detail.
        if isinstance(payload, dict) and "error_code" in payload and "data" in payload:
            if payload.get("error_code") not in (0, None):
                raise CodeerError(r.status_code, payload.get("message") or "error", payload)
            return payload["data"]
        return payload

    def _raise_for_error(self, status: int, payload: Any) -> None:
        message = payload if isinstance(payload, str) else (payload or {}).get("message") if isinstance(payload, dict) else None
        if status in (401, 403):
            raise AuthError(
                status,
                f"{message or 'auth rejected'}. Session may have expired — re-grab sessionid/csrftoken from browser devtools.",
                payload,
            )
        raise CodeerError(status, message or f"HTTP {status}", payload)


def _maybe_json(raw: str) -> Any:
    try:
        return json_lib.loads(raw)
    except (ValueError, TypeError):
        return raw
