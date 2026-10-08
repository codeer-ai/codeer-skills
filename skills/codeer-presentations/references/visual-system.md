# Codeer Presentation Visual System

Use this reference for all Codeer prospect-facing sales decks and investor pitch
decks. Keep the visual identity stable even when the storyline changes.

## Contents

1. North star and personality
2. Typography
3. Color
4. Spacing and composition
5. Images and screenshots
6. Charts, tables, and diagrams
7. Deck rhythm
8. Anti-patterns
9. Research influences

## 1. North star and personality

Make a Codeer presentation feel like an expert opening a carefully reviewed
working file: calm, precise, candid, and visibly supported by evidence. Explain
AI through human decisions and progressive proof, not spectacle.

Express these paired traits:

- calm, not passive;
- confident, not grandiose;
- technical, not hacker-coded;
- human, not cute;
- candid, not defensive;
- structured, not bureaucratic;
- refined, not decorative;
- optimistic through evidence, not promises.

Use operational language, concrete artifacts, failure modes, and observable
behavior. Make the audience feel more capable of evaluating the product.

Let this product belief influence visual emphasis without turning it into a
mandatory storyline:

> Treat an agent like an apprentice working beside an expert. Let real expert
> feedback accumulate reusable judgment. Let humans decide what the agent
> should learn. Let autonomy be earned through demonstrated performance.

Avoid absolute risk claims such as "zero risk" and avoid language that implies
the system learns safely merely because conversations accumulate.

## 2. Typography

Assign fonts by semantic role.

| Role | Latin | Traditional Chinese | Use |
|---|---|---|---|
| Judgment voice | Source Serif 4 | Noto Serif TC | Major conclusions, section openings, strong quotes, selected hero numbers |
| Workbench voice | Plus Jakarta Sans | Noto Sans TC | Body copy, slide navigation titles, charts, tables, diagrams, captions |
| Evidence metadata | IBM Plex Mono | Noto Sans TC | Eval IDs, versions, timestamps, sample sizes when genuinely technical |

Use static OTF or TTF font files when building a distributable font pack. Define
Latin and East Asian theme fonts separately in PowerPoint.

Use the judgment voice sparingly. Do not set every headline in serif. Prefer it
for a high-salience statement that should feel considered rather than labeled.

Use the workbench voice for operational information. Preserve Plus Jakarta Sans
inside website-derived or product-derived visuals where it already appears.

Use monospace only for real evidence metadata, code, IDs, logs, technical
payloads, or version information. Do not use it as a generic technology signal.

Apply these working sizes on a 16:9 slide:

| Element | Size |
|---|---:|
| Cover or rare hero statement | 44-60pt |
| Main slide conclusion | 32-42pt |
| Navigation-style slide title | 26-34pt |
| Section or module heading | 20-24pt |
| Body copy | 16-20pt |
| Chart/table labels | 13-16pt |
| Caption or source | 9-11pt |

Allow a title to wrap to two lines. At three lines, change the composition or
rewrite the title; do not keep shrinking it.

Do not use tiny uppercase tracked labels above every heading. Do not use
negative letter spacing in body copy. Keep Traditional Chinese line height more
generous than Latin when needed.

Use these fallback intentions when approved fonts are unavailable:

- Source Serif 4 -> Georgia;
- Plus Jakarta Sans -> Aptos;
- Noto Serif TC -> Songti TC or Noto Sans TC;
- Noto Sans TC -> PingFang TC or Microsoft JhengHei;
- IBM Plex Mono -> Consolas or a native monospace.

Treat any fallback as provisional. Render again after installing the approved
fonts. For editable external PowerPoint delivery, test font embedding and warn
when a font cannot be embedded.

## 3. Color

Use only the approved Codeer palette unless the user explicitly authorizes a
brand change.

