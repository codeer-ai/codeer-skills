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

## Setup (one time, outside this skill)

The `codeer` CLI must already be installed and authenticated before this skill
uses it. Do not create or read credential files inside the skill workspace.

For local development of the CLI from this monorepo, use an editable install:

```bash
cd /path/to/codeer-skills/codeer-cli
uv tool install --editable .
```

### Per-project workspace / org

`CODEER_WORKSPACE_ID` and `CODEER_ORGANIZATION_ID` do **not** live in the
global auth config — that would make concurrent sessions on different orgs
collide. They are non-secret scope values and can be passed as CLI flags or
set in the command environment.

For Claude Code, set them per project in `.claude/settings.json`:

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

For Cowork, pass `--workspace` and `--org` explicitly or export them in the
specific bash call. Credentials should be supplied by the Cowork/runtime
environment or by an external CLI credential store, not by files in the skill
workspace.

**At the start of any Codeer-skill session, run `codeer check`**
to validate auth, workspace, and agent config. It prints the active identity
and catches setup problems before any change lands in the wrong place.

## Invocation

Use the installed `codeer` binary. In Cowork, each bash call is independent, so
pass any needed workspace/org values in that call.

```bash
# Domain commands
codeer agent list --workspace <ws> --org <org>
codeer agent versions --agent <id>
codeer kb list --workspace <ws> --org <org>
codeer kb upload --dir kb/ --name "My KB" --workspace <ws> --org <org>
codeer eval list --agent <id>
codeer eval evaluators --workspace <ws>
codeer eval run --agent <id> --latest-draft --workspace <ws>

# Raw API escape hatch
codeer api get /accounts/me
codeer api post /agents --json-file ./my_agent.json
codeer api stream post /chats/42/messages --json '{"message":"hi"}'
```

For the full command reference, see **LIFECYCLE.md**.

## Two-phase lifecycle

### Phase 1: Build (zero to first publish)

| Step | What happens |
| --- | --- |
| 1. Scope | Align on categories, out-of-scope, conversion goals, hard rules, tools |
| 2. KB | Prepare content files, upload to Codeer |
| 3. Agent | Create agent (prompt + tools + KB) |
| 4. Eval cases | MECE categorize usage scenarios, build cases with rubrics |
| 5. Eval + fix | Run eval -> diagnose failures -> apply the smallest generalizable fix -> re-run ALL with regression check -> repeat |
| 6. Publish | After explicit user go-ahead |

### Phase 2: Improve (agent has production traffic)

| Step | What happens |
| --- | --- |
| 1. Observe | Pull conversation histories + feedback from production |
| 2. Analyze | Classify: failures, improvement opportunities, successful patterns to protect |
| 3. Eval cases FIRST | Turn each finding into an eval case BEFORE making any fix |
| 4. Baseline | Run eval on current version (failures should fail, good patterns should pass) |
| 5. Fix | Apply the smallest generalizable change (prompt, KB, or rubric) |
| 6. Re-run ALL | `--diff-vs` regression check: targeted cases pass, nothing else regressed |
| 7. Decide | User reviews results -> publish, iterate more, or roll back |

Then loop back to Step 1 with new production data.

For detailed step-by-step instructions, see **LIFECYCLE.md**.

## What lives in this skill dir

```
codeer-agent/
├── SKILL.md                  <- you are here — setup, dispatch, orientation
├── LIFECYCLE.md              <- stage-by-stage execution, command reference, iteration loop
├── API_CHEATSHEET.md         <- endpoint reference + gotchas
└── scripts/
    ├── codeer                <- unified CLI: codeer <noun> <verb>
    ├── codeer-python         <- managed-venv runner (used internally by codeer)
    ├── _venv_bootstrap.sh    <- shared virtualenv bootstrap
    └── codeer_cli/           <- Python package
        ├── client.py  constants.py  _validate.py
        ├── agents.py  kb.py  chats.py  eval_.py  histories.py
        ├── parse.py          <- typed views over response shapes
        ├── cli.py            <- dispatcher
        └── commands/         <- agent, kb, eval, check, api subcommands
```
