import copy
import unittest

from codeer_cli.project import save_json
from codeer_cli.project_eval import validate_design
from test_project_sync import ProjectFixture


def design_fixture():
    return {"schema_version": 1, "testers": [{"local_id": "tools", "name": "Tool behavior",
             "system_prompt_template": "Judge {tool_steps} against {rubric}", "judge_llm_model_id": "judge-1",
             "rationale": "Reuse one common tool judge for all scenarios",
             "evidence": [{"variable": "tool_steps", "producer": "reasoning_steps", "availability": "verified", "verification": "reviews/evidence.md"}]}],
            "cases": [{"local_id": "handoff", "input": "Human please", "source": {"document": "sources/documents/sop.md"},
                       "meta": {"previous_messages": [{"role": "user", "content": "Order late"}]},
                       "label_ids": ["routing"], "attachment_ids": ["attachment"],
                       "pairs": [{"tester": "tools", "rubric": "Must actually call handoff", "required_evidence": ["tool_steps"]}]},
                      {"local_id": "hours", "input": "Hours?", "source": {"document": "sources/documents/sop.md"},
                       "pairs": [{"tester": "tools", "rubric": "Must not call handoff", "required_evidence": ["tool_steps"]}]}]}


class EvalFixture(ProjectFixture):
    def prepare(self):
        project = self.pull()
        design = design_fixture()
        source = project.root / "sources/documents/sop.md"
        source.write_text("Synthetic SOP: explicit human request calls handoff; hours questions do not.")
        evidence = project.root / "reviews/evidence.md"
        evidence.parent.mkdir(parents=True, exist_ok=True)
        evidence.write_text("MockTransport fixture supplies complete reasoning_steps to the tool_steps Judge variable. Synthetic delivery evidence only.")
        save_json(project.path("evals"), design)
        return project, design

    def apply_design(self):
        code, plan = self.cli("eval", "cases-apply", "--dry-run")
        self.assertEqual(code, 0, plan)
        self.assertEqual(self.cli("eval", "cases-apply", "--expect", plan["token"])[0], 0)
        return plan


