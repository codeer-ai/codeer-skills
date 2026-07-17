from __future__ import annotations

import unittest

import httpx

from codeer_cli.client import CodeerClient, TransportError


class ClientTransportTests(unittest.TestCase):
    def test_request_forwards_per_request_timeout(self) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json={"ok": True})

        client = self._client(handler)
        try:
            result = client.post("/chats/1/messages", json={"message": "Hi"}, timeout=120.0)
        finally:
            client.close()

        self.assertEqual(result, {"ok": True})
        self.assertEqual(requests[0].extensions["timeout"]["read"], 120.0)

    def test_timeout_becomes_transport_error_with_uncertain_write_outcome(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("response took too long", request=request)

        client = self._client(handler)
        try:
            with self.assertRaises(TransportError) as raised:
                client.post("/chats/1/messages", json={"message": "Hi"}, timeout=120.0)
        finally:
            client.close()

        self.assertIn("timed out after 120s", raised.exception.message)
        self.assertIn("inspect current state before retrying", raised.exception.message)
        self.assertEqual(raised.exception.status, 0)
        self.assertTrue(raised.exception.body["outcome_uncertain"])

    def test_connection_error_becomes_transport_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused", request=request)

        client = self._client(handler)
        try:
            with self.assertRaises(TransportError) as raised:
                client.get("/external/me")
        finally:
            client.close()

        self.assertIn("Request failed: GET /external/me", raised.exception.message)
        self.assertFalse(raised.exception.body["outcome_uncertain"])

    def test_stream_connection_error_becomes_transport_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused", request=request)

        client = self._client(handler)
        try:
            with self.assertRaises(TransportError) as raised:
                list(client.stream_sse("POST", "/chats/1/messages", json={"message": "Hi"}))
        finally:
            client.close()

        self.assertIn("Request failed: POST /chats/1/messages", raised.exception.message)
        self.assertFalse(raised.exception.body["outcome_uncertain"])

    @staticmethod
    def _client(handler) -> CodeerClient:
        client = CodeerClient(base_url="https://api.codeer.ai", api_key="test-key")
        client._client.close()
        client._client = httpx.Client(
            base_url=client.base_url,
            timeout=client.timeout,
            transport=httpx.MockTransport(handler),
        )
        return client


if __name__ == "__main__":
    unittest.main()
