---
name: codeer-agent
description: Build, evaluate, publish, and analyze Codeer agents over the Codeer API. Use for Codeer agent design, knowledge base uploads, eval cases and rubrics, draft live tests, publishing, production history analysis, and feedback review.
---

# Codeer Agent Lifecycle — skill

Everything you need to build, evaluate, and improve a Codeer agent against
whatever files the user has in their current directory. Authenticates as the
user via a session cookie, so whatever the user can do in the Codeer UI, this
skill can do over the API.

## Mutation guardrail

**Before any call that changes server state** — creating, updating, deleting,
or publishing an agent, KB, eval case, rubric, or version — state what you
are about to do and wait for explicit user confirmation. This includes every
POST, PUT, PATCH, and DELETE against the Codeer API.

Read-only calls (GET, listing, exporting, diffing) do not need confirmation.

## Which doc to read

| You want to... | Read |
| --- | --- |
| Execute a lifecycle stage (create, upload, eval, publish, iterate) | **LIFECYCLE.md** |
| Look up an endpoint shape, field enum, or gotcha | **API_CHEATSHEET.md** |

## Setup (one time, per user)

1. Create `~/.codeer/session.env` with **auth only**:
   ```
   CODEER_API_BASE=http://localhost:8000         # or your staging/prod base
   CODEER_SESSION_ID=<from browser devtools>
   CODEER_CSRF_TOKEN=<from browser devtools>
   ```
2. `chmod 600 ~/.codeer/session.env`
3. Cookies are found in the Codeer UI's devtools -> Application -> Cookies, after logging in.
4. Sessions expire. If calls start returning 401/403, re-grab the cookies.

The skill's wrappers manage their own Python virtualenv under
`${TMPDIR:-/tmp}/codeer-skills/codeer-agent-venv` by default, installing
`httpx` on first use. Set `CODEER_AGENT_VENV` to override the venv location.

### Per-project workspace / org

`CODEER_WORKSPACE_ID` and `CODEER_ORGANIZATION_ID` do **not** live in the
global `session.env` — that would make concurrent sessions on different orgs
collide. Instead, set them per project in `.claude/settings.json`:

```json
{
  "env": {
    "CODEER_WORKSPACE_ID": "<ws_id>",
    "CODEER_ORGANIZATION_ID": "<org_id>"
  }
}
```

Claude Code exports these into every command run inside that project, so
opening Claude Code in `~/customers/acme/` vs `~/customers/initech/`
automatically pins each session to its own workspace.

**At the start of any Codeer-skill session, run `$SKILL_DIR/scripts/codeer check`**
to validate auth, workspace, and agent config. It prints the active identity
and catches setup problems before any change lands in the wrong place.

## Invocation

All paths use `$SKILL_DIR` to refer to this skill's installation directory.
Resolve this once at the start of a session.

```bash
# Raw API calls via the shell wrapper
$SKILL_DIR/scripts/codeer get /accounts/me
$SKILL_DIR/scripts/codeer get /agents/all --param wid=<ws> --param oid=<org>
$SKILL_DIR/scripts/codeer post /agents --json-file ./my_agent.json
$SKILL_DIR/scripts/codeer stream post /chats/42/messages --json '{"message":"hi","agent_history_id":"..."}'

# Python scripts via the managed-venv runner
$SKILL_DIR/scripts/codeer-python $SKILL_DIR/scripts/kb_upload.py --help
$SKILL_DIR/scripts/codeer-python $SKILL_DIR/scripts/eval_run.py --help
```

Always use the resolved absolute path; the wrapper keeps the caller's CWD so
`--json-file` and upload paths resolve relative to the user's project.

For the full script reference with invocation examples, see **LIFECYCLE.md**.

## Two-phase lifecycle

### Phase 1: Build (zero to first publish)

| Step | What happens |
| --- | --- |
| 1. Scope | Align on categories, out-of-scope, conversion goals, hard rules, tools |
| 2. KB | Prepare content files, upload to Codeer |
| 3. Agent | Create agent (prompt + tools + KB) |
| 4. Eval cases | MECE categorize usage scenarios, build cases with rubrics |
| 5. Eval + fix | Run eval -> fix failures -> re-run ALL with regression check -> repeat |
| 6. Publish | After explicit user go-ahead |

### Phase 2: Improve (agent has production traffic)

| Step | What happens |
| --- | --- |
| 1. Observe | Pull conversation histories + feedback from production |
| 2. Analyze | Classify: failures, improvement opportunities, successful patterns to protect |
| 3. Eval cases FIRST | Turn each finding into an eval case BEFORE making any fix |
| 4. Baseline | Run eval on current version (failures should fail, good patterns should pass) |
| 5. Fix | Apply smallest change (prompt, KB, or rubric) |
| 6. Re-run ALL | `--diff-vs` regression check: targeted cases pass, nothing else regressed |
| 7. Decide | User reviews results -> publish, iterate more, or roll back |

Then loop back to Step 1 with new production data.

For detailed step-by-step instructions, see **LIFECYCLE.md**.

## What lives in this skill dir

```
codeer-agent/
├── SKILL.md                  <- you are here — setup, dispatch, orientation
├── LIFECYCLE.md              <- stage-by-stage execution, scripts reference, iteration loop
├── API_CHEATSHEET.md         <- endpoint reference + gotchas
└── scripts/
    ├── codeer                <- shell wrapper for raw GET/POST against the API
    ├── codeer-python         <- managed-venv Python runner for reusable scripts
    ├── _venv_bootstrap.sh    <- shared virtualenv bootstrap
    ├── kb_upload.py          <- build KB + upload + poll
    ├── agent_apply.py        <- POST or PUT agent from JSON payload
    ├── eval_cases_apply.py   <- bulk-create eval cases with rubrics
    ├── eval_run.py           <- trigger eval, print non-perfect analysis
    ├── agent_diff.py         <- compare system_prompt + tools between two versions
    ├── eval_table_export.py  <- stdlib-only full eval table export
    ├── eval_rubrics.py       <- read per-(case, evaluator) rubrics
    ├── eval_rubrics_apply.py <- apply rubric edits (pairs with eval_rubrics.py)
    ├── eval_reconcile.py     <- compare local eval manifest with server state
    └── codeer_cli/           <- Python package, importable
        ├── client.py  constants.py  _validate.py
        ├── agents.py  kb.py  chats.py  eval_.py  histories.py
        ├── parse.py          <- typed views over response shapes
        └── cli.py
```
