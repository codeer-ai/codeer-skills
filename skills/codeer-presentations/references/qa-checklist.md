# Codeer Presentation QA Checklist

Use this checklist for every slide build, restyle, repair, and template change.
Do not declare readiness from source inspection alone.

## Contents

1. Required QA loop
2. Narrative and copy gate
3. P0 hard failures
4. P1 visual and evidence failures
5. P2 refinement warnings
6. Full-size rendered inspection
7. Contact-sheet inspection
8. Target-audience pass
9. Specialized checks
10. Delivery report

## 1. Required QA loop

Run this sequence:

1. confirm the audience-value contract, target-audience context, narrative
   contract, and slide map are approved when required;
2. verify that the title-only sequence and every section still reconstruct the
   approved story spine;
3. verify that each story-spine claim addresses a material audience friction
   through an appropriate convincing method; do not require quantitative
   evidence when a mechanism, business logic, demonstration, or plan is more
   persuasive;
4. audit every slide's story-spine contribution, causal role, inherited premise
   or tension, primary claim, audience-visible change, convincing support,
   proof implication, mechanism role, prior-knowledge dependency, new concepts,
   consequence, dependency, transition, and any CTA claim tested;
5. run the concept-ledger and cold-reader tests; block orphan concepts and
   conclusions that depend on missing or future explanations;
6. run the concrete-before-compression, mechanism-debt,
   operational-translation, proof-unit, trust-role, retell, verification-CTA,
   and evidence-boundary tests from
   `$codeer-audience-value-narrative` when available;
7. run the Codeer voice and AI-ish copy audit from `copy-and-narrative.md`;
8. inspect source, assets, fonts, and rhythm ledger;
9. run structural and geometric checks available in the presentation runtime;
10. render every slide at 1920x1080 or an equivalent 16:9 output;
11. inspect every slide at full rendered size;
12. generate and inspect a contact sheet of the complete deck;
13. review the complete deck from the declared target audience's perspective and
   record the estimated response, attention curve, unintended interpretations,
   and decision readiness;
14. run a context-isolated cold read after the first complete draft and after
   any material structural revision; compare its retelling and objection with
   the approved contract;
15. record findings by severity and affected slide;
16. fix canonical source files, not only the generated `.pptx`;
17. rebuild and rerender;
18. repeat failed checks and complete one full final pass.

Require at least one fix-and-rerender cycle for a new deck or a substantive
visual-system change. A zero-finding first render still needs explicit full-size
and contact-sheet review.

## 2. Narrative and copy gate

For every new deck or major content revision, block slide production until the
user explicitly approves:

- audience role, context, knowledge, evaluation criteria, likely pushback,
  concern, and decision;
- audience reality, cost or blocked result, desired change, and the
  one-sentence central claim;
- every mechanism's customer question, operational explanation, and role as a
  value mechanism, trust proof, or supporting detail;
- every proof artifact's visible fact, implication, boundary, and provenance;
- the risk served by control or validation, including any justified governance
  or release-control exception;
- the CTA's tested central claim and observable result;
- what the deck should make the audience understand, believe, and do;
- the ordered story spine;
- the main audience friction attached to every story-spine claim and the chosen
  method for earning conviction;
- every section's contribution to the story spine;
- every slide's story-spine contribution, causal role, inherited premise or
  tension, primary claim, audience-visible change, convincing support, proof
  implication, mechanism role, knowledge dependency, new concepts, consequence,
  dependency, transition, and any CTA claim tested;
- open assumptions and claims requiring confirmation.

For a visual-only restyle or minor copy correction, recheck these fields and
preserve the approved meaning. Escalate only when the edit exposes a storyline
conflict or changes the intended conclusion.

Run the copy audit across all visible language. Review search matches in
context; do not perform blind replacement. One justified contrast can pass.
Repeated false contrasts, empty transformation language, slogan cadence, or
unsupported certainty cannot.

## 3. P0 hard failures

Block delivery when any P0 item fails.

### Structure and geometry

- Use 13.333 x 7.5in widescreen geometry.
- Use a registered layout from `layout-contracts.md`.
- Keep all editable content inside the safe region.
- Prevent text, shape, image, chart, table, and footer overlap.
- Prevent clipping, overflow, off-slide objects, and hidden required content.
- Keep title, caption, source, and page-number placeholders clear.
- Preserve intended reading order.
- Give every slide a unique semantic title.
- Prevent corrupt or unopenable PPTX output.

