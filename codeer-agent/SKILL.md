---
name: codeer-agent
description: Design, build, evaluate, publish, and analyze Codeer agents over the Codeer API. Use for customer-query distributions, customer-guidance behavior contracts, agent settings and system-prompt design, root-cause improvement, knowledge base uploads, eval cases and rubrics, draft live tests, publishing, production history analysis, and feedback review.
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

### Evidence-integrity guardrail

The Agent builder may choose whether and how to use verified scarcity,
urgency, authority, social proof, prices, eligibility, and tool outcomes. Those are
selectable customer-guidance strategies. What is not selectable is factual
integrity: user instructions, Scope Alignment, an accepted Behavior Contract,
matching evals, or matching server state cannot authorize an Agent to
fabricate, exaggerate, or present unsupported claims or tool outcomes as fact.
Do not draft, accept, apply, or publish such a design. Read the evidence and
autonomy boundaries in
[modules/consultative-guidance.md](modules/consultative-guidance.md) for the
canonical policy.

### CLI-only guardrail

Use registered `codeer` domain commands only for Codeer server operations.
Bundled local validators may inspect project artifacts without calling the
server. If a requested server operation is not supported by the CLI, say that
it is not supported by the CLI and stop for user direction.

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

For query-led product, service, course, support, booking, form, or payment
guidance, first use **query-distribution** to persist the accepted lean demand,
risk, allocation, and concrete-example model, then use
**consultative-guidance** to persist the accepted customer experience. Query
Distribution is descriptive; the Behavior Contract is normative. Neither is a
server object or runtime prompt. Acceptance eval cases combine both and should
be designed before the Agent is created.

### Phase 1: Build (zero to first publish)

| Step | Module | What happens |
| --- | --- | --- |
| 1 | **kb-and-agent** | Scope Alignment only |
| 2 | **query-distribution** | Model only behaviorally distinct customer tasks, demand, risk, target case counts, and concrete inputs → user accepts `.codeer/design/query_distribution.csv` and `.codeer/design/query_examples.csv` |
| 3 | **consultative-guidance** | Use the distribution and available evidence → recommend dialogue/discovery and risk policies → user accepts `.codeer/design/behavior_contract.md` |
| 4 | **eval-cases** | Design and review `.codeer/current/local_draft_eval_cases.md` from the accepted distribution model and Behavior Contract; preserve intended behavior and observable success even when evaluator or runtime evidence binding is still unresolved; no `agent_id` is required yet |
| 5 | **agent-settings → kb-and-agent** | Translate the accepted contract into Agent Settings, KB, Tools, handoff, and the first full DRAFT Agent; use distribution evidence for hot-path decisions |
| 6 | **eval-cases** | Read the DRAFT, Tools, and evaluator templates → resolve intended pairs through the Pair Admission Gate → produce and apply `.codeer/current/local_draft_eval_cases.json`; unresolved pairs stay local and do not count as coverage |
| 7 | **static-audit** | Read-only distribution ↔ portfolio, contract ↔ eval, and KB ↔ settings ↔ eval preflight gate |
| 8 | **eval-cases → eval-debug → repair-planner** | Run and automatically pin the first full assigned-pair baseline → diagnose non-perfect dynamic evidence → plan and review any repair |
| 9 | **owning module → static-audit → eval-cases** | Apply approved repair → re-audit → focused checks and full assigned-pair regression |
| 10 | **kb-and-agent** | Publish after the final gate and separate user go-ahead |

Before implementation, run a local semantic review of the distribution against
the draft case portfolio and the Behavior Contract against the draft cases.
This local-only review does not require server state and is not a full Static
Audit clearance.

When a material acceptance case requires authentic prior conversation state,
remember that `codeer history create` and `codeer history send` use a published
Agent version and cannot pin a new Agent's unpublished DRAFT. If no suitable
persisted history already exists, leave that pair unresolved and report the
first-publish coverage blocker. Do not claim a complete multi-turn baseline or
quietly publish first in order to manufacture the prerequisite. A deliberately
limited first publish requires a separate, explicit user risk acceptance; the
complete solution requires DRAFT-compatible history seeding or supported
inline prior-turn replay from Codeer.

