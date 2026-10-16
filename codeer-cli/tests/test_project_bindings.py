"""Binding names and per-invocation credentials select actual scopes."""
import contextlib
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
from codeer_cli.commands import profile
import test_project_deployments as fixtures


class BindingCommandsTests(unittest.TestCase):
    setUp = fixtures.DeploymentTests.setUp
    cli = fixtures.DeploymentTests.cli

    def test_named_bind_and_offline_listing_with_multiple_agents(self):
        code, result = self.cli("agent", "bind", "beta-a-main", "--agent", "a")
        self.assertEqual(code, 0, self.error)
        self.assertEqual(result["binding"], "beta-a-main")
        self.assertEqual(result["remote_mutations"], 0)
        self.assertEqual(self.cli("agent", "bind", "beta-a-candidate", "--new-agent")[0], 0)
        self.assertEqual(self.cli("agent", "use", "beta-a-main")[0], 0)
        calls = len(self.api.calls)
        code, result = self.cli("agent", "bindings")
        self.assertEqual(code, 0, self.error)
        self.assertEqual(len(self.api.calls), calls)
        rows = {row["name"]: row for row in result["bindings"]}
        self.assertEqual(rows["beta-a-main"]["agent_id"], "a")
        self.assertTrue(rows["beta-a-main"]["selected"])
        self.assertEqual(rows["beta-a-candidate"]["status"], "awaiting_create")
        self.assertEqual(rows["beta-a-candidate"]["workspace_id"], "w")
        self.assertEqual(self.cli("--binding", "beta-a-candidate", "status")[0], 0)
        self.artifact = self.root

    def test_conflicting_binding_or_name_is_rejected_without_requests(self):
        for args in (("--binding", "a", "--deployment", "b", "status"),
                     ("agent", "bind", "a", "--alias", "b", "--new-agent")):
            calls = len(self.api.calls)
            self.assertEqual(self.cli(*args)[0], 2)
            self.assertEqual(len(self.api.calls), calls)

    def test_listing_exposes_acknowledged_agent_identity_before_creation_is_reconciled(self):
        from codeer_cli.project import discover
        self.assertEqual(self.cli("agent", "bind", "candidate", "--new-agent")[0], 0)
        project = discover().select("candidate")
        project.save_state({"resources": {"agent": {"server_id": "known-created-agent", "status": "outcome_unknown"}}})
        calls = len(self.api.calls)
        row = self.cli("agent", "bindings")[1]["bindings"][0]
        self.assertIsNone(row["agent_id"])
        self.assertEqual(row["known_agent_id"], "known-created-agent")
        self.assertEqual(row["status"], "creation_unresolved")
        self.assertEqual(row["unresolved_resources"], ["agent"])
        self.assertEqual(len(self.api.calls), calls)


class ExplicitProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "profiles.json"
        self.path.write_text(json.dumps({"default": "beta", "profiles": {
            "prod": {"api_key": "synthetic-prod", "api_base": "https://prod.invalid"},
            "beta": {"api_key": "synthetic-beta", "api_base": "https://beta.invalid"},
        }}))
        self.addCleanup(patch.stopall)
        patch("codeer_cli.commands.profile._profiles_path", return_value=self.path).start()
        patch.dict(os.environ, {}, clear=True).start()

    def call(self, *args):
        output, error = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            code = main(list(args))
        return code, output.getvalue(), error.getvalue()

    def test_explicit_profile_is_temporary_and_never_prints_key(self):
        before = self.path.read_bytes()
        code, output, _ = self.call("--profile", "prod", "profile", "current")
        self.assertEqual(code, 0)
        self.assertIn("https://prod.invalid", output)
        self.assertNotIn("synthetic-prod", output)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(profile.resolve_profile()["name"], "beta")

    def test_conflicting_url_or_environment_key_fails_before_client_creation(self):
        for env in ({"CODEER_API_BASE": "https://beta.invalid"},
                    {"CODEER_API_KEY": "synthetic-env"}):
            with patch.dict(os.environ, env, clear=True), patch("codeer_cli.cli.CodeerClient.from_env") as client:
                code, _, error = self.call("--profile", "prod", "check")
                self.assertEqual(code, 2)
                self.assertIn("conflict", error.lower())
                client.assert_not_called()

    def test_equivalent_url_and_offline_profile_selection(self):
        with patch.dict(os.environ, {"CODEER_API_BASE": "https://prod.invalid/"}, clear=True):
            self.assertEqual(self.call("--profile", "prod", "profile", "current")[0], 0)

    def test_real_clients_use_one_profile_for_bind_check_refresh_and_preview(self):
        from codeer_cli.project import discover, save_json
        data = json.loads(self.path.read_text())
        data["profiles"]["beta-second"] = {"api_key": "synthetic-second", "api_base": "https://beta.invalid"}
        data["profiles"]["beta-rotate"] = {"api_key": "synthetic-rotate", "api_base": "https://beta.invalid"}
        self.path.write_text(json.dumps(data))
        calls = []
        agent = {"id": "a", "name": "Same Agent name", "system_prompt": "Fixture", "attachment_ids": [], "primary_object_ids": []}
        def factory():
            selected = profile.resolve_profile()
            client = CodeerClient(selected["api_base"], selected["api_key"])
            client._client.close()
            def handler(request):
                key = request.headers["x-api-key"]
                workspace = "w2" if key == "synthetic-second" else "w1"
                calls.append((str(request.url.host), key, request.method, request.url.path))
                path = request.url.path.removeprefix("/api/v1")
                result = {"profile": {"default_workspace_id": workspace, "default_organization_id": "o", "workspaces": [{"id": workspace, "name": "Workspace " + workspace}]}} if path == "/external/me" else [] if path.endswith("/versions") else agent
                return httpx.Response(200, json={"data": result, "error_code": 0})
            client._client = httpx.Client(base_url=client.base_url, headers={"x-api-key": client.api_key}, transport=httpx.MockTransport(handler))
            return client
        previous = Path.cwd()
        project_root = Path(self.temp.name) / "project"
        project_root.mkdir()
        os.chdir(project_root)
        self.addCleanup(os.chdir, previous)
        with patch("codeer_cli.cli.CodeerClient.from_env", side_effect=factory), patch("codeer_cli.client.CodeerClient.from_env", side_effect=factory):
            self.assertEqual(self.call("init")[0], 0)
            for name, selected in (("beta-main", "beta"), ("beta-second", "beta-second"), ("prod-main", "prod")):
                code, _, error = self.call("--profile", selected, "agent", "bind", name, "--agent", "a")
                self.assertEqual(code, 0, error)
            rows = json.loads(self.call("agent", "bindings")[1])["bindings"]
            self.assertEqual({(row["api_base"], row["workspace_id"], row["agent_id"]) for row in rows},
                             {("https://beta.invalid", "w1", "a"), ("https://beta.invalid", "w2", "a"), ("https://prod.invalid", "w1", "a")})
            self.assertEqual(self.call("agent", "use", "beta-main")[0], 0)
            self.assertEqual(self.call("--profile", "beta", "check", "--json")[0], 0)
            self.assertEqual(self.call("--profile", "beta", "status", "--refresh")[0], 0)
            self.assertEqual(self.call("--profile", "beta", "agent", "pull")[0], 0)
            project = discover()
            save_json(project.path("agent"), {"name": "Same Agent name"})
            project.path("instructions").write_text("Fixture")
            code, output, error = self.call("--profile", "beta", "agent", "apply", "--dry-run")
            self.assertEqual(code, 0, error)
            preview = json.loads(output)
            self.assertEqual(preview["operator"]["profile"], "beta")
            self.assertEqual(self.call("--profile", "beta-rotate", "agent", "apply", "--expect", preview["token"])[0], 2)
            self.assertEqual(self.call("--profile", "beta-rotate", "check", "--json")[0], 0)
            self.assertEqual(self.call("--profile", "beta-second", "status", "--refresh")[0], 2)
            self.assertEqual(self.call("--profile", "prod", "check", "--json")[0], 1)
        self.assertEqual(profile.resolve_profile()["name"], "beta")
        self.assertFalse(any(method not in ("GET",) for _, _, method, _ in calls))


if __name__ == "__main__":
    unittest.main()
