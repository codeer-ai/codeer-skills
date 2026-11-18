"""Offline settings contracts and actionable knowledge-file validation."""
import unittest

from codeer_cli.constants import UNIFIED_TOOL_TYPES
from codeer_cli.portable import check_agent, kb_folder_warnings
from codeer_cli.project_agent import FIELDS
import test_project_deployments as fixtures


class SchemaCommandTests(unittest.TestCase):
    setUp = fixtures.DeploymentTests.setUp
    cli = fixtures.DeploymentTests.cli

    def test_agent_schema_runs_without_credentials_and_matches_fields(self):
        code, output = self.cli("agent", "schema")
        self.assertEqual(code, 0, self.error)
        self.assertEqual(output["file"], "agent/settings.json")
        self.assertEqual(set(output["schema"]["properties"]), set(FIELDS))
        tool = output["schema"]["properties"]["unified_tools"]["items"]
        self.assertEqual(set(tool["properties"]["type"]["enum"]), UNIFIED_TOOL_TYPES)
        self.assertEqual(output["example"]["unified_tools"][0]["knowledge_node_ids"], ["kb:support/01_policy.md"])
        self.assertEqual(self.api.calls, [])

    def test_eval_schema_runs_without_credentials(self):
        code, output = self.cli("eval", "schema")
        self.assertEqual(code, 0, self.error)
        self.assertEqual(output["file"], "evals/design.json")
        case = output["schema"]["properties"]["cases"]["items"]
        self.assertIn("pairs", case["required"])
        self.assertEqual(case["not"], {"required": ["rubric"]})
        self.assertEqual(self.api.calls, [])

    def test_eval_schema_example_passes_design_validation(self):
        from codeer_cli.project_eval import validate_design

        _, output = self.cli("eval", "schema")
        result = validate_design(output["example"])
        self.assertEqual(result["structural_issues"], [])
        self.assertEqual(result["pair_count"], 1)


class KnowledgeFileReferenceTests(unittest.TestCase):
    cli = fixtures.DeploymentTests.cli
    bind = fixtures.DeploymentTests.bind

    def setUp(self):
        fixtures.DeploymentTests.setUp(self)
        self.project = self.bind()
        self.project.save_state({"resources": {"kb:support": {
            "server_id": "kb-root", "status": "ready",
            "file_ids": {"01_policy.md": "file-1", "02_pickup.md": "file-2"},
        }}})

    def settings(self, *refs):
        return {"name": "Support", "unified_tools": [{"id": "support-kb", "type": "knowledge_base", "knowledge_node_ids": list(refs)}]}

    def test_folder_reference_warns_with_the_file_references_to_use(self):
        warnings = kb_folder_warnings(self.project, self.settings("kb:support"))
        self.assertEqual(len(warnings), 1)
        self.assertIn("kb:support is a knowledge base folder", warnings[0])
        self.assertIn("kb:support/01_policy.md, kb:support/02_pickup.md", warnings[0])
        self.assertIn("codeer agent schema", warnings[0])
        # Advisory only: the existing portable check still accepts the folder reference.
        check_agent(self.project, self.settings("kb:support"))

    def test_file_references_have_no_warning(self):
        settings = self.settings("kb:support/01_policy.md", "kb:support/02_pickup.md")
        self.assertEqual(kb_folder_warnings(self.project, settings), [])
        check_agent(self.project, settings)


if __name__ == "__main__":
    unittest.main()