class ProjectEvalTests(EvalFixture, unittest.TestCase):
    def test_shared_tester_cases_and_stable_input_change(self):
        project, design = self.prepare()
        self.apply_design()
        self.assertEqual(len(self.api.testers), 1)
        self.assertEqual(len(self.api.cases), 2)
        state = project.state()
        sid = state["resources"]["case:handoff"]["server_id"]
        design["cases"][0]["input"] = "Can I speak to a person?"
        save_json(project.path("evals"), design)
        self.apply_design()
        self.assertEqual(len(self.api.cases), 2)
        self.assertEqual(self.api.cases[sid]["input"], "Can I speak to a person?")
        self.assertEqual(self.api.cases[sid]["label_ids"], ["routing"])
        self.assertEqual(self.api.cases[sid]["attachment_ids"], ["attachment"])
        self.assertTrue(self.api.cases[sid]["meta"]["previous_messages"])
        self.assertEqual(self.cli("eval", "reconcile")[0], 0)

    def test_same_input_distinct_context_and_explicit_pair_removal(self):
        project, design = self.prepare()
        design["cases"][1]["input"] = design["cases"][0]["input"]
        save_json(project.path("evals"), design)
        self.apply_design()
        self.assertEqual(len(self.api.cases), 2)
        design["testers"].append({**copy.deepcopy(design["testers"][0]), "local_id": "new-judge", "name": "New judge", "rationale": "Different evidence policy"})
        design["cases"][0]["pairs"].append({"tester": "new-judge", "rubric": "Alternative", "required_evidence": ["tool_steps"]})
        save_json(project.path("evals"), design)
        self.apply_design()
        sid = project.state()["resources"]["case:handoff"]["server_id"]
        old_tester = project.state()["resources"]["tester:tools"]["server_id"]
        design["cases"][0]["pairs"] = design["cases"][0]["pairs"][1:]
        design["cases"][0]["remove_tester_ids"] = [old_tester]
        save_json(project.path("evals"), design)
        self.apply_design()
        self.assertEqual(len(self.api.pairs[sid]), 1)

    def test_evidence_and_missing_tester_never_apply(self):
        project, design = self.prepare()
        for mutate in (lambda d: d["testers"].clear(),
                       lambda d: d["testers"][0]["evidence"][0].update(availability="unknown"),
                       lambda d: d["testers"][0].update(system_prompt_template="Only {output}"),
                       lambda d: d["cases"].append(copy.deepcopy(d["cases"][0]))):
            broken = copy.deepcopy(design)
            mutate(broken)
            self.assertFalse(validate_design(broken)["design_complete"])
            save_json(project.path("evals"), broken)
            self.assertEqual(self.cli("eval", "cases-apply", "--dry-run")[0], 2)
        self.assertEqual(len(self.api.cases), 0)

    def test_malformed_nested_design_is_reported_without_crashing_status(self):
        project, design = self.prepare()
        for mutate in (lambda d: d.update(testers=None),
                       lambda d: d["testers"][0].update(evidence=None),
                       lambda d: d["testers"][0].update(system_prompt_template=17),
                       lambda d: d["cases"][0].update(pairs="invalid"),
                       lambda d: d["cases"][0]["pairs"].append(None)):
            broken = copy.deepcopy(design)
            mutate(broken)
            save_json(project.path("evals"), broken)
            self.assertEqual(self.cli("validate")[0], 1)
            code, status = self.cli("status")
            self.assertEqual(code, 0)
            self.assertTrue(status["structural_issues"])

    def test_import_preserves_shared_ids_and_local_work(self):
        project, design = self.prepare()
        self.apply_design()
        before = project.path("evals").read_bytes()
        self.assertEqual(self.cli("eval", "pull")[0], 0)
        self.assertEqual(project.path("evals").read_bytes(), before)
        self.assertEqual(len(self.api.testers), 1)
        self.assertEqual(project.state()["resources"]["tester:tools"]["server_id"], "t1")

    def test_shared_model_change_shows_all_affected_cases(self):
        project, design = self.prepare()
        self.apply_design()
        design["testers"][0]["judge_llm_model_id"] = None
        save_json(project.path("evals"), design)
        _, plan = self.cli("eval", "cases-apply", "--dry-run")
        self.assertEqual(len(plan["plans"][0]["shared_impact"]), 2)
        self.assertEqual(self.cli("eval", "cases-apply", "--expect", plan["token"])[0], 0)
        self.assertIsNone(self.api.testers["t1"]["judge_llm_model_id"])

    def test_resource_commands_share_mapping_diff_and_receipts(self):
        project, _ = self.prepare()
        self.apply_design()
        args = ("eval", "case-update", "--case", "c1", "--input", "Person please")
        _, plan = self.cli(*args, "--dry-run")
        self.assertEqual(len(plan["plans"]), 1)
        self.assertEqual(self.cli(*args, "--expect", plan["token"])[0], 0)
        self.assertEqual(self.api.cases["c1"]["input"], "Person please")
        args = ("eval", "evaluator-update", "--evaluator", "t1", "--clear-judge-model")
        _, plan = self.cli(*args, "--dry-run")
        self.assertEqual(len(plan["plans"][0]["shared_impact"]), 2)
        self.assertEqual(self.cli(*args, "--expect", plan["token"])[0], 0)
        self.assertIsNone(self.api.testers["t1"]["judge_llm_model_id"])
        manifest = project.root / "rubrics.json"
        save_json(manifest, {"agent_id": "a", "cases": [{"case_id": "c1", "rubrics_by_evaluator": {"t1": "Call handoff only"}}]})
        args = ("eval", "rubrics-apply", "--rubrics", str(manifest))
        _, plan = self.cli(*args, "--dry-run")
        self.assertEqual([p["resource"] for p in plan["plans"]], ["pairs:handoff"])
        self.assertEqual(self.cli(*args, "--expect", plan["token"])[0], 0)
        self.assertEqual(self.api.pairs["c1"][0]["rubric"], "Call handoff only")
