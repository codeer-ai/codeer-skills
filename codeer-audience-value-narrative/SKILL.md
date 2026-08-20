---
name: codeer-audience-value-narrative
description: Shape, review, or repair audience-first Codeer product narratives across sales decks, investor decks, demo scripts and videos, landing pages, and substantive proposals. Use when Codex must turn product features, internal concepts, screenshots, workflows, or click-by-click demonstrations into a persuasive account of what changes for a specific audience; define a memorable central claim; connect every mechanism to an established customer problem; translate Prompt, Eval, versioning, and similar product language into operational terms; select evidence without inventing outcomes; or make the next step directly test the claim. Do not use for internal status updates, purely technical reference documentation with no persuasion or decision objective, or visual-only production that preserves an approved narrative.
---

# Codeer Audience-Value Narrative

Build the reasoning path that Codeer audience-facing artifacts share before a
format-specific skill turns it into slides, video, a page, or a proposal.

Skill version: `0.1.0`.

Treat the method as a causal dependency graph, not a mandatory page order or
copy formula. Preserve truthful product detail and adapt the sequence to the
audience's decision.

## Choose the mode

- `shape`: establish a new narrative or materially change the intended claim,
  evidence, or action;
- `adapt`: translate an approved narrative into another format without silently
  changing its meaning;
- `repair`: fix feature-first, jargon-first, proof-free, or generic-CTA drift;
- `review`: diagnose the artifact and report findings without editing it.

For `shape`, show one concise audience-value contract and obtain approval before
substantial production when the central story or decision is not already
approved. For `adapt`, preserve the contract. For `repair`, escalate only when
the fix would change the approved meaning. For `review`, lead with the most
consequential audience mismatch.

## Load references progressively

- Read `references/examples.md` when translating internal terminology, repairing
  feature-first material, or drafting a demo.
- Read `references/regression-fixtures.md` only when changing this skill or
  validating whether a rule generalizes.

## Build the audience-value contract

Inspect supplied customer context, prior artifacts, product sources, evidence,
and meeting context before asking questions. State material assumptions.

Use these fields as the review artifact:

```yaml
audience:
  role: "Who must recognize this as their situation?"
  context: "Why are they evaluating this now?"
  current_belief: "What do they already believe about the problem or category?"
  objection: "What most plausibly makes them resist or say no?"
  decision: "What decision can they actually make?"
reality:
  actor: "Who experiences the current workflow?"
  recognizable_situation: "What repeatedly happens?"
  cost_or_blocked_result: "What useful work, decision, quality, or opportunity is constrained?"
  desired_change: "What should become different in the work or result?"
central_claim:
  retell: "One sentence the audience should remember and repeat"
mechanisms:
  - customer_question: "Which established problem makes this mechanism necessary?"
    operational_explanation: "Who does what, with which artifact, under what condition?"
    product_label: "Optional internal or product term introduced after the behavior"
    role: "value-mechanism | trust-proof | supporting-detail"
proof:
  - artifact: "Conversation, product state, result, plan, comparison, or evidence"
    visible_fact: "What can the audience actually observe?"
    implication: "What does that change about work, risk, or the decision?"
    limitation_or_condition: "What this proof does not establish"
    provenance: "Source, status, period, sample, or representative label"
trust:
  concern: "Which risk must be reduced?"
  proof: "Which control, review, validation, or release behavior reduces it?"
cta:
  action: "What should the audience do next?"
  claim_tested: "Which central claim will that action test?"
  observable_result: "What could the audience inspect or decide afterward?"
open_boundaries:
  - "Unsupported facts, assumptions, unknowns, and product-status limits"
```

Do not force every field into visible copy. The contract governs selection and
sequence; the final artifact should feel natural, not templated.

## Apply the dependency rules

### Establish relevance before product structure

Begin from an actor, recognizable situation, consequence, opportunity cost,
desired result, or pending decision. Do not make the audience learn a product
taxonomy before it knows why the subject matters.

Allow a framework-first or control-first opening when the declared audience
already accepts the stakes and is explicitly evaluating architecture,
governance, compliance, or coverage. Record that exception in the contract.

### Make every mechanism pay its debt

Introduce a feature or mechanism only after establishing the customer question
it answers. Complete this sentence:

> This mechanism matters now because the audience has already seen that...

If the sentence is empty, delay the mechanism, move it to supporting detail, or
remove it. Do not let completeness of the product inventory determine the
audience-facing sequence.

