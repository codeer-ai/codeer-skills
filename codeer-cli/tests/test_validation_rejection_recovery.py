import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from codeer_cli import agents
from codeer_cli._validate import validate_suggested_questions
from codeer_cli.client import CodeerError
from codeer_cli.deployment import rejected_create_plan, recover_rejected_create
from codeer_cli.project import Project, ProjectError, read_json, save_json
from codeer_cli.project_agent import preview
from codeer_cli.sync import apply_change, plan_change


def validation_error():
    return CodeerError(422, "Invalid request payload", {
        "message": "Invalid request payload",
        "data": {"errors": [{"field": "suggested_questions", "message": "Maximum 3 suggested questions allowed",
                              "type": "value_error", "input": "must-not-be-retained"}]},
    })


class ValidationRejectionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.project = Project(self.root, {"schema_version": 2, "name": "fixture"})
        self.project.select("local")
        self.project.bind(api_base="http://unit.local", workspace_id="w", agent_id=None, intent="create")
        self.client = Mock(base_url="http://unit.local", api_key="synthetic", agent_id=None)
        self.client.resolve_scope.return_value = ("w", "o")
        self.client.get.return_value = []
        self.profile = patch("codeer_cli.commands.profile.resolve_profile", return_value={"name": "fixture"})
        self.profile.start()
        self.addCleanup(self.profile.stop)
        self.scope = {"api_base": "http://unit.local", "workspace_id": "w", "agent_id": None}

    def make_plan(self):
        plan = plan_change(self.project, "agent", None, {}, {"name": "Support"}, {})
        plan["scope"] = self.scope
        return plan

    def test_question_limits_reject_create_update_before_http(self):
        self.assertEqual(validate_suggested_questions(None), [])
        self.assertEqual(validate_suggested_questions(["字" * 200] * 3), ["字" * 200] * 3)
        for bad in (["a"] * 4, ["a" * 201], "abc", [None]):
            with self.subTest(value=bad), self.assertRaises(ValueError):
                validate_suggested_questions(bad)
        with self.assertRaisesRegex(ValueError, "Maximum 3"):
            agents.create(self.client, workspace_id="w", name="a", system_prompt="p", suggested_questions=["a"] * 5)
        with self.assertRaisesRegex(ValueError, "Maximum 3"):
            agents.update(self.client, "a", name="a", system_prompt="p", unified_tools=[], use_search=False,
                          suggested_questions=["a"] * 5)
        self.client.post.assert_not_called()
        self.client.patch.assert_not_called()

    def test_project_preview_also_rejects_invalid_questions(self):
        save_json(self.root / "agent/settings.json", {"name": "a", "suggested_questions": ["a"] * 5})
        with self.assertRaisesRegex(ValueError, "Maximum 3"):
            preview(self.project, self.client)
        self.client.post.assert_not_called()

    def test_validation_rejection_retains_details_without_input_echo(self):
        plan = self.make_plan()
        with self.assertRaises(CodeerError):
            apply_change(self.project, plan, plan["token"], Mock(side_effect=validation_error()), Mock())
        entry = self.project.state()["resources"]["agent"]
        receipt = read_json(self.root / entry["receipt"])
        self.assertEqual(entry["status"], "rejected")
        self.assertEqual(receipt["http_error"]["status"], 422)
        self.assertEqual(receipt["http_error"]["validation_errors"][0]["field"], "suggested_questions")
        self.assertNotIn("must-not-be-retained", str(receipt))
        self.assertNotIn("unreconciled_previous_operation", self.make_plan()["conflicts"])

    def test_non_validation_failures_stay_unknown(self):
        for error in (CodeerError(0, "timeout"), CodeerError(500, "error"), CodeerError(422, "other error")):
            with self.subTest(status=error.status):
                self.project.save_state({"resources": {}})
                plan = self.make_plan()
                with self.assertRaises(CodeerError):
                    apply_change(self.project, plan, plan["token"], Mock(side_effect=error), Mock())
                self.assertEqual(self.project.state()["resources"]["agent"]["status"], "outcome_unknown")

    def test_readback_validation_failure_does_not_clear_committed_create(self):
        plan = self.make_plan()
        with self.assertRaises(CodeerError):
            apply_change(self.project, plan, plan["token"], Mock(return_value={"id": "created"}),
                         Mock(side_effect=validation_error()))
        entry = self.project.state()["resources"]["agent"]
        self.assertEqual(entry["status"], "outcome_unknown")
        self.assertEqual(entry["server_id"], "created")

    def legacy_evidence(self):
        path = self.project.local_dir / "receipts/legacy.json"
        receipt = {"status": "outcome_unknown", "error": "CodeerError", "scope": self.scope,
                   "plan": {"resource": "agent", "server_id": None, "scope": self.scope,
                            "token": "old-preview", "payload": {"name": "Support", "suggested_questions": ["a"] * 5}}}
        save_json(path, receipt)
        self.project.save_state({"resources": {"agent": {"status": "outcome_unknown", "scope": self.scope,
                                                          "receipt": str(path.relative_to(self.root))}}})
        save_json(self.root / "agent/settings.json", {"suggested_questions": ["a"] * 3})
        (self.root / "investigation.md").write_text("Operator observed the validation 422; backend max is three.")
        evidence = {"schema_version": 1, "receipt_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "scope": self.scope, "request_token": "old-preview", "http_status": 422,
                    "message": "Invalid request payload", "operator_attested_validation_rejection": True,
                    "verification": "investigation.md"}
        save_json(self.root / "evidence.json", evidence)
        return path, evidence

    def test_legacy_recovery_preserves_original_and_makes_no_remote_write(self):
        path, _ = self.legacy_evidence()
        before = path.read_bytes()
        plan = rejected_create_plan(self.project, self.client, "evidence.json")
        self.assertEqual(self.project.state()["resources"]["agent"]["status"], "outcome_unknown")
        result = recover_rejected_create(self.project, self.client, plan, plan["token"])
        self.assertEqual(result["remote_mutations"], 0)
        self.assertEqual(self.project.state()["resources"]["agent"]["status"], "rejected")
        self.assertEqual(path.read_bytes(), before)
        self.client.post.assert_not_called()
        self.client.patch.assert_not_called()

    def test_legacy_recovery_refuses_missing_wrong_or_stale_evidence(self):
        for field, value in (("receipt_sha256", "wrong"), ("http_status", 500),
                             ("operator_attested_validation_rejection", False), ("scope", {})):
            with self.subTest(field=field):
                _, evidence = self.legacy_evidence()
                evidence[field] = value
                save_json(self.root / "evidence.json", evidence)
                with self.assertRaises(ProjectError):
                    rejected_create_plan(self.project, self.client, "evidence.json")
        self.legacy_evidence()
        plan = rejected_create_plan(self.project, self.client, "evidence.json")
        self.client.get.return_value = [{"id": "another", "name": "Other"}]
        with self.assertRaisesRegex(ProjectError, "preview changed"):
            recover_rejected_create(self.project, self.client, plan, plan["token"])

    def test_recorded_kb_validation_rejection_is_recoverable_but_not_an_arbitrary_400(self):
        path, evidence = self.legacy_evidence()
        message = "Tool validation failed: One or more knowledge node files are not in the workspace"
        receipt = read_json(path)
        receipt["plan"]["payload"]["suggested_questions"] = ["a"] * 3
        receipt["http_error"] = {"status": 400, "message": message}
        save_json(path, receipt)
        evidence.update(http_status=400, message=message, receipt_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        save_json(self.root / "evidence.json", evidence)
        plan = rejected_create_plan(self.project, self.client, "evidence.json")
        self.assertEqual(recover_rejected_create(self.project, self.client, plan, plan["token"])["status"], "rejected")
        self.project.save_state({"resources": {}})
        plan = self.make_plan()
        error = CodeerError(400, message, {"message": message})
        with self.assertRaises(CodeerError):
            apply_change(self.project, plan, plan["token"], Mock(side_effect=error), Mock())
        self.assertEqual(self.project.state()["resources"]["agent"]["status"], "rejected")
        self.project.save_state({"resources": {}})
        plan = self.make_plan()
        with self.assertRaises(CodeerError):
            apply_change(self.project, plan, plan["token"], Mock(side_effect=CodeerError(400, "other")), Mock())
        self.assertEqual(self.project.state()["resources"]["agent"]["status"], "outcome_unknown")

    def test_legacy_recovery_refuses_existing_identity_response_or_name(self):
        path, _ = self.legacy_evidence()
        entry = self.project.state()
        entry["resources"]["agent"]["server_id"] = "known"
        self.project.save_state(entry)
        with self.assertRaises(ProjectError):
            rejected_create_plan(self.project, self.client, "evidence.json")
        path, _ = self.legacy_evidence()
        receipt = read_json(path)
        receipt["response"] = {"id": "known"}
        save_json(path, receipt)
        with self.assertRaises(ProjectError):
            rejected_create_plan(self.project, self.client, "evidence.json")
        self.legacy_evidence()
        self.client.get.return_value = [{"id": "existing", "name": "Support"}]
        with self.assertRaisesRegex(ProjectError, "same-name"):
            rejected_create_plan(self.project, self.client, "evidence.json")


if __name__ == "__main__":
    unittest.main()
