"""Regression triggers from the implementation/design review, using CLI entry points."""
import copy
import unittest
from unittest.mock import patch

import httpx

from codeer_cli.client import CodeerError
from codeer_cli.evidence import ensure_ready, snapshot
from codeer_cli.project import ProjectError, discover, read_json, save_json
from codeer_cli.project_agent import canonical, writable
from codeer_cli.project_eval import command_apply
from test_project_sync import ProjectFixture
from test_project_eval import EvalFixture
from test_project_evidence import EvidenceFixture


class AgentReviewTests(ProjectFixture, unittest.TestCase):
    def test_create_preview_cannot_move_to_another_workspace(self):
        project = discover()
        save_json(project.path("agent"), {"name": "New"})
        project.path("instructions").write_text("Instructions")
        _, plan = self.cli("agent", "apply", "--dry-run")
        original = self.api.client
        def other_scope():
            client = original()
            client.resolve_scope = lambda: ("other-customer", "o")
            return client
        with patch.object(self.api, "client", side_effect=other_scope):
            self.assertNotEqual(self.cli("agent", "apply", "--expect", plan["token"])[0], 0)
        self.assertFalse(any(m == "POST" and p == "/external/agents" for m, p, _ in self.api.calls))

    def test_create_preview_cannot_move_to_another_api(self):
        project = discover()
        save_json(project.path("agent"), {"name": "New"})
        project.path("instructions").write_text("Instructions")
        _, plan = self.cli("agent", "apply", "--dry-run")
        original = self.api.client
        def other_api():
            client = original()
            client.base_url = "https://other-fixture.invalid"
            return client
        with patch.object(self.api, "client", side_effect=other_api):
            self.assertNotEqual(self.cli("agent", "apply", "--expect", plan["token"])[0], 0)
        self.assertFalse(any(m == "POST" and p == "/external/agents" for m, p, _ in self.api.calls))

    def test_preview_binds_api_profile_and_version_note(self):
        project = self.pull()
        project.path("instructions").write_text("Changed")
        _, plan = self.cli("agent", "apply", "--note", "Reviewed", "--dry-run")
        self.assertNotEqual(self.cli("agent", "apply", "--note", "Different", "--expect", plan["token"])[0], 0)
        with patch("codeer_cli.commands.profile.resolve_profile", return_value={"name": "different-profile"}):
            self.assertNotEqual(self.cli("agent", "apply", "--note", "Reviewed", "--expect", plan["token"])[0], 0)
        self.assertEqual(self.cli("agent", "apply", "--note", "Reviewed", "--expect", plan["token"])[0], 0)
        self.assertEqual([b for m, _, b in self.api.calls if m == "PATCH"][-1]["version_note"], "Reviewed")

    def test_reconcile_keeps_newer_local_proposal_after_unknown_readback(self):
        project = self.pull()
        project.path("instructions").write_text("Reviewed proposal")
        _, plan = self.cli("agent", "apply", "--dry-run")
        original = self.api.handler
        def timeout(request):
            if request.method == "GET" and request.url.path.endswith("/agents/a") and self.api.agent["system_prompt"] == "Reviewed proposal":
                raise httpx.ReadTimeout("readback interrupted", request=request)
            return original(request)
        with patch.object(self.api, "handler", side_effect=timeout):
            self.assertNotEqual(self.cli("agent", "apply", "--expect", plan["token"])[0], 0)
        project.path("instructions").write_text("Newer proposal")
        self.assertEqual(self.cli("agent", "pull", "--agent", "a", "--reconcile")[0], 0)
        _, preview = self.cli("agent", "diff", "--local")
        self.assertEqual(preview["payload"]["system_prompt"], "Newer proposal")
        self.assertEqual(preview["local_base"]["system_prompt"], "Reviewed proposal")

    def test_http_defaults_preserve_body_values_and_contract_order(self):
        tool = {"id": "http", "type": "http_request", "http_request": {"method": "POST", "url_template": "https://fixture.invalid", "body": {"template": {"payload": "{{payload}}", "nullable": None}, "input_contracts": {"payload": {"type": "object"}}}}}
        local = {"unified_tools": [tool], "llm_model_settings": {"model": {"temperature": None, "max_tokens": 100}}}
        remote = copy.deepcopy(local)
        config = remote["unified_tools"][0]["http_request"]
        config.update(headers=None, query_params=None, auth={"type": "none", "token": None, "api_key": None, "api_key_location": None, "api_key_param_name": None, "username": None, "password": None, "header_name": None, "header_value": None})
        config["body"]["input_contracts"]["payload"].update(format="text", json_type="any")
        remote["llm_model_settings"]["model"].pop("temperature")
        result = canonical(local)
        self.assertEqual(result, writable(remote))
        self.assertEqual(list(result["unified_tools"][0]["http_request"]["body"]["template"]), ["payload", "nullable"])
        self.assertIn("nullable", result["unified_tools"][0]["http_request"]["body"]["template"])
        self.assertNotEqual(canonical({"unified_tools": [tool]}), canonical({"unified_tools": [{**tool, "http_request": {**tool["http_request"], "body": {"template": {"payload": "{{payload}}"}}}}]}))

    def test_success_and_noop_preserve_remote_only_changes_on_next_apply(self):
        project = self.pull()
        self.api.agent["description"] = "Web description"
        for prompt in ("Original", "Changed", "Changed again"):
            project.path("instructions").write_text(prompt)
            _, plan = self.cli("agent", "diff", "--local")
            self.assertEqual(plan["payload"]["description"], "Web description")
            self.assertEqual(self.cli("agent", "apply", "--expect", plan["token"])[0], 0)
            self.assertNotIn("agent.description", project.status()["local_changes"])
        local = read_json(project.path("agent"))
        local["description"] = "Intentional new local value"
        save_json(project.path("agent"), local)
        _, plan = self.cli("agent", "diff", "--local")
        self.assertEqual(plan["payload"]["description"], local["description"])

    def test_normal_reconcile_does_not_restore_an_older_receipt_checkpoint(self):
        project = self.pull()
        self.api.agent["description"] = "Web value"
        project.path("instructions").write_text("Changed prompt")
        _, plan = self.cli("agent", "apply", "--dry-run")
        self.cli("agent", "apply", "--expect", plan["token"])
        local = read_json(project.path("agent"))
        local["description"] = "Web value"
        save_json(project.path("agent"), local)
        _, plan = self.cli("agent", "apply", "--dry-run")
        self.cli("agent", "apply", "--expect", plan["token"])
        self.cli("agent", "pull", "--agent", "a", "--reconcile")
        self.api.agent["description"] = "Newer web value"
        _, plan = self.cli("agent", "diff", "--local")
        self.assertFalse(plan["conflicts"])
        self.assertEqual(plan["payload"]["description"], "Newer web value")

    def test_minimal_tool_and_handoff_survive_server_defaults(self):
        project = self.pull()
        local = read_json(project.path("agent"))
        local.update(unified_tools=[{"id": "kb", "type": "knowledge_base", "knowledge_node_ids": ["kb-one"]}], human_handoff={"enabled": False})
        save_json(project.path("agent"), local)
        _, plan = self.cli("agent", "apply", "--dry-run")
        self.assertEqual(self.cli("agent", "apply", "--expect", plan["token"])[0], 0)
        _, second = self.cli("agent", "diff", "--local")
        self.assertFalse(second["changed"])


