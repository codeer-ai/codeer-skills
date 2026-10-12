"""CLI target contracts: required targets and legacy fallback stay distinct."""
import contextlib
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import httpx

from codeer_cli.cli import main
from codeer_cli.project import read_json, save_json
from test_project_eval import EvalFixture


class TargetResolutionTests(EvalFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        environment = patch.dict(os.environ, {"CODEER_AGENT_ID": ""})
        environment.start()
        self.addCleanup(environment.stop)
        self.standalone = TemporaryDirectory()
        self.addCleanup(self.standalone.cleanup)

    def test_negative_feedback_missing_target_stops_before_client(self):
        for directory, prefix in ((self.root, ()), (self.root, ("--outside-project",)),
                                  (Path(self.standalone.name), ())):
            with self.subTest(directory=directory, prefix=prefix):
                os.chdir(directory)
                with patch("codeer_cli.cli.CodeerClient.from_env", side_effect=AssertionError("client created")), contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as error:
                        main([*prefix, "history", "negative-feedback"])
                self.assertEqual(error.exception.code, 2)
        os.chdir(self.root)
        self.pull()
        with patch("codeer_cli.cli.CodeerClient.from_env", side_effect=AssertionError("client created")), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                main(["--outside-project", "history", "negative-feedback"])
        self.assertEqual(error.exception.code, 2)

    def test_negative_feedback_bound_and_explicit_targets_filter_requests(self):
        self.pull()
        original = self.api.handler
        queries = []

        def handler(request):
            if request.url.path.endswith("/histories"):
                queries.append(dict(request.url.params))
                return httpx.Response(200, json={"data": [], "error_code": 0})
            return original(request)

        with patch.object(self.api, "handler", side_effect=handler):
            for args in (("history", "negative-feedback"),
                         ("--outside-project", "history", "negative-feedback", "--agent", "a")):
                self.assertEqual(self.cli(*args), (0, []))
        self.assertEqual([q.get("agent_id") for q in queries], ["a", "a"])

    def test_negative_feedback_preserves_project_mismatch_guards(self):
        self.pull()
        with patch("codeer_cli.cli.CodeerClient.from_env", side_effect=AssertionError("client created")), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["history", "negative-feedback", "--agent", "other"]), 2)
        original = self.api.client

        def wrong_agent():
            client = original()
            client.agent_id = "other"
            return client

        before = len(self.api.calls)
        with patch.object(self.api, "client", side_effect=wrong_agent):
            self.assertEqual(self.cli("history", "negative-feedback")[0], 2)
        self.assertFalse(any(path.endswith("/histories") for _, path, _ in self.api.calls[before:]))

    def test_legacy_eval_target_fallback_and_explicit_precedence(self):
        project, design = self.prepare()
        self.apply_design()
        manifest = project.root / "legacy-cases.json"
        save_json(manifest, {"cases": [{"input": c["input"]} for c in design["cases"]]})
        original = self.api.client
        original_handler = self.api.handler

        def legacy_handler(request):
            if request.url.path.endswith("/rubrics:batch"):
                body = json.loads(request.content)
                self.api.calls.append((request.method, "/external/eval/rubrics:batch", body))
                rows = [{"case_id": cid, "rubric": pair["rubric"]}
                        for cid in body["case_ids"] for pair in self.api.pairs.get(cid, [])
                        if pair["evaluator_id"] == body["evaluator_id"]]
                return httpx.Response(200, json={"data": rows, "error_code": 0})
            return original_handler(request)

        transport = patch.object(self.api, "handler", side_effect=legacy_handler)
        transport.start()
        self.addCleanup(transport.stop)
        for directory, prefix in ((self.root, ("--outside-project",)), (Path(self.standalone.name), ())):
            os.chdir(directory)
            for client_agent, environment_agent, explicit in (("a", "", ()), (None, "a", ()),
                                                              ("a", "other", ()), ("other", "other", ("--agent", "a"))):
                for action in ("export", "reconcile"):
                    with self.subTest(directory=directory, action=action, client_agent=client_agent,
                                      environment_agent=environment_agent, explicit=explicit):
                        def client():
                            result = original()
                            result.agent_id = client_agent
                            return result

                        output = project.root / "legacy-output" / action
                        output.mkdir(parents=True, exist_ok=True)
                        options = ("--out-dir", str(output)) if action == "export" else ("--manifest", str(manifest), "--out", str(output / "report.json"))
                        before = len(self.api.calls)
                        with patch.dict(os.environ, {"CODEER_AGENT_ID": environment_agent}), patch.object(self.api, "client", side_effect=client):
                            code, _ = self.cli(*prefix, "eval", action, *options, *explicit)
                        self.assertEqual(code, 0)
                        artifact = output / ("eval_table_full.json" if action == "export" else "report.json")
                        self.assertEqual(read_json(artifact)["agent_id"], "a")
                        self.assertTrue(any(path == "/external/eval/agents/a/cases" for _, path, _ in self.api.calls[before:]))
                        self.assertFalse(any(method != "GET" and not path.endswith(":batch") for method, path, _ in self.api.calls[before:]))

    def test_legacy_eval_without_any_target_rejects_before_resource_queries(self):
        manifest = self.root / "legacy-cases.json"
        save_json(manifest, {"cases": []})
        os.chdir(self.standalone.name)
        for action, options in (("export", ()), ("reconcile", ("--manifest", str(manifest)))):
            with self.subTest(action=action):
                before = len(self.api.calls)
                try:
                    code = self.cli("eval", action, *options)[0]
                except SystemExit as error:
                    code = error.code
                self.assertEqual(code, 2)
                self.assertFalse(any(path.startswith("/external/eval/") for _, path, _ in self.api.calls[before:]))

    def test_legacy_eval_project_binding_and_mismatch_guards_remain_active(self):
        self.prepare()
        self.apply_design()
        original = self.api.client

        def wrong_agent():
            client = original()
            client.agent_id = "other"
            return client

        for action, options in (("export", ("--out-dir", str(self.root / "bound-export"))), ("reconcile", ())):
            with self.subTest(action=action):
                if action == "reconcile":
                    code, plan = self.cli("eval", action)
                    self.assertEqual(code, 0)
                    self.assertEqual(plan["scope"]["agent_id"], "a")
                with patch("codeer_cli.cli.CodeerClient.from_env", side_effect=AssertionError("client created")), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(main(["eval", action, *options, "--agent", "other"]), 2)
                before = len(self.api.calls)
                with patch.object(self.api, "client", side_effect=wrong_agent):
                    self.assertEqual(self.cli("eval", action, *options)[0], 2)
                self.assertFalse(any(path.startswith("/external/eval/") for _, path, _ in self.api.calls[before:]))

    def test_other_required_agent_commands_still_stop_before_client(self):
        commands = (("agent", "pull"), ("agent", "diff"), ("agent", "versions"),
                    ("agent", "impact"), ("agent", "publish", "--history", "h1"),
                    ("eval", "pull"), ("eval", "snapshot", "--history", "h1", "--out", "anchor.json"),
                    ("eval", "list"), ("eval", "run"), ("eval", "cases-apply"), ("eval", "rubrics"))
        for prefix in ((), ("--outside-project",)):
            for command in commands:
                with self.subTest(prefix=prefix, command=command):
                    with patch.dict(os.environ, {"CODEER_AGENT_ID": "a"}), patch("codeer_cli.cli.CodeerClient.from_env", side_effect=AssertionError("client created")), contextlib.redirect_stderr(io.StringIO()):
                        with self.assertRaises(SystemExit) as error:
                            main([*prefix, *command])
                    self.assertEqual(error.exception.code, 2)

    def test_optional_history_list_remains_unfiltered_outside_project(self):
        self.pull()
        original = self.api.handler
        queries = []

        def handler(request):
            if request.url.path.endswith("/histories"):
                queries.append(dict(request.url.params))
                return httpx.Response(200, json={"data": [], "error_code": 0})
            return original(request)

        with patch.object(self.api, "handler", side_effect=handler):
            self.assertEqual(self.cli("--outside-project", "history", "list")[0], 0)
        self.assertEqual(len(queries), 1)
        self.assertNotIn("agent_id", queries[0])
