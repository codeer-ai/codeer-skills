"""Two real identities share a Tester; separation touches only mapped Cases."""
import copy
import contextlib
import io
import json
import os
import unittest
from unittest.mock import patch

import httpx

from codeer_cli.project import discover, save_json
import test_project_deployments as fixtures


class SharedAPI(fixtures.PortableAPI):
    def __init__(self):
        super().__init__()
        self.main_agent = {**copy.deepcopy(self.agent), "id": "b"}
        self.testers = {"t1": {"id": "t1", "name": "Judge", "system_prompt_template": "Original"}}
        self.cases = {"c1": {"id": "c1", "agent_id": "a"}, "c2": {"id": "c2", "agent_id": "b"}}
        self.pairs = {cid: [{"evaluator_id": "t1", "rubric": "Accept"}] for cid in self.cases}
        self.lose_pair_response = False
        self.lose_create_response = False
        self.kb_sequence = 0
        self.kb_text["old-file"] = "Synthetic FAQ\n"

    def handler(self, request):
        path = request.url.path.removeprefix("/api/v1")
        if path == "/external/knowledge-bases/nodes" and request.method == "POST":
            self.kb_sequence += 1
            self.calls.append((request.method, path, json.loads(request.content)))
            return httpx.Response(200, json={"data": {"id": f"new-kb-{self.kb_sequence}"}, "error_code": 0})
        if path == "/external/knowledge-bases/files:upload":
            sid = f"new-file-{self.kb_sequence}"
            self.kb_text[sid] = "Synthetic FAQ\n"
            return httpx.Response(200, json={"data": {"nodes": [{"node_id": sid, "original_name": "faq.md"}]}, "error_code": 0})
        if path == "/external/agents/all":
            return httpx.Response(200, json={"data": [self.agent, self.main_agent], "error_code": 0})
        if path in ("/external/eval/agents/a/cases", "/external/eval/agents/b/cases"):
            agent_id = path.split("/")[-2]
            return httpx.Response(200, json={"data": [row for row in self.cases.values() if row["agent_id"] == agent_id], "error_code": 0})
        result = super().handler(request)
        if self.lose_pair_response and path.endswith("/case-evaluator-infos"):
            self.lose_pair_response = False
            raise httpx.ReadTimeout("committed replacement, response lost", request=request)
        if self.lose_create_response and path == "/external/eval/evaluators" and request.method == "POST":
            self.lose_create_response = False
            raise httpx.ReadTimeout("committed creation, identity lost", request=request)
        return result


