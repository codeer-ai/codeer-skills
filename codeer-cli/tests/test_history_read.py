from __future__ import annotations

import json
import unittest

import httpx
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from codeer_cli.client import CodeerClient
from codeer_cli import cli, histories
from codeer_cli.commands import history as history_cmd


class FakeClient:
    def resolve_scope(self) -> tuple[str, str]:
        return "workspace-1", "organization-1"


class HistoryReadTests(unittest.TestCase):
    def test_run_conversations_uses_management_and_writes_unmodified_parts(self) -> None:
        client = FakeClient()
        response = {
            "chat_id": 18649,
            "messages": [
                {
                    "id": 10,
                    "conversation_group_id": "group-1",
                    "sequence": 1,
                    "part_kind": "user-prompt",
                    "content": {"content": "Question"},
                    "metadata": {"agent_history_id": "version-1"},
                    "source": "stack",
                    "attached_files": [],
                    "feedbacks": [],
                },
                {
                    "id": 11,
                    "conversation_group_id": "group-1",
                    "sequence": 2,
                    "part_kind": "tool-return",
                    "content": {"content": {"owner": "Ada", "members": ["Grace"]}},
                    "metadata": {"reasoning_step_type": "consultant_http_request"},
                    "source": "stack",
                    "attached_files": [],
                    "feedbacks": [],
                },
            ],
        }
        args = SimpleNamespace(history_id=18649, full=False, out=None)

        with TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "history.json"
            args.out = str(out_path)
            stdout = StringIO()
            with (
                patch.object(history_cmd.hist_mod, "get_messages", return_value=response) as list_messages,
                redirect_stdout(stdout),
            ):
                result = history_cmd.run_conversations(args, client)

            artifact = json.loads(out_path.read_text())

        self.assertEqual(result, 0)
        list_messages.assert_called_once_with(client, 18649)
        self.assertEqual(artifact, response)
        self.assertEqual(artifact["messages"][1]["content"]["content"]["owner"], "Ada")
        summary = json.loads(stdout.getvalue())
        self.assertEqual(summary["turn_count"], 1)
        self.assertEqual(summary["part_count"], 2)
        self.assertTrue(summary["stdout_is_summary"])
        self.assertEqual(summary["parts"][1]["part_kind"], "tool-return")

    def test_negative_feedback_uses_management_part_feedback_and_grouped_user_prompt(self) -> None:
        client = FakeClient()
        history_rows = [{
            "id": 18649,
            "name": "Support chat",
            "external_user_id": "user-1",
            "created_at": "2026-08-10T00:00:00Z",
        }]
        parts = {
            "chat_id": 18649,
            "messages": [
                {
                    "id": 1,
                    "conversation_group_id": "group-1",
                    "part_kind": "user-prompt",
                    "content": {"content": "Why did this fail?"},
                },
                {
                    "id": 2,
                    "conversation_group_id": "group-1",
                    "part_kind": "tool-call",
                    "content": {"tool_name": "http_request", "args": {"path": "/status"}},
                },
                {
                    "id": 3,
                    "conversation_group_id": "group-1",
                    "part_kind": "text",
                    "content": {"content": "The service is healthy."},
                    "feedbacks": [{"type": "sys_improve", "content": "Incorrect"}],
                },
            ],
        }

        with (
            patch.object(histories, "list", return_value=history_rows),
            patch.object(histories, "get_messages", return_value=parts) as list_messages,
        ):
            rows = histories.list_negative_feedback_turns(client, agent_id="agent-1")

        list_messages.assert_called_once_with(client, 18649)
        self.assertEqual(rows, [{
            "history_id": 18649,
            "history_title": "Support chat",
            "external_user_id": "user-1",
            "created_at": "2026-08-10T00:00:00Z",
            "turn_idx": 0,
            "part_idx": 2,
            "conversation_group_id": "group-1",
            "conversation_part_id": 3,
            "feedback_type": "sys_improve",
            "feedback_text": "Incorrect",
            "user_message": "Why did this fail?",
            "assistant_excerpt": "The service is healthy.",
        }])

    def test_full_requires_out_before_any_request(self) -> None:
        with patch.object(histories, "get_messages") as read:
            self.assertEqual(history_cmd.run_conversations(
                SimpleNamespace(history_id=1, full=True, out=None), FakeClient()), 2)
        read.assert_not_called()

    def test_client_visible_keeps_owner_contract_explicit(self) -> None:
        with patch.object(history_cmd.chats_mod, "list_messages", return_value={"messages": []}) as read:
            with redirect_stdout(StringIO()):
                history_cmd.run_conversations(SimpleNamespace(
                    history_id=1, full=False, out=None, client_visible=True, user="owner"), FakeClient())
        read.assert_called_once_with(unittest.mock.ANY, 1, external_user_id="owner")

    def test_negative_feedback_does_not_hide_permission_failure(self) -> None:
        from codeer_cli.client import AuthError
        with patch.object(histories, "list", return_value=[{"id": 1}]), patch.object(
                histories, "get_messages", side_effect=AuthError(403, "revoked")):
            with self.assertRaises(AuthError):
                histories.list_negative_feedback_turns(FakeClient(), agent_id="agent-1")


