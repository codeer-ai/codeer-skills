"""Logical references stay consistent across apply, pull, recovery and status."""
import copy
import os
import unittest
from unittest.mock import patch

import httpx

from codeer_cli.project import discover, read_json, save_json
from test_project_evidence import EvidenceFixture


class CrossEntryRegressionTests(EvidenceFixture, unittest.TestCase):
    def prepare_environment_model(self):
        project, design = self.prepare()
        environment = patch.dict(os.environ, {"CROSS_ENTRY_JUDGE": "judge-1"})
        environment.start()
        self.addCleanup(environment.stop)
        design["testers"][0]["judge_llm_model_id"] = "env:CROSS_ENTRY_JUDGE"
        save_json(project.path("evals"), design)
        return project

    def interrupted_tester_create(self):
        project = self.prepare_environment_model()
        code, plan = self.cli("eval", "cases-apply", "--dry-run")
        self.assertEqual(code, 0, plan)
        original = self.api.handler

        def lose_readback(request):
            if request.method == "GET" and request.url.path.endswith("/evaluators/t1"):
                raise httpx.ReadTimeout("Created identity known; readback interrupted", request=request)
            return original(request)

        with patch.object(self.api, "handler", side_effect=lose_readback):
            self.assertEqual(self.cli("eval", "cases-apply", "--expect", plan["token"])[0], 1)
        entry = project.state()["resources"]["tester:tools"]
        self.assertEqual((entry["status"], entry["server_id"]), ("outcome_unknown", "t1"))
        return project

    def remove_tester_pair(self):
        project, design = self.prepare()
        design["testers"].append({**copy.deepcopy(design["testers"][0]),
                                  "local_id": "alternate", "name": "Alternate Judge"})
        design["cases"][0]["pairs"].append({"tester": "alternate", "rubric": "Call handoff",
                                             "required_evidence": ["tool_steps"]})
        save_json(project.path("evals"), design)
        self.apply_design()
        design["cases"][0]["pairs"] = design["cases"][0]["pairs"][1:]
        design["cases"][0]["remove_tester_ids"] = ["tester:tools"]
        save_json(project.path("evals"), design)
        self.assertIn("pairs:handoff", project.status()["local_changes"])
        self.apply_design()
        return project

    def test_environment_model_apply_pull_status_and_preview_stay_aligned(self):
        project = self.prepare_environment_model()
        self.apply_design()
        authored = project.path("evals").read_bytes()
        remote = copy.deepcopy((self.api.testers, self.api.cases, self.api.pairs))
        self.assertEqual(self.cli("eval", "pull")[0], 0)
        code, status = self.cli("status")
        self.assertEqual(code, 0)
        self.assertEqual(status["local_changes"], [])
        self.assertNotEqual(status["next_action"]["code"], "review_local_changes")
        entry = discover().state()["resources"]["tester:tools"]
        self.assertEqual(entry["observed"]["judge_llm_model_id"], "env:CROSS_ENTRY_JUDGE")
        proposals = list((project.root / "reviews").glob("*.import-design.json"))
        self.assertEqual(len(proposals), 1)
        self.assertEqual(read_json(proposals[0])["testers"][0]["judge_llm_model_id"], "env:CROSS_ENTRY_JUDGE")
        self.assertEqual(self.cli("eval", "pull")[0], 0)
        self.assertEqual(list((project.root / "reviews").glob("*.import-design.json")), proposals)
        code, plan = self.cli("eval", "cases-apply", "--dry-run")
        self.assertEqual(code, 0, plan)
        self.assertFalse(any(row["changed"] or row["conflicts"] for row in plan["plans"]))
        self.assertEqual(project.path("evals").read_bytes(), authored)
        self.assertEqual((self.api.testers, self.api.cases, self.api.pairs), remote)

    def test_environment_model_known_create_recovers_without_duplicate_or_pin_rewrite(self):
        project = self.interrupted_tester_create()
        entry = project.state()["resources"]["tester:tools"]
        original_receipt = project.root / entry["receipt"]
        original_bytes = original_receipt.read_bytes()
        (project.root / "reviews/recovery.md").write_text(f"Pinned interruption: {entry['receipt']}\n")
        authored = project.path("evals").read_bytes()
        remote = copy.deepcopy((self.api.testers, self.api.cases, self.api.pairs))
        self.assertEqual(self.cli("eval", "pull", "--reconcile")[0], 0)
        entry = project.state()["resources"]["tester:tools"]
        self.assertEqual(entry["status"], "imported_unvalidated")
        self.assertEqual(entry["server_id"], "t1")
        self.assertEqual(entry["observed"]["judge_llm_model_id"], "env:CROSS_ENTRY_JUDGE")
        recovered = read_json(project.root / entry["receipt"])
        self.assertTrue(recovered["reconciliation"]["payload_matches"])
        self.assertEqual(original_receipt.read_bytes(), original_bytes)
        self.assertNotEqual(project.root / entry["receipt"], original_receipt)
        self.assertEqual(project.path("evals").read_bytes(), authored)
        self.assertEqual((self.api.testers, self.api.cases, self.api.pairs), remote)
        self.apply_design()
        self.assertEqual(sum(method == "POST" and path == "/external/eval/evaluators"
                             for method, path, _ in self.api.calls), 1)
        self.assertEqual(project.status()["local_changes"], [])
        self.audit(project)
        self.assertEqual(self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")[0], 0)

    def test_recovery_keeps_a_genuinely_different_tester_unresolved(self):
        project = self.interrupted_tester_create()
        self.api.testers["t1"]["name"] = "Changed remotely after interruption"
        self.assertEqual(self.cli("eval", "pull", "--reconcile")[0], 0)
        entry = project.state()["resources"]["tester:tools"]
        self.assertEqual(entry["status"], "outcome_unknown")
        self.assertEqual(entry["observed"]["judge_llm_model_id"], "env:CROSS_ENTRY_JUDGE")
        code, plan = self.cli("eval", "cases-apply", "--dry-run")
        self.assertNotEqual(code, 0)
        self.assertIn("tester:tools", plan["conflicts"])
        self.assertEqual(len(self.api.testers), 1)

    def test_recovery_does_not_accept_a_changed_model_environment(self):
        project = self.interrupted_tester_create()
        with patch.dict(os.environ, {"CROSS_ENTRY_JUDGE": "another-model"}):
            self.assertEqual(self.cli("eval", "pull", "--reconcile")[0], 0)
            entry = project.state()["resources"]["tester:tools"]
            self.assertEqual(entry["status"], "outcome_unknown")
            self.assertEqual(entry["observed"]["judge_llm_model_id"], "judge-1")
        self.assertEqual(self.cli("eval", "pull", "--reconcile")[0], 0)
        self.assertEqual(project.state()["resources"]["tester:tools"]["status"], "imported_unvalidated")
        self.assertEqual(len(self.api.testers), 1)

    def test_removed_pair_stays_clean_through_pull_preview_and_exact_run(self):
        project = self.remove_tester_pair()
        entry = project.state()["resources"]["pairs:handoff"]
        removed = project.state()["resources"]["tester:tools"]["server_id"]
        self.assertIn(removed, entry["removed_ids"])
        self.assertEqual(self.cli("eval", "pull")[0], 0)
        code, status = self.cli("status")
        self.assertEqual(code, 0)
        self.assertEqual(status["local_changes"], [])
        self.assertNotEqual(status["next_action"]["code"], "review_local_changes")
        code, plan = self.cli("eval", "cases-apply", "--dry-run")
        self.assertEqual(code, 0, plan)
        self.assertFalse(any(row["changed"] for row in plan["plans"]))
        self.audit(project)
        code, run = self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")
        self.assertEqual(code, 0, run)
        self.assertEqual(run["counts"], {"passed": 2})

    def test_remote_reintroduction_of_removed_pair_still_blocks_apply_and_run(self):
        project = self.remove_tester_pair()
        resources = project.state()["resources"]
        case = resources["case:handoff"]["server_id"]
        tester = resources["tester:tools"]["server_id"]
        self.api.pairs[case].append({"evaluator_id": tester, "rubric": "Remote reintroduction"})
        self.assertEqual(self.cli("eval", "pull")[0], 0)
        self.assertIn("pairs:handoff", project.status()["local_changes"])
        code, plan = self.cli("eval", "cases-apply", "--dry-run")
        self.assertNotEqual(code, 0)
        self.assertIn("pairs:handoff", plan["conflicts"])
        self.audit(project)
        previous = self.api.run_number
        self.assertEqual(self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")[0], 2)
        self.assertEqual(self.api.run_number, previous)

    def test_missing_tester_mapping_cannot_make_a_removal_look_complete(self):
        project = self.remove_tester_pair()
        state = project.state()
        del state["resources"]["tester:tools"]
        project.save_state(state)
        self.assertIn("pairs:handoff", project.status()["local_changes"])
        self.assertNotEqual(self.cli("eval", "cases-apply", "--dry-run")[0], 0)
