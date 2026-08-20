---
name: codeer-presentations
description: Build, restyle, or review prospect-facing Codeer sales decks and Codeer investor pitch decks in PowerPoint/PPTX or compatible presentation source code. Use when Codex creates or edits Codeer slides, adapts an approved audience-value narrative into a story spine and slide map, confirms slide purposes or transitions, defines a presentation master or template, treats product screenshots, styles charts/tables/diagrams, audits Codeer voice and deck-level consistency, or runs rendered visual QA. For a new or materially changed product narrative, use the Codeer audience-value narrative skill first when available. Do not use for internal task-management, project-status, or handoff decks.
---

# Codeer Presentations

Build Codeer sales and investor presentations that feel like an expert opening a
carefully reviewed working file: calm, precise, candid, and supported by visible
reasoning, mechanism, or evidence appropriate to the claim.

Skill version: `0.6.0`.

Treat this version as an empirical starting point. Improve it from accepted and
rejected real slides, not from speculative component design.

## Stay inside the scope

Use this skill for visual direction, slide construction, template work, deck
restyling, and rendered review. Keep these concerns in scope:

- approved audience-value contract, deck objective, story spine, section roles, and
  slide-to-slide logic;
- each slide's causal role, primary claim, convincing support, consequence,
  knowledge dependency, and transition;
- Codeer's presentation voice and non-AI-ish copy;
- Codeer's presentation tone and personality;
- typography, color, spacing, and composition;
- master-slide and template foundations;
- image and product-screenshot treatment;
- chart, table, and diagram styling;
- deck-level visual rhythm and consistency;
- anti-pattern detection and rendered QA.

Do not silently invent or overwrite the storyline. For a new deck or major
revision, reconstruct the narrative contract, show it to the user, and obtain
explicit approval before building slides. For a visual-only restyle or minor
copy repair, audit the contract and report drift without stopping for approval
unless the requested change would alter meaning. Do not add internal
task-management, project-status, handoff, or delivery-process material.

Do not create a reusable explanatory component in advance. First build it for a
real slide, render it, and obtain user acceptance. Promote it into the system
only after it proves useful again.

## Load the visual contract

Load references progressively:

- Always read `references/visual-system.md` before visual work.
- Always read `references/copy-and-narrative.md` before writing, rewriting, or
  approving presentation content.
- Read `references/layout-contracts.md` before a build, restyle, repair, or
  template change.
- Read `references/qa-checklist.md` before a review, rendered inspection, or
  readiness claim.

For a new story or material content revision, also use
`$codeer-audience-value-narrative` when it is available. Treat its approved
contract as the upstream source for audience reality, desired change, central
claim, mechanism roles, proof implications, trust treatment, evidence
boundaries, and verification CTA. Do not create a competing deck-only value
thesis.

If the audience-value skill is unavailable, capture those fields explicitly
before continuing. Do not let the slide map begin from a feature inventory.

When available, use the workspace sources of truth for current product and
brand context:

- `codeer-landingpage/DESIGN.md` for the public visual system;
- `codeer-landingpage/BLOG_WRITING_PRINCIPLES.md` for editorial voice;
- `codeer-copilot/DESIGN.md` and `codeer-copilot/user-docs/docs/images/` for
  product behavior and authentic screenshots.

Prefer high-level product sources. Do not scan broad implementation directories
unless the slide requires source-level behavior.

## Choose the operating mode

- `new-deck`: create slides from user-approved content or an outline.
- `new-slide`: create one or a few slides inside the Codeer system.
- `narrative`: define or repair the audience, objective, storyline, slide
  roles, claims, dependencies, and transitions before slide production.
- `restyle`: preserve content and meaning while applying the Codeer system.
- `template`: create or revise the Codeer master and layout contracts.
- `review`: inspect source and rendered slides without silently editing them.
- `repair`: fix approved visual or geometric findings and rerender.

Infer the mode when obvious and state it briefly. Ask only for missing input
that materially changes the result.

## Pass the narrative gate

Treat the narrative gate as mandatory for every new deck and every major
content revision. Do not generate or substantially rewrite slides until the
user explicitly approves it.

Present one concise review artifact containing:

1. **Audience-value contract**: audience reality, cost or blocked result,
   desired change, one-sentence central claim, mechanism-to-problem mapping,
   proof and its implication, trust treatment, claim-testing CTA, evidence
   boundaries, and any justified technical or governance exception;