class HistoryPaginationTests(unittest.TestCase):
    def page(self, rows, *, limit=2, offset=0, total=3):
        return {"chat_id": 1, "export_contract": "history-parts-v1", "part_revision": "revision", "messages": rows,
                "page": {"limit": limit, "offset": offset, "total_records": total}}

    def test_all_pages_with_server_cap_and_exact_content(self):
        from unittest.mock import Mock
        call = {"id": 1, "part_kind": "tool-call", "content": {"args": {"nested": [1, "x"]}}}
        returned = {"id": 2, "part_kind": "tool-return", "content": {"content": {"error": "failed"}}}
        client = Mock()
        client.get.side_effect = [self.page([call, returned]), self.page([{"id": 3}], offset=2)]
        result = histories.get_messages(client, 1, limit=1000)
        self.assertEqual(result["messages"], [call, returned, {"id": 3}])
        self.assertNotIn("page", result)
        self.assertEqual(client.get.call_args_list[1].kwargs["params"]["offset"], 2)

    def test_empty_and_exact_multiple_finish_without_extra_request(self):
        from unittest.mock import Mock
        for rows, total in [([], 0), ([{"id": 1}, {"id": 2}], 2)]:
            client = Mock()
            client.get.return_value = self.page(rows, total=total)
            self.assertEqual(histories.get_messages(client, 1)["messages"], rows)
            self.assertEqual(client.get.call_count, 1)

    def test_missing_contract_or_incomplete_page_fails(self):
        from unittest.mock import Mock
        for page in [{"messages": []}, self.page([]), self.page([{"id": 1}])]:
            client = Mock()
            client.get.return_value = page
            with self.assertRaises(ValueError):
                histories.get_messages(client, 1)

    def test_revocation_between_pages_is_propagated(self):
        from unittest.mock import Mock
        from codeer_cli.client import AuthError
        client = Mock()
        client.get.side_effect = [self.page([{"id": 1}, {"id": 2}]), AuthError(403, "revoked")]
        with self.assertRaises(AuthError):
            histories.get_messages(client, 1)

    def test_missing_endpoint_explains_required_contract_without_fallback(self):
        from unittest.mock import Mock
        from codeer_cli.client import CodeerError
        client = Mock()
        client.get.side_effect = CodeerError(404, "Not found")
        with self.assertRaisesRegex(CodeerError, "history-parts-v1; no fallback"):
            histories.get_messages(client, 1)
        self.assertEqual(client.get.call_count, 1)

    def test_mutating_history_does_not_claim_complete_snapshot(self):
        from unittest.mock import Mock
        client = Mock()
        client.get.side_effect = [self.page([{"id": 1}, {"id": 2}]),
                                  self.page([{"id": 3}, {"id": 4}], offset=2, total=4)]
        with self.assertRaisesRegex(ValueError, "changed during export"):
            histories.get_messages(client, 1)

    def test_edit_with_same_part_count_is_detected(self):
        from unittest.mock import Mock
        first = self.page([{"id": 1}, {"id": 2}])
        second = self.page([{"id": 3}], offset=2)
        second["part_revision"] = "edited"
        client = Mock()
        client.get.side_effect = [first, second]
        with self.assertRaisesRegex(ValueError, "changed during export"):
            histories.get_messages(client, 1)

    def test_stdout_does_not_expose_tool_payload_and_caps_part_summaries(self):
        parts = [{"id": i, "part_kind": "tool-call", "content": {"args": {"secret": "private-value"}}}
                 for i in range(25)]
        stdout = StringIO()
        with patch.object(histories, "get_messages", return_value={"messages": parts}), redirect_stdout(stdout):
            history_cmd.run_conversations(SimpleNamespace(history_id=1, full=False, out=None), FakeClient())
        summary = json.loads(stdout.getvalue())
        self.assertEqual(len(summary["parts"]), 20)
        self.assertEqual(summary["omitted_part_summaries"], 5)
        self.assertNotIn("private-value", stdout.getvalue())