### Narrative and purpose

- Block a new deck or major content revision without explicit audience-value,
  narrative-contract, and slide-map approval.
- Block a new deck or major content revision when consequential target-audience
  context is missing and no explicit assumption has been approved.
- Block a deck whose locally coherent slide sequence tells a different story
  from the approved spine.
- Give every slide one recorded story-spine contribution, one causal role, one
  primary claim, one audience-visible change, and one consequence in the deck's
  argument.
- Ensure every slide advances the approved audience reasoning or earns its role
  as necessary support.
- Make every slide self-sufficient: its visible title, body, and artifact must
  form a coherent argument using only concepts established on that slide or
  earlier in the deck.
- Block orphan concepts, missing antecedents, and conclusions that introduce a
  feature, comparison, or term not previously explained.
- Prevent a later slide or speaker note from supplying a premise required to
  understand the current slide.
- Block a sequence in which several slides can be reordered without changing
  the argument; repair the causal dependencies first.
- Block delivery when the complete deck has not been reread from the target
  audience's perspective after the latest modification cycle.
- Block delivery when a required context-isolated cold read has not been run or
  its material central-claim mismatch remains unresolved and unreported.
- Preserve a logical transition into and out of every slide.
- Prevent storyline, audience, objective, or requested decision drift.
- Distinguish approved facts, assumptions, proposals, and open questions.

### Voice and copy

- State expected behavior positively and directly. Reserve negative language
  for finite exclusions, hard safety boundaries, or a real misconception.
- Use natural language appropriate to the declared audience and locale.
- Prevent unsupported certainty, AI magic, hype, or grandiose claims.
- Prevent a false contrast from carrying a slide's main claim.
- Prevent repeated AI-ish rhetorical grammar from defining the deck's voice.
- Keep titles specific enough to be useful in an outline or meeting discussion.

### Typography and color

- Use approved fonts or report an explicit fallback.
- Prevent unexpected font substitution.
- Keep title, body, label, chart, table, and caption text at or above minimum
  sizes.
- Use only declared Codeer colors.
- Use approved text/background contrast pairs.
- Prevent brass on white, desk, sage, or evergreen; white on brass; ink on
  evergreen; and evergreen on ink.
- Keep critical meaning independent of color alone.

### Evidence and integrity

- Prevent invented metrics, customer proof, testimonials, or outcomes.
- Prevent a screenshot, click, interface state, or representative example from
  being presented as proof of a business outcome without connecting evidence.
- Show source, period, unit, denominator, and forecast/actual status where
  required.
- Keep generated concepts distinguishable from authentic product evidence.
- Preserve real screenshot content; do not present AI-redrawn UI as shipped UI.
- Remove placeholder text such as `TODO`, `lorem`, `xxx`, `[insert]`, or sample
  customer names not approved for use.
- Redact private data, credentials, internal URLs, tokens, and customer
  identifiers.
- Use opaque redaction, not blur.

### Scope

- Exclude internal task-management, project-status, handoff, or delivery-process
  material unless explicitly requested.
- Do not silently replace an approved storyline; surface and confirm proposed
  narrative changes.
- Do not add an unproven reusable explanatory component to the system.

## 4. P1 visual and evidence failures

Fix P1 findings before delivery unless the user explicitly accepts the tradeoff.

### Narrative and copy refinement

- Repair feature-first ordering when the audience must decode product structure
  before it can recognize the current situation or desired change.
- Put a real or clearly labeled representative conversation, decision, failure,
  correction, product state, or result before the first framework or product
  architecture unless an approved technical exception applies.
- Delay, demote, or remove a mechanism that does not answer an already
  established customer question.
- Explain actor, action, artifact, condition, and decision before relying on
  internal product terms; retain the term when the declared audience needs it.
- State what a screenshot, example, or demonstration visibly proves, what it
  changes in the work or decision, and what it does not establish.
- Treat control, validation, review, traceability, and continuous improvement as
  trust proof for a named risk unless governance or release control is the
  declared audience's primary job.
- Replace a generic CTA with a proportionate next step that tests the central
  claim and names what the audience can inspect or decide afterward.
- Rewrite generic labels such as `The challenge`, `Our solution`, `Why now`, or
  `Why us` when a specific claim or conclusion is available.
