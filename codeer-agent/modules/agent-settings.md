# Agent Settings Design

Use this module whenever creating or changing an agent's system prompt, tools,
KB configuration, retrieval routes, model, or handoff settings.

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
| System prompt | Stable objectives, behavioral invariants, priorities, boundaries, cross-component decisions | Volatile facts, copied eval wording, duplicated tool documentation, a list of narrow exceptions |
| Tool configuration and invocation instructions | What the tool does, when to call it, inputs, limits, and tool-specific query strategy | General response policy or domain content |
| Knowledge base | Maintainable domain facts and source-of-truth content | Agent orchestration or hidden evaluator criteria |
| File structure, retrieval routes, and Context Object FAQs | Reliable routing to existing canonical content | A substitute for missing content or a tool the agent never calls |
| Model selection | Capability, latency, and cost tradeoffs | A way to conceal contradictory or overloaded settings |
| Human handoff settings | Transfer availability and operational triggers | Duplicated conversation policy spread across components |
| Evaluators and rubrics | Observable success and failure criteria | A hidden extension of the agent prompt |
| Eval cases | Reproduction, generalization, boundary, and regression probes | Training examples to copy into settings |

When a behavior spans components, keep the governing principle in one place
and put only component-specific execution details elsewhere.

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
4. Move information or behavior to the component that should own it.
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

- the observed failure and strongest supported mechanism;
- the current configuration defect and relevant evidence;
- the proposed target state and why responsibility belongs in each component;
- what information will be removed, merged, moved, replaced, or added;
- why the whole configuration becomes simpler or more coherent;
- the simplest plausible configuration considered and why any remaining
  complexity is necessary;
- uncertainty, plausible counterarguments, and regression risks;
- reproduction, generalization or contrast, and regression checks.

Reject a proposal that only makes the observed case pass while adding avoidable
rules, duplicated ownership, contradictions, or cognitive load. If an urgent
patch is necessary despite increasing design debt, label it **containment**,
explain the debt, and do not present it as a root correction.
