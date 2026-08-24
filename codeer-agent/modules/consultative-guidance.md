# Consultative Customer Guidance

Use this module to design or intentionally revise the Behavior Contract for a
query-led, one-to-one customer guidance agent before designing its runtime
settings. It applies to product, service, or course consultation; support that
may lead to a booking, form, payment, or handoff; and similar inbound journeys
where the agent answers, clarifies, recommends, narrows, and helps the customer
take a next step.

Do not expand this module into outbound sales calls, presentations, a staged
objection-handling or closing script, price negotiation, or enterprise
multi-stakeholder selling. Those require a different design scope.

The Behavior Contract is a persistent design input, not a Codeer runtime
component. Store the accepted contract at
`.codeer/design/behavior_contract.md` so later Eval Debug and History Analysis
can distinguish implementation divergence from an intentional experience
change. After the user accepts it, use [eval-cases.md](eval-cases.md) to turn it
into observable acceptance cases before creating or changing Agent Settings,
KB, or Tools.

---

## Start from available evidence

Read the completed Scope Alignment from [kb-and-agent.md](kb-and-agent.md) and
the accepted `.codeer/design/query_distribution.csv` from
[query-distribution.md](query-distribution.md), together with
`.codeer/design/query_examples.csv`. Then inspect whatever product documents,
KB content, current settings, tools, evals, and production-history findings are
available. Use the concrete examples to test whether a proposed policy produces
the intended experience. Do not ask the user to repeat decisions already
supported by that evidence.

Ask only unresolved questions whose answers would materially change the
contract. Typical decision gaps are:

- the customer decisions and successful next steps for each in-scope scenario;
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

## Draft the Behavior Contract

Use the clearest format for the agent. Do not force a schema, script, or fixed
number of questions.

### Minimum-sufficient contract rule

Include only decisions that change the Agent's response, next move, evidence
requirement, authority boundary, or success condition. Omit non-material
sections instead of filling placeholders. Consolidate query types under one
general policy when they should be handled the same way.

Do not repeat the Query Distribution, query examples, source inventory, Agent
Settings, or eval-case list inside the contract. Refer to a query type or add a
short illustrative branch only when it makes an otherwise ambiguous policy
reviewable. If a proposed section has no clear downstream use, omit it.

Make the following decisions explicit only when they are material:

1. **Journey outcomes** — the customer decision or next step for each in-scope
   scenario, including acceptable non-conversion outcomes.
2. **Information policy** — what the agent may infer, retrieve, or ask; what is
   required before recommending or acting; and what information is unnecessary
   or too sensitive to collect.
3. **Initiative policy** — when to answer, ask, retrieve, compare, recommend,
   use a tool, or hand off, including the main boundaries between those moves.
4. **Discovery strategy** — the chosen method or composition and the signals
   that should deepen, shorten, or switch it. SPIN may be used lightly as a
   question-design tool, but never as a mandatory interrogation sequence.
5. **Recommendation and refinement** — how many options to surface, how to
   explain fit and tradeoffs, how to use feedback or critique to narrow, and
   how to respond when evidence is insufficient.
6. **Progression and consent** — what readiness signal permits a booking,
   form, payment, or other consequential action; what must be confirmed first;
   and how the user can decline or step back.
7. **Handoff and limits** — human-transfer triggers, unsupported requests, and
   the helpful context to provide without pretending the transfer succeeded.
8. **Risk and boundary policies** — rare or high-consequence conditions that
   require a stable, observable change in verification, uncertainty disclosure,
   consent, recommendation, action, or handoff. State the general policy rather
   than cataloging concrete edge cases.
9. **Success and failure behavior** — observable outcomes the acceptance evals
   must cover, including nearby boundaries and important non-conversion cases.

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

## Acceptance gate and handoff

Draft new or revised content in conversation or at
`.codeer/current/local_draft_behavior_contract.md`. Present the complete
contract or before/after diff and confirm with the user that it captures the
intended experience, chosen discovery strategy, and material risk policies.
Do not replace the canonical file before the user accepts the design change.

Before requesting acceptance, check the proposed contract against the
Evidence and autonomy boundaries. The contract may choose how to use verified
scarcity, urgency, authority, social proof, prices, eligibility, or tool
results, but it cannot authorize fabrication, exaggeration, or unsupported
claims. User acceptance does not override this boundary.

The accepted file should record material unresolved assumptions. Add status,
contract version, dates, or applicable Agent/version metadata only when the
current project workflow will use them; otherwise rely on file and revision
history. The contract is ready when a reviewer can tell, for the important
branches, which next move is appropriate, what evidence or user input is
needed, what the Agent must not do, and what a successful outcome looks like.

After acceptance, persist `.codeer/design/behavior_contract.md`. Then use
[eval-cases.md](eval-cases.md) to design the acceptance cases and rubrics
locally. Those cases are the first executable expression of the contract, but
they must test its behavior rather than prescribe exact wording. Only after the
cases are reviewed should [agent-settings.md](agent-settings.md) and
[kb-and-agent.md](kb-and-agent.md) translate the accepted contract into Agent
Settings, KB, Tools, and handoff configuration.

For an existing agent, revise the contract only when production-history or
eval evidence indicates that the accepted customer experience itself should
change or is materially ambiguous. Show the current and proposed behavior,
obtain user acceptance, update the canonical contract, update acceptance evals
first, and only then plan the runtime repair. Do not use this module when an
unchanged contract already makes the correct behavior clear and the defect
belongs to implementation or eval.