- Review every `不是 X，而是 Y`, `不只 X，更是 Y`, `not X, but Y`, and
  `not just X` construction; keep only distinctions the audience genuinely
  needs.
- Review slogan-like `從 X 到 Y`, `先 X，再 Y`, `from X to Y`, `reimagined`,
  `future of`, and transformation-language patterns.
- Replace abstract praise with an actor, action, artifact, condition, evidence,
  or decision.
- Break up repeated pairs, triads, parallel fragments, and identical title
  grammar across neighboring slides.
- Remove generic manifesto closings and end with a concrete decision, input, or
  next action.
- Read the deck aloud and repair synthetic cadence, unnatural mixed language,
  excessive punctuation, and forced line breaks.

### Hierarchy and composition

- Make one argument dominant.
- Make one visual anchor obvious.
- Make the reading path apparent within three seconds.
- Keep body-slide titles left aligned unless the registered layout permits
  centered composition.
- Prevent three-line titles; rewrite or change layout.
- Prevent uniform visual weight across unrelated elements.
- Prevent random negative-space holes and accidental near-centering.
- Prevent symmetric composition when the information is not equivalent.
- Use spacing tokens consistently.
- Prevent boxes that do not represent an artifact, boundary, or functional
  group.

### Screenshots and images

- Keep meaningful screenshot text readable at full render size.
- Crop irrelevant chrome, sidebars, empty workspace, and navigation.
- Preserve aspect ratio and avoid visible raster upscaling.
- Keep comparison screenshots at identical scale and crop.
- Use consistent border, radius, padding, and shadow treatment.
- Limit annotations to one to three and keep them off meaningful UI text.
- Keep generated imagery from implying customer, product, or outcome evidence.
- Confirm image source and usage rights when external assets are included.

### Charts

- Keep category and data labels readable and untruncated.
- Use a defensible baseline.
- Distinguish actual, forecast, target, and benchmark.
- Keep units and time periods visible.
- Use direct labels instead of an unnecessary legend.
- Prevent overlapping labels, excessive series, rainbow colors, and tiny plotted
  islands inside large blank areas.
- Keep simple charts editable when the runtime supports it.

### Tables

- Keep body text at 14pt or larger when practical.
- Keep approximately six columns and eight visible rows as a density limit.
- Right-align numeric values and left-align prose.
- Use `—` rather than zero for unavailable data.
- Prevent spreadsheet screenshots when an editable table is practical.
- Keep source, definitions, period, and sample size close to the table.

### Diagrams

- Use one reading direction.
- Keep no more than four nodes per row and roughly eight visible nodes.
- Keep connectors behind nodes and avoid crossings.
- Use arrowheads only where direction matters.
- Keep text native and editable where practical.
- Prevent paragraphs inside nodes, decorative icons, and ambiguous containment.

### Rhythm

- Review any layout repeated more than twice.
- Review any anchor type repeated more than three times.
- Review more than three dense slides or two dark slides in a row.
- Review brass-dominant treatment on more than 25% of slides.
- Review evergreen full-slide surfaces on more than 10% of slides.
- Prevent a cover-only motif that never recurs.
- Prevent one slide from appearing to come from another template.

## 5. P2 refinement warnings

Resolve when practical or record as intentional.

- Tighten a loose crop around the real evidence.
- Replace a legend with direct labels.
- Remove a low-value icon, border, or container.
- Consolidate nearly duplicate annotations.
- Increase deliberate negative space around an important conclusion.
- Align captions, sources, or page numbers more consistently.
- Reduce an overly prominent logo or footer.
- Replace a decorative photograph with product evidence or typography.
- Normalize small differences in corner radius, rule weight, or shadow.
- Reduce unnecessary transition or animation behavior.

Do not spend refinement effort polishing a slide whose evidence or hierarchy is
still wrong.

## 6. Full-size rendered inspection

Inspect every slide at 1920x1080 or equivalent. Do not rely only on thumbnail or
object-bound checks.

Ask:

- Can the smallest intended text be read without zooming?
- Does the title visibly dominate the slide?
- Is the main evidence identifiable immediately?
- Are line breaks natural in English and Traditional Chinese?
- Did fonts, symbols, punctuation, or CJK characters substitute incorrectly?
- Do artifacts, charts, and tables align to the grid?
- Does any annotation appear detached from its target?
- Are white screenshots legible on light backgrounds?
- Are dark-slide contrast and brass usage correct?
- Do cropped screenshots preserve necessary context?
- Are chart labels, table values, and diagram nodes readable?
- Are sources visible but subordinate?
- Is any private or internal information exposed?
- Does the visible copy still match the approved slide question and purpose?
- Did line wrapping accidentally turn natural sentences into slogan fragments?

