# Lifecycle composition

Read for a cross-module build, repair or production-feedback journey. For a local question, read only its owning module. Project mechanics and evidence use [project.md](../reference/project.md).

## Choose the next action from evidence

For a build, resume or next-step request, recover the user's current outcome,
scope and authorization first. Read the relevant established design and draft,
source index, implementation, case drafts and configured manifest; inspect the
receipts, audit and exact runs supporting progress claims. Use `codeer status`
and `codeer validate` for machine-checkable facts. The log explains rationale;
neither prose nor file presence establishes completion.

Choose the earliest missing prerequisite for the requested action, rather than
restarting the whole build or assigning one global stage to every scenario:

| Evidence / missing prerequisite | Next action | Completion condition |
| --- | --- | --- |
| Unfinished resource, publication or run operation | Inspect its receipt/results and reconcile recorded identities | Known outcomes; unknown creates/triggers investigated before retry |
| Structural errors | Repair the named files/references | Structural checks pass; semantic and evidence checks remain separate |
| Website content not yet available for local review | Obtain a bounded read-only snapshot/export through available capabilities; identify missing access/content if unavailable | Actual source content and provenance are saved; no crawler target is created to bypass acquisition |
| Local build artifacts without a covering, current local alignment review | Review sources, design, KB, Instructions and acceptance cases before the first remote apply | Covered relationships are aligned or have explicit scoped decisions; reviewed identities/findings are recorded |
| Established behavior and case drafts, but unknown Tester/Tool evidence contracts | Inspect supported capabilities/templates and actual producer/delivery; review candidate pairs | Supported pairs are admitted; unresolved candidates and affected requirements remain explicit |
| Reviewed local configuration without deployment readback | Resolve explicit mappings, preview authorized changes, apply and read back | Agent/KB/Eval match reviewed content and referenced KB is READY |
| Applied content without a current pre-eval audit | Audit the exact version, dependencies and intended pairs | Current semantic clearance covers the intended run |
| Matching audit without a baseline | Recheck live prerequisites and execute within authorization | Exact run records intended, completed, skipped and unresolved pairs separately |
| Run execution errors or missing evidence | Inspect exact results and execution dependencies | Evidenced fault resolved; current version/audit checked before retry |
| Quality failures with usable runtime evidence | Diagnose, propose the affected repair and regression | Reviewed repair, matching readback and renewed affected verification |
| Passing, unchanged run with missing/invalid audit before publication | Review and renew audit for the exact version/pairs; retain existing run/results | Current audit and acceptance coverage are established; rerun only if new findings change configuration or require missing coverage |
| Passing run | Check confirmed acceptance coverage and exact publish target | Acceptance evidence is complete; publication separately authorized |

Several rows may apply to different units. State the affected scope and continue
independent authorized work; a deferred handoff capability does not prevent
authoring factual-answer cases. Do not silently reduce accepted scope or call a
limited run the complete acceptance baseline. Capability reads are separate
from remote writes; an offline-only request stays offline, and a missing target
is clarified when a target-specific operation actually needs it.

Use `status.next_action` as a starting point, then check its evidence and missing
prerequisite against the actual artifacts and task. Offline status knows only
recorded observations, not live readiness, business decisions or a root cause.
An `error` outcome does not establish poor answer quality or expired SSO; verify
the error evidence before naming a cause. Mixed runs may need execution repair
and quality diagnosis for different pairs. Preserve exact IDs and receipts.

At start/resume and a meaningful handoff, briefly state established progress,
the missing prerequisite and affected scope, the next action and what finishes
it. Continue already-authorized work without asking again. A completed bounded
request ends at its scope with a concrete handoff. Repeat a review only for new
content, new evidence, a material unresolved finding or invalidated clearance;
name that trigger and retain unaffected conclusions. Do not keep expanding
cases or redesigning the Agent when the missing prerequisite is a capability,
deployment or execution dependency. Keep records in existing artifacts/logs;
do not create a second workflow-state document.

### Completion meanings

