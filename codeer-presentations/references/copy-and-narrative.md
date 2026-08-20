# Codeer Presentation Narrative and Voice

Use this reference whenever writing, rewriting, reviewing, or approving Codeer
presentation content. It governs the reasoning path and visible language, not
the visual layout.

## Contents

1. Narrative contract
2. Storytelling boundary conditions
3. Per-slide causal-chain map
4. Codeer presentation voice
5. AI-ish language patterns
6. Rewrite method
7. Copy audit

## 1. Narrative contract

Use the approved contract from `$codeer-audience-value-narrative` as the source
of truth for audience reality, desired change, central claim, mechanisms, proof,
trust treatment, evidence boundaries, and CTA. Do not create a second value
thesis for the deck.

If that skill is unavailable, capture the same fields before slide planning.
Then add this deck-specific overlay and obtain explicit approval before a new
deck or major content revision:

```yaml
audience:
  role: "Who is in the room?"
  context: "Why are they seeing this now?"
  current_knowledge: "What do they already know or believe?"
  evaluation_criteria: "How will they judge the proposal or company?"
  likely_pushback: "What are they predisposed to question, resist, or compare?"
  main_concern: "What risk, need, or question matters most?"
  decision: "What decision are they able to make?"
objective:
  understand: "What should become clear?"
  believe: "What conclusion should feel earned?"
  do: "What concrete next action should follow?"
story_spine:
  - "Ordered strategic claims that earn the central claim and decision"
open_assumptions:
  - "Claims, prices, product status, or facts needing confirmation"
```

Treat target-audience context as required input, not optional background.
Inspect supplied customer materials, program criteria, prior decks, meeting
context, and known stakeholders before asking the user. Ask about any missing
context that could materially change the story. When proceeding from an
inference, state the assumed audience context and its uncertainty explicitly.

The story spine must describe how the audience's thinking moves. A list such
as `Problem / Solution / Product / Pricing` is an agenda, not a storyline.

### Lock the story spine before slide logic

Treat the story spine as the deck's structural skeleton. Write it as four to
seven ordered strategic claims that together earn the intended conclusion.
These claims define which story the deck tells; they are not a summary inferred
from a finished set of slides.

Use this narrative hierarchy in order:

1. approved audience-value contract and central claim;
2. deck objective and intended decision;
3. approved story spine;
4. target-audience friction that must be resolved;
5. section contribution to the spine;
6. per-slide causal chain;
7. convincing support appropriate to each claim;
8. copy and visual execution.

Do not optimize a lower level while a higher level is unresolved. Tight
transitions between adjacent slides are useful, but they do not prove that the
deck follows the right spine. A locally coherent sequence can still tell the
wrong story, overemphasize a secondary capability, or arrive at an unimportant
conclusion.

Before repairing transitions, perform the spine test:

> The approved story needs the audience to believe **[spine claim]**. This
> section establishes it through **[necessary reasoning, mechanism, or support]**.

If this cannot be completed plainly, remove the section, move it to supporting
evidence, or revise the spine explicitly with the user. Never let an attractive
slide silently redefine the deck's argument.

When the slide titles are read alone, they should reconstruct the approved
story spine. If they form a different argument, the deck has drifted even when
every adjacent transition sounds reasonable.

Do not infer that the audience should buy, invest, or approve merely because
the deck is a sales or investor deck. State the actual decision appropriate to
this meeting.

## 2. Storytelling boundary conditions

Apply the cross-format dependency rules to slide sequence and visible copy.
This section is the deck adapter, not a competing audience-value method.

A systematic explanation can be accurate, complete, and easy to follow while
still failing as a pitch. Treat systematic decomposition as an internal map of
the material, not as the default audience-facing structure.

A story is a sequence of audience-state changes. Every slide must change what
the audience notices, feels, believes, or wants to know next. Information that
does not create such a change is supporting detail, an appendix candidate, or
material to remove.

Use these boundary conditions:

### Begin from lived reality

Start with an actor, situation, opportunity cost, consequence, or decision the
audience can recognize. Do not lead with a taxonomy of product requirements,
failure modes, or system components.

Allow a framework-first or control-first opening when the declared audience
already accepts the stakes and is explicitly evaluating architecture,
governance, compliance, or coverage. Record the exception instead of inserting
a generic pain scene.