2. **Audience**: role, context, current knowledge, evaluation criteria, likely
   pushback, main concern, and decision;
3. **Deck objective**: what the audience should understand, believe, or do;
4. **Story spine**: the small set of ordered strategic claims that the whole
   deck must prove, not merely section names or a summary written after the
   slides;
5. **Persuasion plan**: for every story-spine claim, identify the target
   audience's main friction and the most suitable way to earn belief, such as a
   mechanism, business logic, concrete example, product demonstration, plan, or
   evidence;
6. **Slide map**: for every slide, identify the story-spine claim it advances,
   then list its causal role, inherited premise or tension, primary claim,
   audience-visible change, convincing support, proof implication, mechanism
   role, consequence, prior-knowledge dependency, new concepts, dependency on
   adjacent slides, logical bridge to the next claim, and any CTA claim tested;
7. **Open assumptions**: facts, prices, product status, or claims requiring
   confirmation.

Do not pass the narrative gate until the target-audience context is explicit.
Inspect available materials first. Ask about missing context when it could
materially change the story; otherwise state the assumption and uncertainty.

Treat narrative as a hierarchy: audience-value contract -> objective -> story
spine -> audience friction -> section claims -> slide chain -> convincing
support -> visual execution. Lock the upper level before optimizing the lower
one. Local causal continuity cannot rescue the wrong story: a slide may connect
tightly to its neighbors and still pull the deck away from the approved spine.
Remove, move, or demote such a slide even when its internal logic is sound.

For an existing deck, first reconstruct what it currently says. Distinguish
the current storyline from proposed changes and flag slides that do not advance
the audience's reasoning. Ask the user to approve the audience, objective,
story spine, and slide map together.

For a visual-only restyle or a minor copy correction, do not create an
unnecessary approval loop. Recheck the same fields, preserve the approved
meaning, and report any inconsistency before delivery.

## Work source-first

1. Inspect the supplied outline, deck, data, images, screenshots, and existing
   source before designing.
2. Build against the approved audience-value contract, narrative contract, and
   slide map. Keep each slide accountable first to one approved story-spine
   claim, then to one causal role, one primary claim, and one consequence in the
   deck's argument.
3. Preserve factual meaning, product fidelity, customer privacy, and source
   provenance.
4. Select registered layout contracts rather than injecting arbitrary
   coordinates.
5. Record each slide's `layout`, `surface`, `density`, `anchor`, `scale`, and
   `accent` in a rhythm ledger.
6. Keep charts, tables, diagrams, annotations, and text editable whenever the
   presentation runtime permits.
7. Treat the source files as canonical. Rebuild the `.pptx`; do not patch the
   binary output as the only record of a fix.
8. Render, inspect, fix the source, and render again before delivery.

Use an available presentation-generation skill or library for file operations,
but let this skill govern Codeer-specific taste and QA. Do not allow a generic
template, automatic design suggestion, or library default to override the
visual contract.

## Write like Codeer

Follow `references/copy-and-narrative.md`. Write direct, positive, operational
sentences that name the actor, action, artifact, condition, or decision. Make a
slide title sound like a useful sentence someone at Codeer would say in the
meeting, not a polished slogan generated for a pitch-deck template.

Explain the actor, action, artifact, condition, and decision before relying on
internal labels such as Prompt, Eval, test case, trace, memory, or version. Keep
the label when the declared audience needs the precision; do not replace it
mechanically from a fixed glossary.

Use contrast only when the distinction is necessary to the reasoning. Do not
default to patterns such as "not X, but Y," "not only X, but also Y," "from X
to Y," or their Chinese equivalents. Reject repeated rhetorical symmetry,
empty transformation language, abstract noun stacks, slogan fragments, and
generic future-facing claims.

Run a copy audit across titles, subtitles, body text, diagram labels, table
headings, chart annotations, and closing language. A phrase can be acceptable
in isolation and still fail when the deck repeats the same rhetorical grammar.

## Design around convincing support

Give every content slide one dominant argument, one visual anchor, and one
obvious reading path. Choose the support that best resolves the audience's main
friction: a visible mechanism, concrete situation, business logic, product
artifact, credible plan, contrast, or evidence. Do not force quantitative proof
onto every slide. Evidence is one way to build conviction, not the structure of
the story.

Never treat a screenshot or product action as self-explanatory. Name what the
audience can observe and what that fact changes about the work, risk, or
decision. Treat control, validation, review, and continuous improvement as
trust proof for a named risk unless governance or release control is the
audience's primary job.

