from __future__ import annotations

import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

import httpx

from codeer_cli import cli, histories
from codeer_cli.client import CodeerClient
from codeer_cli.commands import history as history_cmd


class FakeClient:
    def resolve_scope(self) -> tuple[str, str]:
        return "workspace-1", "organization-1"


class HistoryReadTests(unittest.TestCase):
    def test_run_list_filters_and_summarizes_ai_draft_lifecycle(self) -> None:
        client = FakeClient()
        args = SimpleNamespace(
            agent="agent-1",
            user=None,
            feedback=None,
            has_ai_drafts=True,
            exclude_users=None,
            version=None,
            limit=50,
            offset=0,
            full=False,
            out=None,
        )
        rows = [{
            "id": 18649,
            "name": "Support chat",
            "ai_draft_count": 3,
            "dismissed_draft_count": 2,
            "regenerated_draft_count": 2,
            "applied_draft_count": 1,
            "sent_from_ai_draft_count": 1,
        }]

        stdout = StringIO()
        with (
            patch.object(history_cmd.hist_mod, "list", return_value=rows) as list_histories,
            redirect_stdout(stdout),
        ):
            result = history_cmd.run_list(args, client)

        summary = json.loads(stdout.getvalue())
        self.assertEqual(result, 0)
        list_histories.assert_called_once_with(
            client,
            agent_id="agent-1",
            workspace_id="workspace-1",
            organization_id="organization-1",
            external_user_id=None,
            feedback_filter=None,
            has_ai_drafts=True,
            exclude_users=[],
            limit=50,
            offset=0,
        )
        self.assertEqual(summary[0]["ai_draft_count"], 3)
        self.assertEqual(summary[0]["dismissed_draft_count"], 2)
        self.assertEqual(summary[0]["sent_from_ai_draft_count"], 1)

    def test_list_can_filter_histories_with_ai_drafts(self) -> None:
        class RecordingClient(FakeClient):
            def __init__(self) -> None:
                self.calls: list[tuple[str, dict]] = []

            def get(self, path: str, **kwargs):
                self.calls.append((path, kwargs))
                return [{"id": 18649, "ai_draft_count": 2}]

        client = RecordingClient()

        rows = histories.list(client, has_ai_drafts=True, limit=50)

        self.assertEqual(rows[0]["ai_draft_count"], 2)
        self.assertEqual(client.calls, [(
            "/external/histories",
            {"params": {"limit": 50, "offset": 0, "order_by": "desc", "has_ai_drafts": True}},
        )])

    def test_run_conversations_uses_management_export_and_writes_unmodified_parts(self) -> None:
        client = FakeClient()
        response = {
            "chat_id": 18649,
            "export_contract": "history-parts-v1",
            "part_revision": "revision-1",
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
                    "content": {
                        "tool_name": "http_request",
                        "tool_call_id": "call-1",
                        "content": {"owner": "Ada", "members": ["Grace"]},
                        "outcome": "success",
                    },
                    "metadata": {"reasoning_step_type": "consultant_http_request"},
                    "source": "stack",
                    "attached_files": [],
                    "feedbacks": [],
                },
            ],
        }
        args = SimpleNamespace(
            history_id=18649,
            full=False,
            out=None,
            client_visible=False,
            user=None,
        )

        with TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "history.json"
            args.out = str(out_path)
            stdout = StringIO()
            with (
                patch.object(history_cmd.hist_mod, "list_messages", return_value=response) as list_messages,
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
        self.assertEqual(summary["export_mode"], "management")
        self.assertEqual(summary["export_contract"], "history-parts-v1")
        self.assertEqual(summary["parts"][1]["part_kind"], "tool-return")
        self.assertEqual(summary["parts"][1]["tool_name"], "http_request")
        self.assertNotIn("Ada", stdout.getvalue())

    def test_run_conversations_client_visible_requires_user_and_uses_v2(self) -> None:
        client = FakeClient()
        args = SimpleNamespace(
            history_id=18649,
            full=False,
            out=None,
            client_visible=True,
            user="user-1",
        )
        response = {"chat_id": 18649, "messages": []}

        with (
            patch.object(history_cmd.chats_mod, "list_messages", return_value=response) as list_messages,
            redirect_stdout(StringIO()),
        ):
            result = history_cmd.run_conversations(args, client)

        self.assertEqual(result, 0)
        list_messages.assert_called_once_with(client, 18649, external_user_id="user-1")

        args.user = None
        with redirect_stdout(StringIO()):
            result = history_cmd.run_conversations(args, client)
        self.assertEqual(result, 2)

    def test_run_conversations_bounds_stdout_part_summaries(self) -> None:
        client = FakeClient()
        args = SimpleNamespace(
            history_id=18649,
            full=False,
            out=None,
            client_visible=False,
            user=None,
        )
        response = {
            "chat_id": 18649,
            "export_contract": "history-parts-v1",
            "part_revision": "revision-1",
            "messages": [
                {
                    "id": part_id,
                    "conversation_group_id": f"group-{part_id}",
                    "part_kind": "text",
                    "content": {"content": f"Part {part_id}"},
                }
                for part_id in range(25)
            ],
        }

        stdout = StringIO()
        with (
            patch.object(history_cmd.hist_mod, "list_messages", return_value=response),
            redirect_stdout(stdout),
        ):
            result = history_cmd.run_conversations(args, client)

        summary = json.loads(stdout.getvalue())
        self.assertEqual(result, 0)
        self.assertEqual(summary["part_count"], 25)
        self.assertEqual(summary["part_summaries_shown"], 20)
        self.assertTrue(summary["part_summaries_truncated"])

    def test_management_export_follows_server_pages_and_preserves_parts(self) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            offset = int(request.url.params["offset"])
            parts = [
                {
                    "id": part_id,
                    "conversation_group_id": "group-1",
                    "sequence": part_id,
                    "part_kind": "tool-return" if part_id == 2 else "text",
                    "content": {"content": {"part": part_id}},
                }
                for part_id in range(offset + 1, min(offset + 2, 3) + 1)
            ]
            payload = {
                "chat_id": 18649,
                "messages": parts,
                "export_contract": "history-parts-v1",
                "provider_raw_trace": "not_included",
                "system_prompts": "not_included",
                "missing_parts_do_not_prove_non_execution": True,
                "legacy_tool_outcomes": "not_recorded",
                "page": {"limit": 2, "offset": offset, "total_records": 3},
                "part_revision": "revision-1",
            }
            return httpx.Response(200, json={"error_code": 0, "data": payload})

        client = CodeerClient(base_url="https://api.codeer.ai", api_key="test-key")
        client._client.close()
        client._client = httpx.Client(
            base_url=client.base_url,
            transport=httpx.MockTransport(handler),
        )
        try:
            result = histories.list_messages(client, 18649, limit=500)
        finally:
            client.close()

        self.assertEqual([part["id"] for part in result["messages"]], [1, 2, 3])
        self.assertEqual(result["pages_fetched"], 2)
        self.assertEqual(result["page"]["total_records"], 3)
        self.assertEqual(
            [request.url.path for request in requests],
            [
                "/api/v1/external/histories/18649/messages",
                "/api/v1/external/histories/18649/messages",
            ],
        )
        self.assertEqual([request.url.params["offset"] for request in requests], ["0", "2"])

    def test_management_export_rejects_cross_page_revision_change(self) -> None:
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            offset = int(request.url.params["offset"])
            payload = {
                "chat_id": 18649,
                "messages": [{"id": offset + 1}],
                "export_contract": "history-parts-v1",
                "page": {"limit": 1, "offset": offset, "total_records": 2},
                "part_revision": f"revision-{call_count}",
            }
            return httpx.Response(200, json={"error_code": 0, "data": payload})

        client = CodeerClient(base_url="https://api.codeer.ai", api_key="test-key")
        client._client.close()
        client._client = httpx.Client(base_url=client.base_url, transport=httpx.MockTransport(handler))
        try:
            with self.assertRaisesRegex(ValueError, "changed while paging"):
                histories.list_messages(client, 18649, limit=1)
        finally:
            client.close()

    def test_ai_draft_export_follows_server_pagination_and_preserves_records(self) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            offset = int(request.url.params["offset"])
            all_drafts = [
                {
                    "id": 11,
                    "content": "Initial reply",
                    "outcome": "dismissed",
                    "dismiss_feedback": "Too long",
                    "tool_activities": [{"display_result": {"private": "kept"}}],
                },
                {
                    "id": 12,
                    "content": "Short reply",
                    "outcome": "applied",
                    "generation_instruction": "Make it shorter",
                    "refinement_source_draft_id": 11,
                    "delivery": {"status": "sent", "actual_content": "Human-edited reply"},
                    "tool_activities": [],
                },
                {
                    "id": 13,
                    "content": "Warm reply",
                    "outcome": "dismissed",
                    "generation_instruction": "Make it warmer",
                    "refinement_source_draft_id": 11,
                    "dismiss_feedback": "Still too formal",
                    "tool_activities": [],
                },
            ]
            page_drafts = all_drafts[offset : offset + 2]
            return httpx.Response(200, json={
                "error_code": 0,
                "message": "",
                "data": page_drafts,
                "pagination": {"limit": 2, "offset": offset, "total_records": 3},
            })

        client = CodeerClient(base_url="https://api.codeer.ai", api_key="test-key")
        client._client.close()
        client._client = httpx.Client(base_url=client.base_url, transport=httpx.MockTransport(handler))
        try:
            result = histories.list_ai_drafts(client, 18649, limit=500)
        finally:
            client.close()

        self.assertEqual([draft["id"] for draft in result["drafts"]], [11, 12, 13])
        self.assertEqual(result["drafts"][0]["tool_activities"][0]["display_result"]["private"], "kept")
        self.assertEqual(result["total_records"], 3)
        self.assertEqual(result["pages_fetched"], 2)
        self.assertEqual(result["snapshot_consistency"], "best-effort")
        self.assertEqual(
            [request.url.path for request in requests],
            [
                "/api/v1/external/histories/18649/ai-drafts",
                "/api/v1/external/histories/18649/ai-drafts",
            ],
        )
        self.assertEqual([request.url.params["offset"] for request in requests], ["0", "2"])

    def test_ai_draft_export_rejects_cross_page_total_change(self) -> None:
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            offset = int(request.url.params["offset"])
            return httpx.Response(200, json={
                "error_code": 0,
                "data": [{"id": call_count}],
                "pagination": {
                    "limit": 1,
                    "offset": offset,
                    "total_records": 2 if call_count == 1 else 3,
                },
            })

        client = CodeerClient(base_url="https://api.codeer.ai", api_key="test-key")
        client._client.close()
        client._client = httpx.Client(base_url=client.base_url, transport=httpx.MockTransport(handler))
        try:
            with self.assertRaisesRegex(ValueError, "total_records changed"):
                histories.list_ai_drafts(client, 18649, limit=1)
        finally:
            client.close()

    def test_run_ai_drafts_writes_complete_records_and_summarizes_signals(self) -> None:
        client = FakeClient()
        response = {
            "history_id": 18649,
            "source_endpoint": "/api/v1/external/histories/18649/ai-drafts",
            "snapshot_consistency": "best-effort",
            "total_records": 2,
            "pages_fetched": 1,
            "drafts": [
                {
                    "id": 11,
                    "content": "Initial private draft",
                    "outcome": "dismissed",
                    "result_type": "reply",
                    "dismiss_reason": "other",
                    "dismiss_feedback": "Focus on the plan change",
                    "generation_instruction": None,
                    "refinement_source_draft_id": None,
                    "context_through_sequence": 4,
                    "tool_activities": [{"display_result": {"private": "secret tool payload"}}],
                    "proposed_actions": None,
                    "delivery": None,
                    "created_at": "2026-09-20T00:00:00Z",
                },
                {
                    "id": 12,
                    "content": "Shorter private draft",
                    "outcome": "applied",
                    "result_type": "reply",
                    "dismiss_reason": None,
                    "dismiss_feedback": None,
                    "generation_instruction": "Make it shorter",
                    "refinement_source_draft_id": 11,
                    "context_through_sequence": 4,
                    "tool_activities": [],
                    "proposed_actions": {"request_form": {}},
                    "delivery": {"status": "sent", "actual_content": "Human-edited final reply"},
                    "created_at": "2026-09-20T00:01:00Z",
                },
            ],
        }
        args = SimpleNamespace(history_id=18649, full=False, out=None)

        with TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "ai-drafts.json"
            args.out = str(out_path)
            stdout = StringIO()
            with (
                patch.object(history_cmd.hist_mod, "list_ai_drafts", return_value=response) as list_ai_drafts,
                redirect_stdout(stdout),
            ):
                result = history_cmd.run_ai_drafts(args, client)
            artifact = json.loads(out_path.read_text())

        summary = json.loads(stdout.getvalue())
        self.assertEqual(result, 0)
        list_ai_drafts.assert_called_once_with(client, 18649)
        self.assertEqual(artifact, response)
        self.assertEqual(artifact["drafts"][0]["tool_activities"][0]["display_result"]["private"], "secret tool payload")
        self.assertEqual(summary["outcome_counts"], {"dismissed": 1, "applied": 1})
        self.assertEqual(summary["regenerated_draft_count"], 1)
        self.assertEqual(summary["sent_from_ai_draft_count"], 1)
        self.assertTrue(summary["drafts"][0]["has_dismiss_feedback"])
        self.assertTrue(summary["drafts"][1]["has_generation_instruction"])
        self.assertTrue(summary["drafts"][1]["has_actual_content"])
        self.assertNotIn("Focus on the plan change", stdout.getvalue())
        self.assertNotIn("Make it shorter", stdout.getvalue())
        self.assertNotIn("Initial private draft", stdout.getvalue())
        self.assertNotIn("Human-edited final reply", stdout.getvalue())
        self.assertNotIn("secret tool payload", stdout.getvalue())

    def test_run_ai_drafts_full_explicitly_opts_into_sensitive_previews(self) -> None:
        response = {
            "history_id": 18649,
            "snapshot_consistency": "best-effort",
            "total_records": 1,
            "pages_fetched": 1,
            "drafts": [{
                "id": 12,
                "content": "Private generated draft",
                "outcome": "applied",
                "generation_instruction": "Make it shorter",
                "dismiss_feedback": None,
                "delivery": {"status": "sent", "actual_content": "Private actual reply"},
                "tool_activities": [],
            }],
        }
        with TemporaryDirectory() as tmpdir:
            args = SimpleNamespace(
                history_id=18649,
                full=True,
                out=str(Path(tmpdir) / "ai-drafts.json"),
            )
            stdout = StringIO()
            with (
                patch.object(history_cmd.hist_mod, "list_ai_drafts", return_value=response),
                redirect_stdout(stdout),
            ):
                result = history_cmd.run_ai_drafts(args, FakeClient())

        self.assertEqual(result, 0)
        summary = json.loads(stdout.getvalue())
        self.assertEqual(summary["drafts"][0]["generation_instruction_preview"], "Make it shorter")
        self.assertEqual(summary["drafts"][0]["content_preview"], "Private generated draft")
        self.assertEqual(summary["drafts"][0]["actual_content_preview"], "Private actual reply")

    def test_run_ai_drafts_full_requires_out(self) -> None:
        args = SimpleNamespace(history_id=18649, full=True, out=None)

        with patch.object(history_cmd.hist_mod, "list_ai_drafts") as list_ai_drafts:
            result = history_cmd.run_ai_drafts(args, FakeClient())

        self.assertEqual(result, 2)
        list_ai_drafts.assert_not_called()

    def test_negative_feedback_uses_management_parts_and_grouped_user_prompt(self) -> None:
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
            patch.object(histories, "list_messages", return_value=parts) as list_messages,
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

    def test_negative_feedback_does_not_hide_management_read_failures(self) -> None:
        with (
            patch.object(histories, "list", return_value=[{"id": 18649}]),
            patch.object(histories, "list_messages", side_effect=RuntimeError("read failed")),
        ):
            with self.assertRaisesRegex(RuntimeError, "read failed"):
                histories.list_negative_feedback_turns(FakeClient(), agent_id="agent-1")

    def test_full_requires_out_before_any_request(self) -> None:
        with patch.object(histories, "list_messages") as read:
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
                histories, "list_messages", side_effect=AuthError(403, "revoked")):
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
        result = histories.list_messages(client, 1, limit=1000)
        self.assertEqual(result["messages"], [call, returned, {"id": 3}])
        self.assertEqual(result["page"], {"limit": 2, "offset": 0, "total_records": 3})
        self.assertEqual(result["pages_fetched"], 2)
        self.assertEqual(client.get.call_args_list[1].kwargs["params"]["offset"], 2)

    def test_empty_and_exact_multiple_finish_without_extra_request(self):
        from unittest.mock import Mock
        for rows, total in [([], 0), ([{"id": 1}, {"id": 2}], 2)]:
            client = Mock()
            client.get.return_value = self.page(rows, total=total)
            self.assertEqual(histories.list_messages(client, 1)["messages"], rows)
            self.assertEqual(client.get.call_count, 1)

    def test_missing_contract_or_incomplete_page_fails(self):
        from unittest.mock import Mock
        invalid_pages = [
            {"messages": []}, self.page([]), self.page([{"id": 1}]),
            self.page([{"id": 1}, {"id": 2}], total=1),
            self.page([{"id": 1}, {"id": 2}, {"id": 3}]),
        ]
        for page in invalid_pages:
            with self.subTest(page=page):
                client = Mock()
                client.get.return_value = page
                with self.assertRaises(histories.HistoryExportError):
                    histories.list_messages(client, 1)

    def test_revocation_between_pages_is_propagated(self):
        from unittest.mock import Mock
        from codeer_cli.client import AuthError
        client = Mock()
        client.get.side_effect = [self.page([{"id": 1}, {"id": 2}]), AuthError(403, "revoked")]
        with self.assertRaises(AuthError):
            histories.list_messages(client, 1)

    def test_missing_endpoint_explains_required_contract_without_fallback(self):
        from unittest.mock import Mock
        from codeer_cli.client import CodeerError
        client = Mock()
        client.get.side_effect = CodeerError(404, "Not found")
        with self.assertRaisesRegex(CodeerError, "history-parts-v1; no fallback"):
            histories.list_messages(client, 1)
        self.assertEqual(client.get.call_count, 1)

    def test_mutating_history_does_not_claim_complete_snapshot(self):
        from unittest.mock import Mock
        client = Mock()
        client.get.side_effect = [self.page([{"id": 1}, {"id": 2}]),
                                  self.page([{"id": 3}, {"id": 4}], offset=2, total=4)]
        with self.assertRaisesRegex(ValueError, "changed while paging"):
            histories.list_messages(client, 1)

    def test_edit_with_same_part_count_is_detected(self):
        from unittest.mock import Mock
        first = self.page([{"id": 1}, {"id": 2}])
        second = self.page([{"id": 3}], offset=2)
        second["part_revision"] = "edited"
        client = Mock()
        client.get.side_effect = [first, second]
        with self.assertRaisesRegex(ValueError, "changed while paging"):
            histories.list_messages(client, 1)

    def test_stdout_does_not_expose_tool_payload_and_caps_part_summaries(self):
        parts = [{"id": i, "part_kind": "tool-call", "content": {"args": {"secret": "private-value"}}}
                 for i in range(25)]
        stdout = StringIO()
        with patch.object(histories, "list_messages", return_value={"messages": parts}), redirect_stdout(stdout):
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
        self.assertEqual(artifact, {
            **contract, "messages": rows,
            "page": {"limit": 2, "offset": 0, "total_records": 3}, "pages_fetched": 2,
        })
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
            ([{"messages": []}], "missing export_contract"),
            ([page([{"id": 1}])], "Incomplete"),
            (
                [page([{"id": 1}, {"id": 2}]), page([{"id": 3}], 2, "changed")],
                "changed while paging",
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
                "list_messages",
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