Inspect PDF output separately when PDF is a deliverable. Verify that fonts,
transparency, SVGs, and image crops survive conversion.

## 7. Contact-sheet inspection

Create a contact sheet containing every slide in sequence. Use a consistent
thumbnail size and enough columns to compare neighboring slides.

Inspect:

- surface distribution and accidental dark-slide clusters;
- repeated layouts and mechanical left/right alternation;
- density runs and whether every slide feels equally crowded;
- overuse of brass, evergreen, screenshots, tables, or photographs;
- title-position drift;
- inconsistent screenshot framing;
- abrupt changes in typography, radius, shadow, or rule language;
- orphan slides that appear imported from another deck;
- a weak cover/closing relationship;
- motifs that appear once and disappear;
- important slides that fail to stand out at thumbnail scale;
- repeated title grammar or rhetorical contrast patterns across the sequence;
- slides whose apparent purpose does not match their position in the story.

Do not add a decorative rhythm-break slide merely to improve the contact sheet.
Change rhythm only when the content supports a different scale, surface, or
evidence type.

## 8. Target-audience pass

After every requested modification or completed revision cycle, reread the
whole deck as the declared target audience. Ignore presenter knowledge that is
not visible in the slides. Review the complete sequence, including slides that
were not edited.

First state the audience lens used for the pass:

- role and situation;
- existing knowledge and likely prior beliefs;
- evaluation criteria and likely pushback;
- decision the audience can make;
- assumptions made because context was unavailable.

Run separate passes when materially different audiences will see the deck. Do
not average a buyer, investor, and accelerator reviewer into one generic reader.

Estimate the following responses:

### Immediate read and mental model

- What does the audience think the company, problem, or proposal is after the
  cover and first few slides?
- Does it place the company in the intended category, or misclassify it?
- Can it explain the deck's central claim in one sentence?

### Relevance and stakes

- Why should this audience care now?
- Are the consequence, urgency, opportunity cost, or strategic value tangible?
- Where is the likely "so what?" reaction?

### Comprehension and cognitive load

- Which terms, diagrams, screenshots, claims, or transitions require hidden
  knowledge?
- Where does density or abstraction force the audience to work too hard?
- What is technically understandable but still hard to absorb?

### Attention and narrative momentum

- Where do curiosity, concern, confidence, or interest rise?
- Where does attention drop because of repetition, premature detail, weak
  stakes, or a detour?
- Does each slide create a reason to continue?

### Trust and credibility

- Which claims feel earned, and which feel asserted?
- Is evidence specific, legible, comparable, and correctly scoped?
- Does tone feel candid and competent, or defensive, inflated, or evasive?

### Pushback and alternatives

- What objections, alternative explanations, or counterexamples will arise?
- Why might the audience prefer the status quo, an incumbent, a general tool,
  internal work, or doing nothing?
- What comparison, proof, constraint, or risk treatment will it request?

### Risk and unintended interpretation

- What negative conclusion might the audience infer even when the deck does not
  state it?
- Could the company appear services-heavy, unscalable, unfocused, too early,
  easy to copy, operationally risky, or dependent on one customer or partner?
- Does one slide accidentally contradict the intended positioning elsewhere?

### Aha moments and insight

- Where does a new, useful, and memorable understanding genuinely land?
- Is the aha earned by the preceding tension and evidence?
- Which intended aha remains generic, unclear, or unsupported?
- Does a later slide bury, repeat, or dilute the insight?

### Memorability and retelling

- What one sentence, image, example, or number will the audience remember?
- What would it tell a colleague after the meeting?
- Is the remembered takeaway the one the deck intended?
- Does its one-sentence retelling match the approved central claim, or has a
  feature, framework, or trust mechanism displaced the intended value?

### Decision readiness

- Is the audience now more likely to take the intended action?
- What is the strongest reason to proceed and the strongest reason to say no?
- What unanswered question or missing evidence still blocks the decision?
- Is the requested next step proportionate and clear?
- Which central claim does that next step test, and what can the audience inspect
  or decide after completing it?

Apply the relevant decision lens:

- **Buyer:** workflow fit, time to value, implementation burden, control,
  integration, security, proof, ROI, ownership, and procurement risk.
