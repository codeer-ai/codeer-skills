"""Codeer Copilot Sandbox connection: Unix socket transport and target workspace header."""
from __future__ import annotations

import json
import os
import socketserver
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from unittest.mock import patch

from codeer_cli.client import CodeerClient


class _Handler(BaseHTTPRequestHandler):
    seen: list[dict[str, str]] = []

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        type(self).seen.append({"path": self.path, **{k.lower(): v for k, v in self.headers.items()}})
        body = json.dumps({"data": {"ok": True}, "error_code": 0}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args) -> None:
        pass


class _UnixServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True

    def get_request(self):
        request, _ = super().get_request()
        return request, ("sandbox", 0)


class SandboxClientTests(unittest.TestCase):
    def client(self, key: str, **env: str) -> CodeerClient:
        with patch.dict(os.environ, env, clear=True):
            client = CodeerClient(base_url="http://localhost", api_key=key)
        self.addCleanup(client.close)
        return client

    def test_copilot_turn_key_names_the_target_workspace(self) -> None:
        client = self.client("copilot-turn:abc", CODEER_WORKSPACE_ID="ws-1")
        self.assertEqual(client._client.headers["X-Codeer-Workspace-Id"], "ws-1")
        self.assertFalse(client._client.trust_env)

    def test_workspace_api_key_is_unchanged(self) -> None:
        client = self.client("workspace-key", CODEER_WORKSPACE_ID="ws-1")
        self.assertNotIn("X-Codeer-Workspace-Id", client._client.headers)
        self.assertTrue(client._client.trust_env)

    def test_copilot_turn_key_without_workspace_sends_no_header(self) -> None:
        client = self.client("copilot-turn:abc")
        self.assertNotIn("X-Codeer-Workspace-Id", client._client.headers)

    def test_requests_go_through_the_runtime_socket(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        socket_path = str(Path(directory.name) / "runtime.sock")
        server = _UnixServer(socket_path, _Handler)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        _Handler.seen = []

        client = self.client("copilot-turn:abc", CODEER_RUNTIME_SOCKET=socket_path, CODEER_WORKSPACE_ID="ws-1")
        self.assertEqual(client.get("/external/me"), {"ok": True})

        self.assertEqual(len(_Handler.seen), 1)
        request = _Handler.seen[0]
        self.assertEqual(request["path"], "/api/v1/external/me")
        self.assertEqual(request["x-api-key"], "copilot-turn:abc")
        self.assertEqual(request["x-codeer-workspace-id"], "ws-1")


if __name__ == "__main__":
    unittest.main()
