# Eval assessment, reports and customer clarification

Use after an ordinary Eval to turn captured results into a readable assessment,
improvement recommendation and, when needed, a customer clarification draft.
Also use when reviewing existing results, preparing a missing-information
questionnaire or incorporating its replies. This is part of the existing Eval
journey, not a new mode or CLI command. Respect execute/export-only requests,
local scope and existing authorization; do not send the draft to anyone unless
asked. A questionnaire is not a prerequisite for starting useful work.

## Assess the captured run

Resolve the exact target, AgentHistory/version, run, selected pairs and captured
Case/Rubric/Tester context. Use existing CLI evidence: offline `eval inspect-run`
for recorded/derived states, original `runs/<run-id>/run.json` and its snapshot /
input files for actual responses, criteria and traces. Inspect-run is not a
semantic review. `eval export --run-id` may refresh evidence and is not an
offline report command; follow [batch evidence rules](../reference/project.md#batch-reviews-and-project-entry)
before refresh or diagnosis. Project `eval export --run-id <id>` writes a JSON
run export, not CSV or summary Markdown. The separate Agent/history/version
table-export path produces CSV/JSON/summary Markdown and may see newer results
for that version; verify exact result IDs before using it for a prior run.
Neither export performs this assessment. Missing evidence stays missing; never
borrow a newer result or another binding's answer.

Explain execution/completion separately from answer quality and coverage.
Review non-perfect results through [Eval Debug](eval-debug.md); use
[triage](regression-triage.md) for substantial or comparable runs. Inspect useful
PASS controls, especially consequential actions and behavior touched by a
change. State the actual review scope; a sampled PASS review is not exhaustive.
A first run is a baseline, not proof of improvement. Changed evaluators or
criteria limit score comparisons; a score flip alone does not establish a
stable behavior change.

For each material finding establish the observed behavior, consequence, source
or criterion, strongest supported cause and remaining uncertainty. Distinguish:

| Finding | Next action |
| --- | --- |
| Missing, conflicting or outdated business fact/policy | Recover designated sources first; ask the smallest unresolved business question |
| Authoritative source exists but curated knowledge omits it | Repair source-to-KB mapping; do not ask the customer to resupply an established rule |
| Relevant content not retrieved or retrieved but misused | Inspect routing, tool use and settings; propose the evidenced owner, not an automatic prompt patch |
| Reasonable response fails an unsupported criterion or Judge misreads evidence | Review the criterion/Judge; resolve material acceptance choices before runtime repair |
| Tool, platform, delivery or evidence problem | Keep an internal verification item; customer policy answers do not prove technical completion |

If only a pasted summary is available, distinguish a visible answer defect from
an unverified implementation cause. Give a bounded finding and the smallest
missing anchor; do not refuse all useful analysis or claim a full root-cause review.

Recommend priority by consequence, affected scope and dependencies, not just
score. State what can be fixed from existing evidence, what needs a decision,
what is unverified and what can continue independently. Use
[Repair Planner](repair-planner.md) for changes within scope, with successful
behavior to protect and the smallest useful verification. A proposal grants no
new apply, run or publish permission.

## Write a decision-ready batch report

For every newly assessed run, record its conclusion and next action in the
relevant batch review, normally `reviews/batches/<batch-id>/report.md`. Keep
successive runs distinguishable: append a short run-specific conclusion and
update the current recommendation without erasing prior observations or
decisions. Depth follows significance; a passing run with no actionable finding
needs only a brief bounded conclusion and coverage limits. Repeated reads or
unchanged checks reuse the report; explicit export-only work need not add one.
Without a project, provide the bounded assessment in chat rather than forcing
initialization. Do not maintain a parallel issue/status database.

Lead with what the Agent did, why it matters and the recommended next step.
Use the reader's vocabulary; explain technical ownership through the behavior
it must fix. Prefer short finding paragraphs when table cells would become
multi-sentence logs. Keep long traces and internal identifiers outside the main
findings; tables should make decisions easier to compare.
For material findings make these recoverable, adapting prose or tables to the
audience rather than imposing a fixed schema:

- original user question and relevant actual answer, labeled when excerpted;
- expected behavior and its basis, including the disputed criterion if any;
- observed defect or disagreement, decisive evidence and uncertainty;
- recommended change or exact decision needed, priority and affected scope;
- successful behavior to protect and verification/completion condition.

Keep exact run/history/result IDs, fingerprints and detailed traces in a compact
evidence section or linked attachments. Distinguish test answers, production
conversation observations and suggested wording. “Production environment” does
not mean a draft test answer was delivered to a real customer. Preserve evidence
using the project rules, including pins for updateable runs.

Before editing an existing report, check whether active audit metadata or fixed
delivery evidence fingerprints it. Leave a fingerprinted report unchanged;
continue in a sibling follow-up document within the batch and point README/log
navigation there. Do not move old evidence or silently regenerate clearance.
If findings invalidate the prior semantic conclusion, state that and obtain the
required current review before the next gated operation, even if old bytes match.

## Stop tuning when the standard needs discussion

When a reasonable answer repeatedly fails the same expectation, or evidence
already exposes a material criterion/source/design conflict, pause affected
runtime repairs and reruns. Do not require a fixed number of failed iterations.
Prepare the concrete discussion item first: original question, actual response,
criterion and basis, decisive evidence, exact disputed choice, recommended
resolution and consequence. Separate a clear Judge defect from an unresolved
business acceptance choice. Continue unrelated authorized work.

Do not weaken criteria to improve scores or generate answers repeatedly to find
a pass. A supported fixed-response Judge check tests grading; a new Agent run
also changes the response. If fixed-response rejudging is unavailable, report
that limitation rather than inventing a command. Preserve historical scores;
accepted criterion changes establish a changed comparison context.

## Prepare a customer clarification draft only for real gaps

When the assessment exposes material business information that designated
sources and accepted decisions do not resolve, check relevant existing
questionnaires, replies and pending items when available. With no existing
questionnaire or reply, prepare the first local draft from the available sources
and observations without waiting for another request. Discovery gaps can justify
a draft before any Eval; neither prior questionnaires nor repeated runs are
prerequisites. If no material business gap exists, say so and omit the draft.
Keep implementation, Judge and platform questions in the internal report.

Reuse unchanged unresolved items by linking their existing questions and replies
in the current batch assessment, including replies of “not yet confirmed.” A new
run or different answer wording alone does not make the missing decision new.
Add or update questions only for new or materially changed information needs;
keep unaffected pending questions traceable without asking them again.

An unreviewed, unshared working draft may be edited in place. Before revising a
reviewed or shared questionnaire, preserve its exact content at a stable version
or path and identify the successor's relationship to it. Match later replies
to the version the customer received, even after a newer draft exists. Reuse the
project's naming and evidence conventions; no extra workflow database or fixed
version schema is required.

Normally save `customer-questionnaire.md` alongside the batch report. Keep the
customer document self-contained: purpose, applicable channel/task, brief source
context, how to answer, and prioritized questions. Use the established customer
language; it may differ from the collaboration language. Do not impose a fixed
question count, channel or full operations survey. Group duplicates, keep each
item focused on one necessary decision, and explain an out-of-scope gap internally
rather than quietly shrinking the agreed Agent scope.

Use these customer-readable fields (translate naturally):

- **Customer question** — a concrete situation the customer recognizes.
- **Current actual answer** — exact relevant response, with excerpts labeled.
- **Please confirm** — the smallest missing fact or decision affecting that
  answer; add one plain sentence on its use only when the connection is unclear.
- **Your answer** — allow editing the answer, a short reply, an existing
  document/link, or “not yet confirmed” for unresolved decisions. An established
  “none / not offered” answer is a fact, not an unknown.

Give the known test date/version or production-observation context once near the
top, marking unavailable metadata as unknown; retain per-item evidence mappings
internally. Label a hypothetical question as such. With no actual answer for that
question/scenario, use “not yet tested” only if it has not been tested; otherwise
use “test incomplete / no recorded answer” as the captured state warrants. Put any proposed wording in a
separately labeled suggestion. Never turn a proposal
into an actual answer, join excerpts into a misleading claim, or treat omitted
content as an invented quote. Remove internal IDs, paths, KB/Tester jargon,
sentinels and unnecessary personal data from the customer draft.

Ask only what changes the answer or next action. For example, if an answer says
two activities are both required for a reward but sources do not establish that
relationship, ask whether rewards are separate or require both. Do not ask the
customer to diagnose retrieval or rewrite the evaluator. Reuse confirmed scope;
offer a recommendation separately when useful, without preselecting a policy.
Missing actual customer questions may justify a separate request for de-identified
examples, not a claim that synthetic questions represent measured demand.

## Incorporate replies and resume

Preserve the returned wording, questionnaire revision, source/confirmation and
applicable task/channel/version in the batch before interpreting it. Keep the
reviewed questionnaire recoverable; do not overwrite it with the customer's
reply or the builder's paraphrase. Map replies to the original gaps using simple
references when useful; no new mandatory decision schema is needed.

Distinguish resolved facts, partial answers, unanswered items and conflicts.
“Not yet confirmed” leaves a gap open. A supplied example is not automatically
policy, and a reply does not silently supersede a designated source. Resolve
material authority, applicability or policy conflicts through the existing
[confirmation rules](../reference/agent-design.md#confirmation-and-progressive-revision).
Clear applicable instructions need no repeat approval.

Within the authorized local scope, carry established facts to the source index /
source record, intended behavior to the resolved Agent design, runtime content
to KB/Instructions/settings, and acceptance decisions to Case/Rubric/Tester
design as appropriate. Change only affected owners; do not copy every reply
into every artifact. Keep unresolved items in the existing draft/report and
recommend an explicit interim handling without inventing policy. Identify the
smallest affected regression and previously successful behavior to protect.
Resume already-authorized work; new remote changes, additional runs and
publication retain their existing authorization boundaries. End with what is
resolved, what remains and the concrete next action.