For a problem slide, show what the customer repeatedly experiences and why the
obvious choices are costly. The audience should feel the trap before learning
its technical decomposition.

### Create tension without manufacturing drama

Emotion in a business deck comes from relevance and consequence, not hype.
Use real tensions such as:

- necessary work displacing higher-value work;
- speed conflicting with acceptable quality;
- delegation creating training and checking burden;
- improvement risking regression;
- growth increasing effort faster than revenue.

Do not exaggerate the customer, competitor, or risk to make the story exciting.
Let a recognizable dilemma carry the emotional weight.

### Put concrete experience before abstraction

Show a real or representative conversation, decision, failure, correction, or
outcome before summarizing it with a framework. Let the audience infer the
pattern from evidence, then name the pattern.

Use an abstraction as a bridge, compression device, or conclusion. Do not let a
large conceptual diagram replace the example that gives the idea meaning.

Do not treat a screenshot or product state as self-explanatory. State what is
visible, what it implies for the work or decision, and what it does not prove.

### Make every mechanism answer an established problem

Do not organize solution slides around the product architecture or feature
inventory. Introduce a mechanism only after the audience understands the
specific struggle, dilemma, or unanswered question it resolves.

A solution slide has not earned its place when it explains what the product
does but cannot complete this sentence:

> This matters now because the previous slide showed that...

Explain the actor, action, artifact, condition, and decision before relying on
Prompt, Eval, version, trace, memory, knowledge base, or similar internal terms.
Keep a term when the audience needs its precision; do not use a fixed glossary
or word ban.

Treat control, validation, review, traceability, and continuous improvement as
proof that reduces a named risk. Promote one to a primary claim only when
governance, compliance, or release control is the audience's actual job.

### Preserve causal nextness

Order slides by because and therefore, not by topic categories. Each answer
must supply a premise, consequence, or unresolved tension that makes the next
claim necessary.

If several slides can be reordered without changing the argument, the deck is
probably an inventory rather than a story. Rebuild the sequence around causal
dependence, rising stakes, discovery, or proof.

### Require self-sufficient slides and progressive knowledge

Make every slide internally complete while allowing it to depend on concepts
that earlier slides have explicitly established. The visible title, body, and
artifact must form one coherent argument. Speaker notes or presenter knowledge
cannot supply a missing premise.

Use a concept ledger during review:

1. record the concepts the deck has explicitly established before each slide;
2. list every new product term, distinction, actor, metric, or mechanism used on
   the current slide;
3. introduce or demonstrate each new concept before drawing a conclusion from
   it;
4. allow later slides to depend only on concepts already established, never on
   a future explanation;
5. ensure references such as `this`, `the same Agent`, `one of the steps`,
   `next version`, or `these results` have a visible and unambiguous antecedent.

Block orphan concepts. A closing line must not introduce a feature, comparison,
or category that the slide and preceding deck have never explained. For
example, `回覆建議只是其中一步` fails when reply suggestions have not appeared
in the slide or earlier sequence. Either introduce the mechanism before using
that conclusion or remove the line.

Run the cold-reader test on each slide:

> Given only the concepts established so far, can a reader explain what this
> slide claims, why it follows, and how the visible content supports it?

If not, the slide is not self-sufficient or the knowledge dependency is out of
order, even when its wording sounds polished.

### Choose support that increases conviction

Treat evidence as one persuasion method among several. Use a mechanism,
business logic, product demonstration, concrete situation, credible plan,
comparison, or quantitative evidence according to the audience friction being
resolved.

For a seed-stage investor deck, do not force immature scale metrics to carry the
emotional or strategic weight of the story. A small number can weaken the pitch
when the reader interprets it as a scale benchmark rather than the narrow signal
it actually supports. Establish a compelling value proposition and market
reason first; use early metrics only when their scope and conclusion are clear.

Do not create a standalone evidence slide by convention. Keep it only when it
advances the approved story spine or resolves a material objection. This does
not permit unsupported factual claims, hidden adverse facts, invented proof, or
inflated certainty.

### Use systematic views in a supporting role

