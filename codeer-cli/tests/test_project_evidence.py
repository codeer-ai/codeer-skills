from codeer_cli.evidence import classify
from codeer_cli.project import fingerprint, read_json, save_json
import unittest
import httpx

from test_project_eval import EvalFixture


class EvidenceFixture(EvalFixture):
    def setup_evidence(self):
        project, design = self.prepare()
        self.apply_design()
        acceptance = {"pairs": [{"case": c["local_id"], "tester": "tools"} for c in design["cases"]]}
        source = project.root / "reviews/acceptance.md"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("Synthetic fixture approval for both pairs; minimum score 1.")
        acceptance["confirmation"] = {"source": "reviews/acceptance.md", "source_fingerprint": fingerprint(source.read_text()), "scope_fingerprint": fingerprint(acceptance)}
        save_json(project.path("acceptance"), acceptance)
        self.audit(project)
        return project

    def audit(self, project, history_id="h1"):
        out = project.root / "reviews/anchor.json"
        self.assertEqual(self.cli("eval", "snapshot", "--history", history_id, "--out", str(out))[0], 0)
        anchor = read_json(out)
        report = project.root / "reviews/audit.md"
        report.write_text("Synthetic SOP aligned; tools and evidence delivery reviewed.")
        save_json(project.root / "reviews/current.audit.json", {"schema_version": 1, "conclusion": "pass",
                  "revision": anchor["revision"], "remote_fingerprint": anchor["remote_fingerprint"], "history_id": history_id,
                  "pairs": anchor["snapshot"]["pairs"], "report": "reviews/audit.md", "report_fingerprint": fingerprint(report.read_text())})


