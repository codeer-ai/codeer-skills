"""Second review: project scope, tabular dependencies, release recovery, upload bytes."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import httpx

from codeer_cli.evidence import ensure_ready, snapshot
from codeer_cli._validate import ToolValidationError, validate_unified_tools
from codeer_cli.commands.agent import _summarize_tool, _tool_summary
from codeer_cli.parse import parse_agent
from codeer_cli.project import ProjectError, fingerprint, read_json
from test_project_evidence import EvidenceFixture


class AdditionalReviewTests(EvidenceFixture, unittest.TestCase):
    def delete_handler(self, request):
        if request.method == "DELETE" and "/eval/cases/" in request.url.path:
            sid = request.url.path.rsplit("/", 1)[1]
            self.api.calls.append(("DELETE", request.url.path, None))
            self.api.cases.pop(sid)
            return httpx.Response(200, json={"data": {}, "error_code": 0})
        return self.original_handler(request)

    def test_foreign_case_delete_is_blocked_in_preview_and_mutation(self):
        project = self.pull()
        self.api.cases["foreign"] = {"id": "foreign", "agent_id": "other-agent", "input": "Other"}
        # Even a stale/incorrect local mapping cannot override remote ownership.
        state = project.state()
        state["resources"]["case:foreign"] = {"server_id": "foreign"}
        project.save_state(state)
        self.original_handler = self.api.handler
        with patch.object(self.api, "handler", side_effect=self.delete_handler):
            for extra in (("--dry-run",), ()):
                self.assertEqual(self.cli("eval", "case-delete", "--case", "foreign", *extra)[0], 2)
        self.assertIn("foreign", self.api.cases)
        self.assertFalse(any(m == "DELETE" for m, _, _ in self.api.calls))

    def test_mapped_case_delete_checks_current_owner_after_preview(self):
        project, _ = self.prepare()
        self.apply_design()
        sid = project.state()["resources"]["case:handoff"]["server_id"]
        self.assertEqual(self.cli("eval", "case-delete", "--case", sid, "--dry-run")[0], 0)
        self.api.cases[sid]["agent_id"] = "other-agent"
        self.original_handler = self.api.handler
        with patch.object(self.api, "handler", side_effect=self.delete_handler):
            self.assertEqual(self.cli("eval", "case-delete", "--case", sid)[0], 2)
        self.assertIn(sid, self.api.cases)

    def test_case_delete_requires_mapping_known_owner_and_matching_saved_scope(self):
        project = self.pull()
        self.api.cases["own"] = {"id": "own", "agent_id": "a", "input": "Own"}
        self.original_handler = self.api.handler
        with patch.object(self.api, "handler", side_effect=self.delete_handler):
            self.assertEqual(self.cli("eval", "case-delete", "--case", "own")[0], 2)
            state = project.state()
            state["resources"]["case:own"] = {"server_id": "own", "scope": {"workspace_id": "elsewhere"}}
            project.save_state(state)
            self.assertEqual(self.cli("eval", "case-delete", "--case", "own")[0], 2)
            state["resources"]["case:own"].pop("scope")
            project.save_state(state)
            self.api.cases["own"].pop("agent_id")
            self.assertEqual(self.cli("eval", "case-delete", "--case", "own")[0], 2)
        self.assertIn("own", self.api.cases)

    def test_outside_project_case_delete_preserves_standalone_operation(self):
        self.pull()
        self.api.cases["foreign"] = {"id": "foreign", "agent_id": "other-agent", "input": "Other"}
        self.original_handler = self.api.handler
        with patch.object(self.api, "handler", side_effect=self.delete_handler):
            self.assertEqual(self.cli("--outside-project", "eval", "case-delete", "--case", "foreign", "--dry-run")[0], 0)
            self.assertEqual(self.cli("--outside-project", "eval", "case-delete", "--case", "foreign")[0], 0)
        self.assertNotIn("foreign", self.api.cases)

    def test_imported_tabular_file_status_changes_fingerprint_and_blocks_readiness(self):
        self.api.agent["unified_tools"] = [{"id": "table", "type": "tabular_data", "knowledge_node_id": "file-table"}]
        project = self.setup_evidence()
        with self.api.client() as client:
            before = snapshot(project, client, "h1")
            ensure_ready(project, before)
            self.api.file_status = "FAILED"
            after = snapshot(project, client, "h1")
            self.assertNotEqual(before["remote_fingerprint"], after["remote_fingerprint"])
            self.assertIn("file-table", after["snapshot"]["kb"])
            with self.assertRaisesRegex(ProjectError, "readiness"):
                ensure_ready(project, after)

    def test_tabular_readiness_blocks_run_and_publication_even_after_new_audit(self):
        self.api.agent["unified_tools"] = [{"id": "table", "type": "tabular_data", "knowledge_node_id": "file-table"}]
        project = self.setup_evidence()
        self.assertEqual(self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")[0], 0)
        self.api.file_status = "FAILED"
        self.audit(project)
        before = self.api.run_number
        self.assertEqual(self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")[0], 2)
        self.assertEqual(self.cli("agent", "publish", "--history", "h1", "--dry-run")[0], 2)
        self.assertEqual(self.api.run_number, before)
        self.assertFalse(any(path.endswith(":publish") for _, path, _ in self.api.calls))

    def test_tabular_managed_source_changes_block_run_and_publication(self):
        self.api.agent["unified_tools"] = [{"id": "table", "type": "tabular_data", "knowledge_node_id": "file-table"}]
        project = self.setup_evidence()
        source = project.root / "kb/table.csv"
        source.parent.mkdir()
        source.write_text("item,price\nA,1\n")
        state = project.state()
        state["resources"]["kb:table"] = {"server_id": "kb-root", "node_ids": ["file-table"],
            "source": {"directory": "kb", "glob": "*.csv"}, "local": {"table.csv": fingerprint(source.read_bytes().hex())}}
        project.save_state(state)
        self.audit(project)
        self.assertEqual(self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")[0], 0)
        source.write_text("item,price\nA,2\n")
        self.audit(project)
        self.assertEqual(self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")[0], 2)
        self.assertEqual(self.cli("agent", "publish", "--history", "h1", "--dry-run")[0], 2)

    def test_tabular_snapshot_identity_changes_invalidate_fingerprint(self):
        self.api.agent["unified_tools"] = [{"id": "table", "type": "tabular_data", "knowledge_node_id": "file-table"}]
        project = self.setup_evidence()
        original = self.api.handler
        with self.api.client() as client:
            before = snapshot(project, client, "h1")
        def changed_snapshot(request):
            response = original(request)
            if request.url.path.endswith("/files:status"):
                body = response.json()
                for row in body["data"]:
                    row["snapshot_object_id"] = 74
                return httpx.Response(200, json=body)
            return response
        with patch.object(self.api, "handler", side_effect=changed_snapshot), self.api.client() as client:
            after = snapshot(project, client, "h1")
        self.assertNotEqual(before["remote_fingerprint"], after["remote_fingerprint"])

    def test_tabular_import_can_be_edited_and_parser_reports_both_reference_shapes(self):
        tools = [{"id": "table", "type": "tabular_data", "knowledge_node_id": "file-table"},
                 {"id": "search", "type": "knowledge_base", "knowledge_node_ids": ["file-search", "file-table"]}]
        self.api.agent["unified_tools"] = tools
        project = self.pull()
        project.path("instructions").write_text("Updated instructions with existing table")
        code, plan = self.cli("agent", "apply", "--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(self.cli("agent", "apply", "--expect", plan["token"])[0], 0)
        self.assertEqual(parse_agent(self.api.agent).kb_attached_node_ids, ["file-search", "file-table"])
        validate_unified_tools(tools)
        for value in (None, "", " ", ["file-table"]):
            with self.assertRaises(ToolValidationError):
                validate_unified_tools([{"id": "table", "type": "tabular_data", "knowledge_node_id": value}])

    def test_tabular_source_change_is_visible_in_version_diff_and_compact_summary(self):
        before = {"id": "table", "type": "tabular_data", "knowledge_node_id": "file-before"}
        after = {**before, "knowledge_node_id": "file-after"}
        self.assertNotEqual(_summarize_tool(before), _summarize_tool(after))
        self.assertIn("file-after", _summarize_tool(after))
        self.assertEqual(_tool_summary([after])[0]["knowledge_node_count"], 1)

    def test_publish_mismatch_blocks_retry_and_is_reconciled_without_writing(self):
        project = self.setup_evidence()
        self.assertEqual(self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")[0], 0)
        self.api.run_mode = "publish_mismatch"
        _, plan = self.cli("agent", "publish", "--history", "h1", "--dry-run")
        code, release = self.cli("agent", "publish", "--history", "h1", "--expect", plan["token"])
        self.assertEqual((code, release["status"]), (1, "readback_mismatch"))
        for extra in (("--dry-run",), ("--expect", plan["token"])):
            self.assertEqual(self.cli("agent", "publish", "--history", "h1", *extra)[0], 2)
        before = len([m for m, _, _ in self.api.calls if m != "GET"])
        self.assertEqual(self.cli("agent", "publish", "--history", "h1", "--reconcile")[0], 0)
        self.assertEqual(len([m for m, _, _ in self.api.calls if m != "GET"]), before)
        stored = read_json(next((project.root / "releases").glob("*/release.json")))
        self.assertEqual(stored["status"], "reconciled_observation")
        self.assertEqual(stored["actual_history_id"], release["actual_history_id"])
        self.assertEqual(self.cli("agent", "publish", "--history", "h1", "--dry-run")[0], 0)

    def test_publish_mismatch_reconcile_records_later_matching_observation(self):
        project = self.setup_evidence()
        self.assertEqual(self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")[0], 0)
        self.api.run_mode = "publish_mismatch"
        _, plan = self.cli("agent", "publish", "--history", "h1", "--dry-run")
        _, release = self.cli("agent", "publish", "--history", "h1", "--expect", plan["token"])
        self.assertIn("reconcile", self.cli("status")[1]["next_step"])
        self.api.agent["publish_history_id"] = "h1"
        self.assertEqual(self.cli("agent", "publish", "--history", "h1", "--reconcile")[0], 0)
        stored = read_json(next((project.root / "releases").glob("*/release.json")))
        self.assertEqual(stored["status"], "published_reconciled")
        self.assertEqual(stored["actual_history_id"], release["actual_history_id"])
        self.assertEqual(stored["reconciliation"]["actual_history_id"], "h1")
        self.assertIn("readback is complete", self.cli("status")[1]["next_step"])

    def test_kb_upload_uses_reviewed_bytes_when_source_changes_during_root_creation(self):
        project = self.pull()
        directory = project.root / "kb"
        directory.mkdir()
        source = directory / "faq.md"
        source.write_bytes(b"REVIEWED_ORIGINAL_BYTES")
        args = ("kb", "upload", "--dir", str(directory), "--name", "New KB", "--local-id", "new", "--poll-timeout", "0")
        _, plan = self.cli(*args, "--dry-run")
        original = self.api.handler
        sent = []
        def handler(request):
            if request.method == "POST" and request.url.path.endswith("/knowledge-bases/nodes"):
                source.write_bytes(b"UNREVIEWED_CHANGED_BYTES")
                return httpx.Response(200, json={"data": {"id": "kb-created"}, "error_code": 0})
            if request.url.path.endswith("/files:upload"):
                sent.append(request.content)
            return original(request)
        with patch.object(self.api, "handler", side_effect=handler):
            code, receipt = self.cli(*args, "--expect", plan["token"])
        self.assertEqual((code, receipt["status"]), (0, "ready"))
        self.assertEqual(len(sent), 1)
        self.assertIn(b"REVIEWED_ORIGINAL_BYTES", sent[0])
        self.assertNotIn(b"UNREVIEWED_CHANGED_BYTES", sent[0])
        self.assertIn(b'filename="faq.md"', sent[0])
        entry = project.state()["resources"]["kb:new"]
        self.assertEqual(entry["local"]["faq.md"], fingerprint(b"REVIEWED_ORIGINAL_BYTES".hex()))
        self.assertNotIn("REVIEWED_ORIGINAL_BYTES", (project.root / entry["receipt"]).read_text())

    def test_kb_staging_survives_source_deletion_and_is_removed_after_failed_upload(self):
        project = self.pull()
        directory = project.root / "kb"
        directory.mkdir()
        source = directory / "table.csv"
        source.write_bytes(b"item,price\nA,1\n")
        args = ("kb", "upload", "--dir", str(directory), "--name", "New KB", "--local-id", "new", "--poll-timeout", "0")
        _, plan = self.cli(*args, "--dry-run")
        original = self.api.handler
        sent = []
        staged = []
        def staging(**kwargs):
            temporary = TemporaryDirectory(**kwargs)
            staged.append(Path(temporary.name))
            return temporary
        def handler(request):
            if request.method == "POST" and request.url.path.endswith("/knowledge-bases/nodes"):
                source.unlink()
                return httpx.Response(200, json={"data": {"id": "kb-created"}, "error_code": 0})
            if request.url.path.endswith("/files:upload"):
                sent.append(request.content)
                raise httpx.ReadTimeout("lost upload response", request=request)
            return original(request)
        with patch("codeer_cli.project_kb.TemporaryDirectory", side_effect=staging), patch.object(self.api, "handler", side_effect=handler):
            self.assertEqual(self.cli(*args, "--expect", plan["token"])[0], 1)
        self.assertEqual(len(sent), 1)
        self.assertIn(b"item,price\nA,1\n", sent[0])
        self.assertIn(b'filename="table.csv"', sent[0])
        self.assertIn(b"Content-Type: text/csv", sent[0])
        self.assertTrue(staged)
        self.assertTrue(all(not path.exists() for path in staged))
        self.assertEqual(project.state()["resources"]["kb:new"]["status"], "outcome_unknown")