Keep matrices, component maps, lifecycle summaries, and capability tables when
they clarify or prove an argument the audience already cares about. These views
are good at answering "How is this organized?", "How does it work?", or "Is the
coverage complete?" They usually do not answer the earlier question "Why should
I care?"

Therefore, first establish relevance through a recognizable situation,
consequence, dilemma, or piece of evidence. Use the systematic view afterward
to organize the answer or prove completeness. Lead with the systematic view
only when the declared audience already accepts the stakes and explicitly needs
a technical or reference-first explanation.

Systematic completeness remains a factual boundary: the story may select and
sequence information, but it must not distort product truth, hide material
limitations, or imply evidence that does not exist.

### Diagnose an explanatory deck

Treat these as warning signs:

- slide titles name topics or modules rather than implications;
- the first problem slide could describe any company in the category;
- pain is divided into neat boxes but no customer's struggle is visible;
- a product section answers questions the audience has not yet asked;
- the deck becomes clearer when read, but not more important or memorable;
- removing or reordering a slide does not change the reasoning;
- the audience must accept an abstraction before seeing a concrete example.

### Revision loop: transform explanation into story

Use this loop when a draft explains the subject accurately but does not yet
accumulate audience interest or conviction:

1. Preserve the systematic draft as the factual inventory.
2. Identify whose point of view the audience should inhabit.
3. Replace abstract problem categories with a scene, consequence, or deadlock.
4. Compare every section with the approved story spine and remove or demote
   locally coherent detours.
5. State the spine contribution, causal role, and primary claim of each slide.
6. Reorder slides so each conclusion becomes a premise or tension for the next
   claim.
7. Attach each product mechanism to the exact tension it resolves.
8. Move remaining system detail into supporting material, later clarification,
   or appendix.
9. Read the sequence aloud and check whether the approved argument, interest,
   and conviction accumulate together.

Do not optimize only for emotional intensity. The target is earned attention:
the audience understands why the problem matters, why existing choices fail,
why the proposed mechanism is relevant, and why the chosen support should
change its decision.

## 3. Per-slide causal-chain map

Create one row for every slide before production:

| Field | Required answer |
|---|---|
| Slide | Number and working title |
| Story-spine contribution | Which approved strategic claim this slide advances and why that claim is necessary |
| Causal role | What changes in the argument because this slide exists |
| Inherited premise or tension | What the previous slide established that this slide must advance or resolve |
| Primary claim | The one conclusion the audience should leave with |
| Audience-visible change | What becomes different in the audience's work, risk, understanding, or decision because this claim is true |
| Audience friction resolved | The main hesitation, misconception, or risk this slide must reduce |
| Convincing support | The mechanism, logic, example, demonstration, contrast, plan, or evidence that makes the claim believable |
| Proof implication | What the visible support establishes, and what it does not establish |
| Mechanism role | `value-mechanism`, `trust-proof`, `supporting-detail`, or not applicable |
| Prior knowledge dependency | The exact concepts this slide assumes earlier slides have established |
| New concepts introduced | Terms or mechanisms that must be explained visibly before the slide uses their implications |
| Consequence | What now follows if the primary claim is true |
| Dependency test | Why this slide cannot move elsewhere or be removed without weakening the argument |
| Transition out | The next proposition or tension that follows logically, not a predicted audience question |
| CTA claim tested | For an action slide, which central claim the requested next step lets the audience examine; otherwise not applicable |

Do not use a brainstormed list of possible audience questions as the ordering
method. Real audiences can ask many valid questions; predicting one does not
prove that a story is logically connected. Audience questions remain useful
during objection handling and review, but they are not the narrative spine.

Use a claim, not an internal content label. `Product overview` is not a claim.
`The service lead decides which Agent behaviors can be released and which still
require human review` is.

Each slide must do one primary job. Split a slide when it tries to establish a
problem, explain the product, prove the result, and ask for a decision at once.

First test spine fidelity:

> This slide exists to establish **[approved story-spine claim]**. Without it,
> the deck cannot earn **[intended conclusion]** because **[reason]**.

Then test slide self-sufficiency and local sequence aloud:

> Using only **[established prior concepts]** and the visible content on this
> slide, **[primary claim]** is understandable and supported.

> Because **[previous premise or support]** is true, **[this claim]** follows.
> Therefore **[next consequence or tension]** must now be established.

