from __future__ import annotations

import unittest

from codeer_cli import eval_ as eval_mod
from codeer_cli.commands.eval_cmd import (
    _assigned_evaluators_by_case,
    _pairs_from_rubric_batches,
    _planned_eval_pairs,
    _remove_non_runnable_skipped_pairs,
    _skipped_pairs_from_trigger_response,
)


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []

    def get(self, path: str, **kwargs):
        self.calls.append(("GET", path, kwargs))
        if path == "/external/eval/agents/agent-1/cases":
            return {"cases": [{"id": "case-1"}, {"id": "case-2"}], "total": 2}
        return []

    def post(self, path: str, **kwargs):
        self.calls.append(("POST", path, kwargs))
        if path == "/external/eval/cases":
            return {"id": "case-1"}
        if path == "/external/eval/rubrics:batch":
            return [
                {"case_id": "case-1", "evaluator_id": "eval-1", "rubric": "Must pass"},
                {"case_id": "case-2", "evaluator_id": "eval-1", "rubric": ""},
            ]
        return {"ok": True}

    def put(self, path: str, **kwargs):
        self.calls.append(("PUT", path, kwargs))
        return {"ok": True}


class EvalPairClientTests(unittest.TestCase):
    def test_list_cases_accepts_enveloped_server_response(self) -> None:
        client = FakeClient()

        cases = eval_mod.list_cases(client, "agent-1")  # type: ignore[arg-type]

        self.assertEqual(cases, [{"id": "case-1"}, {"id": "case-2"}])
        self.assertEqual(client.calls[0][0:2], ("GET", "/external/eval/agents/agent-1/cases"))

    def test_external_trigger_endpoint_for_agent_history_runs(self) -> None:
        client = FakeClient()

        eval_mod.trigger(  # type: ignore[arg-type]
            client,
            case_ids=["case-1", "case-2"],
            evaluator_ids=["eval-1"],
            agent_history_id="hist-1",
        )

        self.assertEqual(client.calls[0][0:2], ("POST", "/external/eval/runs"))
        self.assertEqual(
            client.calls[0][2]["json"],
            {
                "case_ids": ["case-1", "case-2"],
                "evaluator_ids": ["eval-1"],
                "version_id": "hist-1",
            },
        )

    def test_pairs_from_rubric_batches_keeps_configured_rubrics_only(self) -> None:
        client = FakeClient()

        pairs = _pairs_from_rubric_batches(  # type: ignore[arg-type]
            client,
            case_ids=["case-1", "case-2"],
            evaluator_ids=["eval-1"],
        )

        self.assertEqual(pairs, [{"case_id": "case-1", "evaluator_id": "eval-1"}])
        self.assertEqual(client.calls[0][0:2], ("POST", "/external/eval/rubrics:batch"))

    def test_assignment_helper_paths(self) -> None:
        client = FakeClient()

        eval_mod.get_case_evaluator_infos(client, case_ids=["case-1"])  # type: ignore[arg-type]
        eval_mod.replace_case_evaluator_infos(  # type: ignore[arg-type]
            client,
            case_id="case-1",
            evaluators=[{"evaluator_id": "eval-1", "rubric": "Must pass"}],
        )
        eval_mod.trigger_pairs(  # type: ignore[arg-type]
            client,
            case_evaluator_pairs=[{"case_id": "case-1", "evaluator_id": "eval-1"}],
            agent_history_id="hist-1",
        )

        self.assertEqual(client.calls[0][0:2], ("POST", "/eval/case-evaluator-infos:batch"))
        self.assertEqual(client.calls[0][2]["json"], {"case_ids": ["case-1"]})
        self.assertEqual(client.calls[1][0:2], ("PUT", "/eval/cases/case-1/case-evaluator-infos"))
        self.assertEqual(
            client.calls[1][2]["json"],
            {"evaluators": [{"evaluator_id": "eval-1", "rubric": "Must pass"}]},
        )
        self.assertEqual(client.calls[2][0:2], ("POST", "/eval/trigger"))
        self.assertEqual(
            client.calls[2][2]["json"],
            {
                "case_evaluator_pairs": [{"case_id": "case-1", "evaluator_id": "eval-1"}],
                "agent_history_id": "hist-1",
            },
        )

    def test_create_case_with_rubrics_sends_atomic_evaluator_assignments(self) -> None:
        client = FakeClient()

        eval_mod.create_case_with_rubrics(  # type: ignore[arg-type]
            client,
            agent_id="agent-1",
            input="Question",
            rubrics_by_evaluator={"eval-1": "Must pass", "eval-2": "Must cite"},
        )

        self.assertEqual(len(client.calls), 1)
        self.assertEqual(client.calls[0][0:2], ("POST", "/external/eval/cases"))
        self.assertEqual(
            client.calls[0][2]["json"]["evaluators"],
            [
                {"evaluator_id": "eval-1", "rubric": "Must pass"},
                {"evaluator_id": "eval-2", "rubric": "Must cite"},
            ],
        )


