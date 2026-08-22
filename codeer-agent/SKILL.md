---
name: codeer-agent
description: Design, build, evaluate, publish, and analyze Codeer agents over the Codeer API. Use for agent settings and system-prompt design, root-cause improvement, knowledge base uploads, eval cases and rubrics, draft live tests, publishing, production history analysis, and feedback review.
---

# Codeer Agent Lifecycle — skill

Everything you need to build, evaluate, and improve a Codeer agent against
whatever files the user has in their current directory. Authenticates through
the installed `codeer` CLI, usually via a named CLI profile.

Optimize the resulting agent configuration, not an isolated failing case or
the size of the local diff. Prefer minimum-sufficient settings with simple
instructions, clear component ownership, and low total semantic complexity.
Minimum-sufficient does not mean the shortest system prompt: keep the
operational hot path and invariants resident, and use the KB for authoritative
details and evidence. Read [modules/agent-settings.md](modules/agent-settings.md)
before creating or changing agent settings.

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

Static Audit and Eval Debug are evidence-to-finding stages. Use
**static-audit** to inspect static configuration evidence, either for a scoped
question or as the full pre-eval gate. Use **eval-debug** only after a run has
produced response, tool, retrieval, or judge evidence. When findings warrant a
change, use **repair-planner** as the separate target-state, diff, and
verification-planning stage. Static Audit and Eval Debug share a flexible
finding method based on observation, evidence, consequence, likely ownership,
and uncertainty; neither requires issue codes, JSON, or a fixed report schema.

### Phase 1: Build (zero to first publish)

| Step | Module | What happens |
| --- | --- | --- |
| 1–3 | **kb-and-agent** | Scope alignment → KB prep & upload → Agent creation |
| 4 | **eval-cases** | MECE categories → generate cases per category → apply |
| 5 | **static-audit** | Read-only KB ↔ settings ↔ eval preflight gate |
| 6 | **eval-cases → eval-debug → repair-planner** | Run assigned pairs → diagnose dynamic evidence → plan and review any repair |
| 7 | **owning module → static-audit → eval-cases → kb-and-agent** | Apply approved repair → re-audit → full assigned-pair regression → publish (after user go-ahead) |

### Phase 2: Improve (agent has production traffic)

| Step | Module | What happens |
| --- | --- | --- |
| 1–3 | **history** | Pull production data → separate evidence from diagnosis |
| 4 | **eval-cases** | Add reproduction and validation probes before settings changes |
| 5 | **static-audit** | Verify version, sources, settings, cases, rubrics, evaluators, and assignments |
| 6 | **eval-cases → eval-debug → repair-planner** | Run baseline → diagnose mechanism → plan and review the target state and impact set |
| 7 | **owning module → static-audit → eval-cases** | Apply approved repair → re-audit changed state → focused checks and full assigned-pair regression |
| 8 | **kb-and-agent** | Publish or roll back |

Then loop back to Phase 2 Step 1 with new production data.

---

## Module reference

| You want to... | Read |
| --- | --- |
| Design or change any agent settings | [modules/agent-settings.md](modules/agent-settings.md) |
| Set up KB, create or update an agent | [modules/kb-and-agent.md](modules/kb-and-agent.md) |
| Design eval cases and rubrics | [modules/eval-cases.md](modules/eval-cases.md) |
| Audit KB ↔ settings ↔ eval consistency before running eval | [modules/static-audit.md](modules/static-audit.md) |
| Diagnose existing response/tool/retrieval/judge evidence | [modules/eval-debug.md](modules/eval-debug.md) |
| Turn accepted findings into a target state, diff, and verification plan | [modules/repair-planner.md](modules/repair-planner.md) |
| Analyze production conversations | [modules/history.md](modules/history.md) |
| Understand Codeer server concepts | [reference/concepts.md](reference/concepts.md) |
| Look up CLI commands and flags | [reference/commands.md](reference/commands.md) |
| Troubleshoot errors | [reference/errors.md](reference/errors.md) |

## What lives in this skill dir

```
codeer-agent/
├── SKILL.md              ← you are here — setup, guardrails, phase composition
├── onboarding.md         ← user setup for API-key auth
├── modules/
│   ├── agent-settings.md  ← target-state design and component ownership
│   ├── kb-and-agent.md   ← scope, KB design/upload, agent create/publish
│   ├── eval-cases.md     ← MECE categories, case design, rubric authoring
│   ├── static-audit.md   ← scoped or full static evidence findings
│   ├── eval-debug.md     ← dynamic evidence and causal findings
│   ├── repair-planner.md ← target state, reviewable diffs, impact verification
│   └── history.md        ← production analysis, feedback, coverage gaps
└── reference/
    ├── concepts.md       ← how Codeer server works (KB tools, evaluators, versions)
    ├── commands.md       ← CLI command reference + server links
    └── errors.md         ← common errors and recovery
```
