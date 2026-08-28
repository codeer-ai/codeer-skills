---
name: codeer-agent
description: Design, build, evaluate, publish, and analyze Codeer agents over the Codeer API. Use for scenario-centered behavior contracts, optional customer-query demand analysis, agent settings and system-prompt design, root-cause improvement, knowledge base uploads, eval cases and rubrics, eval-portfolio optimization, version-aware regression analysis, draft live tests, publishing, production history analysis, and feedback review.
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

Before the first Codeer server read or write in a session, run `codeer check`
to validate auth, workspace, and agent config. Purely local design, artifact
review, or static file work does not require a server check.

---

## Sub-agent orchestration

Use sub-agents when the environment supports them and either the work contains
at least two independent units that can share one pinned evidence set and be
meaningfully synthesized, or one bounded review materially benefits from an
independent, context-isolated perspective. Do not delegate a small scoped read
merely to use parallelism. If sub-agents are unavailable or the work is too
coupled, perform the same module sequentially.

The parent Agent remains the decision owner. It must:

- establish the outcome, scope, analysis unit, and exact Agent/version target;
- read or export server state once when practical, then give workers the same
  immutable local evidence and object fingerprints;
- keep user communication, cross-workstream synthesis, final ownership and
  causal judgments, canonical artifact writes, and every server mutation; and
- resolve disagreements from evidence rather than worker votes.

Workers are read-only investigators. They must not mutate Codeer server state,
edit canonical project artifacts, broaden the accepted scope, rewrite the
Behavior Contract, or apply a repair. Give each worker only the shared anchors,
its bounded assignment, and any common coding or judgment guide. For an
independent audit or challenge, do not preload the parent's suspected diagnosis
or proposed repair. Workers should return findings through their handoff rather
than shared files. If a large intermediate artifact is unavoidable, the parent
must assign a unique non-canonical path that no other worker will edit.

A worker handoff may use any reviewable format, but it must preserve the
assigned scope, evidence inspected, observations, consequence, likely owner,
material alternatives or counterexamples, uncertainty, and the smallest next
evidence needed. The parent must reconcile overlap, calibration differences,
and missing units before making a whole-system or population-level claim.

The module-specific sections below define safe work units for History, Static
Audit, Eval Debug, version-aware triage, and Eval-portfolio optimization.

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

Use **regression-triage** after a completed comparable run to connect an exact
Agent-version diff and predeclared impact map with observed result deltas before
Eval Debug assigns the causal owner. Use **eval-portfolio** when the decision is
which cases, pairs, or evaluators provide enough distinct evidence to justify
their run and maintenance cost. Both are read-only analysis and design stages;
neither applies changes.

### Outcome-anchored lifecycle

Anchor design and improvement work in a user-accepted customer or task outcome.
For a first Agent version, choose one **core scenario** and one **core outcome**
that form the smallest valuable end-to-end journey. Do not begin by inventorying
every possible scenario, profile, or edge case. Include acceptable alternative
or non-conversion outcomes and only the material safety, authority, quality, and
autonomy guardrails needed to keep that journey reliable. A small first scope
does not relax the canonical evidence and autonomy boundaries.

Treat the core scenario, outcome, and behavior path as the opening of the
Behavior Contract, not as separate artifacts. Expand the contract one scenario
at a time only when an observable difference changes the intended outcome,
next move, required evidence, Tool or handoff path, consent boundary, or risk
policy. Keep wording, product, Persona, channel, and challenge variations in
Eval coverage when the same decision policy still applies.

Analysis-specific outcomes and measurement choices belong in the current
analysis scope unless they represent a stable intended customer experience that
the user accepts into the contract. Scope Alignment business or conversion
goals and optional demand evidence are inputs to this decision, not parallel
normative authorities. The accepted Behavior Contract is the sole normative
design source for stable runtime customer outcomes and guardrails.

Admit a field, profile, category, finding, or rule only when it helps select an
appropriate Agent decision, measure or explain an outcome, support a fair
comparison, protect a material guardrail, or drive a named downstream review,
Eval, settings, Tool, KB, handoff, or experiment decision. Observable user entry
conditions describe the context the Agent must adapt to; they do not transfer
accountability for the Agent's next move back to the user. Do not create Persona
or operational-profile taxonomies unless an observable distinction selects
different correct handling. A profile may instead be an **analytic stratum**
when it is useful for fair comparison, outcome measurement, or heterogeneous-
effect analysis but does not change the Agent policy; keep that stratum in the
analysis or sampling design rather than turning it into a Query Type, Behavior
Contract branch, or runtime Persona inference.

