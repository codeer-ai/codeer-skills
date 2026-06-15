"""Session-cookie client for raw Codeer platform API calls.

This client is deliberately separate from ``CodeerClient``. The normal CLI
uses API-key profiles and external endpoints; this client is an opt-in escape
hatch for preview and platform debugging with browser session cookies.
"""

from __future__ import annotations

import json as json_lib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Mapping, Optional
from urllib.parse import urlparse

import httpx

from .client import AuthError, CodeerError


def read_env_file(path: Path) -> dict[str, str]:
    """Read a small dotenv-style file without shell evaluation."""
    values: dict[str, str] = {}
    if not path.exists():
        raise AuthError(0, f"Env file does not exist: {path}")

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key:
            values[key] = value
    return values


@dataclass(frozen=True)
class SessionConfig:
    api_base: str
    session_id: str
    csrf_token: str
    app_base: Optional[str] = None
    source: Optional[str] = None

    @classmethod
    def from_sources(
        cls,
        *,
        env_file: str | None = None,
        api_base: str | None = None,
        app_base: str | None = None,
    ) -> "SessionConfig":
        file_values: dict[str, str] = {}
        source: str | None = None

        selected_env_file = env_file or os.environ.get("CODEER_ENV_FILE")
        if selected_env_file:
            path = Path(selected_env_file).expanduser()
            file_values = read_env_file(path)
            source = str(path)

        def pick(name: str) -> str | None:
            if name in file_values:
                return file_values[name]
            return os.environ.get(name)

        resolved_api_base = api_base or pick("CODEER_API_BASE")
        session_id = pick("CODEER_SESSION_ID")
        csrf_token = pick("CODEER_CSRF_TOKEN")
        resolved_app_base = app_base or pick("CODEER_APP_BASE")

        missing = [
            name for name, value in (
                ("CODEER_API_BASE", resolved_api_base),
                ("CODEER_SESSION_ID", session_id),
                ("CODEER_CSRF_TOKEN", csrf_token),
            )
            if not value
        ]
        if missing:
            hint = "Use --env-file session.env, --env-file preview_session.env, or CODEER_ENV_FILE."
            raise AuthError(0, f"Missing required session setting(s): {', '.join(missing)}. {hint}")

        return cls(
            api_base=str(resolved_api_base).rstrip("/"),
            session_id=str(session_id),
            csrf_token=str(csrf_token),
            app_base=str(resolved_app_base).rstrip("/") if resolved_app_base else None,
            source=source or "process environment",
        )


@dataclass
class CodeerSessionClient:
    config: SessionConfig
    timeout: float = 30.0

    def __post_init__(self) -> None:
        origin = self.config.app_base or _origin(self.config.api_base)
        self._client = httpx.Client(
            base_url=self.config.api_base,
            timeout=self.timeout,
            cookies={
                "sessionid": self.config.session_id,
                "csrftoken": self.config.csrf_token,
            },
            headers={
                "Accept": "application/json",
                "X-CSRFToken": self.config.csrf_token,
                "Origin": origin,
                "Referer": origin + "/",
            },
        )

    @classmethod
    def from_env(
        cls,
        *,
        env_file: str | None = None,
        api_base: str | None = None,
        app_base: str | None = None,
        timeout: float = 30.0,
    ) -> "CodeerSessionClient":
        return cls(
            SessionConfig.from_sources(
                env_file=env_file,
                api_base=api_base,
                app_base=app_base,
            ),
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "CodeerSessionClient":
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
        headers: Optional[Mapping[str, str]] = None,
        unwrap: bool = False,
    ) -> Any:
        url = normalize_api_path(path)
        response = self._client.request(
            method.upper(),
            url,
            params=params,
            json=json,
            files=files,
            data=data,
            headers=headers,
        )
        return self._parse(response, unwrap=unwrap)

    def stream_sse(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        json: Any = None,
        data: Any = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Iterator[dict[str, Any]]:
        url = normalize_api_path(path)
        with self._client.stream(
            method.upper(),
            url,
            params=params,
            json=json,
            data=data,
            headers=headers,
        ) as response:
            if response.status_code >= 400:
                body = response.read().decode("utf-8", "replace")
                self._raise_for_error(response.status_code, _maybe_json(body))
            event = "message"
            buf: list[str] = []
            for line in response.iter_lines():
                if line == "":
                    if buf:
                        yield {"event": event, "data": _maybe_json("\n".join(buf))}
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

    def _parse(self, response: httpx.Response, *, unwrap: bool) -> Any:
        text = response.text
        payload = _maybe_json(text) if text else None

        if response.status_code >= 400:
            self._raise_for_error(response.status_code, payload)

        if isinstance(payload, dict) and "error_code" in payload:
            if payload.get("error_code") not in (0, None):
                raise CodeerError(response.status_code, payload.get("message") or "error", payload)
            if unwrap and "data" in payload:
                return payload["data"]
        return payload

    def _raise_for_error(self, status: int, payload: Any) -> None:
        message = payload if isinstance(payload, str) else None
        if isinstance(payload, dict):
            message = payload.get("message") or payload.get("detail") or payload.get("error")
        if status in (401, 403):
            raise AuthError(
                status,
                f"{message or 'auth rejected'}. Session may have expired; refresh sessionid/csrftoken.",
                payload,
            )
        raise CodeerError(status, message or f"HTTP {status}", payload)


def normalize_api_path(path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if path.startswith("/api/"):
        return path
    if path.startswith("api/"):
        return "/" + path
    return f"/api/v1{path if path.startswith('/') else '/' + path}"


def _maybe_json(raw: str) -> Any:
    try:
        return json_lib.loads(raw)
    except (ValueError, TypeError):
        return raw


def _origin(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return url.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}"
