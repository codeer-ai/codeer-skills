#!/usr/bin/env python3
"""Run a lightweight smoke test for codeer-agent skill (external API mode).

Usage:
  CODEER_API_BASE=http://localhost:8000 \
  CODEER_API_KEY=... \
  CODEER_WORKSPACE_ID=... \
  /Users/aaronho/workspace/codeer-ai/codeer-skills/codeer-agent/scripts/codeer-python \
  /Users/aaronho/workspace/codeer-ai/codeer-skills/codeer-agent/scripts/skill_smoke_test.py
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codeer_cli import CodeerClient, agents, eval_ as eval_mod  # noqa: E402


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


def _run() -> list[Check]:
    checks: list[Check] = []
    with CodeerClient.from_env() as c:
        try:
            me = c.get('/me')
            checks.append(Check('me', True, f"user={me.get('email') or me.get('id')}"))
        except Exception as e:
            checks.append(Check('me', False, str(e)))
            return checks

        try:
            rows = agents.list_all(c, workspace_id=c.workspace_id or '', organization_id=c.organization_id or '')
            checks.append(Check('agents_all', True, f'count={len(rows)}'))
        except Exception as e:
            checks.append(Check('agents_all', False, str(e)))

        try:
            rows = eval_mod.list_evaluators(c, workspace_id=c.workspace_id or '')
            checks.append(Check('eval_evaluators', True, f'count={len(rows)}'))
        except Exception as e:
            checks.append(Check('eval_evaluators', False, str(e)))

    return checks


def main() -> int:
    checks = _run()
    print(json.dumps({'checks': [asdict(c) for c in checks]}, ensure_ascii=False, indent=2))
    return 0 if all(c.ok for c in checks) else 1


if __name__ == '__main__':
    raise SystemExit(main())