Production improvement findings must identify a modifiable Agent decision or
action policy, the entry condition and decision point where it applies, a
plausible alternative action and any available successful or failed contrast,
the outcome and guardrails it is expected to affect, and the evidence needed to
validate the change. Action verbs such as `ask`, `retrieve`, `draft`, or
`handoff` are trace labels, not complete findings.
Conversation, exchange, Episode, task, History, work object, user, and cohort
are selectable analysis units; choose the minimum unit that can observe both
the target outcome and the Agent decisions that may affect it rather than
imposing one universal conversation decomposition.

For query-led product, service, course, support, booking, form, or payment
guidance, use **consultative-guidance** to persist the accepted core scenario,
outcome, and behavior path. Use **query-distribution** only when supported
frequency, weighted portfolio allocation, capacity, hot-path, or production-
drift decisions require a separate demand model. Query Distribution is optional
and descriptive; the Behavior Contract is normative. Neither is a server object
or runtime prompt. Acceptance eval cases should be designed before the Agent is
created and can use concrete inputs directly from the accepted scenario and
source evidence when no distribution artifact exists.

Treat the Behavior Contract as the business reviewer and Agent builder's record
of stable intended customer outcomes, guardrails, and material observable
customer-experience decisions. Start with one core scenario, one core outcome,
and the minimum end-to-end decisions and high-consequence boundaries needed to
make that journey reviewable. Do not turn it into a full support manual by
restating generic service norms, canonical skill guardrails, implementation
details, or each eval variant. Add narrower contract detail only when
implementation, eval, or production evidence exposes a material ambiguity or
an intentional experience change; follow
[modules/consultative-guidance.md](modules/consultative-guidance.md) for the
admission and progressive-detail rules.

### Phase 1: Build (zero to first publish)

| Step | Module | What happens |
| --- | --- | --- |
| 1 | **kb-and-agent** | Scope Alignment selects one core scenario, one candidate core outcome, material exclusions, capabilities, and boundaries |
| 2 | **consultative-guidance** | Use available evidence → define the core outcome and guardrails, then the minimum behavior path, Tool, handoff, and risk decisions that advance or protect them → user accepts `.codeer/design/behavior_contract.md` |
| 3 | **query-distribution** *(optional; may run before Step 2)* | Only when an active decision requires demand evidence—for example, selecting the core scenario or allocating a broader portfolio → perform the minimum analysis; persist accepted CSV artifacts only when a reusable demand or allocation model is needed |
| 4 | **eval-portfolio** *(when portfolio or evaluator architecture needs review)* → **eval-cases** | Select the minimum decision-useful portfolio and evaluator coverage, then design and review a small end-to-end acceptance set for the accepted core scenario; use optional distribution evidence only when available and relevant → preserve intended behavior and observable success in `.codeer/current/local_draft_eval_cases.md` before an `agent_id` exists |
| 5 | **agent-settings → kb-and-agent** | Translate the accepted contract into Agent Settings, KB, Tools, handoff, and the first full DRAFT Agent; use optional supported demand evidence only for decisions it can justify |
| 6 | **eval-cases** | Read the DRAFT, Tools, and evaluator templates → resolve intended pairs through the Pair Admission Gate → produce and apply `.codeer/current/local_draft_eval_cases.json`; unresolved pairs stay local and do not count as coverage |
| 7 | **static-audit** | Read-only contract/scenario ↔ eval, contract ↔ implementation, and eval ↔ observable-runtime preflight gate; a full audit may use the three independent alignment lanes; include distribution ↔ portfolio only when an accepted distribution exists |
| 8 | **eval-cases → regression-triage → eval-debug → repair-planner** | Run and automatically pin the first full assigned-pair baseline → organize baseline result clusters → diagnose non-perfect dynamic evidence → plan and review any repair |
| 9 | **owning module → static-audit → eval-cases → regression-triage** | Apply approved repair → re-audit → focused checks and full assigned-pair regression → compare the Agent diff, predicted impact, and observed result delta |
| 10 | **kb-and-agent** | Publish after the final gate and separate user go-ahead |

Before implementation, run a local semantic review of the Behavior Contract's
core scenario and behavior path against the draft cases. When an accepted Query
Distribution exists and is being used, also review it against the draft case
portfolio. This local-only review does not require server state and is not a
full Static Audit clearance.

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

