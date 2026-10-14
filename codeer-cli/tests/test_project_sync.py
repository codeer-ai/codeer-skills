import contextlib
import copy
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx

from codeer_cli.cli import main
from codeer_cli.client import CodeerClient
from codeer_cli.project import discover, read_json, save_json
from codeer_cli.project_agent import observe
from codeer_cli.sync import merge


class API:
    def __init__(self):
        self.agent = {"id": "a", "name": "Support", "system_prompt": "Original", "description": "keep",
                      "use_search": True, "primary_object_ids": [42], "attachment_ids": ["doc"],
                      "suggested_questions": ["Help?"], "unified_tools": [],
                      "human_handoff": {"enabled": True, "idle_timeout_minutes": None,
                                        "handoff_instructions": "Transfer on explicit human request."}}
        self.calls = []
        self.fail_write = False
        self.edit_on_get = None
        self.get_count = 0
        self.nodes = [{"id": "kb-one", "name": "Same"}, {"id": "kb-two", "name": "Same"}]
        self.file_status = "READY"
        self.cases = {}
        self.case_sequence = 0
        self.testers = {}
        self.pairs = {}
        self.results = []
        self.run_number = 0
        self.run_mode = "pass"
        self.history_id = "h1"
        self.bump_versions = False

    def handler(self, request):
        path = request.url.path.removeprefix("/api/v1")
        body = json.loads(request.content) if request.content and "application/json" in request.headers.get("content-type", "") else None
        self.calls.append((request.method, path, body))
        if path == "/external/me":
            result = {"profile": {"default_workspace_id": "w", "default_organization_id": "o"}}
        elif path == "/external/agents/all":
            result = [self.agent]
        elif path == "/external/agents/a/versions":
            result = [{"id": self.history_id, "version_number": int(self.history_id[1:]), "status": "draft"}]
        elif path.startswith("/external/agents/a/versions/") and not path.endswith(":publish"):
            hid = path.rsplit("/", 1)[1]
            result = {**self.agent, "id": hid, "agent_id": "a", "version_number": int(hid[1:]), "status": "draft"}
            if hid == "h0":
                result.update(system_prompt="Previously published", status="published")
        elif path.endswith(":publish"):
            if self.run_mode == "publish_timeout":
                raise httpx.ReadTimeout("publish unknown", request=request)
            if self.run_mode != "publish_mismatch":
                self.agent["publish_history_id"] = self.history_id
            result = {"id": self.history_id}
        elif path == "/external/agents/a" and request.method == "GET":
            self.get_count += 1
            if self.edit_on_get == self.get_count:
                self.agent["description"] = "race"
            result = self.agent
        elif path in ("/external/agents/a", "/external/agents"):
            if self.fail_write:
                raise httpx.ReadTimeout("unknown after send", request=request)
            self.agent.update(body)
            if self.bump_versions and request.method == "PATCH":
                self.history_id = "h" + str(int(self.history_id[1:]) + 1)
            result = self.agent
        elif path == "/external/histories":
            result = [{"id": 12, "name": "Synthetic support", "agent_id": "a", "ai_draft_count": 1}]
        elif path == "/external/histories/12/ai-drafts":
            result = [{"id": 9, "history_id": 12, "thread_key": "synthetic", "outcome": "dismissed",
                       "content": "Claimed transfer", "dismiss_feedback": "No transfer occurred", "tool_activities": [],
                       "delivery": {"status": "not_sent"}}]
            return httpx.Response(200, json={"data": result, "error_code": 0,
                                  "pagination": {"limit": 500, "offset": 0, "total_records": 1}})
        elif path == "/external/histories/12/messages":
            result = {"chat_id": 12, "export_contract": "history-parts-v1", "part_revision": "synthetic-v1",
                      "page": {"limit": 500, "offset": 0, "total_records": 1}, "messages": [
                          {"id": 1, "conversation_group_id": "g1", "sequence": 1, "part_kind": "user-prompt",
                           "content": {"content": "Can I speak to a person?"}, "metadata": {"agent_history_id": "h0"}}]}
        elif path == "/external/knowledge-bases/nodes":
            result = [] if request.url.params.get("parent_id") else self.nodes
        elif path.endswith("/files:status"):
            result = [{"node_id": sid, "status": self.file_status, "snapshot_object_id": 73} for sid in body["node_ids"]]
        elif path == "/external/context-object-faqs":
            result = []
        elif request.method == "POST" and "knowledge-bases" in path:
            result = {"nodes": [{"node_id": "file-new", "original_name": "faq.md"}]}
        elif path == "/external/eval/runs":
            self.run_number += 1
            ids = []
            skipped = []
            for cid in body["case_ids"]:
                for tid in body["evaluator_ids"]:
                    if self.run_mode == "skip":
                        skipped.append({"case_id": cid, "evaluator_id": tid, "reason": "already_running"})
                        continue
                    rid = f"r{self.run_number}-{cid}-{tid}"
                    ids.append(rid)
                    row = {"id": rid, "evaluation_case_id": cid, "evaluator_id": tid, "agent_history_id": body["version_id"],
                           "status": "finished", "score": 1.0, "output": "Here is the requested assistance",
                           "reasoning_steps": [{"tool": "handoff", "status": "success"}] if cid == "c1" else []}
                    if self.run_mode == "dishonest_judge":
                        row.update(output="Claimed handoff", reasoning_steps=[])
                    if self.run_mode == "missing_evidence":
                        row.pop("reasoning_steps")
                    if self.run_mode == "error":
                        row.update(status="failed", score=None, output=None, reasoning_steps=[])
                    if self.run_mode == "failed":
                        row["score"] = 0.0
                    if self.run_mode == "pending":
                        row["status"] = "running"
                    if self.run_mode == "wrong_history":
                        row["agent_history_id"] = "other"
                    if self.run_mode != "old_only":
                        self.results.append(row)
                    if self.run_mode == "duplicate":
                        extra = {**row, "id": rid+"-duplicate"}
                        self.results.append(extra)
                        ids.append(extra["id"])
            if self.run_mode == "trigger_timeout":
                raise httpx.ReadTimeout("trigger outcome unknown", request=request)
            result = {"created_results": ids, "skipped_pairs": skipped}
        elif path == "/external/eval/results:batch":
            if self.run_mode == "change_during_run":
                self.testers["t1"]["description"] = "Changed during execution"
            result = [r for r in self.results if r["evaluator_id"] == body["evaluator_id"] and r["evaluation_case_id"] in body["case_ids"]]
            if self.run_mode != "wrong_history":
                result = [r for r in result if r["agent_history_id"] == body["version_id"]]
            if self.run_mode != "duplicate":
                # Production returns only the latest row for each Case/Tester.
                result = list({(r["evaluation_case_id"], r["evaluator_id"], r["agent_history_id"]): r for r in result}.values())
        elif path == "/external/eval/agents/a/cases":
            result = list(self.cases.values())
        elif path == "/external/eval/evaluators" and request.method == "GET":
            result = list(self.testers.values())
        elif path == "/external/eval/evaluators":
            sid = f"t{len(self.testers)+1}"
            self.testers[sid] = {"id": sid, **body}
            result = self.testers[sid]
        elif path.startswith("/external/eval/evaluators/"):
            sid = path.rsplit("/", 1)[1]
            if request.method == "PUT":
                self.testers[sid].update(body)
            result = self.testers[sid]
        elif path == "/external/eval/cases":
            self.case_sequence += 1
            sid = f"c{self.case_sequence}"
            self.cases[sid] = {"id": sid, **body}
            result = self.cases[sid]
        elif path.endswith("/case-evaluator-infos"):
            sid = path.split("/")[-2]
            self.pairs[sid] = body["evaluators"]
            result = {}
        elif path == "/external/eval/case-evaluator-infos:batch":
            result = [{"case_id": cid, "evaluators": self.pairs.get(cid, [])} for cid in body["case_ids"]]
        elif path.startswith("/external/eval/cases/"):
            sid = path.rsplit("/", 1)[1]
            if sid not in self.cases:
                return httpx.Response(404, json={"message": "Case not found"})
            if request.method == "PUT":
                self.cases[sid].update(body)
            result = self.cases[sid]
        else:
            raise AssertionError((request.method, path, body))
        result = copy.deepcopy(result)
        if path == "/external/eval/agents/a/cases" or path == "/external/eval/cases" or path.startswith("/external/eval/cases/") and not path.endswith("case-evaluator-infos"):
            for case in result if isinstance(result, list) else [result]:
                for field, output in (("attachment_ids", "attachments"), ("label_ids", "labels")):
                    case[output] = [{"id": sid} for sid in case.pop(field, [])]
                case.pop("rubric", None)
        if isinstance(result, dict) and "unified_tools" in result:
            for tool in result["unified_tools"]:
                for field in ("name", "description", "version", "domain", "invocation_instruction", "draft_policy", "agent_id", "knowledge_node_ids", "knowledge_node_id", "image_model", "custom_form_schema", "http_request", "text2speech"):
                    tool.setdefault(field, None)
        return httpx.Response(200, json={"data": copy.deepcopy(result), "error_code": 0})

    def client(self):
        client = CodeerClient("https://fixture.invalid", "synthetic")
        client._client.close()
        client._client = httpx.Client(base_url=client.base_url, transport=httpx.MockTransport(self.handler))
        return client