| Token | Hex | Meaning |
|---|---|---|
| Review Ink | `#14221e` | Authority, decisions, primary text, dark surfaces |
| Expert Evergreen | `#2f6b57` | Verified progress and active behavior |
| Reviewer Brass | `#d7a348` | Human judgment and expert annotation |
| Sage Wash | `#e3eee8` | Supporting context and quiet grouping |
| Desk Background | `#f7f9f7` | Default working surface |
| Artifact White | `#ffffff` | Evidence objects and product surfaces |
| Field Muted | `#52615b` | Secondary explanation and captions |
| Quiet Border | `#dbe7df` | Dividers and artifact boundaries |
| Review Danger | `#b84242` | Failure, unresolved risk, destructive outcomes |

Follow the semantic rule: use color to communicate evidence, state, selection,
risk, or judgment. Do not add color merely because a slide feels quiet.

Use these surface modes:

- `desk`: default; desk background, ink text, white artifacts;
- `sage`: quiet explanation; sage background, ink text;
- `ink`: decisive emphasis; ink background, white text, brass annotation;
- `evergreen`: rare verified outcome; evergreen background, white text.

Use these approved text/background pairs:

| Pair | Contrast |
|---|---:|
| Ink on white | 16.44:1 |
| Ink on desk | 15.54:1 |
| Ink on sage | 13.83:1 |
| White on ink | 16.44:1 |
| Evergreen on white | 6.25:1 |
| White on evergreen | 6.25:1 |
| Brass on ink | 7.22:1 |
| Ink on brass | 7.22:1 |
| Muted on white | 6.52:1 |

Do not use brass text on white, desk, sage, or evergreen. Do not use white text
on brass. Do not place ink on evergreen or evergreen on ink.

Give each slide one dominant accent:

- use evergreen for verified progress;
- use brass for human judgment;
- use danger for real failure or risk;
- otherwise keep the slide neutral.

Allow brass and evergreen to coexist only when their meanings differ clearly.
Do not let them compete at equal weight.

Use brass for expert annotations, requirements, reviewed changes, selected
phrases, or a key number on ink. Do not use brass for generic bullets, icons,
headings, large backgrounds, or premium-looking decoration.

For a typical light slide, keep roughly 80% neutral surface, up to 15%
evergreen, and up to 5% brass. Treat this as an area heuristic, not a quota.

## 4. Spacing and composition

Use one argument, one visual anchor, and one obvious reading path per slide.

Use a 12-column grid on a 13.333 by 7.5 inch 16:9 canvas. Follow exact geometry
from `layout-contracts.md`.

Use only these spacing tokens:

- 6pt: icon-to-label and very tight relationships;
- 10pt: label-to-value;
- 16pt: elements inside one group;
- 24pt: separate content groups;
- 36pt: major structural separation;
- 52pt: deliberate negative space or section separation.

Keep related elements close. Separate different ideas with visibly larger
spacing instead of adding another container.

Prefer asymmetry. Reserve symmetry for a genuine comparison. Use these
composition families:

- 7/5 asymmetric split for explanation plus evidence;
- 8/4 evidence composition for chart/table/screenshot plus interpretation;
- 6/6 comparison for equivalent peers;
- full-width artifact for a dominant screenshot, table, or diagram;
- statement composition with 40-60% negative space;
- data focus for one dominant metric or chart plus interpretation.

Left-align body-slide titles. Center only covers, rare statements, and closing
slides when the composition earns it.

Allow one dominant object and at most two supporting groups. Align the title,
copy, evidence, and captions to shared axes. Form one intentional region of
negative space instead of leaving random gaps.

Use a box only when it represents a real artifact, boundary, or functional
group. Do not wrap every paragraph in a rounded container.

If content does not fit, split or redesign the slide. Never solve overflow by
shrinking all text and spacing.

## 5. Images and screenshots

Use product screenshots as evidence, not decoration. Choose one treatment:

- `full-artifact`: show the relevant workspace when overall context matters;
- `evidence-crop`: crop tightly around one result, feedback item, or decision;
- `context-detail`: show quiet context plus one enlarged crop;
- `matched-comparison`: use identical crop dimensions for before/after states.

For every screenshot, state the visible fact and its implication for the
audience's work, risk, or decision. Do not let interface chrome, a click, or a
status label stand in for a business result the artifact does not establish.

Prefer these target ratios:

| Content | Ratio |
|---|---|
| General product workspace | 16:10 |
| Wide result or workflow | 16:9 |
| Panoramic sequence | 21:9 |
| Dialog, form, or focused panel | 4:3 |
| Small detail or single status | 1:1 |

Crop rather than distort. Preserve the authentic product UI. Do not redraw a
real screenshot with image generation. Label any conceptual UI clearly.

Frame screenshots with a 1px Quiet Border, an 8-10px-equivalent radius when the
product surface is rounded, and the low Codeer artifact shadow only on light
backgrounds. Put a screenshot on a white stage when using a dark slide.

Remove irrelevant browser chrome, sidebars, blank workspace, and navigation.
Keep browser chrome only when the URL or browser state matters.

Limit annotations to one to three. Use brass for expert judgment, evergreen for
verified outcomes, and danger for real failure. Prefer external callouts with
thin connectors. Do not cover meaningful UI text.

When screenshot text is too small, enlarge the relevant crop or quote the exact
text outside the screenshot. Do not rely on arrows pointing to unreadable text.

Use PNG for UI, diagrams, and transparency; JPEG or WebP for photographs; and
SVG for logos and simple icons when PowerPoint rendering remains reliable. Use
at least 1600px width for a large screenshot and avoid raster upscaling beyond
approximately 125%.

Redact emails, customer identifiers, tokens, internal URLs, and sensitive data
with opaque replacement shapes, not blur. Preserve an unmodified source asset
outside the deliverable.

Use photography sparingly. Prefer observational scenes of real work: an expert
reviewing an AI suggestion, colleagues examining examples, hands and documents,
or visible working artifacts. Avoid robots, holograms, generic call centers,
handshakes, people staring excitedly at laptops, synthetic diversity tableaux,
and fake dashboards inside photographs.

Never use generated imagery as customer proof, product proof, a testimonial, a
deployment, or a measured result. Track generated-image provenance in the deck
source or notes.

## 6. Charts, tables, and diagrams

Use one evidence question per visual. Make the evidence easy to inspect and the
conclusion easy to find.

### Charts

Map chart semantics consistently:

- Evergreen `#2f6b57`: primary or verified result;
- Muted `#52615b` or evergreen tint: baseline and context;
- Brass `#d7a348`: human-intervention annotation;
- Danger `#b84242`: failure or unresolved risk;
- dashed evergreen: forecast or provisional period;
- Sage/Quiet Border: inactive context and gridlines.

Use evergreen tints `#598979`, `#82a69a`, `#acc4bc`, and `#d5e1dd` when a
single-hue comparison needs additional levels. Do not introduce a rainbow
palette. Split a chart when more than four series are simultaneously important.

Prefer horizontal bars for long category labels. Sort by value unless sequence
matters. Start quantitative bars at zero. Use direct value labels and square bar
ends.

Use a 2-2.5pt line for a primary trend, a thinner muted line for a benchmark,
and dashes for forecast. Label series directly near their endpoints. Do not
smooth lines when smoothing could imply unmeasured values.

Use pie or donut charts only for a genuine part-to-whole comparison with two to
four categories that sum meaningfully to 100%. Otherwise use bars.

Show unit, period, denominator or comparison, actual/forecast/target status,
and source. Do not present a naked percentage or qualitative phrase as a KPI.

Keep data labels at 14-16pt, category labels at 13-15pt, axis labels at 12pt or
larger, and sources at 9-11pt. Use only subtle value-axis gridlines. Remove the
legend for a single series and avoid repeating the slide title inside the chart.

### Tables

Use tables as reviewed records, not spreadsheet screenshots. Keep roughly six
columns and eight visible rows as a practical maximum. Split or filter larger
tables.

Left-align text, right-align numbers, and use tabular numerals. Use no vertical
rules by default. Use fine horizontal separators, a quiet sage or desk header,
14-16pt body text, and 12-14pt column headings.

Use sage fill for a selected row, evergreen text or marker for verified/pass,
brass marker for expert-reviewed or changed, and danger text or marker for
failed/unresolved. Do not fill the entire table with status colors. Avoid zebra
striping unless row tracking is genuinely difficult.

