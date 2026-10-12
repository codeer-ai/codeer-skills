# Lifecycle composition

Read for a cross-module build, repair or production-feedback journey. For a local question, read only its owning module. Project mechanics and evidence use [project.md](../reference/project.md).

## Build and production improvement journeys

These journeys compose the eight skill modes; they are not the implementation
plan's six engineering phases. Enter at the requested mode for existing Agents.
Use the shared [regression scope](../reference/project.md#regression-scope): full
regression covers confirmed acceptance and declared protection pairs. Account
for exploratory/unresolved assignments explicitly.

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
When scope is open, recommend one **core scenario** and one **core outcome**
that form a valuable end-to-end journey. Preserve all tasks the user has already
put in scope. Follow the shared [discovery and source rules](../reference/agent-design.md#discover-and-ground-the-design),
including early persistence and direct recording of clear instructions.
Do not begin by inventorying
every possible scenario, profile, or edge case. Include acceptable alternative
or non-conversion outcomes and only the material safety, authority, quality, and
autonomy guardrails needed to keep that journey reliable. A small first scope
does not relax the canonical evidence and autonomy boundaries.

Treat the core scenario, outcome, and behavior path as the opening of the
Agent design, not as separate artifacts. Expand the design one scenario
at a time only when an observable difference changes the intended outcome,
next move, required evidence, Tool or handoff path, consent boundary, or risk
policy. Keep wording, product, Persona, channel, and challenge variations in
Eval coverage when the same decision policy still applies.

Analysis-specific outcomes and measurement choices belong in the current
analysis scope unless they represent a stable intended customer experience that
the user establishes as part of the intended behavior. Consolidate applicable
instructions, designated source rules and confirmed choices in the Agent design;
do not make their validity depend on another whole-document approval.
Demand observations alone do not establish objectives. This design record
inherits the canonical evidence and autonomy boundaries. Use
[the acceptance-criteria basis](../modules/consultative-guidance.md#basis-for-acceptance-criteria)
to derive case-level requirements without inventing additional quality rules.

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
analysis or sampling design rather than turning it into a Query Type, Agent design branch, or runtime Persona inference.

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
and descriptive; the Agent design is normative. Neither is a server object
or runtime prompt. Acceptance eval cases should be designed before the Agent is
created and can use concrete inputs directly from the accepted scenario and
source evidence when no distribution artifact exists.

Treat the Agent design as the business reviewer and Agent builder's record
of stable intended customer outcomes, guardrails, and material observable
customer-experience decisions. Record the minimum end-to-end decisions and
high-consequence boundaries needed to make the agreed scope reviewable.
Do not turn it into a full support manual by
restating generic service norms, canonical skill guardrails, implementation
details, or each eval variant. Add narrower design detail only when
implementation, eval, or production evidence exposes a material ambiguity or
an intentional experience change; follow
[shared Agent design](../reference/agent-design.md) for the
admission and progressive-detail rules.

### Phase 1: Build (zero to first publish)

| Step | Module | What happens |
| --- | --- | --- |
| 1 | **kb-and-agent** | Read sources and goals; recover established scope, outcomes, capabilities and boundaries; recommend a small starting scope only when not already specified |
| 2 | **shared design discovery** → **consultative-guidance** *(query-led guidance only)* | Distill established intent and unresolved choices; guide the user through material gaps using concrete recommendations; persist decisions and proposals as work proceeds without a whole-document approval ritual |
| 3 | **query-distribution** *(optional; may run before Step 2)* | Only when an active decision requires demand evidence—for example, selecting the core scenario or allocating a broader portfolio → perform the minimum analysis; persist accepted CSV artifacts only when a reusable demand or allocation model is needed |
| 4 | **eval-portfolio** *(when portfolio or evaluator architecture needs review)* → **eval-cases** | Select the minimum decision-useful portfolio and evaluator coverage, then design and review end-to-end acceptance for the agreed scope; use optional distribution evidence only when available and relevant → preserve intended behavior and observable success in `evals/cases.draft.md` before an `agent_id` exists |
| 5 | **agent-settings → kb-and-agent** | Translate the accepted design into Agent Settings, KB, Tools, handoff, and the first full DRAFT Agent; use optional supported demand evidence only for decisions it can justify |
| 6 | **eval-cases** | Read the DRAFT, Tools, and evaluator templates → resolve intended pairs through the Pair Admission Gate → review and apply stable `evals/design.json`; unresolved pairs stay local and do not count as coverage. `evals/legacy-cases.json` is only for standalone legacy operations |
| 7 | **static-audit** | Read-only design/scenario ↔ eval, design ↔ implementation, and eval ↔ observable-runtime preflight gate; a full audit may use the three independent alignment lanes; include distribution ↔ portfolio only when an accepted distribution exists |
| 8 | **eval-cases → regression-triage → eval-debug → repair-planner** | Run and automatically pin the first full baseline for the agreed scope → organize baseline result clusters → diagnose non-perfect dynamic evidence → plan and review any repair |
| 9 | **owning module → static-audit → eval-cases → regression-triage** | Apply approved repair → re-audit → focused checks and full regression for the agreed scope → compare the Agent diff, predicted impact, and observed result delta |
| 10 | **kb-and-agent** | Publish after the final gate and separate user go-ahead |

Before implementation, run a local semantic review of the Agent design's
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
pre-repair comparison point by automatically copying the results and their
exact version/evaluator context to `reviews/evidence/`. Pin any focused pre-change
eval used as a comparison as well. Match exports to the run's version and
result IDs; see [eval-cases.md](../modules/eval-cases.md). Other debug or batch
results remain optional to pin. If the evaluator template or judge model
changes, establish a new baseline.

For an existing Agent, a new pre-change run is useful when it reduces diagnostic
uncertainty or supplies a needed comparison. Do not run merely to reconfirm a
failure already established by sufficient evidence. A clear static defect may
go directly through Repair Planner to an approved correction and post-change
verification. Preserve the prior configuration and available evidence, explain
why a pre-change run adds no decision value, and do not claim an unmeasured
before/after effect. Before a new Agent's first baseline, resolve clear static
defects through the same approved repair path.

### Phase 2: Improve (existing Agent)

Keep eval-failure diagnosis and production-history improvement as distinct
entry paths.

#### Eval-failure path

1. For a comparable or substantial run, use **regression-triage** to match the
   prior and current Agent/eval context, classify result deltas, and organize
   failure clusters. Send every non-perfect dynamic result to **eval-debug**.
   Determine whether the strongest owner is the eval system, the implementation
   of an unchanged Agent design, or the Agent design itself.
2. For a case, rubric, evaluator, or assignment defect, use
   **repair-planner → eval-cases**. Use **eval-portfolio** first when the
   finding requires broader evaluator architecture, portfolio allocation,
   deduplication, or retirement decisions. Then run Static Audit and rerun the
   affected pairs. Do not change the Agent merely to satisfy a defective eval.
3. For an Agent Settings, KB, Tool, handoff, retrieval, or platform defect
   against an unchanged design, use **repair-planner → owning module**, then
   Static Audit, focused verification, and the required regression.
4. If the design is materially ambiguous or would produce a worse customer
   experience even when implemented correctly, stop implementation planning.
   Use the shared [confirmation rules](../reference/agent-design.md#confirmation-and-progressive-revision)
   to resolve the intended behavior, with **consultative-guidance** only for
   query-led guidance. Update eval cases first, then plan runtime changes.

#### Production-history path

1. Use **history** to read the persistent design artifacts, establish the
   current analysis outcome, population, observation horizon, and unit from the
   request and available evidence, and confirm only material ambiguity with the
   user before pulling the necessary conversations. Compare observable entry
   conditions and Agent decision policies, separate observations from
   diagnosis, identify successful behavior to protect, and distinguish
   implementation defects, design improvements, distribution drift, and
   eval-portfolio gaps.
2. When the analysis decision requires demand or allocation evidence, use
   **query-distribution** for the minimum analysis and persist an optional model
   only when it needs reuse across later allocation, capacity, weighted-
   reporting, or drift decisions. A newly observed scenario normally creates
   an Eval probe first; expand the Agent design only when correct handling
   or a stable risk policy changes.
3. When History exposes several candidate probes, evaluator-design needs,
   suite redundancy, or a material allocation choice, use **eval-portfolio** to
   propose the minimum decision-useful keep, merge, retire, and add set. A
   single clear reproduction or protection probe may go directly to
   **eval-cases**.
4. For an implementation defect against the unchanged design, add the
   smallest reproduction and protection cases and run Static Audit. If a
   focused pre-change eval adds decision value, run it on the current Agent
   before **eval-debug → repair-planner**; otherwise use the sufficient
   existing evidence directly in **repair-planner**.
5. For an intentional design improvement, use the shared
   [confirmation rules](../reference/agent-design.md#confirmation-and-progressive-revision),
   and **consultative-guidance** only for query-led guidance, to
   compare current and proposed customer behavior and obtain user acceptance.
   Update the persistent design and acceptance cases first. Run a focused
   pre-change eval when observing the old behavior will inform the repair or
   comparison; an already established mismatch can proceed to **repair-planner**
   without a redundant run.
6. Apply approved changes through the owning module, run Static Audit, run the
   focused impact set and full regression for the agreed scope, use
   **regression-triage** to compare the planned Agent diff with observed deltas,
   then use **kb-and-agent** for a separately approved publish or rollback.

Repeat the relevant path as new eval or production evidence arrives.

---