class ProjectFixture:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        old = Path.cwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, old)
        self.api = API()
        self.cli("init", "--legacy")

    def cli(self, *args):
        output = io.StringIO()
        with patch("codeer_cli.cli.CodeerClient.from_env", side_effect=self.api.client), contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
            code = main(list(args))
        return code, json.loads(output.getvalue()) if output.getvalue() else None

    def pull(self):
        code, result = self.cli("agent", "pull", "--agent", "a")
        self.assertEqual(code, 0)
        self.assertFalse(result["accepted"])
        return discover()


class SyncCLITests(ProjectFixture, unittest.TestCase):
    def test_real_editable_shape_recovers_attachment_ids_from_matching_history(self):
        editable = {k: v for k, v in self.api.agent.items() if k not in ("primary_object_ids", "attachment_ids", "human_handoff")}
        editable["meta"] = {"human_handoff": self.api.agent["human_handoff"], "response_mode": "ai-draft"}
        history = {**editable, "version_number": 7, "attachments": [{"id": "doc"}],
                   "meta": {**editable["meta"], "primary_objects_info": [{"id": 42}]}}
        class RealShape:
            def get(self, path, **kwargs):
                if path.endswith("/versions"):
                    return [{"id": "h7", "version_number": 7}]
                return history if path.endswith("/h7") else editable
        _, result = observe(RealShape(), "a")
        self.assertEqual(result["attachment_ids"], ["doc"])
        self.assertEqual(result["primary_object_ids"], [42])
        self.assertEqual(result["response_mode"], "ai-draft")
        history["system_prompt"] = "Concurrent edit"
        with self.assertRaisesRegex(ValueError, "differs from latest history"):
            observe(RealShape(), "a")

    def test_import_edit_and_apply_preserves_unmanaged_fields(self):
        project = self.pull()
        self.assertFalse(any(method != "GET" for method, _, _ in self.api.calls))
        project.path("instructions").write_text("Updated")
        self.api.agent["description"] = "web edit"
        code, plan = self.cli("agent", "diff", "--local")
        self.assertEqual(code, 0)
        self.assertEqual(plan["payload"]["description"], "web edit")
        self.assertEqual(self.cli("agent", "apply", "--expect", plan["token"])[0], 0)
        payload = [b for m, _, b in self.api.calls if m == "PATCH"][-1]
        self.assertEqual(payload["system_prompt"], "Updated")
        self.assertEqual(payload["primary_object_ids"], [42])
        self.assertEqual(payload["attachment_ids"], ["doc"])
        self.assertEqual(payload["description"], "web edit")
        self.assertEqual(project.state()["resources"]["agent"]["status"], "applied")

    def test_conflict_and_changed_preview_never_mutate(self):
        project = self.pull()
        project.path("instructions").write_text("Local")
        self.api.agent["system_prompt"] = "Web"
        self.assertEqual(self.cli("agent", "apply", "--dry-run")[0], 1)
        self.assertEqual(self.cli("agent", "apply", "--expect", "bogus")[0], 2)
        self.assertFalse(any(m == "PATCH" for m, _, _ in self.api.calls))

    def test_remote_change_between_preview_and_second_preflight(self):
        project = self.pull()
        project.path("instructions").write_text("Local")
        _, plan = self.cli("agent", "apply", "--dry-run")
        self.api.edit_on_get = self.api.get_count + 2
        self.assertEqual(self.cli("agent", "apply", "--expect", plan["token"])[0], 2)
        self.assertFalse(any(m == "PATCH" for m, _, _ in self.api.calls))

    def test_unknown_outcome_retains_receipt_and_requires_reconciliation(self):
        project = self.pull()
        project.path("instructions").write_text("Local")
        _, plan = self.cli("agent", "apply", "--dry-run")
        self.api.fail_write = True
        self.assertEqual(self.cli("agent", "apply", "--expect", plan["token"])[0], 1)
        entry = project.state()["resources"]["agent"]
        self.assertEqual(entry["status"], "outcome_unknown")
        self.assertEqual(read_json(project.root / entry["receipt"])["status"], "outcome_unknown")
        self.assertEqual(self.cli("agent", "apply", "--dry-run")[0], 1)
        self.api.fail_write = False
        self.assertEqual(self.cli("agent", "pull", "--reconcile")[0], 0)
        self.assertEqual(project.path("instructions").read_text(), "Local")

    def test_create_binds_and_get_stays_read_only(self):
        project = discover()
        save_json(project.path("agent"), {"name": "New"})
        project.path("instructions").write_text("Help")
        _, plan = self.cli("agent", "apply", "--dry-run")
        self.assertEqual(self.cli("agent", "apply", "--expect", plan["token"])[0], 0)
        self.assertEqual(discover().target["agent_id"], "a")
        before = project.path("instructions").read_text()
        self.assertEqual(self.cli("agent", "get", "a")[0], 0)
        self.assertEqual(project.path("instructions").read_text(), before)

    def test_three_way_absence_and_tool_arrays(self):
        base = {"name": "a", "unified_tools": [{"id": "t", "name": "x"}]}
        remote = {**base, "description": "web"}
        self.assertEqual(merge(base, {"name": "b"}, remote), ({**remote, "name": "b"}, []))
        changed = {"unified_tools": [{"id": "t", "name": "y"}]}
        web = {**base, "unified_tools": [{"id": "t", "name": "z"}]}
        self.assertEqual(merge(base, changed, web)[1], ["unified_tools"])

    def test_kb_id_binding_and_addition_readiness(self):
        self.pull()
        directory = self.root / "kb"
        directory.mkdir()
        (directory / "faq.md").write_text("FAQ")
        args = ("kb", "upload", "--dir", str(directory), "--name", "Same", "--kb-id", "kb-two", "--local-id", "support")
        code, plan = self.cli(*args, "--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(plan["kb_id"], "kb-two")
        code, receipt = self.cli(*args, "--expect", plan["token"])
        self.assertEqual(code, 0)
        self.assertEqual(receipt["status"], "ready")
        self.assertEqual(discover().state()["resources"]["kb:support"]["base"][0]["snapshot_object_id"], 73)
        (directory / "faq.md").write_text("replacement")
        code, plan = self.cli(*args, "--dry-run")
        self.assertEqual(code, 1)
        self.assertEqual(plan["unsupported_replacements"], ["faq.md"])
        self.assertEqual(self.cli(*args, "--expect", plan["token"])[0], 2)

    def test_kb_missing_or_failed_readiness_is_not_success(self):
        self.pull()
        directory = self.root / "kb"
        directory.mkdir()
        (directory / "faq.md").write_text("FAQ")
        self.api.file_status = "FAILED"
        args = ("kb", "upload", "--dir", str(directory), "--name", "Same", "--kb-id", "kb-two", "--local-id", "support")
        _, plan = self.cli(*args, "--dry-run")
        code, result = self.cli(*args, "--expect", plan["token"])
        self.assertEqual(code, 1)
        self.assertEqual(result["status"], "not_ready")
        before = sum(path.endswith("files:upload") for _, path, _ in self.api.calls)
        self.assertEqual(self.cli(*args)[0], 1)
        self.api.file_status = "READY"
        self.assertEqual(self.cli(*args)[0], 0)
        self.assertEqual(sum(path.endswith("files:upload") for _, path, _ in self.api.calls), before)

    def test_kb_incremental_addition_does_not_reupload_unchanged_files(self):
        self.pull()
        directory = self.root / "kb"
        directory.mkdir()
        (directory / "faq.md").write_text("FAQ")
        args = ("kb", "upload", "--dir", str(directory), "--name", "Same", "--kb-id", "kb-two", "--local-id", "support")
        _, preview = self.cli(*args, "--dry-run")
        self.assertEqual(self.cli(*args, "--expect", preview["token"])[0], 0)
        (directory / "hours.md").write_text("Hours")
        _, preview = self.cli(*args, "--dry-run")
        self.assertEqual(preview["upload_files"], ["hours.md"])
        self.assertEqual(preview["unsupported_replacements"], [])
        self.assertEqual(self.cli(*args, "--expect", preview["token"])[0], 0)


if __name__ == "__main__":
    unittest.main()
