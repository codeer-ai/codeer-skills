---
name: codeer-agent
description: Build and maintain Codeer agents from customer sources, design Case/Rubric/Tester evaluations, audit evidence, apply reviewed changes, evaluate exact versions, diagnose failures, publish and analyze production feedback. Use explicit build/cases/audit/apply/eval/improve/publish/observe modes or equivalent natural language, including scoped work on existing Agents.
---

# Codeer Agent

Use the installed `codeer` CLI for Codeer server operations. Skill modes are
conversation entry points, not CLI commands. Read only the modules relevant to
the current outcome. Preserve a requested local scope and existing decisions.

Read the compact [platform basics](reference/platform-basics.md) and
[collaboration rules](reference/collaboration.md) at entry. Explain behavior,
consequences and a recommended next step in the user's working language;
project-document and customer-facing Agent languages may differ.

Users can start with sources and an ordinary description of the Agent they
want; they need not know mode names or “Agent design.” You own discovery
and the design record. Follow the shared [design discovery and source rules](reference/agent-design.md#discover-and-ground-the-design):
read first, summarize established intent, recommend useful choices and ask only
material unresolved questions. Save important understanding and proposals as
work proceeds; clear instructions do not need approval again to be recorded.

## Start and resume

Find `project.toml` from the current directory upward. Resolve Agent design through
the [new/legacy path rules](reference/project.md#agent-design-paths-and-existing-projects)
before saving; module paths are defaults, not instructions to move existing files.
Read the configured sources index, applicable accepted design, pending proposals and recent
`logs/YYYY-MM.md` entries (continue existing `log.md`); inspect actual receipts/runs behind status claims. Use
`codeer status` and `codeer validate` offline. The log explains reasons and past
milestones; structured evidence determines current machine state.
For a build or a request to continue/choose the next step, use the
[evidence-based continuation rules](workflows/lifecycle.md#choose-the-next-action-from-evidence).
Report established progress, the actual missing prerequisite, the concrete next
action and its completion condition. Status advice is offline evidence, not
semantic acceptance or new authorization; inspect the relevant artifacts.

For a new development directory use `codeer init <directory>` without credentials.
For schema 2, verify connection, explicitly configure `agent bind --alias <name>
--agent <id>` and select it with `agent use <name>` (or global `--deployment`).
An existing Agent then starts with read-only `agent pull`, then relevant
KB exports and `eval pull`. Import preserves IDs and local work; it does not
approve behavior or recreate shared resources. Missing historical Agent design does
not block scoped diagnosis or a confirmed repair. Read
[project mechanics](reference/project.md) for paths, adoption and evidence.

For “someone changed this on the platform; bring it back,” use the selected
deployment's pull/compare/adopt flow. Present Draft/Published and local differences;
carry forward explicit field choices, ask only unresolved material choices,
and preserve unselected proposals. Adoption writes local content only, never
another deployment. Clone without state requires explicit resource IDs and
alignment decisions; names/profile labels are not identity. Sub-Agent references
remain read-only and block project deployment. Mark missing originals and
unavailable history; an import is not a complete backup.

Without a project, perform bounded local design or existing resource reads
directly; initialization is not required for a question. Explain when a requested
tracked mutation needs initialization. Before the first server operation run
`codeer check`; local work does not need auth. See [onboarding](onboarding.md).

## Mode routing

Choose from the objective, retaining the requested analysis unit and target. For
cross-mode work use the smallest relevant sequence; transitions grant no extra
mutation scope.

| Mode / equivalent request | Read | Inputs → output / completion | Server effect |
| --- | --- | --- | --- |
| `build` / design an Agent from this SOP | [design discovery](reference/agent-design.md), [settings](modules/agent-settings.md), [KB/Agent](modules/kb-and-agent.md) | Sources and goals → grounded design basis and open decisions, local Instructions/settings/KB and acceptance design | Local drafts; apply separately |
| `cases` / turn this failure into a test | [cases](modules/eval-cases.md); [portfolio](modules/eval-portfolio.md) for architecture/coverage review | Source/behavior → Tester, evidence, Case/Rubric, pairs, review; unresolved candidates stay in the draft, admitted pairs enter configured `evals/design.json` | Local design; apply separately |
| `audit` / check only this case | [static audit](modules/static-audit.md), [Agent design](reference/agent-design.md) | Scoped configuration → findings in `reviews/`; full pre-eval clearance binds snapshot, revision, history, covered pairs | Read-only diagnosis |
| `apply` / apply these confirmed changes | [project](reference/project.md), owning module | Reviewed diff and existing confirmation → receipts, readback, remaining gaps; report partial outcomes | Only confirmed KB/Agent/Tester/case/pair batch |
| `eval` / test this exact draft | [cases execution](modules/eval-cases.md), [project evidence](reference/project.md), [debug](modules/eval-debug.md) | Valid audit, exact history, selected pairs → run evidence, results and bounded initial diagnosis; completed differs from passed | Authorized trigger only; no repairs |
| `improve` / explain and fix these failures | [debug](modules/eval-debug.md), [repair](modules/repair-planner.md); [triage](modules/regression-triage.md) for comparable runs | Dynamic evidence or sufficient static findings → cause/uncertainty, local repair diff, affected regression plan | Diagnose/design; confirmed apply separately |
| `publish` / publish the accepted version | [publish](modules/kb-and-agent.md), [project evidence](reference/project.md) | Confirmed acceptance set, current audit/run, exact history → preview, separately authorized publish/readback/release | Explicit publication only |
| `observe` / analyze histories or AI Draft | [history](modules/history.md) | Population/horizon and raw source → de-identified candidates in `reviews/` with provenance, owner and reproduction/protection scope | Reads; no automatic case or prompt changes |

Cases are design-complete only when Tester suitability, per-case requirements,
pairing and evidence are reviewed. Distinguish design-complete, apply-ready and
unresolved using the [completion meanings](workflows/lifecycle.md#completion-meanings).
Authoring a draft is not complete Eval design. Input/Rubric JSON, a template mentioning `{tool_steps}`, or a reply
saying “transferred” does not establish tool evidence. One common tool Tester
can serve many cases with different Rubrics.

For a cross-module build, repair or feedback journey read
[lifecycle](workflows/lifecycle.md). Use [consultative guidance](modules/consultative-guidance.md)
for query-led discovery; [query distribution](modules/query-distribution.md) only
for decisions needing demand/allocation evidence. Read
[coordination](reference/coordination.md) when independent investigations help;
parents retain canonical writes and mutations.

## Shared boundaries

Portable KB import/redeployment includes originals, exact saved text and complete
FAQ through resource export; follow [the KB/FAQ contract](reference/project.md#portable-kb-text-originals-and-faq).
Rebuild FAQ only after target text/range verification. Website crawl settings
are excluded; preserve the gap. Unavailable APIs never authorize URL fallbacks.

Show concrete target, scope, effect and diff before mutations. Carry forward
explicit authorization for the same operation or bounded batch; ask only for a
new material scope, business decision or effect. Publish needs separate
authorization. A dry-run token binds the reviewed diff; it is not user approval.
Reads need no confirmation, including reads implemented as POST.

Before a build's first remote resource write, including KB upload, complete or
reuse the [full local alignment review](modules/static-audit.md#local-alignment-before-first-apply).
It compares sources, established design, KB, Instructions and acceptance cases;
unchanged, covered inputs reuse recorded findings rather than restarting review.
Local design precedes confirmed apply; readback/KB readiness and semantic audit
precede Eval. Audit diagnoses, eval measures, improve proposes; none silently
applies or publishes. Preserve unknown outcomes and reconcile before retry.
Resolve scope mismatches explicitly; never silently switch customer targets.

Save important pending proposals. Accepted behavior belongs in Agent design;
implementation in settings/KB; Tester/Rubric decisions in Eval design. Preserve
confirmation source, exact reviewed content and scope in `reviews/`; append
short reasons, status and evidence links to the current `logs/YYYY-MM.md`
(or existing `log.md`) without copying full
settings/results. Imported behavior is not accepted business policy. Revise the
Agent design only when intended behavior changes or is materially ambiguous.

Apply [evidence and autonomy boundaries](reference/agent-design.md#evidence-and-autonomy-boundaries).
Use [commands](reference/commands.md), [concepts](reference/concepts.md),
[HTTP input contracts](reference/http-input-contracts.md) and
[errors](reference/errors.md) as needed. Unsupported capabilities remain explicit
gaps; use registered CLI commands for server work.
