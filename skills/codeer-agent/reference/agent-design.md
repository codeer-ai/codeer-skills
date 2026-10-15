# Shared Agent design

Use when building or resolving intended behavior in any Agent workflow. The
Agent design is the builder-maintained design basis distilled from user
goals, explicit instructions, applicable authoritative sources and confirmed
tradeoffs. Its authority comes from those inputs, not from its filename or a
ceremony approving the whole document. It is not a runtime component or prompt.

The builder writes and maintains it. Users provide material, explain what they
want and decide material tradeoffs; they need not know this term, fill a template
or manage files. Present concrete understanding, recommendations and open
decisions in ordinary language. For new projects, keep `design/agent-design.md`
for established decisions and `design/agent-design.draft.md` for pending proposals.
First apply the [project path resolution rules](project.md#agent-design-paths-and-existing-projects):
reuse configured or legacy files and their sibling draft; do not create a second
authority under the new name. Implementation belongs in settings
and KB; per-case criteria belong in Eval design. See [project.md](project.md).

## Discover and ground the design

Use the [collaboration and gap guidance](collaboration.md): distinguish missing
questions, missing policy and missing runtime evidence, state unaffected work
and recommend the next action. A generic “need more data” is not sufficient.

Start from the request, available source material and existing decisions. For a
bounded repair, recover only the basis relevant to that repair; do not restart
discovery or require a complete document. For a new Agent, develop a useful
understanding of:

- whom it serves, the tasks and outcomes it should support, and priorities when
  outcomes compete;
- its role, available capabilities and permitted actions;
- limits, exceptions, failure handling and conditions for stopping or handoff;
- observable success and prohibited behavior.

These are reasoning dimensions, not a questionnaire. Read before asking. Explain
what is already established, recommend how to address important gaps, and ask
only questions that could change the design. When the user is unsure, use a
concrete situation and its tradeoff to help them decide. Use
[consultative guidance](../modules/consultative-guidance.md) only for query-led
customer guidance; classification, internal assistance and other tasks do not
inherit sales or conversion methods.

Distinguish evidence from authority:

- Clear, applicable user instructions and confirmed choices can be recorded
  directly. A source explicitly designated as governing the task can supply
  applicable rules without asking the user to approve each paraphrase.
- A supplied document may instead contain facts, examples, historical policy or
  suggestions. Record its role and relevant version in `sources/index.md`; do
  not treat everything in it as current policy merely because it was supplied.
- Current settings, conversations and scores show observed behavior, not what
  the Agent is authorized or expected to do. Builder inferences remain proposals.
- For a material source conflict or unclear intent, show the conflict, recommend
  a resolution and wait for the needed decision. Do not guess precedence. An
  explicit replacement instruction can supersede an earlier rule directly, with
  its basis and history retained.

Persist important established understanding and unresolved proposals during
discovery, not only after the entire design is settled. Preserve a concise source
or confirmation reference for material decisions; no fixed decision schema or
IDs are required. Missing capabilities or evidence are gaps to report with
possible alternatives, not reasons to silently weaken the goal or its tests.

## Draft the Agent design

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

When scope is open, recommend one valuable end-to-end scenario as a starting
point. Preserve all tasks the user has already put in scope; reducing that scope
is a decision to raise, not a default. Do not add a backlog of speculative
scenarios. Add further scenarios when requested or when evidence shows that
correct handling materially differs. When the design expands, keep shared decision policies once at the
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
Use this as an illustration of decision granularity, not as required design
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

The user or authorized project owner determines project-specific experience
requirements through explicit instructions, applicable designated sources and
confirmed choices, consolidated in the Agent design by the builder.
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

A criterion need not quote an Agent design sentence if it is a necessary implication
of an accepted requirement or one of these inherited constraints. Conversely,
calling a preference "basic quality" does not authorize it. When it introduces
a new material product decision or tradeoff, return that decision to the user;
otherwise make unnecessary detail optional. Keep this basis in case reasoning
and rubric review rather than expanding the Agent design into a quality checklist.
Use [eval-cases.md](../modules/eval-cases.md#semantic-acceptance-and-material-omissions)
for judging equivalent wording and omissions.


## Confirmation and progressive revision

Acceptance here means the underlying decision is established, including by an
explicit instruction; it does not require another approval merely to summarize
or save it. For a new material choice, show the complete relevant proposal or
behavior diff, its basis and consequences, then ask for that decision. Preserve
the actual instruction/confirmation source and reviewed content under `reviews/`
and a concise reference in the design; do not manufacture an approval record.

Save pending proposals with the recommendation, evidence, behavior impact and
unresolved question. Keep the existing rule until an explicit replacement or
confirmation resolves the change; then update the current rule and preserve the
prior decision in review/log evidence. Important milestones go in `logs/YYYY-MM.md`
(continue an existing `log.md`) with
their state and evidence link. Unresolved decisions stay in the draft; the
established design may reference their gaps without making assumptions binding.

Missing historical Agent design does not prevent read-only diagnosis or an already
confirmed implementation repair. Clarify only materially unclear business
behavior and continue independent work. Established intent is distinct from
authorization to write remotely: preserve the reviewed operation/batch scope,
preview/readback requirements and separate publication authorization in
[project.md](project.md#scope-import-and-apply).