class EvidenceTests(EvidenceFixture, unittest.TestCase):
    def test_complete_run_and_publication_are_exact_and_read_back(self):
        project = self.setup_evidence()
        self.assertEqual(self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")[0], 0)
        code, plan = self.cli("agent", "publish", "--history", "h1", "--dry-run")
        self.assertEqual(code, 0, plan)
        before = sum(path.endswith(":publish") for _, path, _ in self.api.calls)
        self.assertEqual(before, 0)
        code, release = self.cli("agent", "publish", "--history", "h1", "--expect", plan["token"])
        self.assertEqual(code, 0)
        self.assertEqual(release["status"], "published")
        self.assertEqual(release["actual_history_id"], "h1")
        self.assertEqual(len(list((project.root / "runs").glob("*/run.json"))), 1)

    def test_same_version_old_results_never_complete_new_run(self):
        project = self.setup_evidence()
        self.assertEqual(self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")[0], 0)
        self.api.run_mode = "old_only"
        code, result = self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")
        self.assertEqual(code, 1)
        self.assertEqual(result["counts"], {"missing": 2})
        self.assertEqual(len(list((project.root / "runs").glob("*/run.json"))), 2)

    def test_missing_evidence_error_skip_and_wrong_history(self):
        self.setup_evidence()
        for mode, state in (("missing_evidence", "unjudgeable"), ("error", "error"), ("skip", "skipped"), ("wrong_history", "missing"), ("pending", "missing"), ("failed", "failed")):
            self.api.run_mode = mode
            code, result = self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")
            self.assertEqual(code, 1, mode)
            self.assertEqual(result["counts"], {state: 2}, mode)

    def test_focused_run_cannot_publish_full_scope_and_changes_stale_audit(self):
        project = self.setup_evidence()
        self.assertEqual(self.cli("eval", "run", "--history", "h1", "--cases", "c1", "--poll-timeout", "0")[0], 0)
        self.assertEqual(self.cli("agent", "publish", "--history", "h1", "--dry-run")[0], 2)
        project.path("instructions").write_text("changed")
        self.assertEqual(self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")[0], 2)

    def test_tester_rubric_changes_invalidate_remote_audit(self):
        self.setup_evidence()
        self.api.testers["t1"]["system_prompt_template"] = "web edit"
        self.assertEqual(self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")[0], 2)
        self.assertFalse(any(p == "/external/eval/runs" for _, p, _ in self.api.calls))

    def test_publish_readback_mismatch_and_unknown_outcome_keep_releases(self):
        project = self.setup_evidence()
        self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")
        _, plan = self.cli("agent", "publish", "--history", "h1", "--dry-run")
        self.api.run_mode = "publish_mismatch"
        code, result = self.cli("agent", "publish", "--history", "h1", "--expect", plan["token"])
        self.assertEqual(code, 1)
        self.assertEqual(result["status"], "readback_mismatch")
        self.assertEqual(self.cli("agent", "publish", "--history", "h1", "--reconcile")[0], 0)
        _, plan = self.cli("agent", "publish", "--history", "h1", "--dry-run")
        self.api.run_mode = "publish_timeout"
        self.assertEqual(self.cli("agent", "publish", "--history", "h1", "--expect", plan["token"])[0], 1)
        records = [read_json(p) for p in project.release_paths()]
        self.assertIn("outcome_unknown", [r["status"] for r in records])
        self.assertEqual(self.cli("agent", "publish", "--history", "h1", "--dry-run")[0], 2)
        self.assertEqual(self.cli("agent", "publish", "--history", "h1", "--reconcile")[0], 0)

    def test_exact_run_export_does_not_trigger_again(self):
        project = self.setup_evidence()
        _, result = self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")
        before = self.api.run_number
        code, exported = self.cli("eval", "export", "--run-id", result["id"], "--out-dir", str(project.root / "export"))
        self.assertEqual(code, 0)
        self.assertEqual(exported["status"], "passed")
        self.assertEqual(self.api.run_number, before)

    def test_sources_and_delivery_reports_are_required_and_revision_bound(self):
        project = self.setup_evidence()
        report = project.root / "reviews/evidence.md"
        report.unlink()
        self.assertEqual(self.cli("validate")[0], 1)
        self.assertEqual(self.cli("eval", "cases-apply", "--dry-run")[0], 2)
        report.write_text("Changed evidence delivery, requires semantic re-review")
        self.assertEqual(self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")[0], 2)

    def test_saved_run_export_keeps_original_threshold_and_evidence_policy(self):
        project = self.setup_evidence()
        acceptance = read_json(project.path("acceptance"))
        for pair in acceptance["pairs"]:
            pair["minimum_score"] = 0.5
        save_json(project.path("acceptance"), acceptance)
        self.audit(project)
        self.api.run_mode = "failed"
        # A declared threshold can differ from perfect; exercise it with real rows.
        original = self.api.handler
        def scored(request):
            response = original(request)
            for row in self.api.results:
                row["score"] = 0.7
            if request.url.path.endswith("results:batch"):
                return httpx.Response(200, json={"data": self.api.results, "error_code": 0})
            return response
        self.api.handler = scored
        code, run = self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")
        self.assertEqual(code, 0)
        for pair in acceptance["pairs"]:
            pair["minimum_score"] = 1
        save_json(project.path("acceptance"), acceptance)
        code, exported = self.cli("eval", "export", "--run-id", run["id"], "--out-dir", str(project.root / "export"))
        self.assertEqual(code, 1)  # local evidence changed, historical classification remains intact
        self.assertEqual(exported["counts"], {"passed": 2})
        record = read_json(project.root / "runs" / run["id"] / "run.json")
        self.assertEqual({p["minimum_score"] for p in record["results"]}, {0.5})

    def test_tool_evidence_is_not_claim_text(self):
        self.assertEqual(classify({"status": "finished", "score": 1, "output": "Transferred"}, ["tool_steps"]), "unjudgeable")
        self.assertEqual(classify({"status": "finished", "score": 0, "reasoning_steps": []}, ["tool_steps"]), "failed")
        self.assertEqual(classify({"status": "finished", "score": 1, "reasoning_steps": [{"tool": "handoff", "status": "success"}]}, ["tool_steps"]), "passed")
        self.assertEqual(classify({"status": "finished", "score": 0, "reasoning_steps": [{"tool": "wrong"}]}, ["tool_steps"]), "failed")

    def test_duplicate_results_and_changes_during_run_are_not_pass(self):
        self.setup_evidence()
        for mode in ("duplicate", "change_during_run"):
            self.api.run_mode = mode
            code, result = self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")
            self.assertEqual(code, 1)
            self.assertNotEqual(result["status"], "passed")

    def test_interrupted_trigger_keeps_evidence_and_prevents_blind_retry(self):
        project = self.setup_evidence()
        self.api.run_mode = "trigger_timeout"
        self.assertEqual(self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")[0], 1)
        paths = list((project.root / "runs").glob("*/run.json"))
        record = read_json(paths[0])
        self.assertEqual(record["status"], "outcome_unknown")
        self.assertTrue(record["planned_pairs"])
        before = self.api.run_number
        self.assertEqual(self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")[0], 2)
        self.assertEqual(self.api.run_number, before)
        code, exported = self.cli("eval", "export", "--run-id", record["id"], "--out-dir", str(project.root / "export"))
        self.assertEqual(code, 1)
        self.assertEqual(exported["status"], "outcome_unknown")

    def test_offline_status_marks_unapplied_and_stale_evidence(self):
        project = self.setup_evidence()
        self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")
        project.path("instructions").write_text("Local revision")
        _, status = self.cli("status")
        self.assertIn("agent.system_prompt", status["local_changes"])
        self.assertTrue(status["latest_run"]["local_stale"])
        self.assertFalse(status["audit"]["local_revision_valid"])
