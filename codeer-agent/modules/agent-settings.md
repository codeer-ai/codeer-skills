# Agent Settings Design

Use this module whenever creating or changing an agent's system prompt, tools,
KB configuration, retrieval routes, model, or handoff settings.

For a query-led customer guidance Agent, first read the accepted
`.codeer/design/query_distribution.csv` from
[query-distribution.md](query-distribution.md), the accepted
`.codeer/design/behavior_contract.md` from
[consultative-guidance.md](consultative-guidance.md), and the reviewed
acceptance cases from [eval-cases.md](eval-cases.md). The distribution describes
expected demand and eval allocation; the contract defines the intended customer
experience; the cases test it. None should be copied verbatim into the system
prompt. Translate them into the simplest coherent ownership split across Agent
Settings, KB, Tools, and handoff.

When improving an existing Agent, do not use a settings repair to make an
unapproved change to the Behavior Contract. If evidence indicates that the
intended experience itself should change, return to Consultative Customer
Guidance, obtain user acceptance, and update eval cases before designing the
runtime diff.

Use supported distribution evidence when evaluating frequency and hot-path
residency, but keep its limits visible. Do not put traffic shares, sampling
claims, speculative frequency estimates, or the distribution artifact itself
into the runtime prompt. A distribution change alone warrants settings work
only when it changes the appropriate operational dependency, capacity, tool
path, or accepted Behavior Contract.

When a change starts from Static Audit or Eval Debug findings, use
[repair-planner.md](repair-planner.md) to establish the cross-component target
state, alternatives, and verification scope. This module supplies the detailed
ownership and settings-design gate for the resulting agent diff.

---

## Optimize the resulting system

Treat an eval failure or production finding as evidence about the current
configuration, not as a requirement to encode verbatim. Optimize for the state
of the whole agent after the change:

- The agent satisfies its operating requirements and hard boundaries.
- Each component has one clear responsibility.
- Each behavior has one primary owner.
- Each instruction expresses one decision principle at the broadest stable
  scope supported by the requirements.
- Instructions are aligned and free of avoidable duplication or exceptions.
- The total information presented to the model is the minimum sufficient for
  reliable behavior.

Minimize total semantic complexity, not diff size. A broader rewrite that
removes, merges, or relocates instructions can be better than appending one
line. Do not shorten settings at the expense of correctness, safety, or
necessary context.

A single case can reveal a structural defect. It can justify a general change
when the evidence supports the underlying mechanism, but never turn the case's
wording directly into a special-case instruction.

---

## Give each component a clear owner

| Component | Owns | Should not become |
| --- | --- | --- |
| System prompt | Operational skeleton and invariants: stable objectives, mode and process selection, core flow map, necessary canonical schemas or mappings, priorities, boundaries, and cross-component decisions | Authoritative long-form domain content, volatile facts, full scripts, repeated rules, copied eval wording, large example sets, or narrow exceptions |
| Tool configuration and invocation instructions | What the tool does, when to call it, inputs, limits, and tool-specific query strategy | General response policy or domain content |
| Knowledge base | Authoritative details and evidence: maintainable domain facts, complete definitions and methods, cases, exceptions, and source-of-truth content | The per-turn operational skeleton, required routing or mode decisions, or invariants whose absence causes directional failure |
| File structure, retrieval routes, and Context Object FAQs | Reliable routing to existing canonical content | A substitute for missing content or a tool the agent never calls |
| Model selection | Capability, latency, and cost tradeoffs | A way to conceal contradictory or overloaded settings |
| Human handoff settings | Transfer availability and operational triggers | Duplicated conversation policy spread across components |
| Evaluators and rubrics | Observable success and failure criteria | A hidden extension of the agent prompt |
| Eval cases | Reproduction, generalization, boundary, and regression probes | Training examples to copy into settings |

When a behavior spans components, keep the governing principle in one place
and put only component-specific execution details elsewhere.

---

## Keep the hot path resident

Treat prompt residency versus retrieval as a reliability and performance
decision, not a prompt-length cleanup rule. Keep a compressed representation
in the system prompt when the agent needs it frequently or before it can decide
what to retrieve, and a retrieval miss would cause the wrong mode, workflow,
schema, boundary, or next step. Put the authoritative expansion in the KB when
the content is detailed, topic-specific, evidentiary, or likely to change.

Use these criteria together:

| Criterion | Favors system-prompt residency | Favors on-demand KB retrieval |
| --- | --- | --- |
| Frequency | Needed in most conversations or turns | Needed only for a specific topic or later branch |
| Decision timing | Required to select a mode, workflow, tool, schema, or retrieval route | Needed after the route and task are already known |
| Miss impact | A miss causes a directional, boundary, or structural error | A miss creates a scoped factual gap the agent can retry, disclose, or escalate |
| Shape and stability | Stable, compact invariant, flow map, schema, or required mapping | Full definition, exact method, evidence, examples, exceptions, or volatile facts |
| Cost | Avoided retrieval latency and miss risk justify recurring context tokens | Recurring context cost exceeds the expected latency and miss risk |
| Maintenance | A compressed control rule can remain canonical without copying its expansion | One authoritative source avoids duplicated content and staleness |

