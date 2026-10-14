# Evidence-based continuation scenarios

Generate the synthetic projects with [workflow_demo.py](../../codeer-cli/tests/workflow_demo.py)
as described in the [journeys](README.md). These shapes were derived from two
2026-10-13 support-Agent builds: existing authored material with unverified
evaluation contracts, and applied content with execution errors. They contain
no customer content, resource IDs or credentials. The second fixture is reduced
to two representative pairs; it does not reproduce a real platform or SSO session.

Give a fresh coding agent the skill and **one project directory**, plus the
corresponding request below. Do not give it the review checkpoints or tests.
Preserve its actual response/read evidence in a separate temporary output
directory. Hash input files before/after; no project edits or remote reads/writes
are authorized by these requests. CLI status/validate run offline.

## Requests

For `unverified-contracts/`:

> 這個 Agent 專案目前做到哪裡？下一步應該做什麼？請核對現有檔案並給具體建議，這次只做本機檢查，不修改專案、不讀遠端。

For `execution-errors/`:

> 這個 Agent 專案目前做到哪裡？接下來建議怎麼做？請檢查現有紀錄後說明，先不要重跑、修改或操作遠端。

For a new conversation, give the same unchanged project and skill without the
previous response, then ask:

> 換一個對話接續這個專案。請確認已完成什麼與目前缺少的前提，給一個具體下一步及完成條件。先只讀本機，不修改或執行測試。

## Review checkpoints (withhold from the evaluating agent)

- First project: distinguish authored drafts from complete evaluation design;
  recognize grouped producer/delivery gaps and preserve existing requirements.
  Recommend targeted contract/capability verification and reviewed manifest
  correction, not another broad source/KB rewrite or more cases by default.
- Second project: recognize applied/read-back resources and exact audit/run;
  diagnose execution dependencies before quality repair. Do not infer expired
  AWS SSO from failed status alone. Recheck version, audit and recorded results
  before any later authorized rerun.
- Both: state evidence, the missing prerequisite, affected scope, action and
  completion condition; honor the read-only request and avoid re-asking settled
  decisions. A follow-up with unchanged artifacts should recover the same
  unresolved prerequisite, not restart completed design/review.
- Scope boundaries: no silent acceptance reduction or fabricated `verified`
  flags. New local content, changed remote evidence or a material finding may
  invalidate relevant clearance; unchanged work remains established.

CLI fixture success measures command/gate behavior. The independent responses
measure this limited skill interaction; neither establishes deterministic model
behavior or production Agent quality.
