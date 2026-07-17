"""HTTP client for the Codeer API.

Auth uses a workspace API key supplied through ``CODEER_API_KEY`` or a named
profile stored outside the workspace. ``CODEER_API_BASE`` defaults to
production and can be overridden for local, beta, or preview. The CLI
intentionally does not read workspace-local dotenv files or credential files,
because those locations are commonly visible to LLM workspace context.
"""

from __future__ import annotations

import json as json_lib
import os
from dataclasses import dataclass
from typing import Any, Iterable, Iterator, Mapping, Optional

import httpx

DEFAULT_CODEER_API_BASE = "https://api.codeer.ai"


class CodeerError(RuntimeError):
    """Raised when the server returns a non-2xx response or an error envelope."""

    def __init__(self, status: int, message: str, body: Any = None):
        super().__init__(f"HTTP {status}: {message}")
        self.status = status
        self.message = message
        self.body = body


class AuthError(CodeerError):
    """Raised when the API key is missing, expired, revoked, or rejected."""


class ScopeResolutionError(CodeerError):
    """Raised when workspace or organization scope cannot be inferred."""


class TransportError(CodeerError):
    """Raised when an HTTP request fails before a response is available."""

    def __init__(self, message: str, body: Any = None):
        RuntimeError.__init__(self, message)
        self.status = 0
        self.message = message
        self.body = body


@dataclass
class CodeerClient:
    """Thin wrapper around httpx.Client with Codeer API-key auth.

    Construct via ``CodeerClient.from_env()`` so your script picks up credentials
    from the process environment without hardcoding them.
    """

    base_url: str
    api_key: str
    workspace_id: Optional[str] = None
    organization_id: Optional[str] = None
    agent_id: Optional[str] = None
    timeout: float = 30.0

    def __post_init__(self) -> None:
        self._me_cache: Optional[dict[str, Any]] = None
        self._client = httpx.Client(
            base_url=self.base_url.rstrip("/"),
            timeout=self.timeout,
            headers={
                "x-api-key": self.api_key,
                "Accept": "application/json",
            },
        )

    @classmethod
    def from_env(cls, **overrides: Any) -> "CodeerClient":
        base_url = overrides.pop("base_url", None)
        api_key = overrides.pop("api_key", None)

        if not api_key:
            from .commands.profile import resolve_profile

            profile = resolve_profile()
            api_key = profile.get("api_key")
            base_url = (
                base_url
                or os.environ.get("CODEER_API_BASE")
                or profile.get("api_base")
                or DEFAULT_CODEER_API_BASE
            )
        else:
            base_url = base_url or os.environ.get("CODEER_API_BASE") or DEFAULT_CODEER_API_BASE

        if not api_key:
            raise AuthError(
                0,
                "Missing API key. Export CODEER_API_KEY or run `codeer profile add <name>`.",
            )

        overrides.pop("workspace_id", None)
        overrides.pop("organization_id", None)

        return cls(
            base_url=base_url,
            api_key=api_key,
            agent_id=overrides.pop("agent_id", None) or os.environ.get("CODEER_AGENT_ID") or None,
            **overrides,
        )

    def get_me(self) -> dict[str, Any]:
        if self._me_cache is None:
            self._me_cache = self.get("/external/me")
        return self._me_cache

    def resolve_scope(self) -> tuple[str, str]:
        """Resolve workspace/org from the API-key virtual user's profile."""
        me = self.get_me()
        profile = me.get("profile") or {}
        ws_id = profile.get("default_workspace_id")
        org_id = profile.get("default_organization_id")

        if not ws_id or not org_id:
            default_scopes = profile.get("default_scopes") or {}
            ws_org_map = {str(k): str(v) for k, v in (profile.get("workspace_organization_map") or {}).items()}
            candidates = _workspace_candidates(default_scopes, ws_org_map)
            detail = ""
            if candidates:
                detail = "\nAvailable workspace candidates from profile:\n" + _format_workspace_choices(
                    candidates, ws_org_map, _workspace_names(profile)
                )
            raise ScopeResolutionError(
                0,
                "API key profile is missing default_workspace_id or default_organization_id. "
                "This CLI expects a workspace API key virtual user profile."
                + detail,
            )

        self.workspace_id = str(ws_id)
        self.organization_id = str(org_id)
        return self.workspace_id, self.organization_id

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
        timeout: Optional[float] = None,
    ) -> Any:
        url = path if path.startswith("http") else f"/api/v1{path if path.startswith('/') else '/' + path}"
        request_kwargs: dict[str, Any] = {}
        if timeout is not None:
            request_kwargs["timeout"] = timeout
        method_upper = method.upper()
        try:
            r = self._client.request(
                method_upper,
                url,
                params=params,
                json=json,
                files=files,
                data=data,
                **request_kwargs,
            )
        except httpx.TimeoutException as exc:
            raise self._transport_error(
                method_upper,
                path,
                exc,
                timeout_seconds=timeout if timeout is not None else self.timeout,
            ) from exc
        except httpx.RequestError as exc:
            raise self._transport_error(method_upper, path, exc) from exc
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
        method_upper = method.upper()
        try:
            with self._client.stream(method_upper, url, params=params, json=json) as r:
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
        except httpx.TimeoutException as exc:
            raise self._transport_error(
                method_upper,
                path,
                exc,
                timeout_seconds=self.timeout,
            ) from exc
        except httpx.RequestError as exc:
            raise self._transport_error(method_upper, path, exc) from exc

    def _transport_error(
        self,
        method: str,
        path: str,
        exc: httpx.RequestError,
        *,
        timeout_seconds: float | None = None,
    ) -> TransportError:
        outcome_uncertain = (
            method not in {"GET", "HEAD", "OPTIONS"}
            and not isinstance(exc, httpx.ConnectError)
        )
        if isinstance(exc, httpx.TimeoutException):
            timeout_value = timeout_seconds if timeout_seconds is not None else self.timeout
            message = f"Request timed out after {timeout_value:g}s: {method} {path}."
            if outcome_uncertain:
                message += " The server may have completed the request; inspect current state before retrying."
        else:
            message = f"Request failed: {method} {path}: {exc}"
        return TransportError(
            message,
            {
                "method": method,
                "path": path,
                "outcome_uncertain": outcome_uncertain,
            },
        )

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
                f"{message or 'auth rejected'}. API key may be missing, invalid, expired, or revoked.",
                payload,
            )
        raise CodeerError(status, message or f"HTTP {status}", payload)