Use [collaboration guidance](../reference/collaboration.md) to explain these
distinctions through concrete outcomes, rather than repeating internal labels.

| Report | What it establishes |
| --- | --- |
| Behavior/case draft authored | Input, intended behavior and prohibited outcomes are reviewable; Tester/evidence decisions may remain unresolved |
| Eval design complete | Tester suitability, Case/Rubric, pairs and necessary evidence producer/delivery contracts have been reviewed; no unresolved requirement is counted as executable coverage |
| Apply-ready | The reviewed content also passes format, mapping/dependency and operation prerequisites; it is not applied yet |
| Run-ready | Matching readback, referenced KB readiness and current exact-version/pair audit permit execution |
| Executed / accepted | Actual run outcomes are recorded / confirmed acceptance is covered and passing; neither implies publication |

Contract verification from supported code/templates is distinct from observing
actual runtime delivery. CLI `design_complete` checks declared contracts and
references; a flag or report file cannot perform semantic review. Missing server
IDs do not prevent local design; unknown evidence contracts keep that part a draft.

## Eval feedback and next action

An ordinary request to test an Agent includes a result summary and bounded
initial diagnosis after results become available. Read the actual responses,
rubrics, source facts and decisive traces through [Eval Debug](../modules/eval-debug.md),
with triage for comparable or substantial runs. Respect requests to execute or
export only and retain bounded scope. No new repair, run or publication is
authorized by this transition.

Explain execution/completion separately from answer quality, evidence gaps and
Judge errors. For material findings give the observed behavior and consequence,
strongest supported mechanism, remaining alternatives, recommended repair owner
and smallest verification. Missing policy, curation omission, unreached source,
misuse of retrieved facts, misgrading and execution defects need different fixes.
Correct evidence retrieved with a wrong answer is not by itself proof that
Instructions caused it. Inspect full settings and conflicts; name the smallest
discriminating check if uncertain. Inspect useful PASS controls too.

Hand proposals to Repair Planner within existing authorization. Do not paste
each failed answer into Instructions, silently weaken tests or rerun until scores
improve. Fixed-response Judge checks differ from new Agent generations. End the
bounded task with a recommendation and completion condition, not unexplained
scores or a demand that users choose another mode.

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
| 4a | **eval-cases → project capabilities** | Before finalizing affected Tester templates/Rubrics/pairs, inspect available templates and actual evidence contracts; preserve unknown Tool/multi-turn decisions in the draft. Existing Testers can be inspected before Agent creation; contract-dependent details may need the deployed DRAFT readback in Step 6 |
| 5 | **agent-settings → kb-and-agent** | Prepare local Instructions, settings, KB, Tools and handoff from the established design; website KB starts from read-only saved content, not crawler creation; keep capability assumptions explicit |
| 5a | **static-audit: local alignment** | Before any first remote resource write, review sources ↔ design ↔ KB ↔ Instructions ↔ acceptance cases; reuse covered unchanged findings and resolve affected mismatches |
| 5b | **owning apply modules** | Preview/apply authorized resources only after the local alignment prerequisite; for website-backed KB follow [crawler creation and content readback](../modules/kb-and-agent.md#website-backed-kb-creation), review actual-content differences, then read back the first full DRAFT and KB readiness |
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
Once local KB/Instructions and acceptance artifacts exist, use
[local alignment before first apply](../modules/static-audit.md#local-alignment-before-first-apply).
The earlier design/case check may supply part of its coverage; only new or
changed relationships need additional review. Local reports do not replace the
deployed-version audit in Step 7.

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
pre-repair comparison point by pinning its exact run/result identities and
exact version/evaluator context using [batch evidence rules](../reference/project.md#batch-reviews-and-project-entry).
Only `passed`, `failed` or `stale` run records stay fixed during export: link them
with their raw-file SHA-256. For other statuses, save one original `run.json` byte
snapshot and hash before diagnosis, repair or refresh; export may overwrite the
canonical record. Reuse verified pins and do not duplicate the whole run tree.
Pin any focused pre-change
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