Compare the whole-system tradeoff explicitly. Prompt residency removes a
retrieval round and its latency and miss risk, but spends context on every turn
and can create duplication or stale copies. KB retrieval centralizes detailed
content and reduces recurring context cost, but adds routing dependency,
latency, and retrieval-miss risk. Do not move a required operational dependency
out of the prompt merely because retrieval works on the observed eval case.

Compress rather than copy. Keep the core flow skeleton, mode-selection rules,
canonical output schema, necessary question-to-step mappings, and behavioral
boundaries in the prompt when they meet the criteria above. Store full
step-by-step wording, repeated rules, detailed methods, large example sets,
domain facts, and exceptions in the KB. The prompt may identify when and where
to retrieve the authoritative detail without duplicating it.

Examples:

- **Good split:** A multi-mode advisory agent keeps mode selection, the core
  stage map, its canonical schema, required question-to-step mapping, and
  escalation boundaries in the prompt. The KB owns complete stage definitions,
  exact language, worked examples, edge cases, and supporting evidence.
- **Good split:** A support agent keeps the invariant that unsupported claims
  must not be invented and the decision boundary for KB lookup in the prompt.
  The KB owns product facts, policy text, procedures, and documented exceptions.
- **Bad move:** Put a required schema or mode-selection map only in the KB and
  say to retrieve it when needed. The agent needs that content to recognize the
  need and a miss changes the direction of the response.
- **Bad duplication:** Copy a complete SOP, repeated rules, and many examples
  into the prompt while retaining the same authoritative KB content. This pays
  recurring context cost and creates competing, stale owners.

---

## Diagnose before designing the diff

Before proposing a change:

1. Trace the observed behavior through response reasoning, tool selection,
   retrieval, source content, and evaluator judgment as applicable.
2. Read the complete relevant settings, not only the line that appears closest
   to the symptom. Find conflicts, overlaps, missing priorities, and misplaced
   responsibilities.
3. State the behavioral mechanism at a level that explains the case without
   naming its incidental wording or entities. Check whether the same decision
   principle governs adjacent scenarios; retain category-specific detail only
   when the requirements genuinely differ.
4. Consider meaningful alternative causes and record the supporting and
   contradicting evidence. State uncertainty instead of inventing certainty.
5. Describe the intended target state and component ownership before writing
   the textual diff.

Do not require multiple real cases before acting. When one case leaves the
mechanism uncertain, use paraphrases, nearby boundaries, successful contrasts,
or tool/retrieval probes to distinguish the plausible causes.

---

## Prefer changes in this order

Choose the earliest adequate intervention:

1. Make no agent change when the response is acceptable or the evidence is an
   evaluator/case defect.
2. Remove a contradiction, obsolete instruction, or unnecessary constraint.
3. Consolidate, clarify, or reorder existing instructions and priorities.
4. Move information or behavior to the component that should own it after
   applying the hot-path residency criteria; prompt length alone is not a
   reason to move an operational dependency into retrieval.
5. Replace a narrow rule with one stable invariant at the broadest justified
   scope; do not overgeneralize across genuinely different requirements.
6. Add a new general instruction only when the requirement is genuinely absent.
7. Add a case-specific condition or exception only as a last resort.

System-prompt changes are appropriate when stable agent behavior is the true
owner. Append-only prompt patches are not the default. Prefer delete, merge,
move, reorder, or replace before adding instructions.

---

## Target-state gate

Before showing a settings diff, present:

- the accepted Query Distribution evidence used for frequency or hot-path
  decisions, including material confidence limits and open gaps;
- the accepted Behavior Contract and reviewed acceptance behavior this target
  state is meant to implement, including any material ambiguity still open;
- the observed failure and strongest supported mechanism;
- the current configuration defect and relevant evidence;
- the proposed target state and why responsibility belongs in each component;
- what information will be removed, merged, moved, replaced, or added;
- for every prompt/KB placement decision, why the content must stay resident
  instead of being retrieved on demand, or vice versa, using frequency,
  decision timing, miss impact, latency, recurring context cost, and
  duplication or staleness risk;
- why the whole configuration becomes simpler or more coherent;
- the simplest plausible configuration considered and why any remaining
  complexity is necessary;
- uncertainty, plausible counterarguments, and regression risks;
- reproduction, generalization or contrast, and regression checks.

Reject a proposal that only makes the observed case pass while adding avoidable
rules, duplicated ownership, contradictions, or cognitive load. If an urgent
patch is necessary despite increasing design debt, label it **containment**,
explain the debt, and do not present it as a root correction.