class EvalReviewTests(EvalFixture, unittest.TestCase):
    def test_second_apply_preserves_remote_case_tester_and_pair_changes(self):
        project, design = self.prepare()
        design["cases"][0]["expected_output"] = "Original expectation"
        save_json(project.path("evals"), design)
        self.apply_design()
        self.api.cases["c1"]["expected_output"] = "Web expectation"
        self.api.testers["t1"]["name"] = "Web Tester name"
        self.api.pairs["c1"][0]["rubric"] = "Web Rubric"
        for prompt in ("Edited once", "Edited twice"):
            design["cases"][0]["input"] = prompt
            save_json(project.path("evals"), design)
            self.apply_design()
            self.assertEqual(self.api.cases["c1"]["expected_output"], "Web expectation")
            self.assertEqual(self.api.testers["t1"]["name"], "Web Tester name")
            self.assertEqual(self.api.pairs["c1"][0]["rubric"], "Web Rubric")
            self.assertEqual(project.status()["local_changes"], [])
            with self.api.client() as client:
                ensure_ready(project, snapshot(project, client, "h1"))

    def test_legacy_case_rubric_is_rejected_before_mutation(self):
        project, design = self.prepare()
        design["cases"][0]["rubric"] = "Legacy default evaluator side effect"
        save_json(project.path("evals"), design)
        self.assertNotEqual(self.cli("eval", "cases-apply", "--dry-run")[0], 0)
        self.assertFalse(self.api.cases)
        design["cases"][0].pop("rubric")
        save_json(project.path("evals"), design)
        self.apply_design()
        before = project.path("evals").read_bytes()
        self.assertNotEqual(self.cli("eval", "case-update", "--case", "c1", "--rubric", "Legacy", "--dry-run")[0], 0)
        self.assertEqual(project.path("evals").read_bytes(), before)

    def test_partial_resource_command_keeps_reviewed_local_proposals(self):
        project, _ = self.prepare()
        self.apply_design()
        changes = {"case:handoff": {"input": "Changed first"}, "case:hours": {"input": "Changed second"}}
        with self.api.client() as client:
            preview = command_apply(project, client, changes, dry_run=True, expected=None)
        original = self.api.handler
        def timeout(request):
            if request.url.path.endswith("/cases/c2") and request.method == "GET" and self.api.cases["c2"]["input"] == "Changed second":
                raise httpx.ReadTimeout("second readback interrupted", request=request)
            return original(request)
        with patch.object(self.api, "handler", side_effect=timeout), self.api.client() as client:
            with self.assertRaises(CodeerError):
                command_apply(project, client, changes, dry_run=False, expected=preview["token"])
        self.assertEqual(read_json(project.path("evals"))["cases"][0]["input"], "Changed first")
        self.assertEqual(self.cli("eval", "pull", "--reconcile")[0], 0)
        self.apply_design()
        self.assertEqual(self.api.cases["c1"]["input"], "Changed first")
        self.assertEqual(self.api.cases["c2"]["input"], "Changed second")

    def test_response_attachment_and_label_ids_are_preserved_and_fingerprinted(self):
        project, _ = self.prepare()
        self.apply_design()
        with self.api.client() as client:
            first = snapshot(project, client, "h1")
            self.assertEqual(first["snapshot"]["cases"]["c1"]["attachment_ids"], ["attachment"])
            self.api.cases["c1"]["label_ids"] = ["changed-label"]
            self.assertNotEqual(snapshot(project, client, "h1")["remote_fingerprint"], first["remote_fingerprint"])

    def test_unassigned_tester_with_known_create_id_recovers_without_recreate(self):
        project, _ = self.prepare()
        original = self.api.handler
        def timeout(request):
            if request.method == "GET" and request.url.path.endswith("/evaluators/t1"):
                raise httpx.ReadTimeout("readback interrupted", request=request)
            return original(request)
        _, plan = self.cli("eval", "cases-apply", "--dry-run")
        with patch.object(self.api, "handler", side_effect=timeout):
            self.assertNotEqual(self.cli("eval", "cases-apply", "--expect", plan["token"])[0], 0)
        self.assertEqual(project.state()["resources"]["tester:tools"]["server_id"], "t1")
        self.assertEqual(self.cli("eval", "pull", "--reconcile")[0], 0)
        self.assertNotEqual(project.state()["resources"]["tester:tools"]["status"], "outcome_unknown")
        self.apply_design()
        self.assertEqual(len(self.api.testers), 1)

    def test_pair_removal_is_idempotent_but_remote_readdition_requires_review(self):
        project, design = self.prepare()
        design["testers"].append({**copy.deepcopy(design["testers"][0]), "local_id": "second", "name": "Second"})
        design["cases"][0]["pairs"].append({"tester": "second", "rubric": "Alternative"})
        save_json(project.path("evals"), design)
        self.apply_design()
        design["cases"][0]["pairs"] = design["cases"][0]["pairs"][1:]
        design["cases"][0]["remove_tester_ids"] = ["t1"]
        save_json(project.path("evals"), design)
        self.apply_design()
        self.apply_design()
        self.api.pairs["c1"].append({"evaluator_id": "t1", "rubric": "Remote readdition"})
        _, plan = self.cli("eval", "cases-apply", "--dry-run")
        self.assertTrue(plan["conflicts"])
        # Explicitly accepting a readdition clears the old removal checkpoint.
        design["cases"][0].pop("remove_tester_ids")
        design["cases"][0]["pairs"].append({"tester": "tools", "rubric": "Remote readdition", "required_evidence": ["tool_steps"]})
        save_json(project.path("evals"), design)
        self.apply_design()
        self.assertNotIn("t1", project.state()["resources"]["pairs:handoff"]["removed_ids"])
        self.assertEqual(self.cli("eval", "pull", "--reconcile")[0], 0)
        self.assertNotIn("t1", project.state()["resources"]["pairs:handoff"]["removed_ids"])
        design["cases"][0]["pairs"] = design["cases"][0]["pairs"][:1]
        design["cases"][0]["remove_tester_ids"] = ["t1"]
        save_json(project.path("evals"), design)
        self.apply_design()

    def test_pair_removal_readback_must_prove_removed_id_is_absent(self):
        project, design = self.prepare()
        self.apply_design()
        design["testers"].append({**copy.deepcopy(design["testers"][0]), "local_id": "second", "name": "Second"})
        design["cases"][0]["pairs"] = [{"tester": "second", "rubric": "Alternative"}]
        design["cases"][0]["remove_tester_ids"] = ["t1"]
        save_json(project.path("evals"), design)
        _, plan = self.cli("eval", "cases-apply", "--dry-run")
        original = self.api.handler
        def ignores_removal(request):
            response = original(request)
            if request.url.path.endswith("/c1/case-evaluator-infos"):
                self.api.pairs["c1"].append({"evaluator_id": "t1", "rubric": "Must actually call handoff"})
            return response
        with patch.object(self.api, "handler", side_effect=ignores_removal):
            code, result = self.cli("eval", "cases-apply", "--expect", plan["token"])
        self.assertNotEqual(code, 0)
        self.assertFalse(result["complete"])
        self.assertEqual(project.state()["resources"]["pairs:handoff"]["status"], "readback_mismatch")
        self.assertEqual(self.cli("eval", "pull", "--reconcile")[0], 0)
        self.assertNotIn("t1", project.state()["resources"]["pairs:handoff"].get("removed_ids", []))

    def test_malformed_or_contradictory_removal_never_mutates(self):
        project, design = self.prepare()
        self.apply_design()
        for value in ("t1", ["t1"]):
            design["cases"][0]["remove_tester_ids"] = value
            save_json(project.path("evals"), design)
            self.assertNotEqual(self.cli("eval", "cases-apply", "--dry-run")[0], 0)
        self.assertEqual(self.api.pairs["c1"][0]["evaluator_id"], "t1")

    def test_known_case_and_pairs_readback_interruptions_recover(self):
        for suffix in ("/cases/c1", "/case-evaluator-infos:batch"):
            with self.subTest(suffix=suffix):
                project, design = self.prepare()
                self.apply_design()
                design["cases"][0]["input"] += " changed"
                design["cases"][0]["pairs"][0]["rubric"] += " changed"
                save_json(project.path("evals"), design)
                _, plan = self.cli("eval", "cases-apply", "--dry-run")
                original = self.api.handler
                def timeout(request):
                    updated = self.api.cases["c1"]["input"] == design["cases"][0]["input"] if suffix == "/cases/c1" else self.api.pairs["c1"][0]["rubric"] == design["cases"][0]["pairs"][0]["rubric"]
                    if request.url.path.endswith(suffix) and updated:
                        raise httpx.ReadTimeout("readback interrupted", request=request)
                    return original(request)
                with patch.object(self.api, "handler", side_effect=timeout):
                    self.assertNotEqual(self.cli("eval", "cases-apply", "--expect", plan["token"])[0], 0)
                self.assertEqual(self.cli("eval", "pull", "--reconcile")[0], 0)
                self.apply_design()
                self.assertEqual(len(self.api.cases), 2)