### Translate internal terms through work

Explain the observable workflow before relying on labels such as `Prompt`,
`Eval`, `test case`, `version`, `memory`, `trace`, or `knowledge base`. Record a
term only when it improves precision after the actor, action, artifact,
condition, and decision are understandable.

Do not maintain a static substitution glossary. The right operational language
depends on the audience. A technical buyer may need the label; an operator may
need only the behavior and decision.

### Use trust mechanisms as proof by default

Treat control, validation, review, traceability, and continuous improvement as
evidence that reduces an established risk. Do not promote them into abstract
primary value merely because they describe Codeer's architecture.

Promote one to primary value only when the audience's actual job is governance,
compliance, release control, or another risk-management decision. State the
reason for the exception.

### Put concrete proof before compression

Prefer a real or clearly labeled representative conversation, decision,
failure, correction, product state, or result before a framework that names the
pattern. Use the framework to compress or generalize meaning already made
concrete.

Never treat a screenshot, click, animation, or interface state as self-
explanatory. State both the visible fact and its implication for the work or
decision.

### Make the CTA verify the claim

Choose the smallest proportionate next step that lets the audience examine the
most consequential claim with its own scenario, data, constraints, or decision
criteria. `Contact us`, `book a demo`, and `learn more` are incomplete unless
the artifact specifies what the next interaction will test or make decidable.

## Adapt to the format

### Decks

Pass the approved contract to the relevant presentation skill. Extend it with a
story spine and per-slide causal map. Confirm that the title-only sequence
reconstructs the intended argument and the closing action tests the central
claim.

### Demo scripts and videos

Map every beat as:

```text
audience question -> concrete scene -> action -> visible evidence
-> operational implication -> trust condition or next tension
```

An interface action without an audience question and implication is not a
complete demo beat. Narrate what changes in the work or decision, not every
cursor movement. Show authentic product behavior and label representative data,
conceptual UI, and unshipped behavior.

### Landing pages and proposals

Make each section advance the same contract rather than creating a new slogan
for every block. Use capabilities after relevance is established. Let proof
resolve the strongest objection, and make the CTA test the claim appropriate to
the buyer's readiness.

## Run the acceptance tests

Block or revise the artifact when any of these tests fails:

1. **Audience-change test**: Can the audience identify its current situation and
   the desired change without first decoding the product architecture?
2. **Concrete-before-compression test**: Before the first framework or product
   structure, has the artifact shown or specifically planned a real or clearly
   labeled representative conversation, decision, failure, correction, product
   state, or result, unless an approved technical exception applies?
3. **Mechanism-debt test**: Does every visible mechanism answer an already
   established customer question?
4. **Operational-translation test**: After removing internal labels, can the
   audience explain who does what, what it sees, and what it decides?
5. **Proof-unit test**: Does every example or demo show a visible fact, its
   implication, and its boundary?
6. **Trust-role test**: Is control or validation serving a named risk, or is a
   valid governance exception recorded?
7. **Retell test**: Can a cold reader state what changes for whom and why the
   claim is credible in one sentence?
8. **Verification-CTA test**: Does the next step test the central claim and name
   an observable result?
9. **Evidence-boundary test**: Are claims no stronger than their provenance,
   sample, status, and method permit?

Treat missing audience, invented proof, or unsupported outcome claims as hard
failures. Treat feature-first ordering, untranslated terms, proof without an
implication, abstraction before concrete meaning, abstract trust language, and
a generic CTA as material failures unless the contract records a justified
exception.

## Protect evidence integrity

Do not invent conversion rates, time savings, ROI, customer outcomes,
testimonials, or causal effects. When a quantitative claim matters, preserve the
source, period, unit, denominator, sample, baseline, and actual/forecast status
that are necessary to interpret it. Otherwise use a bounded qualitative claim.

Distinguish observed facts, representative examples, proposals, inferences, and
unknowns. Never imply that a UI event proves a business result without evidence
connecting them.

## Complete the audience pass

After the first complete draft, run the context-isolated cold read required for
audience-facing artifacts. Provide the reader only the audience identity and
artifact. Compare its answer to `central_claim.retell` and compare its objection
to the contract's predicted objection. Revise once when the mismatch is
structural; do not tune indefinitely to one reader's wording.

Report the approved contract, material exceptions, evidence boundaries,
cold-read result, and any remaining mismatch. For a review, distinguish visible
artifact facts from inferred audience response.
