from __future__ import annotations

import argparse
import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from types import SimpleNamespace

from codeer_cli import eval_ as eval_mod
from codeer_cli.commands.eval_cmd import (
    register,
    run_evaluator_create,
    run_evaluator_update,
)


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []

    def post(self, path: str, **kwargs):
        self.calls.append(("POST", path, kwargs))
        return {"id": "created", **kwargs["json"]}

    def put(self, path: str, **kwargs):
        self.calls.append(("PUT", path, kwargs))
        return {"id": "updated", **kwargs["json"]}

    def resolve_scope(self):
        return "ws-1", "org-1"


class EvaluatorRequestTests(unittest.TestCase):
    def test_create_evaluator_sends_judge_model(self) -> None:
        client = FakeClient()

        eval_mod.create_evaluator(
            client,  # type: ignore[arg-type]
            workspace_id="ws-1",
            name="Correctness",
            system_prompt_template="Judge {output}",
            judge_llm_model_id="model-1",
        )

        self.assertEqual(client.calls[0][0:2], ("POST", "/external/eval/evaluators"))
        self.assertEqual(client.calls[0][2]["json"]["judge_llm_model_id"], "model-1")

    def test_create_evaluator_omits_unspecified_judge_model(self) -> None:
        client = FakeClient()

        eval_mod.create_evaluator(
            client,  # type: ignore[arg-type]
            workspace_id="ws-1",
            name="Correctness",
            system_prompt_template="Judge {output}",
        )

        self.assertNotIn("judge_llm_model_id", client.calls[0][2]["json"])

    def test_update_evaluator_sends_judge_model(self) -> None:
        client = FakeClient()

        eval_mod.update_evaluator(
            client,  # type: ignore[arg-type]
            "eval-1",
            judge_llm_model_id="model-2",
        )

        self.assertEqual(client.calls[0][2]["json"], {"judge_llm_model_id": "model-2"})

    def test_update_evaluator_omits_unspecified_judge_model(self) -> None:
        client = FakeClient()

        eval_mod.update_evaluator(
            client,  # type: ignore[arg-type]
            "eval-1",
            name="Updated",
        )

        self.assertEqual(client.calls[0][2]["json"], {"name": "Updated"})

    def test_update_evaluator_sends_null_to_clear_judge_model(self) -> None:
        client = FakeClient()

        eval_mod.update_evaluator(
            client,  # type: ignore[arg-type]
            "eval-1",
            judge_llm_model_id=None,
        )

        self.assertEqual(client.calls[0][2]["json"], {"judge_llm_model_id": None})


class EvaluatorCliTests(unittest.TestCase):
    def test_create_dry_run_reports_set_judge_model(self) -> None:
        client = FakeClient()
        args = SimpleNamespace(
            name="Correctness",
            system_prompt_template="Judge {output}",
            system_prompt_template_file=None,
            description=None,
            judge_model="model-1",
            dry_run=True,
        )

        report, result = self._capture(run_evaluator_create, args, client)

        self.assertEqual(result, 0)
        self.assertEqual(
            report["judge_model"], {"action": "set", "model_id": "model-1"}
        )
        self.assertEqual(client.calls, [])

    def test_create_dry_run_reports_system_default_when_model_is_omitted(self) -> None:
        client = FakeClient()
        args = SimpleNamespace(
            name="Correctness",
            system_prompt_template="Judge {output}",
            system_prompt_template_file=None,
            description=None,
            judge_model=None,
            dry_run=True,
        )

        report, result = self._capture(run_evaluator_create, args, client)

        self.assertEqual(result, 0)
        self.assertEqual(
            report["judge_model"],
            {"action": "use_system_default", "model_id": None},
        )
        self.assertEqual(client.calls, [])

    def test_update_dry_run_reports_set_judge_model(self) -> None:
        client = FakeClient()
        args = self._update_args(judge_model="model-2")

        report, result = self._capture(run_evaluator_update, args, client)

        self.assertEqual(result, 0)
        self.assertEqual(
            report["judge_model"], {"action": "set", "model_id": "model-2"}
        )
        self.assertEqual(client.calls, [])

    def test_update_dry_run_reports_unspecified_judge_model_as_unchanged(self) -> None:
        client = FakeClient()
        args = self._update_args(name="Updated")

        report, result = self._capture(run_evaluator_update, args, client)

        self.assertEqual(result, 0)
        self.assertEqual(report["judge_model"], {"action": "unchanged"})
        self.assertEqual(client.calls, [])

    def test_update_dry_run_reports_explicit_clear(self) -> None:
        client = FakeClient()
        args = self._update_args(clear_judge_model=True)

        report, result = self._capture(run_evaluator_update, args, client)

        self.assertEqual(result, 0)
        self.assertEqual(
            report["judge_model"],
            {"action": "clear_to_system_default", "model_id": None},
        )
        self.assertEqual(client.calls, [])

    def test_update_clear_flag_sends_explicit_null(self) -> None:
        client = FakeClient()
        args = self._update_args(clear_judge_model=True, dry_run=False)

        _, result = self._capture(run_evaluator_update, args, client)

        self.assertEqual(result, 0)
        self.assertEqual(client.calls[0][2]["json"], {"judge_llm_model_id": None})

    def test_update_other_field_does_not_send_judge_model(self) -> None:
        client = FakeClient()
        args = self._update_args(name="Updated", dry_run=False)

        _, result = self._capture(run_evaluator_update, args, client)

        self.assertEqual(result, 0)
        self.assertEqual(client.calls[0][2]["json"], {"name": "Updated"})

    def test_parser_rejects_set_and_clear_together(self) -> None:
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="group")
        register(subparsers)

        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "eval",
                    "evaluator-update",
                    "--evaluator",
                    "eval-1",
                    "--judge-model",
                    "model-1",
                    "--clear-judge-model",
                ]
            )

    @staticmethod
    def _capture(func, args, client) -> tuple[dict, int]:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            result = func(args, client)
        return json.loads(stdout.getvalue()), result

    @staticmethod
    def _update_args(**overrides) -> SimpleNamespace:
        values = {
            "evaluator": "eval-1",
            "name": None,
            "system_prompt_template": None,
            "system_prompt_template_file": None,
            "description": None,
            "judge_model": None,
            "clear_judge_model": False,
            "dry_run": True,
        }
        values.update(overrides)
        return SimpleNamespace(**values)


if __name__ == "__main__":
    unittest.main()
