"""Reproduce synthetic API journeys and retain their reviewable artifacts."""
import argparse
from pathlib import Path
import shutil

from test_project_workflow import WorkflowTests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.out_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    for name, method in (("new-agent", "test_new_agent_repair_regression_and_release"),
                         ("existing-agent", "test_existing_agent_web_conflict_and_history_candidates")):
        destination = output / name
        if destination.exists():
            parser.error(f"Use a fresh output directory; exists: {destination}")
        test = WorkflowTests(method)
        test.setUp()
        try:
            getattr(test, method)()
            shutil.copytree(test.artifact, destination)
            print(f"PASS {name}: {destination}")
        finally:
            test.doCleanups()


if __name__ == "__main__":
    main()