Do not add a proof or traction slide merely because pitch-deck convention
suggests one. In an early-stage investor deck, prioritize the decisive investor
friction. De-emphasize or omit a small metric when it does not strengthen the
intended conclusion or would invite an irrelevant scale comparison. Never use
this rule to hide a material fact or leave a factual claim unsupported.

When using factual customer, market, product, or financial claims, preserve
source provenance and confidence limits. Prefer authentic Codeer artifacts such
as expert feedback, examples, standards, conversations, eval results, traces,
and verified changes when they materially strengthen the argument.

Use photography only when it adds human context. Never use generated imagery as
customer proof, a product screenshot, a measured outcome, or a real deployment.
Label conceptual product visuals so they cannot be mistaken for shipped UI.

Use brass only where human judgment visibly matters. Use evergreen for verified
progress. Use danger red only for actual failure or unresolved risk.

## Keep one visual system

Use the same typography roles, color semantics, grid, artifact treatment,
caption style, chart language, and annotation language in prospect sales and
investor decks. Change the evidence mix and density, not the brand identity.

Allow layout variation when the evidence shape changes. Reject both extremes:
the same header-and-three-cards slide repeated throughout, and a deck where
every slide looks imported from a different template.

## Require rendered QA

Never declare a deck ready from source inspection alone.

Run the checks in `references/qa-checklist.md`. At minimum:

1. recheck the approved story spine, section-to-spine mapping, and every
   slide-map row;
2. recheck the audience-visible change, one-sentence central claim,
   mechanism-to-problem mapping, proof implications, trust roles, evidence
   boundaries, and CTA-to-claim mapping;
3. run the Codeer voice and AI-ish copy audit;
4. run structural and placeholder checks;
5. render every slide at 1920x1080 or equivalent 16:9 output;
6. inspect every slide at full size;
7. inspect a contact sheet for rhythm and drift;
8. reread the complete deck from the declared target audience's perspective;
9. run the context-isolated cold read required for audience-facing artifacts;
10. fix the source and complete at least one rerender cycle;
11. report remaining warnings, assumptions, missing fonts, and unverified assets.

Do not claim readiness when fonts were substituted, screenshot text is
unreadable, evidence lacks a source, privacy is unverified, or a P0 QA item
fails.

## Run the target-audience pass

After every requested modification or completed revision cycle, review the
entire deck again from the declared target audience's perspective. Do not limit
this pass to the edited slides and do not rely on presenter knowledge that is
absent from the deck.

Report an estimated target-audience response covering:

- the audience's immediate interpretation of the company, problem, or proposal;
- attention and narrative momentum, including where interest rises or drops;
- comprehension, relevance, sequence, credibility, and visual friction;
- likely objections, competing explanations, comparisons, and evidence demands;
- trust formation, perceived risk, and unintended negative interpretations;
- genuine aha moments, missing aha moments, and what the audience will remember
  or repeat afterward;
- whether a cold reader retells the approved central claim rather than a feature
  inventory;
- decision readiness: what moves the audience toward action, which central
  claim the CTA lets it test, and what information still prevents the intended
  decision.

For each material finding, name the affected slide, estimated audience reaction,
severity, reason, and recommended response. Label the pass as an inference from
the declared audience context, not as observed user research.

Treat this as a readiness gate. Resolve material friction and pushback before
delivery or record them as explicit warnings. Preserve strong aha moments
through later edits; do not bury or dilute them with additional explanation.

## Evolve from real slides

When the user reports a problem, identify its layer before changing the skill:

- one-slide content fit -> repair that slide;
- repeated layout or style failure -> revise the visual or layout contract;
- renderer inconsistency -> add deterministic code after the pattern is proven;
- accepted recurring visual -> consider promoting it to a reusable component;
- false-positive QA rule -> narrow the rule and regression-test existing slides.

Preserve previously accepted slides as visual regression references. Do not
broaden the component library merely because a pattern is easy to generate.

## Report the result

For a build or repair, report:

- files created or changed;
- narrative-contract and slide-map confirmation status;
- audience-value contract, central-claim, and CTA verification status;
- context-isolated cold-read result and any remaining mismatch;
- Codeer voice and AI-ish copy-audit status;
- render and QA status;
- fonts, assets, or sources that remain provisional;
- deliberate deviations from the visual contract;
- what was intentionally left outside the scope.

For a review, lead with the highest-severity findings and cite the affected
slides. Do not silently redesign the deck.