If the sentence does not make sense, repair the argument, reorder the slides,
or remove the slide. If several slides can change places without affecting the
argument, the deck is still a content inventory. Do not use a decorative
section divider to hide a logic gap.

For a new deck or major revision, show the complete map to the user and wait
for explicit approval. For a visual restyle or minor copy repair, audit the map
without blocking unless the requested edit changes its meaning.

## 4. Codeer presentation voice

Make the language sound like a knowledgeable operator speaking plainly in the
room.

- Lead with a specific conclusion, decision, action, or observed condition.
- Prefer subject + verb + object. Name who does what, with which artifact, and
  under what condition.
- Use positive formulations that state the intended behavior directly. Use
  negative language for finite exclusions, hard safety boundaries, or a real
  audience misconception that the deck must correct.
- Use operational nouns: draft, review, case, source, standard, correction,
  release, conversation, handoff, result, and decision.
- Explain technical language through the concrete workflow before relying on
  the label.
- Keep confidence proportional to evidence. State what is current, proposed,
  tested, provisional, or still unknown.
- Make the audience feel capable of evaluating the proposal.
- Use natural Traditional Chinese. Keep English only when it is the established
  product term or clearer than a forced translation.
- Let Codeer appear as a participant with a proposal, not an all-knowing
  narrator. Prefer `我們建議先...` or a direct factual sentence over grand
  declarations.
- End with a concrete decision, input, or next action rather than a manifesto.

Write titles as useful meeting sentences. A strong title usually names a
specific change, implication, or decision and can stand alone in the deck's
outline.

Prefer:

- `第一階段由 AI 提供草稿，原美學同仁確認後才送出`
- `系統要清楚知道哪些能回答、哪些要追問、哪些必須交給真人`
- `費用分為首期導入與持續服務兩部分`

Avoid turning every title into a slogan. Navigation labels are acceptable when
the slide's role is truly navigational.

## 5. AI-ish language patterns

Treat these as detection patterns, not a blind word blacklist. Revise when a
pattern substitutes rhetoric for meaning, creates a false contrast, or repeats
across the deck.

### Default contrast frames

- `不是 X，而是 Y`
- `不只 X，更是 Y`
- `不只是 X，也／而且 Y`
- `與其 X，不如 Y`
- `not X, but Y`
- `not just X—Y`
- `more than X`

These frames often manufacture an opponent so the second half sounds profound.
State the positive claim directly unless the audience genuinely holds X and
the deck must correct it.

### Transformation templates

- `從 X 到 Y` / `from X to Y`
- `先 X，再 Y` used as a slogan rather than a real sequence
- `X，重新定義` / `X, reimagined`
- `the future of...`, `next-generation...`, `a new era of...`
- `unlock`, `unleash`, `redefine`, `revolutionize`, `transform`, `empower`

Name the concrete changed behavior, owner, or output instead.

### Polished symmetry

- repeated pairs and triads such as `更快、更準、更安心`;
- parallel fragments such as `能用、能練、能檢查、能更新`;
- three equal claims with identical grammar merely because three feels
  complete;
- repeated sentence structures across consecutive slide titles.

Parallelism is allowed when the items are genuinely distinct and exhaustive.
Otherwise it makes the deck sound generated and flattens emphasis.

### Empty abstraction

- stacks such as `智慧驅動的創新服務轉型`;
- broad praise such as `seamless`, `powerful`, `robust`, `holistic`, `scalable`,
  `intelligent`, or `world-class` without a named mechanism;
- labels such as `Value`, `Innovation`, `Impact`, or `Possibility` standing in
  for an actual conclusion;
- qualitative claims formatted like metrics.

Replace the abstraction with an actor, action, artifact, condition, or observed
result.

### Pitch-deck autopilot

- `The challenge`, `Our solution`, `Why now`, or `Why us` when a more specific
  claim or conclusion is available;
- `What if...?` openings that do not correspond to a real audience concern;
- generic closings such as `Let's build the future together`;
- rhetorical questions whose answer is obvious;
- a title, subtitle, and closing line that repeat the same thesis in polished
  variations.

### Synthetic cadence