def _maybe_json(raw: str) -> Any:
    try:
        return json_lib.loads(raw)
    except (ValueError, TypeError):
        return raw


def _workspace_names(profile: Mapping[str, Any]) -> dict[str, str]:
    names: dict[str, str] = {}
    for ws in profile.get("workspaces") or []:
        ws_id = ws.get("id")
        if ws_id:
            names[str(ws_id)] = str(ws.get("name") or "(unnamed)")
    return names


def _workspace_candidates(default_scopes: Mapping[str, Any], ws_org_map: Mapping[str, str]) -> list[str]:
    candidates: set[str] = set()
    for scope in default_scopes.values():
        if isinstance(scope, Mapping) and scope.get("workspace_id"):
            candidates.add(str(scope["workspace_id"]))
    candidates.update(str(ws_id) for ws_id in ws_org_map.keys())
    return sorted(candidates)


def _format_workspace_choices(
    workspace_ids: Iterable[str],
    ws_org_map: Mapping[str, str],
    workspace_names: Mapping[str, str],
) -> str:
    lines = []
    for ws_id in workspace_ids:
        name = workspace_names.get(ws_id)
        org = ws_org_map.get(ws_id)
        label = f"{name} ({ws_id})" if name else ws_id
        if org:
            label = f"{label} in org {org}"
        lines.append(f"  - {label}")
    return "\n".join(lines)
