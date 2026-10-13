"""Third review: design authority, explicit retirement, ignores and release identity."""
from copy import deepcopy
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

import httpx

from codeer_cli.project import Project, read_json, save_json
from test_project_evidence import EvidenceFixture


class RetirementReviewTests(EvidenceFixture, unittest.TestCase):
    def deletion_handler(self, request):
        if request.method == "DELETE" and "/eval/cases/" in request.url.path:
            sid = request.url.path.rsplit("/", 1)[1]
            self.api.calls.append(("DELETE", request.url.path, None))
            self.api.cases.pop(sid)
            self.api.pairs.pop(sid, None)
            return httpx.Response(200, json={"data": {}, "error_code": 0})
        return self.original_handler(request)

    def test_alternate_design_cannot_diverge_from_canonical_proposal(self):
        project, design = self.prepare()
        self.apply_design()
        alternate = project.root / "reviews/revised-design.json"
        revised = deepcopy(design)
        revised["cases"][0]["input"] = "Reviewed replacement wording"
        save_json(alternate, revised)
        before = deepcopy(self.api.cases)
        local = project.path("evals").read_bytes()
        state = (project.root / ".codeer/state.json").read_bytes()
        for extra in (("--dry-run",), ("--expect", "unreviewed")):
            self.assertEqual(self.cli("eval", "cases-apply", "--cases", str(alternate), *extra)[0], 2)
        self.assertEqual(self.api.cases, before)
        self.assertEqual(project.path("evals").read_bytes(), local)
        self.assertEqual((project.root / ".codeer/state.json").read_bytes(), state)

    def test_configured_custom_design_is_the_authority_for_default_and_explicit_apply(self):
        project, design = self.prepare()
        custom = project.root / "reviews/adopted-design.json"
        save_json(custom, design)
        manifest = project.root / "project.toml"
        manifest.write_text(manifest.read_text().replace("[paths]\n", '[paths]\nevals = "reviews/adopted-design.json"\n'))
        project = Project.load(project.root)
        self.assertEqual(project.path("evals"), custom)
        # The old default file cannot silently override the adopted design.
        self.assertEqual(self.cli("eval", "cases-apply", "--cases", "evals/design.json", "--dry-run")[0], 2)
        code, plan = self.cli("eval", "cases-apply", "--cases", str(custom), "--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(self.cli("eval", "cases-apply", "--expect", plan["token"])[0], 0)
        _, unchanged = self.cli("eval", "cases-apply", "--dry-run")
        self.assertFalse(any(p["changed"] for p in unchanged["plans"]))

    def test_existing_gitignore_protects_private_outputs_and_is_idempotent(self):
        root = Path(self.temp.name) / "existing-repository"
        root.mkdir()
        original = "# Existing repository rules\n.venv/\n!runs/"  # No final newline.
        (root / ".gitignore").write_text(original)
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        self.assertEqual(self.cli("init", str(root), "--legacy")[0], 0)
        first = (root / ".gitignore").read_bytes()
        self.assertTrue(first.decode().startswith(original + "\n"))
        private = [".codeer/state.json", "sources/history/import/raw.json", "runs/example/run.json", "releases/example/raw-response.json", "sources/documents/sop.pdf"]
        result = subprocess.run(["git", "check-ignore", "--stdin"], cwd=root, input="\n".join(private), text=True, capture_output=True, check=False)
        self.assertEqual(result.stdout.splitlines(), private)
        self.assertEqual(self.cli("init", str(root))[0], 0)
        self.assertEqual((root / ".gitignore").read_bytes(), first)

    def test_init_restores_final_ignore_defaults_after_appended_negation(self):
        root = Path(self.temp.name)
        ignore = root / ".gitignore"
        ignore.write_text(ignore.read_text() + "# Authored rule\n!.codeer/\n")
        self.assertEqual(self.cli("init")[1]["updated"], [".gitignore"])
        self.assertIn("# Authored rule\n!.codeer/\n", ignore.read_text())
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        self.assertEqual(subprocess.run(["git", "check-ignore", ".codeer/state.json"], cwd=root, capture_output=True).returncode, 0)
        self.assertEqual(self.cli("init")[1]["updated"], [])

    def test_init_preserves_existing_ignore_bytes_and_line_endings(self):
        root = Path(self.temp.name)
        ignore = root / ".gitignore"
        original = b"# Existing rules\r\n.venv/\r\n# Legacy comment: \xff\r\n"
        ignore.write_bytes(original)
        self.assertEqual(self.cli("init")[0], 0)
        combined = ignore.read_bytes()
        self.assertTrue(combined.startswith(original))
        self.assertEqual(self.cli("init")[0], 0)
        self.assertEqual(ignore.read_bytes(), combined)

    def publish_h1(self):
        project = self.setup_evidence()
        self.assertEqual(self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")[0], 0)
        code, plan = self.cli("agent", "publish", "--history", "h1", "--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(self.cli("agent", "publish", "--history", "h1", "--expect", plan["token"])[0], 0)
        return project

    def test_older_release_does_not_clear_new_history_after_passing_run(self):
        project = self.publish_h1()
        self.api.history_id = "h2"
        self.audit(project, "h2")
        self.assertEqual(self.cli("eval", "run", "--history", "h2", "--poll-timeout", "0")[0], 0)
        status = self.cli("status")[1]
        self.assertEqual(status["latest_run"]["history_id"], "h2")
        self.assertEqual(status["latest_release"]["plan"]["history_id"], "h1")
        self.assertIn("publish only", status["next_step"])

    def test_older_release_does_not_clear_new_revision_or_remote_configuration(self):
        project = self.publish_h1()
        project.path("design").parent.mkdir(parents=True, exist_ok=True)
        project.path("design").write_text("New accepted behavior documentation")
        self.audit(project)
        self.assertEqual(self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")[0], 0)
        self.assertIn("publish only", self.cli("status")[1]["next_step"])
        # Keep this revision but create a matching release to isolate the next change.
        _, plan = self.cli("agent", "publish", "--history", "h1", "--dry-run")
        self.assertEqual(self.cli("agent", "publish", "--history", "h1", "--expect", plan["token"])[0], 0)
        self.api.testers["t1"]["description"] = "Reviewed remote change"
        self.assertEqual(self.cli("eval", "pull", "--reconcile")[0], 0)
        self.audit(project)
        self.assertEqual(self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")[0], 0)
        self.assertIn("publish only", self.cli("status")[1]["next_step"])

    def test_matching_release_remains_current_after_rerun_of_same_configuration(self):
        self.publish_h1()
        self.assertEqual(self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")[0], 0)
        self.assertIn("readback is complete", self.cli("status")[1]["next_step"])

    def test_known_new_history_invalidates_old_run_before_new_run_exists(self):
        project = self.publish_h1()
        self.api.history_id = "h2"
        self.audit(project, "h2")
        status = self.cli("status")[1]
        self.assertTrue(status["latest_run"]["remote_stale_at_last_query"])
        self.assertNotIn("readback is complete", status["next_step"])

    def test_deleted_case_can_be_retired_and_other_resources_reconciled(self):
        project, design = self.prepare()
        self.apply_design()
        sid = project.state()["resources"]["case:handoff"]["server_id"]
        authored = project.path("evals").read_bytes()
        self.original_handler = self.api.handler
        with patch.object(self.api, "handler", side_effect=self.deletion_handler):
            self.assertEqual(self.cli("eval", "case-delete", "--case", sid)[0], 0)
        self.assertNotIn(sid, self.api.cases)
        self.assertEqual(project.path("evals").read_bytes(), authored)
        resources = project.state()["resources"]
        for key in ("case:handoff", "pairs:handoff"):
            self.assertEqual(resources[key]["status"], "retired")
            self.assertEqual(resources[key]["server_id"], sid)
        receipt = read_json(project.root / resources["case:handoff"]["delete_receipt"])
        self.assertEqual(receipt["status"], "retired")
        self.assertTrue(receipt["readback"]["absent"])
        self.assertEqual(self.cli("eval", "cases-apply", "--dry-run")[0], 2)
        design["cases"] = design["cases"][1:]
        save_json(project.path("evals"), design)
        self.assertEqual(self.cli("eval", "pull", "--reconcile")[0], 0)
        self.assertEqual(project.state()["resources"]["case:handoff"]["status"], "retired")
        self.assertEqual(self.cli("eval", "cases-apply", "--dry-run")[0], 0)

    def prepare_deletion(self):
        project, design = self.prepare()
        self.apply_design()
        self.original_handler = self.api.handler
        return project, design, project.state()["resources"]["case:handoff"]["server_id"]

    def test_delete_is_journaled_before_request_and_dry_run_is_read_only(self):
        project, _, sid = self.prepare_deletion()
        before = (project.root / ".codeer/state.json").read_bytes()
        files = set((project.root / ".codeer/receipts").glob("*.json"))
        code, preview = self.cli("eval", "case-delete", "--case", sid, "--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(preview["case_id"], sid)
        self.assertIn("input_preview", preview["current"])
        self.assertNotIn("input", preview["current"])
        self.assertIn(sid, self.api.cases)
        self.assertFalse(any(method == "DELETE" for method, _, _ in self.api.calls))
        self.assertEqual((project.root / ".codeer/state.json").read_bytes(), before)
        self.assertEqual(set((project.root / ".codeer/receipts").glob("*.json")), files)
        def handler(request):
            if request.method == "DELETE":
                entries = project.state()["resources"]
                for key in ("case:handoff", "pairs:handoff"):
                    self.assertEqual(entries[key]["status"], "pending")
                receipt = read_json(project.root / entries["case:handoff"]["delete_receipt"])
                self.assertEqual(receipt["status"], "pending")
                self.assertEqual(receipt["scope"]["agent_id"], "a")
            return self.deletion_handler(request)
        with patch.object(self.api, "handler", side_effect=handler):
            self.assertEqual(self.cli("eval", "case-delete", "--case", sid)[0], 0)

    def test_unknown_committed_delete_reconciles_absence_without_repeating_delete(self):
        project, _, sid = self.prepare_deletion()
        def handler(request):
            response = self.deletion_handler(request)
            if request.method == "DELETE":
                raise httpx.ReadTimeout("delete response lost", request=request)
            return response
        with patch.object(self.api, "handler", side_effect=handler):
            self.assertEqual(self.cli("eval", "case-delete", "--case", sid)[0], 1)
        entry = project.state()["resources"]["case:handoff"]
        self.assertEqual(entry["status"], "outcome_unknown")
        path = project.root / entry["delete_receipt"]
        original = read_json(path)
        self.assertEqual(self.cli("eval", "pull")[0], 0)
        self.assertEqual(project.state()["resources"]["case:handoff"]["status"], "outcome_unknown")
        for extra in ((), ("--dry-run",)):
            self.assertEqual(self.cli("eval", "case-delete", "--case", sid, *extra)[0], 2)
        mutations = [(m, path) for m, path, _ in self.api.calls if m != "GET" and not path.endswith(":batch")]
        self.assertEqual(self.cli("eval", "pull", "--reconcile")[0], 0)
        # Eval readback uses POST batch queries; count DELETE specifically.
        self.assertEqual(sum(m == "DELETE" for m, _, _ in self.api.calls), 1)
        self.assertEqual([(m, path) for m, path, _ in self.api.calls if m != "GET" and not path.endswith(":batch")], mutations)
        stored = read_json(path)
        self.assertEqual(stored["status"], original["status"])
        self.assertEqual(stored["error"], original["error"])
        self.assertEqual(stored["reconciliation"]["status"], "retired")
        self.assertEqual(project.state()["resources"]["pairs:handoff"]["status"], "retired")

    def test_uncommitted_delete_reconciles_presence_and_requires_explicit_retry(self):
        project, _, sid = self.prepare_deletion()
        def handler(request):
            if request.method == "DELETE":
                self.api.calls.append(("DELETE", request.url.path, None))
                raise httpx.ReadTimeout("request not committed", request=request)
            return self.original_handler(request)
        with patch.object(self.api, "handler", side_effect=handler):
            self.assertEqual(self.cli("eval", "case-delete", "--case", sid)[0], 1)
        self.assertEqual(self.cli("eval", "pull", "--reconcile")[0], 0)
        self.assertIn(sid, self.api.cases)
        self.assertEqual(sum(m == "DELETE" for m, _, _ in self.api.calls), 1)
        self.assertNotIn("delete_receipt", project.state()["resources"]["case:handoff"])
        self.assertEqual(self.cli("eval", "cases-apply", "--dry-run")[0], 0)
        with patch.object(self.api, "handler", side_effect=self.deletion_handler):
            self.assertEqual(self.cli("eval", "case-delete", "--case", sid)[0], 0)

    def test_delete_readback_mismatch_can_be_observed_without_repeating_write(self):
        project, _, sid = self.prepare_deletion()
        def handler(request):
            if request.method == "DELETE":
                self.api.calls.append(("DELETE", request.url.path, None))
                return httpx.Response(200, json={"data": {}, "error_code": 0})
            return self.original_handler(request)
        with patch.object(self.api, "handler", side_effect=handler):
            code, receipt = self.cli("eval", "case-delete", "--case", sid)
        self.assertEqual((code, receipt["status"]), (1, "readback_mismatch"))
        self.assertFalse(receipt["readback"]["absent"])
        self.assertEqual(self.cli("eval", "case-delete", "--case", sid)[0], 2)
        self.assertEqual(self.cli("eval", "pull", "--reconcile")[0], 0)
        self.assertEqual(sum(m == "DELETE" for m, _, _ in self.api.calls), 1)
        stored = read_json(project.root / project.state()["resources"]["case:handoff"]["last_delete_receipt"])
        self.assertEqual(stored["status"], "readback_mismatch")
        self.assertEqual(stored["readback"], receipt["readback"])

    def test_unrecorded_disappearance_is_not_implicitly_retired(self):
        project, _, sid = self.prepare_deletion()
        self.api.cases.pop(sid)
        self.assertEqual(self.cli("eval", "pull", "--reconcile")[0], 2)
        self.assertNotEqual(project.state()["resources"]["case:handoff"]["status"], "retired")
        self.assertNotIn("delete_receipt", project.state()["resources"]["case:handoff"])

    def test_retired_case_does_not_block_later_tester_unknown_outcome_recovery(self):
        project, design, sid = self.prepare_deletion()
        with patch.object(self.api, "handler", side_effect=self.deletion_handler):
            self.assertEqual(self.cli("eval", "case-delete", "--case", sid)[0], 0)
        design["cases"] = design["cases"][1:]
        save_json(project.path("evals"), design)
        tid = project.state()["resources"]["tester:tools"]["server_id"]
        args = ("eval", "evaluator-update", "--evaluator", tid, "--name", "Reviewed new name")
        _, plan = self.cli(*args, "--dry-run")
        fail_get = False
        def handler(request):
            nonlocal fail_get
            if request.url.path.endswith("/evaluators/" + tid):
                if request.method == "GET" and fail_get:
                    fail_get = False
                    raise httpx.ReadTimeout("update readback lost", request=request)
                if request.method == "PUT":
                    fail_get = True
            return self.original_handler(request)
        with patch.object(self.api, "handler", side_effect=handler):
            self.assertEqual(self.cli(*args, "--expect", plan["token"])[0], 1)
        self.assertEqual(self.cli("eval", "pull", "--reconcile")[0], 0)
        self.assertEqual(project.state()["resources"]["tester:tools"]["status"], "imported_unvalidated")
        self.assertEqual(project.state()["resources"]["case:handoff"]["status"], "retired")

    def test_retired_local_id_cannot_be_reused_for_implicit_creation_or_update(self):
        project, _, sid = self.prepare_deletion()
        with patch.object(self.api, "handler", side_effect=self.deletion_handler):
            self.assertEqual(self.cli("eval", "case-delete", "--case", sid)[0], 0)
        self.assertEqual(self.cli("validate")[0], 1)
        self.assertEqual(self.cli("eval", "case-update", "--case", sid, "--input", "Recreate?", "--dry-run")[0], 2)
        self.assertEqual(self.cli("eval", "cases-apply", "--dry-run")[0], 2)
        self.assertNotIn(sid, self.api.cases)

    def test_pending_delete_scope_mismatch_does_not_retire_or_repeat_delete(self):
        project, _, sid = self.prepare_deletion()
        def handler(request):
            response = self.deletion_handler(request)
            if request.method == "DELETE":
                raise httpx.ReadTimeout("lost", request=request)
            return response
        with patch.object(self.api, "handler", side_effect=handler):
            self.assertEqual(self.cli("eval", "case-delete", "--case", sid)[0], 1)
        path = project.root / project.state()["resources"]["case:handoff"]["delete_receipt"]
        receipt = read_json(path)
        receipt["scope"]["workspace_id"] = "other"
        save_json(path, receipt)
        self.assertEqual(self.cli("eval", "pull", "--reconcile")[0], 2)
        self.assertEqual(project.state()["resources"]["case:handoff"]["status"], "outcome_unknown")
        self.assertEqual(sum(m == "DELETE" for m, _, _ in self.api.calls), 1)

    def test_delete_readback_auth_error_stays_unknown_until_confirmed_absent(self):
        project, _, sid = self.prepare_deletion()
        def handler(request):
            if request.method == "GET" and request.url.path.endswith("/cases/" + sid) and sid not in self.api.cases:
                return httpx.Response(403, json={"message": "Not authorized"})
            return self.deletion_handler(request)
        with patch.object(self.api, "handler", side_effect=handler):
            self.assertEqual(self.cli("eval", "case-delete", "--case", sid)[0], 3)
            self.assertEqual(self.cli("eval", "pull", "--reconcile")[0], 3)
        self.assertEqual(project.state()["resources"]["case:handoff"]["status"], "outcome_unknown")
        self.assertEqual(self.cli("eval", "pull", "--reconcile")[0], 0)
        self.assertEqual(project.state()["resources"]["case:handoff"]["status"], "retired")

    def test_pair_identity_or_scope_mismatch_blocks_delete_before_write(self):
        project, _, sid = self.prepare_deletion()
        original = deepcopy(project.state())
        for field, value in (("server_id", "other-case"), ("scope", {"workspace_id": "other"}), ("status", "outcome_unknown")):
            state = deepcopy(original)
            state["resources"]["pairs:handoff"][field] = value
            project.save_state(state)
            for extra in ((), ("--dry-run",)):
                self.assertEqual(self.cli("eval", "case-delete", "--case", sid, *extra)[0], 2)
        self.assertFalse(any(m == "DELETE" for m, _, _ in self.api.calls))

    def test_retired_identity_unexpectedly_present_is_not_silently_reimported(self):
        project, _, sid = self.prepare_deletion()
        old_case = deepcopy(self.api.cases[sid])
        with patch.object(self.api, "handler", side_effect=self.deletion_handler):
            self.assertEqual(self.cli("eval", "case-delete", "--case", sid)[0], 0)
        self.api.cases[sid] = old_case
        for extra in ((), ("--reconcile",)):
            self.assertEqual(self.cli("eval", "pull", *extra)[0], 2)
        self.assertEqual(project.state()["resources"]["case:handoff"]["status"], "retired")

    def test_intentional_new_local_id_creates_new_case_without_reusing_retired_identity(self):
        project, design, sid = self.prepare_deletion()
        with patch.object(self.api, "handler", side_effect=self.deletion_handler):
            self.assertEqual(self.cli("eval", "case-delete", "--case", sid)[0], 0)
        design["cases"][0]["local_id"] = "handoff-replacement"
        save_json(project.path("evals"), design)
        code, plan = self.cli("eval", "cases-apply", "--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(self.cli("eval", "cases-apply", "--expect", plan["token"])[0], 0)
        entries = project.state()["resources"]
        self.assertNotEqual(entries["case:handoff-replacement"]["server_id"], sid)
        self.assertEqual(entries["case:handoff"]["status"], "retired")
        self.assertNotIn(sid, self.api.cases)


if __name__ == "__main__":
    unittest.main()