- many slogan fragments instead of natural sentences;
- excessive colons, em dashes, slashes, and forced line breaks;
- a tiny label followed by a large inspirational sentence on every slide;
- frequent one-sentence paragraphs with identical length and rhythm;
- unnecessary quotation marks around ordinary words;
- an English term inserted mainly to sound modern.

Read the deck aloud. If it sounds like ad copy rather than someone explaining a
decision, rewrite it.

### Inflated certainty and magic

- `always`, `never`, `guaranteed`, `zero risk`, `perfect`, or absolute control
  claims unsupported by evidence;
- AI described as understanding, learning, or improving without naming the
  review data, release process, or verification;
- one workflow presented as universally correct;
- the audience or competitors caricatured to make Codeer appear necessary.

State the mechanism, scope, evidence, limitation, and human decision.

## 6. Rewrite method

When a sentence feels AI-ish:

1. Identify the factual claim or decision hidden inside it.
2. Remove the rhetorical frame, especially the first half of a false contrast.
3. Name the actor and observable action.
4. Add the condition, evidence, or scope when it changes the meaning.
5. Use the shortest natural sentence that preserves the claim.
6. Compare it with adjacent slides and vary repeated grammar.

Examples from real Codeer presentation work:

| AI-ish draft | More Codeer-like |
|---|---|
| `讓 know-how 真的用得上，而不是再多一個聊天機器人` | `Codeer 把資深同仁的判斷整理成第一線可遵循的服務標準` |
| `不是隨便答答的 FAQ，而是需要專業判斷的場景` | `這些場景都需要明確的專業判斷與服務邊界` |
| `好用的系統不是什麼都答，而是該幫的時候幫` | `系統要清楚知道哪些能回答、哪些要追問、哪些必須交給真人` |
| `不是一開始就讓 AI 自動回` | `第一階段由 AI 提供草稿，同仁確認後才送出` |
| `先從一個流程開始，驗證價值再擴大` | `第一階段聚焦一個高頻、標準清楚的流程` |
| `費用跟著導入範圍與持續改善工作走` | `費用分為首期導入與持續服務兩部分` |

Do not mechanically replace every sentence with these examples. Preserve the
audience, evidence, product truth, and natural phrasing of the current deck.

## 7. Copy audit

Audit all visible language: cover, titles, subtitles, body text, quotes, diagram
labels, table headings, chart annotations, footnotes, and closing copy.

For every slide, verify:

- the slide directly advances an approved story-spine claim;
- the title states or advances the mapped primary claim;
- the slide has one causal role and one primary claim;
- the slide resolves a material audience friction using an appropriate
  convincing method;
- the slide's audience-visible change follows from the primary claim;
- every concept used in the title, body, and closing has been introduced on the
  current slide or earlier in the deck;
- the visible content is sufficient to understand the claim without speaker
  notes or future slides;
- factual claims are supported and sourced when evidence is used;
- every screenshot, example, or demonstration states both the visible fact and
  its implication without claiming an unsupported business outcome;
- the consequence follows from the claim without an unstated logical leap;
- an abstract framework follows concrete meaning rather than substituting for it;
- each product mechanism resolves a tension or question already established;
- internal product terms follow an understandable operational explanation;
- control, validation, review, or continuous improvement serves a named risk
  unless a documented governance or release-control exception applies;
- the transition from the previous slide and to the next slide is explicit in
  the slide map, speaker notes, or presentation plan;
- the language states the intended behavior positively and directly;
- technical terms are necessary and understandable in context;
- an action slide names the central claim its CTA tests and what the audience
  can inspect or decide afterward;
- certainty matches evidence and product status;
- the copy sounds natural when read aloud;
- no rhetorical pattern is carrying meaning that should be factual.

Across the deck, search for repeated patterns, including:

```text
不是|而是|不只|不只是|更是|與其|不如
not .* but|not just|more than
從 .* 到|from .* to|重新定義|reimagined
future of|new era|next-generation
unlock|unleash|redefine|revolutionize|transform|empower
更快.*更準|seamless|powerful|robust|holistic|scalable|intelligent
```

Search results are review prompts, not automatic failures. Fail the copy audit
when a pattern creates false opposition, empty emphasis, unsupported certainty,
or a noticeably repeated synthetic cadence.