class TesterForkTests(unittest.TestCase):
    cli = fixtures.DeploymentTests.cli
    bind = fixtures.DeploymentTests.bind

    def setUp(self):
        fixtures.DeploymentTests.setUp(self)
        self.api = SharedAPI()
        self.project = self.bind()
        scope = {"api_base": self.api.base_url, "workspace_id": "w", "organization_id": "o", "agent_id": "a"}
        with self.api.client() as client:
            scope = self.project.check_scope(client)
        self.project.save_state({"resources": {
            "tester:judge": {"server_id": "t1", "status": "applied", "scope": scope},
            "case:first": {"server_id": "c1", "status": "applied", "scope": scope},
        }})
        save_json(self.project.path("evals"), {"schema_version": 1, "testers": [{"local_id": "judge", "name": "Judge", "system_prompt_template": "Candidate", "rationale": "Reviewed fixture Judge", "evidence": []}],
                                              "cases": [{"local_id": "first", "input": "Fixture", "source": {"document": "sources/index.md"}, "pairs": [{"tester": "judge", "rubric": "Accept", "required_evidence": []}]}]})

    def fork(self, *extra):
        code, plan = self.cli("eval", "tester-fork", "--tester", "judge", "--dry-run")
        self.assertEqual(code, 0, self.error)
        return self.cli("eval", "tester-fork", "--tester", "judge", "--expect", plan["token"], *extra)

    def test_separates_candidate_without_modifying_shared_source(self):
        before = copy.deepcopy(self.api.testers["t1"])
        _, plan = self.cli("eval", "tester-fork", "--tester", "judge", "--dry-run")
        self.assertEqual({r["agent_id"] for r in plan["source_users"]}, {"a", "b"})
        self.assertEqual(self.fork()[0], 0, self.error)
        self.assertEqual(self.api.testers["t1"], before)
        self.assertEqual(self.api.pairs["c1"], [{"evaluator_id": "t2", "rubric": "Accept"}])
        self.assertEqual(self.api.pairs["c2"], [{"evaluator_id": "t1", "rubric": "Accept"}])
        self.assertEqual(discover().state()["resources"]["tester:judge"]["server_id"], "t2")
        save_json(self.root / "reviews/shared-impact.json", plan)
        self.artifact = self.root

    def test_partial_reconnection_resumes_without_duplicate_creation(self):
        self.api.lose_pair_response = True
        self.assertEqual(self.fork()[0], 1)
        self.assertEqual(discover().state()["resources"]["tester:judge"]["server_id"], "t1")
        self.assertEqual(self.cli("eval", "tester-fork", "--tester", "judge", "--reconcile")[0], 0, self.error)
        self.assertEqual(self.fork()[0], 0, self.error)
        self.assertEqual(len(self.api.testers), 2)
        self.assertEqual(self.api.pairs["c2"][0]["evaluator_id"], "t1")

    def test_unknown_create_never_repeats_and_stale_preview_never_writes(self):
        _, plan = self.cli("eval", "tester-fork", "--tester", "judge", "--dry-run")
        self.api.pairs["c1"][0]["rubric"] = "Edited elsewhere"
        self.assertEqual(self.cli("eval", "tester-fork", "--tester", "judge", "--expect", plan["token"])[0], 2)
        self.assertEqual(len(self.api.testers), 1)
        self.api.lose_create_response = True
        self.assertEqual(self.fork()[0], 1)
        self.assertEqual(self.fork()[0], 2)
        self.assertEqual(len(self.api.testers), 2)

    def test_rubric_only_leaves_shared_tester_and_main_unchanged(self):
        # command_apply limits the write to the pair; unchanged shared Tester
        # settings are intentionally retained in the fixture's local design.
        from codeer_cli.project import read_json
        design = read_json(self.project.path("evals"))
        design["testers"][0]["system_prompt_template"] = "Original"
        save_json(self.project.path("evals"), design)
        state = self.project.state()
        state["resources"]["pairs:first"] = {"server_id": "c1", "base": {"t1": "Accept"}, "local_base": {"t1": "Accept"}, "tracking_version": 1}
        self.project.save_state(state)
        manifest = self.root / "rubrics.json"
        save_json(manifest, {"agent_id": "a", "cases": [{"case_id": "c1", "rubrics_by_evaluator": {"t1": "Candidate-only rubric"}}]})
        before = copy.deepcopy(self.api.testers)
        args = ["eval", "rubrics-apply", "--rubrics", str(manifest)]
        code, plan = self.cli(*args, "--dry-run")
        self.assertEqual(code, 0, self.error)
        self.assertEqual(self.cli(*args, "--expect", plan["token"])[0], 0, self.error)
        self.assertEqual(self.api.testers, before)
        self.assertEqual(self.api.pairs["c2"][0]["rubric"], "Accept")
        self.assertEqual(self.api.pairs["c1"][0]["rubric"], "Candidate-only rubric")

    def test_shared_update_exposes_users_and_changed_impact_invalidates_preview(self):
        from codeer_cli.project import read_json
        design = read_json(self.project.path("evals"))
        design["testers"][0]["system_prompt_template"] = "Original"
        save_json(self.project.path("evals"), design)
        state = self.project.state()
        entry = state["resources"]["tester:judge"]
        entry.update(base={"name": "Judge", "system_prompt_template": "Original"},
                     local_base={"name": "Judge", "system_prompt_template": "Original"}, tracking_version=1)
        self.project.save_state(state)
        args = ["eval", "evaluator-update", "--evaluator", "t1", "--name", "Shared reviewed Judge"]
        code, plan = self.cli(*args, "--dry-run")
        self.assertEqual(code, 0, self.error)
        self.assertEqual({row["agent_id"] for row in plan["plans"][0]["shared_impact"]}, {"a", "b"})
        self.api.cases["c3"] = {"id": "c3", "agent_id": "b"}
        self.api.pairs["c3"] = [{"evaluator_id": "t1", "rubric": "Additional use"}]
        self.assertEqual(self.cli(*args, "--expect", plan["token"])[0], 2)
        self.assertEqual(self.api.testers["t1"]["name"], "Judge")
        _, fresh = self.cli(*args, "--dry-run")
        self.assertEqual(self.cli(*args, "--expect", fresh["token"])[0], 0, self.error)
        self.assertEqual(self.api.testers["t1"]["name"], "Shared reviewed Judge")
        self.assertEqual(self.api.pairs["c2"][0]["evaluator_id"], "t1")

    def test_known_created_tester_with_environment_model_recovers_logical_payload(self):
        from codeer_cli.project import read_json
        design = read_json(self.project.path("evals"))
        design["testers"][0]["judge_llm_model_id"] = "env:FORK_MODEL"
        save_json(self.project.path("evals"), design)
        original_handler = self.api.handler
        interrupted = False
        def handler(request):
            nonlocal interrupted
            if request.method == "GET" and request.url.path.endswith("/evaluators/t2") and not interrupted:
                interrupted = True
                raise httpx.ReadTimeout("known identity, readback lost", request=request)
            return original_handler(request)
        with patch.dict(os.environ, {"FORK_MODEL": "model-available"}):
            with patch.object(self.api, "handler", side_effect=handler):
                self.assertEqual(self.fork()[0], 1)
            self.assertEqual(discover().state()["resources"]["fork-tester:judge"]["server_id"], "t2")
            self.assertEqual(self.cli("eval", "tester-fork", "--tester", "judge", "--reconcile")[0], 0, self.error)
            self.assertEqual(self.fork()[0], 0, self.error)
        self.assertEqual(len(self.api.testers), 2)

    def test_model_environment_change_invalidates_fork_preview_before_creation(self):
        from codeer_cli.project import read_json
        design = read_json(self.project.path("evals"))
        design["testers"][0]["judge_llm_model_id"] = "env:FORK_MODEL"
        save_json(self.project.path("evals"), design)
        original_handler = self.api.handler
        def handler(request):
            if request.url.path.endswith("/llm/models"):
                return httpx.Response(200, json={"data": [{"model_id": "model-available"}, {"model_id": "model-second"}], "error_code": 0})
            return original_handler(request)
        with patch.object(self.api, "handler", side_effect=handler):
            with patch.dict(os.environ, {"FORK_MODEL": "model-available"}):
                code, preview = self.cli("eval", "tester-fork", "--tester", "judge", "--dry-run")
                self.assertEqual(code, 0, self.error)
            with patch.dict(os.environ, {"FORK_MODEL": "model-second"}):
                code, fresh = self.cli("eval", "tester-fork", "--tester", "judge", "--dry-run")
                self.assertEqual(code, 0, self.error)
                self.assertNotEqual(preview["token"], fresh["token"])
                self.assertEqual(self.cli("eval", "tester-fork", "--tester", "judge", "--expect", preview["token"])[0], 2)
                self.assertEqual(set(self.api.testers), {"t1"})
                self.assertEqual(self.cli("eval", "tester-fork", "--tester", "judge", "--expect", fresh["token"])[0], 0, self.error)
        self.assertEqual(self.api.testers["t2"]["judge_llm_model_id"], "model-second")

    def test_mismatched_new_tester_returns_failure_without_reconnecting_cases(self):
        original_handler = self.api.handler
        def handler(request):
            result = original_handler(request)
            if request.method == "POST" and request.url.path.endswith("/evaluators"):
                self.api.testers["t2"]["system_prompt_template"] = "Different server content"
            return result
        with patch.object(self.api, "handler", side_effect=handler):
            code, result = self.fork()
        self.assertEqual(code, 1)
        self.assertEqual(result["status"], "readback_mismatch")
        self.assertEqual(self.api.pairs["c1"][0]["evaluator_id"], "t1")
        self.assertEqual(discover().state()["resources"]["fork-tester:judge"]["server_id"], "t2")

    def test_completed_fork_cannot_be_reconciled_into_another_creation(self):
        self.assertEqual(self.fork()[0], 0, self.error)
        self.assertEqual(self.cli("eval", "tester-fork", "--tester", "judge", "--reconcile")[0], 2)
        self.assertEqual(len(self.api.testers), 2)

    def test_reconcile_and_preview_are_mutually_exclusive_before_authentication(self):
        from codeer_cli.cli import main
        for args in (("eval", "tester-fork", "--tester", "judge", "--reconcile", "--dry-run"),
                     ("kb", "upload", "--dir", "kb", "--name", "Fixture", "--reconcile", "--dry-run")):
            with patch("codeer_cli.cli.CodeerClient.from_env") as client, contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    main(list(args))
                self.assertEqual(raised.exception.code, 2)
                client.assert_not_called()