class EvalPairPlannerTests(unittest.TestCase):
    def test_plans_only_assigned_pairs_for_specific_evaluator(self) -> None:
        rows = [
            {"case_id": "case-1", "evaluators": [{"evaluator_id": "eval-1", "rubric": "A"}]},
            {"case_id": "case-2", "evaluators": [{"evaluator_id": "eval-2", "rubric": "B"}]},
        ]

        pairs, skipped = _planned_eval_pairs(
            case_ids=["case-1", "case-2"],
            assigned_by_case=_assigned_evaluators_by_case(rows),
            requested_evaluator_ids=["eval-1"],
        )

        self.assertEqual(pairs, [{"case_id": "case-1", "evaluator_id": "eval-1"}])
        self.assertEqual(
            skipped,
            [{"case_id": "case-2", "evaluator_id": "eval-1", "reason": "not_assigned"}],
        )

    def test_omitted_evaluator_runs_all_assigned_pairs(self) -> None:
        rows = [
            {
                "case_id": "case-1",
                "evaluators": [
                    {"evaluator_id": "eval-1", "rubric": "A"},
                    {"evaluator_id": "eval-2", "rubric": "B"},
                ],
            },
            {"case_id": "case-2", "evaluators": []},
        ]

        pairs, skipped = _planned_eval_pairs(
            case_ids=["case-1", "case-2"],
            assigned_by_case=_assigned_evaluators_by_case(rows),
            requested_evaluator_ids=None,
        )

        self.assertEqual(
            pairs,
            [
                {"case_id": "case-1", "evaluator_id": "eval-1"},
                {"case_id": "case-1", "evaluator_id": "eval-2"},
            ],
        )
        self.assertEqual(skipped, [])

    def test_trigger_response_skipped_pairs_are_normalized(self) -> None:
        skipped = _skipped_pairs_from_trigger_response({
            "skipped_pairs": [
                {"case_id": "case-1", "evaluator_id": "eval-1", "reason": "not_assigned"},
                {"case_id": "case-2", "evaluator_id": "eval-1"},
                {"case_id": None, "evaluator_id": "eval-1", "reason": "not_assigned"},
            ]
        })

        self.assertEqual(
            skipped,
            [
                {"case_id": "case-1", "evaluator_id": "eval-1", "reason": "not_assigned"},
                {"case_id": "case-2", "evaluator_id": "eval-1", "reason": "skipped"},
            ],
        )

    def test_non_runnable_skipped_pairs_are_removed_from_poll_targets(self) -> None:
        pairs = [
            {"case_id": "case-1", "evaluator_id": "eval-1"},
            {"case_id": "case-2", "evaluator_id": "eval-1"},
            {"case_id": "case-3", "evaluator_id": "eval-1"},
        ]
        skipped = [
            {"case_id": "case-2", "evaluator_id": "eval-1", "reason": "not_assigned"},
            {"case_id": "case-3", "evaluator_id": "eval-1", "reason": "already_running"},
        ]

        self.assertEqual(
            _remove_non_runnable_skipped_pairs(pairs, skipped),
            [
                {"case_id": "case-1", "evaluator_id": "eval-1"},
                {"case_id": "case-3", "evaluator_id": "eval-1"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
