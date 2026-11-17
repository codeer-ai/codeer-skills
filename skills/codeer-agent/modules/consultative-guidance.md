# Consultative Customer Guidance

Use this module to design or intentionally revise the Agent design for a
query-led, one-to-one customer guidance agent before designing its runtime
settings. It applies to product, service, or course consultation; support that
may lead to a booking, form, payment, or handoff; and similar inbound journeys
where the agent answers, clarifies, recommends, narrows, and helps the customer
take a next step.

Do not expand this module into outbound sales calls, presentations, a staged
objection-handling or closing script, price negotiation, or enterprise
multi-stakeholder selling. Those require a different design scope.

Use the shared [design discovery and source rules](../reference/agent-design.md#discover-and-ground-the-design)
for authority, persistence and user interaction. This module adds methods for
query-led customer guidance, not another approval process. Record established
decisions and pending proposals as you work. Once the relevant behavior is
established, use [eval-cases.md](eval-cases.md) to design observable acceptance
cases before creating or changing Agent Settings, KB or Tools.

---

## Start from available evidence

Read available Scope Alignment decisions from [kb-and-agent.md](kb-and-agent.md), then
inspect whatever product documents, KB content, current settings, Tools, evals,
and production-history findings are available. When accepted
`design/query_distribution.csv` or
`design/query_examples.csv` artifacts exist and are relevant, read them
through [query-distribution.md](query-distribution.md); do not require or create
them merely to begin the first Agent design. Use concrete source examples
to test whether a proposed policy produces the intended experience. Do not ask
the user to repeat decisions already supported by that evidence.

Ask only unresolved questions whose answers would materially change the
design. Typical decision gaps are:

- the requested scenarios and core customer or task outcomes for the first
  version, including acceptable alternative or non-conversion outcomes,
  observable success evidence, and material guardrails;
- what can already be inferred or retrieved, what must be learned before a
  recommendation or action, and what the agent should not ask for;
- the cost and reversibility of a wrong recommendation or premature action;
- when the user expects a direct answer versus guided discovery;
- which facts, comparisons, media, forms, payments, bookings, or handoffs the
  available KB and Tools can actually support; and
- which discovery approach the customer prefers when more than one approach is
  suitable.

Recommend a suitable approach and explain the decisive tradeoff. The user may
choose another compatible method; do not present one sales framework as the
only valid option.

---

## Start with one core scenario and outcome

When the first-version scope is open, recommend one **core scenario**: the smallest valuable
end-to-end situation that expresses why the Agent exists. Define it with the
observable user intention or task, starting state, material constraint, and
supported Agent role. Select the central value path, not merely the easiest FAQ
or the query most likely to pass an Eval. Preserve explicitly requested tasks;
do not silently reduce an already defined scope to one scenario.

Pair it with one **core outcome**: the user-visible result the Agent should help
produce in that scenario. An Agent action such as asking three questions or
calling a Tool is not an outcome. Capture only what later behavior, Eval, or
governance decisions will use:

- the core customer or task outcome;
- acceptable alternative, refusal, handoff, or non-conversion outcomes;
- observable immediate evidence that the intended experience occurred;
- a delayed or cross-conversation outcome only when it is material and there is
  a plausible way to observe it;
- safety, authority, quality, autonomy, cost, or other guardrails that must not
  be sacrificed for the primary outcome; and
- material attribution limits when the business or longitudinal result is not
  fully under the Agent's control.

Keep the core scenario and outcome at the opening of
`design/agent-design.md`; do not create separate scenario or
outcome documents. Reconcile Scope Alignment business and conversion
goals with any descriptive demand evidence using the shared source rules.
The builder records established project-specific outcomes and guardrails in
the Agent design, which inherits the evidence and autonomy boundaries below.
A booking, purchase, containment, or retention
proxy does not become an Agent objective merely because it appeared during
Scope Alignment or a demand analysis.

Use outcomes as the reason for the later information, initiative, discovery,
recommendation, Tool, consent, risk, and handoff policies. Do not optimize a
business proxy such as conversion, containment, satisfaction, or retention in
isolation from the customer outcome and guardrails. Analysis-specific outcomes,
time windows, and statistical definitions belong in the current analysis scope
unless the user accepts them as a stable intended customer experience.

Treat observable user entry conditions as policy-selection context. Add a
second scenario only when a distinct intention, journey or work-object state,
constraint, readiness, urgency, risk, or authority changes the core outcome,
correct answer, next move, required evidence, Tool, handoff, consent, or risk
policy. Do not infer a Persona, personality, sophistication, or motivation from
wording when the available evidence does not establish it. If a distinction
changes only a concrete example, presentation variation, sampling need, or
outcome comparison, keep it in Eval or analysis rather than expanding the
design.

Apply an outcome-relevance gate to proposed design content. Keep it only when
it helps the Agent select an appropriate decision, advances or protects an
accepted outcome, resolves a fair-comparison or governance need, or has a named
downstream Eval or implementation use. Otherwise omit it.

---

## Choose the least burdensome useful next move

Design a policy for choosing among response and action types. Use information
sufficiency, consequence of error, user effort, reversibility, urgency, and
action readiness together:

- **Answer directly** when the query is answerable and a question would only
  delay useful help. Offer refinement after the answer when appropriate.
- **Ask** when a missing answer could materially change the recommendation,
  eligibility, safety, or next step. Prefer one high-information question at a
  time unless a structured form is clearly more efficient.
- **Retrieve** when the response or recommendation depends on authoritative
  facts that are not already established in the conversation.
- **Show or generate a visual** only when visual comparison materially improves
  the decision and an approved retrievable image URL or configured tool can
  support it. The frontend may render image URLs; absence of images in the
  current KB is a content gap, not evidence that the Agent lacks visual
  presentation capability.
- **Recommend** once the agent has enough information to narrow responsibly.
  Explain the match in customer-relevant terms, distinguish facts from
  judgment, and preserve meaningful alternatives.
- **Request a form, booking, or payment** only after the customer has indicated
  readiness and the required inputs and consequences are clear. Do not use an
  action tool merely to simulate progress.
- **Hand off** when the user requests a person, the decision exceeds the
  agent's authority or evidence, or a defined risk boundary requires human
  judgment.

Mixed-Initiative Dialogue is the control structure for these choices. Adaptive
Selling is a quality principle: adapt initiative, discovery depth, comparison
breadth, and explanation to observable needs without manipulating the user or
inventing personality claims. Read
[../reference/consultative-guidance-methods.md](../reference/consultative-guidance-methods.md)
when selecting discovery and recommendation methods.

---

## Control the level of detail

For the first design, cover only the core scenario's end-to-end path,
material branch decisions, and any high-consequence boundary that cannot safely
be deferred. Coverage does not require a scenario inventory or a separate rule
for every query, method, risk example, or eval case. One stable principle may
govern many concrete cases. Simplicity narrows the initial journey; it does not
relax evidence integrity, consent, authority, or handoff boundaries.

Add a statement to the customer-reviewed design only when all of these are
true:

- it resolves a customer-experience or business decision that is not already
  clear from a higher-level design principle or a canonical skill boundary;
- it changes observable behavior—such as the next move, required evidence,
  recommendation, consent, action, uncertainty disclosure, or handoff—for a
  material journey or risk;
- it is stable enough to apply beyond one wording, product, or incident; and
- an acceptance case could test its outcome or boundary without prescribing
  exact response wording.

If a proposed statement has no clear downstream use, omit it.

Do not add content merely because it is useful somewhere in the Agent system.
Keep these in their owning layer instead:

- generic service norms and common conversational competence;
- the canonical Evidence and autonomy boundaries below, unless a
  domain-specific choice changes observable behavior or governance requires an
  explicit acknowledgement;
- optional Query Distribution evidence, query examples, and source inventory
  in their own design or source artifacts instead of repeating them;
- product facts and complete procedures in the KB;
- prompt, retrieval, tool-schema, and orchestration details in Agent Settings
  or Tool configuration; and
- concrete examples, paraphrases, rare variants, and nearby boundaries in the
  eval portfolio when they instantiate an already-clear principle.

Refer to a query type or add a short illustrative branch only when it makes an
otherwise ambiguous policy reviewable.

Increase detail progressively. Add the smallest general rule only when
implementation, eval, or production-history evidence shows that the existing
design permits materially different interpretations, omits a real experience
decision, or should intentionally change. State the triggering evidence or
ambiguity in the revision context and generalize only to the broadest scope it
supports. If the design already determines the desired behavior, repair the
implementation or eval instead. One incident normally warrants a reproduction
or boundary probe, not a case-specific design clause.

---

## Draft the Agent design

Use the shared [Agent design](../reference/agent-design.md) for compact decision structure, progressive detail and compression examples. This module supplies the query-led discovery methods above.

### Evidence and autonomy boundaries

Apply the shared [evidence and autonomy boundaries](../reference/agent-design.md#evidence-and-autonomy-boundaries).

## Basis for acceptance criteria

Use the shared [acceptance-criteria basis](../reference/agent-design.md#basis-for-acceptance-criteria); consult [eval-cases.md](eval-cases.md#semantic-acceptance-and-material-omissions) for equivalent wording and omissions.

## Acceptance gate and handoff

Apply the shared [confirmation and revision rules](../reference/agent-design.md#confirmation-and-progressive-revision).
Persist important proposals in `design/agent-design.draft.md`, including
during incomplete discovery. Show the relevant behavior or before/after diff;
ask about unresolved experience, discovery-strategy or risk choices, without
asking the user to reapprove clear instructions or their transcription.
Readiness means the requested scope has sufficient end-to-end decisions and
material boundaries to design its acceptance cases. It does not require a
complete scenario inventory or restatement of every applicable norm.

Before requesting acceptance, check the proposed design against the
Evidence and autonomy boundaries. The design may choose how to use verified
scarcity, urgency, authority, social proof, prices, eligibility, or tool
results, but it cannot authorize fabrication, exaggeration, or unsupported
claims. User acceptance does not override this boundary, and the design does
not need to repeat the canonical list for the boundary to apply.

The accepted file records established decisions and explicit exclusions; link
material gaps to pending proposals without making assumptions binding.
Add status, design version, dates, or applicable
Agent/version metadata only when the current project workflow will use them;
otherwise rely on file and revision history. The design is ready when a
reviewer can tell, for the accepted core scenario, what outcome and guardrails
govern the journey, which next move is appropriate for each material observable
condition, what evidence or user input is needed, and what the Agent must not
do.

As decisions become established, persist `design/agent-design.md`. Then use
[eval-cases.md](eval-cases.md) to design the acceptance cases and rubrics
locally. Those cases are the first executable expression of the design, but
they must test its behavior rather than prescribe exact wording. Only after the
cases are reviewed should [agent-settings.md](agent-settings.md) and
[kb-and-agent.md](kb-and-agent.md) translate the accepted design into Agent
Settings, KB, Tools, and handoff configuration.

For an existing agent, revise the design only when production-history or
eval evidence indicates that the accepted customer experience itself should
change or is materially ambiguous. Show the current and proposed behavior,
resolve new choices through the shared confirmation rules, update the canonical
design, update acceptance evals
first, and only then plan the runtime repair. Do not use this module when an
unchanged design already makes the correct behavior clear and the defect
belongs to implementation or eval.