- **Investor:** wedge, market expansion, differentiation, moat, traction quality,
  business model, unit economics, team, timing, and venture-scale potential.
- **Accelerator reviewer:** selection fit, technical ambition, credible
  program-period milestone, unique program leverage, readiness to benefit,
  coachability, and regional or global potential.

For every material item, report:

- affected slide or sequence;
- category;
- estimated reaction in the audience's voice;
- severity: P0 decision-blocking, P1 material, or P2 minor;
- visible evidence that led to the inference;
- recommended response: revise, add evidence, reorder, clarify verbally, or
  accept as a deliberate tradeoff.

Summarize the attention curve across the deck: hook, first drop, strongest
recovery, primary aha, and closing decision state. Separate observed slide
content from inferred audience reaction, and label the result as estimated
feedback rather than user research.

Report these findings to the user after the modification. Resolve material
friction and pushback before delivery or record them as warnings accepted by
the user. Do not invent a positive aha moment merely because the slide was
designed to create one.

## 9. Specialized checks

### Font portability

- Confirm every approved font is installed in the build environment.
- Confirm Latin and East Asian theme-font mappings.
- Test editable font embedding when the deck will be shared as PowerPoint.
- Prefer full-character embedding when recipients must edit and licensing
  permits it.
- Record fonts that cannot be embedded.
- Open the deck in the target PowerPoint environment when possible.

### Template and master

- Keep light and dark variants geometrically consistent.
- Keep editable content off the master.
- Keep master decoration outside content placeholders.
- Keep placeholder types and reading order correct.
- Ensure users can replace media without deleting master-owned elements.
- Reapply changed layouts and rerender affected slides.

### Comparison integrity

- Use the same scale, crop, baseline, period, and units.
- Preserve equivalent internal hierarchy.
- Prevent a visual treatment from exaggerating one side.
- Make missing or unavailable information explicit.

### Accessibility

- Give each slide a unique semantic title.
- Add alt text for meaningful images, charts, and diagrams.
- Keep reading order logical.
- Avoid color-only status communication.
- Keep ordinary text contrast at least 4.5:1 and prefer 7:1 for important body
  copy and projected readability.

### Anti-AI review

Fail or revise when the deck relies on:

- purple/blue gradients, glass, glow, aurora, particles, or orbs;
- centered title plus three equal cards;
- tiny uppercase eyebrow loops;
- icons above every heading;
- floating device mockups and perspective screenshots;
- four KPI cards plus a donut;
- generic circular workflows or spaghetti diagrams;
- random color changes and multicolored icon sets;
- decorative monospace and faux technical labels;
- staged or synthetic stock imagery presented as authenticity;
- claims of certainty unsupported by visible evidence.

Also fail or revise when the language relies on:

- repeated `not X, but Y` or `不是 X，而是 Y` contrasts;
- repeated `not only X` or `不只 X，更是 Y` escalation;
- transformation clichés such as `from X to Y`, `reimagined`, `unlock`, or
  `the future of` without a concrete mechanism;
- polished pairs and triads used to simulate completeness;
- abstract noun stacks, generic innovation language, or unlabeled hype;
- slogan fragments, excessive em dashes or colons, and identical sentence
  cadence across slides;
- generic rhetorical questions or manifesto-style closing language.

## 10. Delivery report

Report:

- canonical source path;
- generated PPTX/PDF path when applicable;
- rendered slide and contact-sheet paths;
- structural check result;
- narrative-contract and slide-map approval status;
- audience-value contract, central-claim retell, mechanism-role, proof-unit, and
  verification-CTA status;
- target-audience context and post-modification audience-pass status;
- context-isolated cold-read result, structural revision if any, and remaining
  mismatch;
- estimated target-audience response, attention curve, and decision-readiness
  findings;
- Codeer voice and AI-ish copy-audit result;
- P0/P1/P2 findings and their disposition;
- fix-and-rerender cycles completed;
- font and embedding status;
- asset provenance and redaction status;
- intentional deviations from the visual contract;
- remaining warnings and unverified assumptions.

Use these readiness states:

- `ready`: all P0 and P1 items pass after rendered review;
- `ready-with-warnings`: all P0 pass and the user accepts recorded P1/P2 tradeoffs;
- `not-ready`: any P0 fails, or rendered review has not occurred.

Never describe a source-only build as ready.