class KBForkTests(unittest.TestCase):
    cli = fixtures.DeploymentTests.cli
    bind = fixtures.DeploymentTests.bind
    local_agent = fixtures.DeploymentTests.local_agent
    decision = fixtures.DeploymentTests.decision

    def setUp(self):
        fixtures.DeploymentTests.setUp(self)
        self.api = SharedAPI()
        self.project = self.bind()
        (self.root / "kb").mkdir()
        (self.root / "kb/faq.md").write_text("Synthetic FAQ\n")
        save_json(self.root / "resources.json", {"schema_version": 1, "knowledge": {"faq": {"directory": "kb", "glob": "*.md"}}})
        self.api.agent["unified_tools"] = [{"id": "search", "type": "knowledge_base", "knowledge_node_ids": ["old-kb"]}]
        self.api.main_agent["unified_tools"] = copy.deepcopy(self.api.agent["unified_tools"])
        self.project.save_state({"resources": {"kb:faq": {"server_id": "old-kb", "file_ids": {"faq.md": "old-file"}, "status": "ready"}}})
        self.args = ["kb", "upload", "--fork", "--local-id", "faq", "--dir", str(self.root / "kb"), "--glob", "*.md", "--name", "Candidate", "--poll-timeout", "0"]

    def test_separate_files_require_subsequent_agent_and_faq_review(self):
        _, preview = self.cli(*self.args, "--dry-run")
        self.assertEqual(preview["fork_from"], "old-kb")
        self.assertEqual(preview["source_users"][0]["node_ids"], ["old-kb"])
        self.assertTrue(preview["references_pending"])
        code, result = self.cli(*self.args, "--expect", preview["token"])
        self.assertEqual(code, 0, self.error)
        self.assertTrue(result["references_pending"])
        entry = discover().state()["resources"]["kb:faq"]
        self.assertEqual(entry["server_id"], "new-kb-1")
        self.assertEqual(entry["file_ids"], {"faq.md": "new-file-1"})
        self.assertEqual(self.api.agent["unified_tools"][0]["knowledge_node_ids"], ["old-kb"])
        self.assertEqual(self.api.kb_text["old-file"], "Synthetic FAQ\n")
        self.local_agent(unified_tools=[{"id": "search", "type": "knowledge_base", "knowledge_node_ids": ["kb:faq"]}])
        self.decision("--keep-local", "unified_tools")
        code, plan = self.cli("agent", "apply", "--dry-run")
        self.assertEqual(code, 0, self.error)
        self.assertEqual(self.cli("agent", "apply", "--expect", plan["token"])[0], 0, self.error)
        self.assertEqual(self.api.agent["unified_tools"][0]["knowledge_node_ids"], ["new-kb-1"])
        self.assertEqual(self.api.main_agent["unified_tools"][0]["knowledge_node_ids"], ["old-kb"])
        self.artifact = self.root

    def test_not_ready_can_be_reconciled_without_another_upload(self):
        self.api.file_status = "PROCESSING"
        _, plan = self.cli(*self.args, "--dry-run")
        self.assertEqual(self.cli(*self.args, "--expect", plan["token"])[0], 1)
        self.assertEqual(discover().state()["resources"]["kb:faq"]["server_id"], "old-kb")
        self.api.file_status = "READY"
        self.assertEqual(self.cli(*self.args, "--reconcile")[0], 0, self.error)
        self.assertEqual(discover().state()["resources"]["kb:faq"]["server_id"], "new-kb-1")
        self.assertEqual(self.api.kb_sequence, 1)
        self.assertEqual(self.cli(*self.args, "--reconcile")[0], 2)
        self.assertEqual(self.api.kb_sequence, 1)

    def test_fork_preserves_unfinished_faq_recovery_before_any_upload(self):
        from codeer_cli.project import read_json
        from codeer_cli.project_knowledge import faq_plan
        definitions = read_json(self.root / "resources.json")
        definitions["knowledge"]["faq"]["faq_file"] = "kb/faqs.json"
        save_json(self.root / "resources.json", definitions)
        save_json(self.root / "kb/faqs.json", {"schema_version": 1, "files": {"faq.md": {"content": "Synthetic FAQ\n", "faqs": {}}}})
        _, preview = self.cli(*self.args, "--dry-run")
        with self.api.client() as client:
            plan = faq_plan(self.project, client, "faq")
        receipt = self.project.local_dir / "receipts/faq-interrupted.json"
        save_json(receipt, {"plan": plan, "status": "outcome_unknown", "operations": [], "completed": []})
        original = receipt.read_bytes()
        for status in ("pending", "outcome_unknown", "readback_mismatch"):
            with self.subTest(status=status):
                state = self.project.state()
                state["resources"]["faq:faq"] = {"status": status, "scope": plan["scope"], "ids": {}, "receipt": str(receipt.relative_to(self.root))}
                self.project.save_state(state)
                before = self.project.state_path.read_bytes()
                for mode in (("--dry-run",), ("--expect", preview["token"]), ("--reconcile",)):
                    self.assertEqual(self.cli(*self.args, *mode)[0], 2, self.error)
                    self.assertIn("faq:faq", self.error)
                    self.assertEqual(self.project.state_path.read_bytes(), before)
                self.assertEqual(receipt.read_bytes(), original)
                self.assertEqual(self.api.kb_sequence, 0)
        self.assertEqual(self.cli("kb", "faq-sync", "--local-id", "faq", "--reconcile")[0], 0, self.error)
        self.api.file_status = "PROCESSING"
        _, fresh = self.cli(*self.args, "--dry-run")
        self.assertEqual(self.cli(*self.args, "--expect", fresh["token"])[0], 1, self.error)
        state = self.project.state()
        partial = copy.deepcopy(state["resources"]["fork-kb:faq"])
        state["resources"]["faq:faq"]["status"] = "outcome_unknown"
        self.project.save_state(state)
        self.api.file_status = "READY"
        self.assertEqual(self.cli(*self.args, "--reconcile")[0], 2)
        self.assertEqual(self.project.state()["resources"]["fork-kb:faq"], partial)
        self.assertEqual(self.project.state()["resources"]["kb:faq"]["server_id"], "old-kb")
        self.assertEqual(self.cli("kb", "faq-sync", "--local-id", "faq", "--reconcile")[0], 0, self.error)
        self.assertEqual(self.cli(*self.args, "--reconcile")[0], 0, self.error)
        self.assertEqual(discover().state()["resources"]["kb:faq"]["server_id"], "new-kb-1")
        self.assertEqual(self.api.kb_sequence, 1)

    def test_fork_waits_for_unknown_agent_readback_before_switching_mapping(self):
        self.local_agent(unified_tools=[{"id": "search", "type": "knowledge_base", "knowledge_node_ids": ["kb:faq"]}])
        self.decision("--keep-local")
        self.project.path("instructions").write_text("Reviewed update before KB separation")
        _, plan = self.cli("agent", "apply", "--dry-run")
        original_handler = self.api.handler
        wrote = False
        def handler(request):
            nonlocal wrote
            if request.method == "GET" and request.url.path.endswith("/agents/a") and wrote:
                raise httpx.ReadTimeout("committed Agent write; readback lost", request=request)
            response = original_handler(request)
            if request.method == "PATCH" and request.url.path.endswith("/agents/a"):
                wrote = True
            return response
        with patch.object(self.api, "handler", side_effect=handler):
            self.assertEqual(self.cli("agent", "apply", "--expect", plan["token"])[0], 1)
        self.assertEqual(discover().state()["resources"]["agent"]["status"], "outcome_unknown")
        for status in ("pending", "readback_mismatch", "outcome_unknown"):
            state = self.project.state()
            state["resources"]["agent"]["status"] = status
            self.project.save_state(state)
            before = self.project.state_path.read_bytes()
            self.assertEqual(self.cli(*self.args, "--dry-run")[0], 2)
            self.assertIn("agent", self.error)
            self.assertEqual(self.project.state_path.read_bytes(), before)
        self.assertEqual(self.api.kb_sequence, 0)
        self.assertEqual(self.cli("agent", "pull", "--reconcile")[0], 0, self.error)
        self.assertEqual(discover().state()["resources"]["agent"]["status"], "imported_unvalidated")
        _, fresh = self.cli(*self.args, "--dry-run")
        self.assertEqual(self.cli(*self.args, "--expect", fresh["token"])[0], 0, self.error)

    def test_unrelated_faq_operation_does_not_block_selected_kb_separation(self):
        state = self.project.state()
        unresolved = {"status": "outcome_unknown", "receipt": "retained-other-operation.json"}
        state["resources"]["faq:another-kb"] = unresolved
        self.project.save_state(state)
        code, plan = self.cli(*self.args, "--dry-run")
        self.assertEqual(code, 0, self.error)
        self.assertEqual(self.cli(*self.args, "--expect", plan["token"])[0], 0, self.error)
        self.assertEqual(self.project.state()["resources"]["faq:another-kb"], unresolved)

    def test_pinned_known_response_unknown_kb_recovers_without_rewriting_source(self):
        from codeer_cli.project import read_json
        _, plan = self.cli(*self.args, "--dry-run")
        original_handler = self.api.handler
        def timeout(request):
            if request.url.path.endswith("/files:status"):
                raise httpx.ReadTimeout("readiness response lost", request=request)
            return original_handler(request)
        with patch.object(self.api, "handler", side_effect=timeout):
            self.assertEqual(self.cli(*self.args, "--expect", plan["token"])[0], 1)
        entry = discover().state()["resources"]["fork-kb:faq"]
        self.assertEqual(entry["status"], "outcome_unknown")
        self.assertEqual(entry["server_id"], "new-kb-1")
        path = self.root / entry["receipt"]
        raw = path.read_bytes()
        (self.root / "reviews").mkdir()
        import hashlib
        (self.root / "reviews/unknown-kb-baseline.md").write_text(hashlib.sha256(raw).hexdigest().upper())
        self.assertEqual(self.cli(*self.args, "--reconcile")[0], 0, self.error)
        current = discover().state()["resources"]["kb:faq"]
        self.assertEqual(current["status"], "ready")
        self.assertEqual(path.read_bytes(), raw)
        self.assertNotEqual(current["receipt"], str(path.relative_to(self.root)))
        self.assertEqual(read_json(self.root / current["receipt"])["provenance"]["original_path"], str(path.relative_to(self.root)))
        self.assertEqual(self.api.kb_sequence, 1)
