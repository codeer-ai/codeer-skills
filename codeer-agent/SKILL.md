---
name: codeer-agent
description: Build, evaluate, publish, and analyze Codeer agents over the Codeer API. Use for Codeer agent design, knowledge base uploads, eval cases and rubrics, draft live tests, publishing, production history analysis, and feedback review.
---

# Codeer Agent Lifecycle — skill

Everything you need to build, evaluate, and improve a Codeer agent against
whatever files the user has in their current directory. Authenticates through
an admin workspace API key supplied by the user's runtime environment.

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

Use the registered `codeer` domain commands only. If a requested operation is
not supported by the CLI, say that it is not supported by the CLI and stop for
user direction.

## Setup (one time, outside this skill)

The `codeer` CLI must already be installed and authenticated before this skill
uses it. Do not create or read credential files inside the skill workspace.
For user setup instructions, see **onboarding.md**.

For local development of the CLI from this monorepo, use an editable install:

```bash
cd /path/to/codeer-skills/codeer-cli
uv tool install --editable .
```

### Workspace / org scope

See **onboarding.md** for auth, workspace scope, and per-environment setup.

**At the start of any Codeer-skill session, run `codeer check`**
to validate auth, workspace, and agent config. It prints the active identity
and catches setup problems before any change lands in the wrong place.

## Invocation

Use the installed `codeer` binary.

```bash
# Domain commands
codeer agent list
codeer agent versions --agent <id>
codeer kb list
codeer kb upload --dir kb/ --name "My KB"
codeer eval list --agent <id>
codeer eval evaluators
codeer eval run --agent <id>
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
| 6. Re-run ALL | Run the full suite again and review targeted fixes plus unrelated case scores |
| 7. Decide | User reviews results -> publish, iterate more, or roll back |

Then loop back to Step 1 with new production data.

For detailed step-by-step instructions, see **LIFECYCLE.md**.

## What lives in this skill dir

```
codeer-agent/
├── SKILL.md                  <- you are here — setup, dispatch, orientation
├── onboarding.md             <- user setup for API-key auth
└── LIFECYCLE.md              <- stage-by-stage execution, command reference, iteration loop
```
