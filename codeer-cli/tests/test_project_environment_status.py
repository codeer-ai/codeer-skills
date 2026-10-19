"""Offline environment freshness must not rewrite exact-run evidence."""
import contextlib
import hashlib
import io
import json
import os
import unittest
from unittest.mock import patch

from codeer_cli.cli import main
from codeer_cli.project import read_json, save_json
from test_project_evidence import EvidenceFixture


class EnvironmentStatusTests(EvidenceFixture, unittest.TestCase):
    def prepare_environment(self):
        project = self.setup_evidence()
        environment = patch.dict(os.environ, {"STATUS_JUDGE": "judge-1"})
        environment.start()
        self.addCleanup(environment.stop)
        design = read_json(project.path("evals"))
        design["testers"][0]["judge_llm_model_id"] = "env:STATUS_JUDGE"
        save_json(project.path("evals"), design)
        self.apply_design()
        self.audit(project)
        return project

    def passing_run(self):
        project = self.prepare_environment()
        code, run = self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")
        self.assertEqual(code, 0, run)
        return project, run

    def tree_hashes(self, root):
        return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in root.rglob("*") if path.is_file()}

    def offline_status(self, *options):
        output, error = io.StringIO(), io.StringIO()
        with (patch("codeer_cli.cli.CodeerClient.from_env", side_effect=AssertionError("Offline status created a client")),
              patch("socket.socket.connect", side_effect=AssertionError("Offline status used the network")),
              contextlib.redirect_stdout(output), contextlib.redirect_stderr(error)):
            code = main(["status", *options])
        self.assertEqual(code, 0, error.getvalue())
        return output.getvalue() if "--human" in options else json.loads(output.getvalue())

    def test_changed_and_missing_environment_require_review_without_rewriting_run(self):
        project, run = self.passing_run()
        original = self.tree_hashes(project.root)
        self.assertEqual(self.offline_status()["next_action"]["code"], "review_acceptance")
        for value in ("synthetic-changed-model", None):
            with self.subTest(value=value), patch.dict(os.environ):
                if value is None:
                    del os.environ["STATUS_JUDGE"]
                else:
                    os.environ["STATUS_JUDGE"] = value
                for options in ((), ("--full",)):
                    status = self.offline_status(*options)
                    self.assertIn("environment", status["local_changes"])
                    self.assertTrue(status["latest_run"].get("environment_stale"))
                    self.assertFalse(status["latest_run"]["local_stale"])
                    self.assertEqual(status["latest_run"]["status"], "passed")
                    self.assertEqual(status["next_action"]["code"], "review_local_changes")
                    self.assertIn("environment", status["next_action"]["action"].lower())
                    self.assertNotIn("synthetic-changed-model", json.dumps(status))
                human = self.offline_status("--human")
                self.assertIn("environment", human.lower())
                self.assertNotIn("synthetic-changed-model", human)
                self.assertEqual(self.tree_hashes(project.root), original)
                self.assertEqual(self.cli("agent", "publish", "--history", "h1", "--dry-run")[0], 2)
        status = self.offline_status()
        self.assertFalse(status["latest_run"].get("environment_stale"))
        self.assertNotIn("environment", status["local_changes"])
        self.assertEqual(status["next_action"]["code"], "review_acceptance")
        self.assertEqual(self.tree_hashes(project.root), original)
        code, plan = self.cli("agent", "publish", "--history", "h1", "--dry-run")
        self.assertEqual(code, 0, plan)
        self.assertEqual(plan["run"]["id"], run["id"])
        self.assertEqual(self.api.run_number, 1)
        self.assertEqual(self.tree_hashes(project.root / "runs"),
                         {key.removeprefix("runs/"): value for key, value in original.items() if key.startswith("runs/")})

    def test_environment_change_preempts_baseline_advice_without_a_run(self):
        project = self.prepare_environment()
        self.assertEqual(self.offline_status()["next_action"]["code"], "run_baseline")
        original = self.tree_hashes(project.root)
        with patch.dict(os.environ, {"STATUS_JUDGE": "synthetic-changed-model"}):
            status = self.offline_status()
            self.assertIsNone(status["latest_run"])
            self.assertIn("environment", status["local_changes"])
            self.assertEqual(status["next_action"]["code"], "review_local_changes")
            self.assertEqual(self.tree_hashes(project.root), original)
        self.assertEqual(self.offline_status()["next_action"]["code"], "run_baseline")

    def test_refresh_cannot_make_an_old_run_current_for_a_new_environment(self):
        project, run = self.passing_run()
        original = self.tree_hashes(project.root / "runs")
        with patch.dict(os.environ, {"STATUS_JUDGE": "synthetic-changed-model"}):
            code, status = self.cli("status", "--refresh")
            self.assertEqual(code, 0, status)
            self.assertTrue(status["latest_run"].get("environment_stale"))
            self.assertFalse(status["latest_run"]["local_stale"])
            self.assertEqual(status["next_action"]["code"], "renew_verification")
            self.assertTrue(self.offline_status("--full")["latest_run"].get("environment_stale"))
            previous = self.api.run_number
            self.assertEqual(self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")[0], 2)
            self.assertEqual(self.api.run_number, previous)
            self.assertEqual(self.tree_hashes(project.root / "runs"), original)
        code, status = self.cli("status", "--refresh")
        self.assertEqual(code, 0, status)
        self.assertFalse(status["latest_run"].get("environment_stale"))
        self.assertEqual(status["next_action"]["code"], "review_acceptance")
        code, plan = self.cli("agent", "publish", "--history", "h1", "--dry-run")
        self.assertEqual(code, 0, plan)
        self.assertEqual(plan["run"]["id"], run["id"])
        self.assertEqual(self.tree_hashes(project.root / "runs"), original)

    def test_unreferenced_environment_changes_do_not_invalidate_evidence(self):
        project, _ = self.passing_run()
        original = self.tree_hashes(project.root)
        with patch.dict(os.environ, {"UNREFERENCED_STATUS_VARIABLE": "synthetic-unused"}):
            status = self.offline_status()
            self.assertNotIn("environment", status["local_changes"])
            self.assertFalse(status["latest_run"].get("environment_stale"))
            self.assertEqual(status["next_action"]["code"], "review_acceptance")
        self.assertEqual(self.tree_hashes(project.root), original)

    def test_environment_change_preempts_observe_without_changing_release(self):
        project, _ = self.passing_run()
        code, plan = self.cli("agent", "publish", "--history", "h1", "--dry-run")
        self.assertEqual(code, 0, plan)
        self.assertEqual(self.cli("agent", "publish", "--history", "h1", "--expect", plan["token"])[0], 0)
        self.assertEqual(self.offline_status()["next_action"]["code"], "observe")
        original = self.tree_hashes(project.root)
        with patch.dict(os.environ, {"STATUS_JUDGE": "synthetic-changed-model"}):
            status = self.offline_status()
            self.assertEqual(status["next_action"]["code"], "review_local_changes")
            self.assertEqual(status["latest_release"]["status"], "published")
            self.assertTrue(status["latest_run"].get("environment_stale"))
            self.assertEqual(self.tree_hashes(project.root), original)
        self.assertEqual(self.offline_status()["next_action"]["code"], "observe")

    def test_no_snapshot_does_not_invent_an_environment_change(self):
        project = self.prepare_environment()
        state = project.state()
        state.pop("last_anchor")
        project.save_state(state)
        original = self.tree_hashes(project.root)
        status = self.offline_status()
        self.assertIsNone(status["latest_run"])
        self.assertNotIn("environment", status["local_changes"])
        self.assertEqual(status["next_action"]["code"], "pre_eval_audit")
        self.assertEqual(self.tree_hashes(project.root), original)