class EvidenceReviewTests(EvidenceFixture, unittest.TestCase):
    def test_missing_historical_result_cannot_be_filled_by_newer_run(self):
        project = self.setup_evidence()
        _, first = self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")
        self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")
        path = project.root / "runs" / first["id"] / "run.json"
        saved = read_json(path)
        saved["results"][0]["result"] = None
        saved["status"] = "incomplete"
        save_json(path, saved)
        _, exported = self.cli("eval", "export", "--run-id", first["id"], "--out-dir", str(project.root / "export"))
        self.assertEqual(exported["status"], "incomplete")
        after = read_json(path)
        self.assertIsNone(after["results"][0]["result"])
        self.assertEqual(after["results"][1]["result"], saved["results"][1]["result"])

    def test_failed_historical_export_remains_failed(self):
        project = self.setup_evidence()
        self.api.run_mode = "failed"
        _, first = self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")
        self.api.run_mode = "pass"
        self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")
        _, exported = self.cli("eval", "export", "--run-id", first["id"], "--out-dir", str(project.root / "export"))
        self.assertEqual(exported["status"], "failed")
        self.assertEqual(exported["counts"], {"failed": 2})

    def test_old_run_export_preserves_exact_saved_results_after_newer_run(self):
        project = self.setup_evidence()
        _, first = self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")
        original = read_json(project.root / "runs" / first["id"] / "run.json")
        before = (project.root / "runs" / first["id"] / "run.json").read_bytes()
        self.assertEqual(self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")[0], 0)
        code, _ = self.cli("eval", "export", "--run-id", first["id"], "--out-dir", str(project.root / "export"))
        self.assertEqual(code, 0)
        saved = read_json(project.root / "runs" / first["id"] / "run.json")
        self.assertEqual(saved["results"], original["results"])
        self.assertEqual(saved["status"], "passed")
        self.assertEqual((project.root / "runs" / first["id"] / "run.json").read_bytes(), before)

    def test_export_preserves_release_run_fingerprint_and_resumes_pending_ids(self):
        project = self.setup_evidence()
        self.api.run_mode = "pending"
        _, pending = self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")
        for row in self.api.results:
            row["status"] = "finished"
        _, exported = self.cli("eval", "export", "--run-id", pending["id"], "--out-dir", str(project.root / "export"))
        self.assertTrue(exported["record_updated"])
        self.assertEqual(exported["status"], "passed")
        _, plan = self.cli("agent", "publish", "--history", "h1", "--dry-run")
        self.assertEqual(self.cli("agent", "publish", "--history", "h1", "--expect", plan["token"])[0], 0)
        from codeer_cli.project import fingerprint
        path = project.root / "runs" / pending["id"] / "run.json"
        before = fingerprint(read_json(path))
        _, exported = self.cli("eval", "export", "--run-id", pending["id"], "--out-dir", str(project.root / "export"))
        self.assertFalse(exported["record_updated"])
        self.assertEqual(fingerprint(read_json(path)), before)
        self.assertEqual(plan["run"]["fingerprint"], before)

    def test_status_uses_same_report_history_and_pair_audit_checks(self):
        project = self.setup_evidence()
        path = project.root / "reviews/current.audit.json"
        original = read_json(path)
        for field, value in (("schema_version", 99), ("history_id", "h0"), ("pairs", []), ("report_fingerprint", "edited")):
            save_json(path, {**original, field: value})
            self.assertFalse(project.status()["audit"]["valid_at_last_remote_query"], field)
            self.assertNotEqual(self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")[0], 0)
        save_json(path, original)
        (project.root / "reviews/audit.md").write_text("Changed audit content")
        self.assertFalse(project.status()["audit"]["local_revision_valid"])

    def test_status_references_valid_audit_even_when_newest_record_is_invalid(self):
        project = self.setup_evidence()
        original = read_json(project.root / "reviews/current.audit.json")
        save_json(project.root / "reviews/zzz.audit.json", {**original, "history_id": "h0"})
        status = project.status()["audit"]
        self.assertTrue(status["valid_at_last_remote_query"])
        self.assertEqual(status["record"]["history_id"], "h1")


class KBReviewTests(EvidenceFixture, unittest.TestCase):
    def upload_args(self, project):
        directory = project.root / "kb"
        directory.mkdir(exist_ok=True)
        (directory / "faq.md").write_text("KB source")
        return ("kb", "upload", "--local-id", "support", "--kb-id", "kb-one", "--name", "Support", "--dir", str(directory), "--poll-timeout", "0")

    def test_known_file_ids_reconcile_is_read_only(self):
        project = self.pull()
        args = self.upload_args(project)
        _, plan = self.cli(*args, "--dry-run")
        original = self.api.handler
        def timeout(request):
            if request.url.path.endswith("/files:status"):
                raise httpx.ReadTimeout("poll interrupted", request=request)
            return original(request)
        with patch.object(self.api, "handler", side_effect=timeout):
            self.assertNotEqual(self.cli(*args, "--expect", plan["token"])[0], 0)
        self.assertEqual(project.state()["resources"]["kb:support"]["node_ids"], ["file-new"])
        before = len([1 for m, p, _ in self.api.calls if m == "POST" and not p.endswith("files:status")])
        self.assertEqual(self.cli(*args, "--reconcile")[0], 0)
        self.assertEqual(project.state()["resources"]["kb:support"]["status"], "ready")
        self.assertEqual(before, len([1 for m, p, _ in self.api.calls if m == "POST" and not p.endswith("files:status")]))

    def test_unknown_upload_identity_cannot_be_reconciled_or_retried(self):
        project = self.pull()
        args = self.upload_args(project)
        _, plan = self.cli(*args, "--dry-run")
        original = self.api.handler
        def timeout(request):
            if request.url.path.endswith("files:upload"):
                original(request)  # Server may have committed; response identity was lost.
                raise httpx.ReadTimeout("upload response lost", request=request)
            return original(request)
        with patch.object(self.api, "handler", side_effect=timeout):
            self.assertNotEqual(self.cli(*args, "--expect", plan["token"])[0], 0)
        before = len(self.api.calls)
        self.assertNotEqual(self.cli(*args, "--reconcile")[0], 0)
        self.assertNotEqual(self.cli(*args, "--expect", plan["token"])[0], 0)
        self.assertFalse(any(p.endswith("files:upload") for _, p, _ in self.api.calls[before:]))

    def test_older_known_id_upload_receipt_recovers_without_new_metadata(self):
        project = self.pull()
        args = self.upload_args(project)
        _, plan = self.cli(*args, "--dry-run")
        self.cli(*args, "--expect", plan["token"])
        state = project.state()
        entry = state["resources"]["kb:support"]
        entry["status"] = "outcome_unknown"
        for field in ("source", "scope", "upload_complete"):
            entry.pop(field)
        receipt_path = project.root / entry["receipt"]
        receipt = read_json(receipt_path)
        receipt["plan"].pop("source")
        save_json(receipt_path, receipt)
        project.save_state(state)
        self.assertEqual(self.cli(*args, "--reconcile")[0], 0)
        recovered = project.state()["resources"]["kb:support"]
        self.assertEqual(recovered["status"], "ready")
        self.assertEqual(recovered["source"]["directory"], "kb")
        self.assertNotIn("kb:support", project.status()["local_changes"])

    def test_upload_binding_rejects_directory_and_kb_id_switch(self):
        project = self.pull()
        args = self.upload_args(project)
        _, plan = self.cli(*args, "--dry-run")
        self.cli(*args, "--expect", plan["token"])
        self.assertNotEqual(self.cli(*args, "--reconcile", "--kb-id", "kb-two")[0], 0)
        other = project.root / "other-kb"
        other.mkdir()
        (other / "faq.md").write_text("Different source")
        self.assertNotEqual(self.cli(*args, "--dir", str(other), "--dry-run")[0], 0)

    def test_managed_kb_add_edit_delete_invalidate_revision_and_readiness(self):
        project = self.setup_evidence()
        args = self.upload_args(project)
        _, plan = self.cli(*args, "--dry-run")
        self.assertEqual(self.cli(*args, "--expect", plan["token"])[0], 0)
        self.api.agent["unified_tools"] = [{"id": "kb", "type": "knowledge_base", "knowledge_node_ids": ["kb-one"]}]
        # Reconcile local Agent proposal to the now-observed remote tool.
        self.cli("agent", "pull", "--agent", "a", "--reconcile")
        local = read_json(project.path("agent"))
        local["unified_tools"] = self.api.agent["unified_tools"]
        save_json(project.path("agent"), local)
        base = project.revision()
        source = project.root / "kb/faq.md"
        for action in (lambda: source.write_text("Changed"), lambda: source.unlink(), lambda: (source.parent / "new.md").write_text("New")):
            action()
            self.assertNotEqual(project.revision(), base)
            self.assertIn("kb:support", project.status()["local_changes"])
            with self.api.client() as client:
                with self.assertRaisesRegex(ProjectError, "KB.*local|local.*KB"):
                    ensure_ready(project, snapshot(project, client, "h1"))

    def test_reauditing_cannot_clear_unapplied_direct_file_source_changes(self):
        project = self.setup_evidence()
        args = self.upload_args(project)
        _, plan = self.cli(*args, "--dry-run")
        self.cli(*args, "--expect", plan["token"])
        local = read_json(project.path("agent"))
        local["unified_tools"] = [{"id": "kb", "type": "knowledge_base", "knowledge_node_ids": ["file-new"]}]
        save_json(project.path("agent"), local)
        _, plan = self.cli("agent", "apply", "--dry-run")
        self.assertEqual(self.cli("agent", "apply", "--expect", plan["token"])[0], 0)
        self.audit(project)
        self.assertEqual(self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")[0], 0)
        (project.root / "kb/faq.md").write_text("Changed source")
        self.audit(project)
        self.assertNotEqual(self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")[0], 0)
        self.assertNotEqual(self.cli("agent", "publish", "--history", "h1", "--dry-run")[0], 0)
