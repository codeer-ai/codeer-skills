from __future__ import annotations

import unittest
from contextlib import redirect_stdout
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from codeer_cli import chats as chats_mod
from codeer_cli.client import TransportError
from codeer_cli.commands import history as history_cmd


class FakeClient:
    base_url = "https://api.codeer.ai"

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def resolve_scope(self) -> tuple[str, str]:
        return "workspace-1", "organization-1"

    def post(self, path: str, **kwargs):
        self.calls.append((path, kwargs))
        return {"ok": True}


class HistorySendTests(unittest.TestCase):
    def test_chat_send_forwards_response_timeout(self) -> None:
        client = FakeClient()

        chats_mod.send_published_agent_message(
            client,  # type: ignore[arg-type]
            chat_id=18649,
            message="Continue",
            agent_id="agent-1",
            timeout=120.0,
        )

        self.assertEqual(client.calls[0][0], "/chats/18649/messages")
        self.assertEqual(client.calls[0][1]["timeout"], 120.0)

    def test_run_send_resolves_agent_and_appends_to_existing_history(self) -> None:
        client = FakeClient()
        args = SimpleNamespace(
            history_id=18649,
            agent=None,
            user=None,
            message=["Use the recommended options"],
            timeout=120.0,
            out=None,
        )

        with (
            patch.object(
                history_cmd.hist_mod,
                "get",
                return_value={
                    "id": 18649,
                    "agent_id": None,
                    "external_user_id": None,
                    "meta": {
                        "conversation_agent_id": "agent-1",
                        "external_user_id": "user-1",
                    },
                },
            ),
            patch.object(
                history_cmd.hist_mod,
                "get_conversations",
                return_value=[
                    {"role": "user", "content": "Initial"},
                    {"role": "assistant", "content": "Reply"},
                    {"role": "user", "content": "Use the recommended options"},
                    {"role": "assistant", "content": "Final"},
                ],
            ),
            patch.object(
                history_cmd.chats_mod,
                "send_published_agent_message",
                return_value={"conversation_id": 4},
            ) as send,
            redirect_stdout(StringIO()),
        ):
            result = history_cmd.run_send(args, client)

        self.assertEqual(result, 0)
        send.assert_called_once_with(
            client,
            chat_id=18649,
            message="Use the recommended options",
            agent_id="agent-1",
            external_user_id="user-1",
            stream=False,
            timeout=120.0,
        )

    def test_run_send_rejects_non_positive_timeout(self) -> None:
        client = FakeClient()
        args = SimpleNamespace(
            history_id=18649,
            agent=None,
            user=None,
            message=["Continue"],
            timeout=0,
            out=None,
        )

        with redirect_stdout(StringIO()):
            result = history_cmd.run_send(args, client)

        self.assertEqual(result, 2)

    def test_run_create_rejects_non_finite_timeout(self) -> None:
        client = FakeClient()
        args = SimpleNamespace(
            agent="agent-1",
            title=None,
            user=None,
            message=["Start"],
            timeout=float("nan"),
            out=None,
        )

        with redirect_stdout(StringIO()):
            result = history_cmd.run_create(args, client)

        self.assertEqual(result, 2)
        self.assertEqual(client.calls, [])

    def test_send_transport_error_includes_history_and_turn_context(self) -> None:
        client = FakeClient()

        with patch.object(
            history_cmd.chats_mod,
            "send_published_agent_message",
            side_effect=TransportError(
                "Request timed out",
                {"outcome_uncertain": True},
            ),
        ):
            with self.assertRaises(TransportError) as raised:
                history_cmd._send_messages(
                    client,
                    history_id=18649,
                    agent_id="agent-1",
                    external_user_id="user-1",
                    messages=["First", "Second"],
                    timeout=120.0,
                )

        self.assertIn("turn 1/2", raised.exception.message)
        self.assertEqual(raised.exception.body["history_id"], 18649)
        self.assertEqual(raised.exception.body["turn"], 1)
        self.assertTrue(raised.exception.body["outcome_uncertain"])


if __name__ == "__main__":
    unittest.main()
