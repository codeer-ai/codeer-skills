# Shared Behavior Contract

Use in build, audit and improve. `design/behavior-contract.md` holds accepted customer-specific decisions. Proposed changes go in `design/behavior-contract.draft.md`; implementation belongs in Agent settings/Instructions and KB, and per-case criteria in Eval design. See [project.md](project.md) for confirmation and log evidence.

## Draft the Behavior Contract

Use this compact first-version structure by default. Omit a field that has no
material downstream use, and adapt the presentation only when another format
makes the same decisions easier to review:

1. **Core scenario** — observable user intention or task, starting state,
   material constraint, supported Agent role, and explicit first-version
   exclusions.
2. **Core outcome** — the user-visible result, acceptable alternative or
   non-conversion outcomes, immediate observable evidence, material attribution
   limits, and guardrails.
3. **Behavior path** — only the decision points that can change the next move.
   For each, make the observable signal, expected move, required information or
   evidence, and stop or handoff condition reviewable. Cover answer, ask,
   retrieve, compare, recommend, Tool, consent, or handoff only when material.
4. **Material boundaries** — domain-specific facts the Agent must not invent,
   unsupported actions, sensitive-data or consent limits, and rare but high-
   consequence conditions that change verification, uncertainty disclosure,
   action, or handoff. State stable policies, not an edge-case catalog.
5. **Acceptance behavior** — the smallest observable success and prohibited
   behavior needed to turn the core scenario into acceptance Evals without
   prescribing exact wording.

The first version should not contain a backlog of speculative scenarios. Add
one scenario at a time after evidence shows that correct handling materially
differs. When the contract expands, keep shared decision policies once at the
highest stable scope and add only the scenario-specific override; do not copy
the full behavior path into every scenario.

### Compression example

**Over-expanded:** Require the reviewer to approve separate rules saying that
the Agent greets politely, uses clear language, avoids repeating known
information, asks one question at a time, explains every option, offers further
help, does not pressure a refusal, and apologizes when information is missing.

**Decision-oriented:** "For product-selection journeys, answer supported factual
questions before starting discovery. Ask only for a missing constraint that can
change fit, then offer a small evidence-grounded shortlist with the relevant
tradeoffs. Move to a form or payment only after an explicit readiness signal. If
a high-consequence eligibility fact cannot be verified, disclose the uncertainty
and hand off rather than infer it."

The compressed version records the material initiative, evidence, progression,
and risk decisions. Ordinary conversational quality remains expected under the
acceptance-criteria basis below, while concrete product, wording, and boundary
variants belong in the KB and evals.
Use this as an illustration of decision granularity, not as required contract
language.

### Evidence and autonomy boundaries

The Agent builder may choose whether and how to use verified scarcity,
urgency, authority, social proof, prices, eligibility, and tool outcomes. These
are selectable customer-guidance strategies, not prohibited topics. The fixed
boundary is that the Agent must not fabricate, exaggerate, or present
unsupported claims or outcomes as fact. Apply these non-negotiable evidence
and autonomy boundaries regardless of the selected dialogue or sales method:

- ground factual claims in available evidence and disclose material
  uncertainty;
- never fabricate or exaggerate scarcity, urgency, authority, social proof,
  prices, eligibility, tool outcomes, or customer intent, and never present an
  unsupported claim as verified;
- distinguish product facts, the agent's recommendation, and the customer's
  decision;
- preserve customer autonomy and make declining or reconsidering easy;
- explain the purpose and obtain appropriate consent before collecting
  sensitive or persistent structured data or initiating a consequential tool
  action; ordinary conversational clarification need not become a permission
  ritual, and every action should collect only what it needs; and
- identify the agent honestly and use human handoff when human accountability
  or judgment is required.

---

## Basis for acceptance criteria

The user or authorized project owner decides project-specific experience
requirements through the accepted Behavior Contract and explicit instructions.
The builder and reviewer derive case-level criteria from those requirements,
the canonical evidence and autonomy boundaries above, the actual user request,
authoritative case facts, and applicable Tool schemas or operational contracts.
The evaluator applies the resulting rubric to its visible evidence; it does
not invent another standard of "basic quality."

Clarity, relevance, and completeness justify a mandatory criterion only when
its absence would materially obscure the answer, change the correct next move,
or hide an important risk. State that consequence and its basis. For example,
an ambiguous fee or missing condition may change a customer's decision;
repeating already-understood context or adding a preferred greeting usually
does not. Style, answer length, fixed acknowledgement wording, and a preferred
question sequence are not universal pass requirements.

A criterion need not quote a Contract sentence if it is a necessary implication
of an accepted requirement or one of these inherited constraints. Conversely,
calling a preference "basic quality" does not authorize it. When it introduces
a new material product decision or tradeoff, return that decision to the user;
otherwise make unnecessary detail optional. Keep this basis in case reasoning
and rubric review rather than expanding the Contract into a quality checklist.
Use [eval-cases.md](../modules/eval-cases.md#semantic-acceptance-and-material-omissions)
for judging equivalent wording and omissions.


## Confirmation and progressive revision

Persist important pending proposals before a handoff, with the decision, recommendation, evidence, behavior impact and unresolved question. Present the complete proposal or diff; carry forward existing authorization for the same scope. Record the confirmation source and reviewed content/revision under `reviews/`, then update the accepted contract. Append a short reason, status and evidence link to `log.md`. A filename or imported remote behavior is not acceptance.

Keep the original accepted rule until the replacement is confirmed. After confirmation update the current rule, retaining the prior decision in review/log evidence. Missing historical Contract does not prevent read-only diagnosis or an already confirmed implementation repair. Ask only when the intended business behavior is materially unclear.