1. For a comparable or substantial run, use **regression-triage** to match the
   prior and current Agent/eval context, classify result deltas, and organize
   failure clusters. Send every non-perfect dynamic result to **eval-debug**.
   Determine whether the strongest owner is the eval system, the implementation
   of an unchanged Behavior Contract, or the Behavior Contract itself.
2. For a case, rubric, evaluator, or assignment defect, use
   **repair-planner → eval-cases**. Use **eval-portfolio** first when the
   finding requires broader evaluator architecture, portfolio allocation,
   deduplication, or retirement decisions. Then run Static Audit and rerun the
   affected pairs. Do not change the Agent merely to satisfy a defective eval.
3. For an Agent Settings, KB, Tool, handoff, retrieval, or platform defect
   against an unchanged contract, use **repair-planner → owning module**, then
   Static Audit, focused verification, and the required regression.
4. If the contract is materially ambiguous or would produce a worse customer
   experience even when implemented correctly, stop implementation planning.
   Use **consultative-guidance**, obtain user acceptance of the revised
   contract, update eval cases first, and only then plan runtime changes.

#### Production-history path

1. Use **history** to read the persistent design artifacts, establish the
   current analysis outcome, population, observation horizon, and unit from the
   request and available evidence, and confirm only material ambiguity with the
   user before pulling the necessary conversations. Compare observable entry
   conditions and Agent decision policies, separate observations from
   diagnosis, identify successful behavior to protect, and distinguish
   implementation defects, contract improvements, distribution drift, and
   eval-portfolio gaps.
2. When the analysis decision requires demand or allocation evidence, use
   **query-distribution** for the minimum analysis and persist an optional model
   only when it needs reuse across later allocation, capacity, weighted-
   reporting, or drift decisions. A newly observed scenario normally creates
   an Eval probe first; expand the Behavior Contract only when correct handling
   or a stable risk policy changes.
3. When History exposes several candidate probes, evaluator-design needs,
   suite redundancy, or a material allocation choice, use **eval-portfolio** to
   propose the minimum decision-useful keep, merge, retire, and add set. A
   single clear reproduction or protection probe may go directly to
   **eval-cases**.
4. For an implementation defect against the unchanged contract, add the
   smallest reproduction and protection cases, run Static Audit, and run a
   focused pre-change eval on the current Agent before **eval-debug →
   repair-planner**.
5. For an intentional contract improvement, use **consultative-guidance** to
   compare current and proposed customer behavior and obtain user acceptance.
   Update the persistent contract and acceptance cases first, then run a focused
   pre-change eval on the current Agent so the behavioral delta is visible
   before planning the runtime repair.
6. Apply approved changes through the owning module, run Static Audit, run the
   focused impact set and full assigned-pair regression as required, use
   **regression-triage** to compare the planned Agent diff with observed deltas,
   then use **kb-and-agent** for a separately approved publish or rollback.

Repeat the relevant path as new eval or production evidence arrives.

---

## Module reference

| You want to... | Read |
| --- | --- |
| Build or update an optional customer-query demand and eval-allocation model | [modules/query-distribution.md](modules/query-distribution.md) |
| Design or intentionally revise query-led customer guidance behavior | [modules/consultative-guidance.md](modules/consultative-guidance.md) |
| Design or change any agent settings | [modules/agent-settings.md](modules/agent-settings.md) |
| Set up KB, create or update an agent | [modules/kb-and-agent.md](modules/kb-and-agent.md) |
| Design eval cases and rubrics | [modules/eval-cases.md](modules/eval-cases.md) |
| Optimize evaluator value, case/pair coverage, representativeness, and maintenance cost | [modules/eval-portfolio.md](modules/eval-portfolio.md) |
| Audit contract/scenario ↔ eval and KB ↔ settings consistency, plus optional distribution ↔ portfolio alignment | [modules/static-audit.md](modules/static-audit.md) |
| Compare Agent-version changes, predicted impact, and eval-result deltas | [modules/regression-triage.md](modules/regression-triage.md) |
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
│   ├── query-distribution.md ← optional demand and eval-allocation model
│   ├── kb-and-agent.md   ← scope, KB design/upload, agent create/publish
│   ├── eval-cases.md     ← scenario coverage, case design, rubric authoring
│   ├── eval-portfolio.md ← evaluator value and minimum-sufficient portfolio design
│   ├── static-audit.md   ← scoped or full static evidence findings
│   ├── regression-triage.md ← Agent-version and eval-result delta analysis
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
