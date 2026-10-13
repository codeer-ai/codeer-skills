"""Reproduce synthetic API journeys and retain their reviewable artifacts."""
import argparse
from pathlib import Path
import shutil

from test_project_workflow import WorkflowTests
from test_project_deployments import DeploymentTests
from test_project_resource_exports import ResourceExportTests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.out_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    for name, cls, method in (("new-agent", WorkflowTests, "test_new_agent_repair_regression_and_release"),
                              ("existing-agent", WorkflowTests, "test_existing_agent_web_conflict_and_history_candidates"),
                              ("portable-deployments", DeploymentTests, "test_complete_portable_eval_release_delivery_and_environment_isolation"),
                              ("platform-resume", DeploymentTests, "test_platform_resume_fixture"),
                              ("kb-faq-portability", ResourceExportTests, "test_faq_resume_fixture")):
        destination = output / name
        if destination.exists():
            parser.error(f"Use a fresh output directory; exists: {destination}")
        test = cls(method)
        test.setUp()
        try:
            getattr(test, method)()
            shutil.copytree(test.artifact, destination)
            print(f"PASS {name}: {destination}")
        finally:
            test.doCleanups()


if __name__ == "__main__":
    main()
