import contextlib
import io
import json
import os
from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import httpx

from codeer_cli.cli import main
from codeer_cli.client import CodeerClient
from codeer_cli.commands import profile
from codeer_cli.setup import diagnostic


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.addCleanup(patch.stopall)
        patch("pathlib.Path.home", return_value=self.root).start()
        patch.dict(os.environ, {}, clear=True).start()
        before = Path.cwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, before)

    def test_missing_unselected_unknown_and_missing_key_are_distinct(self):
        self.assertEqual(diagnostic()["status"], "missing_configuration")
        profile._write_profiles({"profiles": {"dev": {"api_key": "synthetic-key"}}})
        self.assertEqual(diagnostic()["status"], "profile_not_selected")
        os.environ["CODEER_PROFILE"] = "missing"
        self.assertEqual(diagnostic()["status"], "unknown_profile")
        profile._write_profiles({"profiles": {"missing": {}}})
        self.assertEqual(diagnostic()["status"], "missing_key")

    def test_parent_project_environment_precedence_never_persists_overrides(self):
        profile._write_profiles({"default": "global", "profiles": {name: {"api_key": name + "-synthetic", "api_base": "https://" + name + ".invalid"} for name in ("global", "parent", "project")}})
        self.assertEqual(profile.resolve_profile()["name"], "global")
        repo = self.root / "repo"
        (repo / ".codeer").mkdir(parents=True)
        (repo / ".codeer/profile").write_text("parent\n")
        child = repo / "projects/one"
        (child / ".codeer").mkdir(parents=True)
        os.chdir(child)
        self.assertEqual(profile.resolve_profile()["name"], "parent")
        (child / ".codeer/profile").write_text("project\n")
        os.chdir(child / ".codeer")
        self.assertEqual(profile.resolve_profile()["name"], "project")
        before = profile._profiles_path().read_bytes()
        os.environ["CODEER_API_KEY"] = "environment-synthetic"
        os.environ["CODEER_API_BASE"] = "https://override.invalid"
        with CodeerClient.from_env() as client:
            self.assertEqual(client.api_key, "environment-synthetic")
            self.assertEqual(client.base_url, "https://override.invalid")
        detail = diagnostic()
        self.assertEqual(detail["source"], "environment")
        self.assertNotIn("environment-synthetic", json.dumps(detail))
        self.assertEqual(profile._profiles_path().read_bytes(), before)

    def test_secure_explicit_add_and_noninteractive_refusal(self):
        with patch("sys.stdin.isatty", return_value=False), patch("getpass.getpass", side_effect=AssertionError("must not wait")), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(profile.run_add(SimpleNamespace(name="dev", api_base="https://fixture.invalid")), 2)
        self.assertFalse(profile._profiles_path().exists())
        output = io.StringIO()
        with patch("sys.stdin.isatty", return_value=True), patch("getpass.getpass", return_value="synthetic-secret"), contextlib.redirect_stdout(output):
            self.assertEqual(profile.run_add(SimpleNamespace(name="dev", api_base="https://fixture.invalid")), 0)
            profile.run_current(SimpleNamespace())
        self.assertEqual(stat.S_IMODE(profile._profiles_path().stat().st_mode), 0o600)
        self.assertEqual((self.root / ".codeer/profile").read_text(), "dev\n")
        self.assertNotIn("synthetic-secret", output.getvalue())
        self.assertNotIn("synthetic-secret", (self.root / ".codeer/profile").read_text())

    def test_api_base_override_is_reported_even_when_key_comes_from_profile(self):
        profile._write_profiles({"default": "dev", "profiles": {"dev": {"api_key": "synthetic", "api_base": "https://profile.invalid"}}})
        os.environ["CODEER_API_BASE"] = "https://override.invalid"
        self.assertEqual(profile.resolve_profile()["api_base"], "https://override.invalid")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            profile.run_current(SimpleNamespace())
        self.assertIn("CODEER_API_BASE override", output.getvalue())
        code, report = self.check(lambda request: httpx.Response(401, json={}))
        self.assertEqual(code, 1)
        self.assertIn("CODEER_API_BASE", report["next_step"])

    def check(self, handler):
        def client():
            value = CodeerClient("https://fixture.invalid", "synthetic")
            value._client.close()
            value._client = httpx.Client(base_url=value.base_url, transport=httpx.MockTransport(handler))
            return value
        output = io.StringIO()
        with patch("codeer_cli.cli.CodeerClient.from_env", side_effect=client), contextlib.redirect_stdout(output):
            result = main(["check", "--json"])
        return result, json.loads(output.getvalue())

    def test_network_timeout_service_permission_and_uncertain_auth_diagnostics(self):
        profile._write_profiles({"default": "dev", "profiles": {"dev": {"api_key": "synthetic"}}})
        before = profile._profiles_path().read_bytes()
        for failure in (httpx.ConnectError, httpx.ReadTimeout):
            def handler(request):
                raise failure("fixture", request=request)
            code, report = self.check(handler)
            self.assertEqual(code, 1)
            self.assertEqual(report["connection"]["status"], "connection_unverified")
            self.assertNotIn("profile add", report["next_step"])
        for status, body, expected in ((503, {}, "connection_unverified"),
                                       (403, {"error_code": 10001}, "permission_denied"),
                                       (401, {}, "authentication_or_access_rejected"),
                                       (403, {}, "authentication_or_access_rejected")):
            code, report = self.check(lambda request: httpx.Response(status, json=body))
            self.assertEqual(code, 1)
            self.assertEqual(report["connection"]["status"], expected)
            self.assertNotIn("expired", report["auth"]["error"])
        self.assertEqual(profile._profiles_path().read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
