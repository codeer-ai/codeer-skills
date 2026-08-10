from __future__ import annotations

import unittest

from codeer_cli import chats
from codeer_cli.client import TransportError


class RecordingClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []

    def post(self, path: str, **kwargs):
        self.calls.append(("POST", path, kwargs))
        return {"id": 123, "name": kwargs["json"]["name"]}

    def get(self, path: str, **kwargs):
        self.calls.append(("GET", path, kwargs))
        return {"chat_id": 123, "messages": []}


class PaginatedClient(RecordingClient):
    def __init__(self, messages: list[dict]) -> None:
        super().__init__()
        self.messages = messages

    def get(self, path: str, **kwargs):
        self.calls.append(("GET", path, kwargs))
        params = kwargs["params"]
        offset = params["offset"]
        limit = params["limit"]
        return {
            "chat_id": 123,
            "reply_context_anchor": {"part_id": 99, "sequence": 99},
            "messages": self.messages[offset:offset + limit],
        }


class ChatV2RequestTests(unittest.TestCase):
    def test_create_uses_v2_and_always_sends_name(self) -> None:
        client = RecordingClient()

        result = chats.create(client, agent_id="agent-1")  # type: ignore[arg-type]

        self.assertEqual(result["id"], 123)
        self.assertEqual(client.calls, [(
            "POST",
            "/chats",
            {
                "api_version": "v2",
                "json": {"agent_id": "agent-1", "name": "CLI conversation"},
            },
        )])

    def test_list_messages_uses_v2_pagination(self) -> None:
        client = RecordingClient()

        result = chats.list_messages(  # type: ignore[arg-type]
            client,
            123,
            external_user_id="user-1",
            limit=200,
        )

        self.assertEqual(result, {"chat_id": 123, "messages": []})
        self.assertEqual(client.calls[0], (
            "GET",
            "/chats/123/messages",
            {
                "api_version": "v2",
                "params": {
                    "limit": 200,
                    "offset": 0,
                    "external_user_id": "user-1",
                },
            },
        ))

    def test_list_messages_fetches_every_page_without_mutating_parts(self) -> None:
        messages = [
            {
                "id": idx,
                "part_kind": "tool-return",
                "content": {"content": {"owner": f"owner-{idx}"}},
                "metadata": {"agent_history_id": f"version-{idx}"},
            }
            for idx in range(5)
        ]
        client = PaginatedClient(messages)

        result = chats.list_messages(client, 123, limit=2)  # type: ignore[arg-type]

        self.assertEqual(result["messages"], messages)
        self.assertEqual(result["reply_context_anchor"], {"part_id": 99, "sequence": 99})
        self.assertEqual(
            [call[2]["params"]["offset"] for call in client.calls],
            [0, 2, 4],
        )

    def test_list_messages_checks_one_empty_page_for_exact_page_multiple(self) -> None:
        client = PaginatedClient([{"id": idx} for idx in range(4)])

        result = chats.list_messages(client, 123, limit=2)  # type: ignore[arg-type]

        self.assertEqual([message["id"] for message in result["messages"]], [0, 1, 2, 3])
        self.assertEqual(
            [call[2]["params"]["offset"] for call in client.calls],
            [0, 2, 4],
        )

    def test_list_messages_rejects_non_positive_page_size(self) -> None:
        with self.assertRaisesRegex(ValueError, "limit must be greater than zero"):
            chats.list_messages(RecordingClient(), 123, limit=0)  # type: ignore[arg-type]


class ChatV2StreamTests(unittest.TestCase):
    def test_collects_structured_events_and_final_text(self) -> None:
        result = chats.collect_stream(iter([
            {
                "event": "response.part.delta",
                "data": {
                    "type": "response.part.delta",
                    "response_id": "response-1",
                    "conversation_group_id": "group-1",
                    "part_kind": "text",
                    "delta": "Hel",
                },
            },
            {
                "event": "response.part.completed",
                "data": {
                    "type": "response.part.completed",
                    "response_id": "response-1",
                    "part": {
                        "part_kind": "text",
                        "content": {"content": "Hello"},
                    },
                },
            },
            {
                "event": "response.completed",
                "data": {
                    "type": "response.completed",
                    "response_id": "response-1",
                    "conversation_group_id": "group-1",
                },
            },
            {"event": "message", "data": "[DONE]"},
        ]))

        self.assertTrue(result["completed"])
        self.assertEqual(result["response_id"], "response-1")
        self.assertEqual(result["conversation_group_id"], "group-1")
        self.assertEqual(result["final_text"], "Hello")

    def test_response_failed_is_not_retried_as_non_streaming(self) -> None:
        with self.assertRaises(TransportError) as raised:
            chats.collect_stream(iter([{
                "event": "response.failed",
                "data": {
                    "type": "response.failed",
                    "response_id": "response-1",
                    "message": "Model unavailable",
                    "code": 503,
                },
            }]))

        self.assertIn("Model unavailable", raised.exception.message)
        self.assertTrue(raised.exception.body["outcome_uncertain"])

    def test_disconnect_before_completed_has_uncertain_outcome(self) -> None:
        with self.assertRaises(TransportError) as raised:
            chats.collect_stream(iter([{
                "event": "response.part.delta",
                "data": {
                    "type": "response.part.delta",
                    "response_id": "response-1",
                    "part_kind": "text",
                    "delta": "Partial",
                },
            }]))

        self.assertIn("before response.completed", raised.exception.message)
        self.assertTrue(raised.exception.body["outcome_uncertain"])


if __name__ == "__main__":
    unittest.main()