class HistoryHttpTransportTests(unittest.TestCase):
    def test_serialized_envelopes_reach_file_through_real_client_and_command(self):
        # Exercise httpx JSON decoding and CodeerClient envelope unwrapping;
        # pagination must remain in data, rather than only the outer envelope.
        rows = [
            {
                "id": 1,
                "sequence": 1,
                "conversation_group_id": "http",
                "part_kind": "tool-call",
                "source": "stack",
                "content": {
                    "tool_name": "http_request",
                    "tool_call_id": "call",
                    "args": {"nested": [1, None, "中文"]},
                },
                "metadata": {"assistant_response_status": "failed"},
            },
            {
                "id": 2,
                "sequence": 2,
                "conversation_group_id": "http",
                "part_kind": "tool-return",
                "source": "stack",
                "content": {
                    "tool_name": "http_request",
                    "tool_call_id": "call",
                    "content": {"status": 403},
                    "outcome": "error",
                },
                "metadata": {"assistant_response_status": "failed"},
            },
            {
                "id": None,
                "conversation_id": 3,
                "sequence": 3,
                "conversation_group_id": "legacy",
                "part_kind": "tool-return",
                "source": "legacy-adapter",
                "content": {"content": {"value": False}},
                "metadata": {"outcome_not_recorded": True},
                "attached_files": [{"name": "file.txt"}],
                "feedbacks": [{"identity": {"external_user_id": "User ABCD", "user_email": None}}],
            },
        ]
        contract = {
            "chat_id": 1,
            "export_contract": "history-parts-v1",
            "part_revision": "stable",
            "provider_raw_trace": "not_included",
            "system_prompts": "not_included",
            "missing_parts_do_not_prove_non_execution": True,
            "legacy_tool_outcomes": "not_recorded",
        }
        requests = []

        def handler(request):
            requests.append(request)
            self.assertEqual(request.method, "GET")
            self.assertEqual(request.url.path, "/api/v1/external/histories/1/messages")
            self.assertEqual(request.headers["x-api-key"], "test-key")
            self.assertNotIn("external_user_id", request.url.params)
            offset = int(request.url.params["offset"])
            data = {
                **contract,
                "messages": rows[offset : offset + 2],
                "page": {"limit": 2, "offset": offset, "total_records": 3},
            }
            envelope = {
                "error_code": 0,
                "data": data,
                "pagination": {"limit": 2, "offset": offset, "total_records": 3},
            }
            return httpx.Response(
                200,
                content=json.dumps(envelope, ensure_ascii=False).encode(),
                headers={"content-type": "application/json"},
            )

        client = CodeerClient(base_url="https://api.codeer.ai", api_key="test-key")
        headers = dict(client._client.headers)
        client._client.close()
        client._client = httpx.Client(
            base_url=client.base_url, headers=headers, transport=httpx.MockTransport(handler)
        )
        try:
            with TemporaryDirectory() as directory:
                target = Path(directory) / "history.json"
                stdout = StringIO()
                with redirect_stdout(stdout):
                    result = history_cmd.run_conversations(
                        SimpleNamespace(history_id=1, full=False, out=str(target)), client
                    )
                artifact = json.loads(target.read_text())
        finally:
            client.close()
        self.assertEqual(result, 0)
        self.assertEqual([request.url.params["offset"] for request in requests], ["0", "2"])
        self.assertEqual(artifact, {**contract, "messages": rows})
        self.assertNotIn("nested", stdout.getvalue())
        self.assertNotIn('"status": 403', stdout.getvalue())
        self.assertEqual(json.loads(stdout.getvalue())["part_count"], 3)


class HistoryCliFailureTests(unittest.TestCase):
    def test_expected_export_failures_return_error_without_writing_or_traceback(self):
        from unittest.mock import Mock

        def page(rows, offset=0, revision="stable"):
            return {
                "chat_id": 1,
                "export_contract": "history-parts-v1",
                "part_revision": revision,
                "messages": rows,
                "page": {"limit": 2, "offset": offset, "total_records": 3},
            }

        cases = [
            ([{"messages": []}], "does not support"),
            ([page([{"id": 1}])], "Incomplete"),
            (
                [page([{"id": 1}, {"id": 2}]), page([{"id": 3}], 2, "changed")],
                "changed during export",
            ),
        ]
        for pages, expected in cases:
            with self.subTest(expected=expected), TemporaryDirectory() as directory:
                client = Mock()
                client.get.side_effect = pages
                target = Path(directory) / "history.json"
                target.write_text("keep existing artifact")
                stdout, stderr = StringIO(), StringIO()
                with (
                    patch.object(cli.CodeerClient, "from_env", return_value=client),
                    redirect_stdout(stdout),
                    redirect_stderr(stderr),
                ):
                    result = cli.main(["history", "conversations", "1", "--out", str(target)])
                self.assertEqual(result, 1)
                self.assertIn(expected, stderr.getvalue())
                self.assertNotIn("Traceback", stderr.getvalue())
                self.assertEqual(stdout.getvalue(), "")
                self.assertEqual(target.read_text(), "keep existing artifact")
                client.close.assert_called_once()

    def test_negative_feedback_reports_the_same_export_failure(self):
        from unittest.mock import Mock

        client = Mock()
        client.resolve_scope.return_value = ("workspace-1", "organization-1")
        stderr = StringIO()
        with (
            patch.object(cli.CodeerClient, "from_env", return_value=client),
            patch.object(histories, "list", return_value=[{"id": 1}]),
            patch.object(
                histories,
                "get_messages",
                side_effect=histories.HistoryExportError("Incomplete export"),
            ),
            redirect_stderr(stderr),
        ):
            result = cli.main(["history", "negative-feedback", "--agent", "agent-1"])
        self.assertEqual(result, 1)
        self.assertIn("Incomplete export", stderr.getvalue())
        client.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