Use `—` for unavailable data rather than zero. Put sample size, period,
definitions, and source directly below the table.

### Diagrams

Use a diagram only when position, sequence, containment, or connection explains
something better than prose.

Choose one reading direction. Use no more than four nodes per row and roughly
eight visible nodes per diagram. Use one consistent node shape, 1-1.5pt
connectors, orthogonal routes where possible, and arrowheads only where
direction matters. Put connectors behind nodes and avoid crossings.

Use white or sage nodes with Quiet Border and a 4-6px-equivalent radius. Use no
shadow by default. Keep node titles at 14-16pt and avoid paragraphs inside
nodes.

Use containment only for a real boundary and limit nesting to two levels. Use
icons only when they distinguish real entity types. Do not use brains, robots,
gears, lightning, or magic wands as generic AI symbols.

Keep charts, tables, diagram shapes, connectors, annotations, and text editable
wherever practical. Prefer native PowerPoint objects, then SVG geometry with
native text, then a high-resolution raster with editable labels outside it.

## 7. Deck rhythm

Track every slide using the rhythm ledger defined in `layout-contracts.md`.
Vary evidence shape and scale without changing the brand system.

Use these starting surface ranges:

- Desk/white: 60-75%;
- Sage: 10-20%;
- Ink: 10-20%;
- Evergreen: 0-10%.

Do not repeat the same layout more than twice in sequence. Review a run of more
than three identical anchor types, three dense slides, or two dark surfaces.
Allow exceptions only when a real sequence benefits from stable framing.

Create rhythm by changing one or two meaningful dimensions at a time: claim to
evidence, screenshot to interpretation, dense table to open conclusion, or
light artifact to dark statement. Do not change typography, color semantics,
shape language, and layout simultaneously.

Keep safe margins, type roles, color semantics, footer position, screenshot
framing, source formatting, chart language, diagram connectors, and artifact
radius stable.

Bias prospect sales decks toward standard density, product screenshots,
comparisons, and expert annotations. Bias investor decks toward
standard-to-dense evidence, charts, tables, product proof, and stronger source
definitions. Do not create separate brand styles.

Use no transition by default, simple Fade for ordinary progression, and Morph
only when the same meaningful object changes state. Never require animation to
understand a slide.

## 8. Anti-patterns

Reject these patterns unless the user explicitly requests and justifies them:

- purple or electric-blue AI gradients;
- glow, glass, aurora, particle, or floating-orb decoration;
- a centered title followed by three equal cards;
- four equal KPI tiles plus a donut chart;
- a tiny uppercase eyebrow on every slide;
- a rounded container around every paragraph;
- an icon above every heading;
- device mockups, perspective tilt, reflections, or floating screenshots;
- random accent colors or multicolored icons;
- brass used like decorative gold;
- qualitative copy presented as a giant metric;
- 3D charts, gauges, radar charts, decorative bubbles, or rainbow series;
- circular-arrow processes used for every workflow;
- spaghetti architecture diagrams;
- stock or generated imagery that could be mistaken for customer evidence;
- shrinking text until overloaded content technically fits;
- changing layout families on every slide merely to create variety;
- repeating one layout throughout merely to create consistency.

## 9. Research influences

Maintain Codeer's own visual identity while preserving the strongest structural
lessons from:

- [Huashu Design](https://github.com/alchaincyf/huashu-design): HTML-first
  craft, editable-output planning, and validating a small showcase before
  scaling;
- [Frontend Slides](https://github.com/zarazhangrui/frontend-slides): visual
  style discovery, fixed-stage rendering, and preserving one spacing/component
  grammar;
- [Guizang PPT Skill](https://github.com/op7418/guizang-ppt-skill): locked
  layout discipline, stable image ratios, semantic screenshot framing, and
  validator-backed constraints;
- [presentation-skill](https://github.com/siril9/presentation-skill):
  source-first editable PPTX generation, semantic layout roles, contact-sheet
  review, and geometric plus rendered QA.

Do not copy their default aesthetics, story structures, or component catalogs.
