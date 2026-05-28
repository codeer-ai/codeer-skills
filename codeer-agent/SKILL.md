---
name: codeer-agent
description: Build, evaluate, publish, and analyze Codeer agents over the Codeer API. Use for Codeer agent design, knowledge base uploads, eval cases and rubrics, draft live tests, publishing, production history analysis, and feedback review.
---

# Codeer Agent Lifecycle — skill

Everything you need to build, evaluate, and improve a Codeer agent against
whatever files the user has in their current directory. Authenticates through
the installed `codeer` CLI, usually via a named CLI profile.

## Guardrails

### Mutation guardrail

**Before any call that changes server state** — creating, updating, or
publishing an agent, KB, eval case, rubric, or version — state what you
are about to do and wait for explicit user confirmation. This includes every
POST, PUT, PATCH, and DELETE against the Codeer API.

Read-only calls (GET, listing, exporting, diffing) do not need confirmation.

### Diff guardrail

**Always show the diff before applying changes** to agents or eval cases.
Never apply `codeer agent apply` or `codeer eval cases-apply` without first
presenting what will change. The user must see and approve the diff.

### CLI-only guardrail

Use registered `codeer` domain commands only. If a requested operation is
not supported by the CLI, say that it is not supported by the CLI and stop
for user direction.

---

## Setup

The `codeer` CLI must already be installed and authenticated before this skill
uses it. See **onboarding.md** for profile setup, workspace scope, and
installation from the public GitHub skill URL.

**At the start of any Codeer-skill session, run `codeer check`**
to validate auth, workspace, and agent config.

---

## Two-phase lifecycle

### Phase 1: Build (zero to first publish)

| Step | Module | What happens |
| --- | --- | --- |
| 1–3 | **kb-and-agent** | Scope alignment → KB prep & upload → Agent creation |
| 4 | **eval-cases** | MECE categories → generate cases per category → apply |
| 5 | **eval-debug** | Run eval → diagnose failures → fix → re-run → repeat |
| 6 | **kb-and-agent** | Publish (after user go-ahead) |

### Phase 2: Improve (agent has production traffic)

| Step | Module | What happens |
| --- | --- | --- |
| 1–3 | **history** | Pull production data → analyze → present findings |
| 4 | **eval-cases** | Add new cases from findings (before any fix) |
| 5 | **eval-debug** | Baseline → fix → re-run ALL → review |
| 6 | **kb-and-agent** | Publish or roll back |

Then loop back to Phase 2 Step 1 with new production data.

---

## Module reference

| You want to... | Read |
| --- | --- |
| Set up KB, create or update an agent | [modules/kb-and-agent.md](modules/kb-and-agent.md) |
| Design eval cases and rubrics | [modules/eval-cases.md](modules/eval-cases.md) |
| Diagnose eval failures and apply fixes | [modules/eval-debug.md](modules/eval-debug.md) |
| Analyze production conversations | [modules/history.md](modules/history.md) |
| Understand Codeer server concepts | [reference/concepts.md](reference/concepts.md) |
| Look up CLI commands and flags | [reference/commands.md](reference/commands.md) |
| Troubleshoot errors | [reference/errors.md](reference/errors.md) |

---

## What lives in this skill dir

```
codeer-agent/
├── SKILL.md              ← you are here — setup, guardrails, phase composition
├── onboarding.md         ← user setup for API-key auth
├── modules/
│   ├── kb-and-agent.md   ← scope, KB design/upload, agent create/publish
│   ├── eval-cases.md     ← MECE categories, case design, rubric authoring
│   ├── eval-debug.md     ← unified triage ladder, prompt discipline, fix loop
│   └── history.md        ← production analysis, feedback, coverage gaps
└── reference/
    ├── concepts.md       ← how Codeer server works (KB tools, evaluators, versions)
    ├── commands.md       ← CLI command reference + server links
    └── errors.md         ← common errors and recovery
```