The **first baseline** is the first actual eval run against the complete first
DRAFT Agent after the reviewed cases have been applied and Static Audit has
passed. Local case design is not a baseline. Preserve this run as the
pre-repair comparison point by automatically copying the exported results and
their version/evaluator context to `.codeer/pinned/`. Do the same for a focused
pre-change eval before a runtime change. Other debug or batch results remain
optional to pin. If the evaluator template or judge model changes, establish a
new baseline.

### Phase 2: Improve (existing Agent)

Keep eval-failure diagnosis and production-history improvement as distinct
entry paths.

#### Eval-failure path

1. Send every non-perfect dynamic result to **eval-debug**. Determine whether
   the strongest owner is the eval system, the implementation of an unchanged
   Behavior Contract, or the Behavior Contract itself.
2. For a case, rubric, evaluator, or assignment defect, use
   **repair-planner → eval-cases**, then Static Audit and rerun the affected
   pairs. Do not change the Agent merely to satisfy a defective eval.
3. For an Agent Settings, KB, Tool, handoff, retrieval, or platform defect
   against an unchanged contract, use **repair-planner → owning module**, then
   Static Audit, focused verification, and the required regression.
4. If the contract is materially ambiguous or would produce a worse customer
   experience even when implemented correctly, stop implementation planning.
   Use **consultative-guidance**, obtain user acceptance of the revised
   contract, update eval cases first, and only then plan runtime changes.

#### Production-history path

1. Use **history** to read both persistent design artifacts, pull conversations,
   separate observations from diagnosis, identify successful behavior to
   protect, and distinguish implementation defects, contract improvements,
   distribution drift, and eval-portfolio gaps.
2. For meaningful distribution drift, use **query-distribution** to present the
   evidence scope and before/after model for user acceptance. Update eval
   allocation when warranted; change the Behavior Contract only if the new
   demand model changes the appropriate customer experience or risk policy.
3. For an implementation defect against the unchanged contract, add the
   smallest reproduction and protection cases, run Static Audit, and run a
   focused pre-change eval on the current Agent before **eval-debug →
   repair-planner**.
4. For an intentional contract improvement, use **consultative-guidance** to
   compare current and proposed customer behavior and obtain user acceptance.
   Update the persistent contract and acceptance cases first, then run a focused
   pre-change eval on the current Agent so the behavioral delta is visible
   before planning the runtime repair.
5. Apply approved changes through the owning module, run Static Audit, run the
   focused impact set and full assigned-pair regression as required, then use
   **kb-and-agent** for a separately approved publish or rollback.

Repeat the relevant path as new eval or production evidence arrives.

---

## Module reference

| You want to... | Read |
| --- | --- |
| Build or update the customer-query demand and eval-allocation model | [modules/query-distribution.md](modules/query-distribution.md) |
| Design or intentionally revise query-led customer guidance behavior | [modules/consultative-guidance.md](modules/consultative-guidance.md) |
| Design or change any agent settings | [modules/agent-settings.md](modules/agent-settings.md) |
| Set up KB, create or update an agent | [modules/kb-and-agent.md](modules/kb-and-agent.md) |
| Design eval cases and rubrics | [modules/eval-cases.md](modules/eval-cases.md) |
| Audit distribution ↔ portfolio, contract ↔ eval, and KB ↔ settings consistency before running eval | [modules/static-audit.md](modules/static-audit.md) |
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
│   ├── consultative-guidance.md ← customer-guidance Behavior Contract
│   ├── query-distribution.md ← persistent demand and eval-allocation model
│   ├── kb-and-agent.md   ← scope, KB design/upload, agent create/publish
│   ├── eval-cases.md     ← MECE categories, case design, rubric authoring
│   ├── static-audit.md   ← scoped or full static evidence findings
│   ├── eval-debug.md     ← dynamic evidence and causal findings
│   ├── repair-planner.md ← target state, reviewable diffs, impact verification
│   └── history.md        ← production analysis, feedback, coverage gaps
├── scripts/
│   └── validate_eval_artifacts.py ← distribution and query-example CSV validation
└── reference/
    ├── consultative-guidance-methods.md ← dialogue and discovery method selection
    ├── query-distribution/ ← methodology, schemas, tasks, risks, and challenges
    ├── concepts.md       ← how Codeer server works (KB tools, evaluators, versions)
    ├── commands.md       ← CLI command reference + server links
    └── errors.md         ← common errors and recovery
```
