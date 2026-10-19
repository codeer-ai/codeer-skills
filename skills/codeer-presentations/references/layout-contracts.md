# Codeer Presentation Layout Contracts

Use this reference to select and implement slide geometry. Treat these contracts
as semantic roles, not storyline templates.

## Contents

1. Canvas and grid
2. Placeholder contract
3. Registered layouts
4. Master-slide boundaries
5. Rhythm ledger
6. Layout selection and overflow
7. Future template architecture

## 1. Canvas and grid

Use PowerPoint widescreen geometry:

| Property | Value |
|---|---:|
| Canvas | 13.333 x 7.5in |
| Left safe margin | 0.72in |
| Right safe margin | 0.72in |
| Top safe margin | 0.50in |
| Bottom safe margin | 0.52in |
| Grid | 12 columns |
| Column gutter | 0.18in |
| Standard title reserve | 0.95-1.15in |
| Minimum title-to-content gap | 0.26in |

Use the slide coordinate system with `(0,0)` at the top left. Keep all editable
content within:

```text
x: 0.72 to 12.613
y: 0.50 to 6.98
```

Reserve the lowest part of the safe region for source, caption, and page-number
content when the layout requires them. Do not let media or tables collide with
that region.

Use the approved spacing tokens from `visual-system.md`. Do not inject arbitrary
micro-spacing to make one crowded slide pass.

## 2. Placeholder contract

Use these semantic placeholder names in source and generated layouts:

| Name | Purpose |
|---|---|
| `title` | Unique visible slide title or conclusion |
| `subtitle` | Optional supporting line |
| `body` | Primary explanation |
| `evidence` | Main chart, screenshot, table, or proof object |
| `media` | Photograph, screenshot, or external figure |
| `takeaway` | Short interpretation of the evidence |
| `caption` | What an artifact or image shows |
| `source` | Provenance, date, sample, or definition |
| `page_number` | Page index on content slides |
| `contact` | Closing contact information |

Not every layout uses every placeholder. Keep placeholder reading order aligned
with visual reading order.

Give every slide a unique title. If the visual design suppresses a visible
title, still provide a semantic title for accessibility and document navigation.

Permit no more than two title lines. Set title placeholders to their maximum
approved bounds and treat overflow as a source error. Do not use automatic text
shrink below the minimum typography scale.

Keep `caption` and `source` separate from `body`. Keep media placeholders clear
of master-owned decoration. Require alt text for meaningful images, charts, and
diagrams.

## 3. Registered layouts

Use these twelve visible PowerPoint layouts derived from ten geometry contracts.

### `COVER.LIGHT`

Use for a quiet prospect-facing opener.

- Surface: desk or white.
- Place `title` in a dominant left-aligned region.
- Place `subtitle` below with a clear 24-36pt gap.
- Allow one optional product artifact or restrained photograph.
- Show the Codeer wordmark.
- Omit page number and routine footer.

### `COVER.INK`

Use for a stronger investor or high-stakes opener.

- Preserve the `COVER.LIGHT` geometry family.
- Use ink background and white type.
- Use brass only for a real expert-judgment phrase or marker.
- Allow one evidence marker or artifact; do not add decorative AI imagery.

### `STATEMENT.LIGHT`

Use for an important conclusion or transition.

- Use desk, white, or sage surface.
- Set one statement in the judgment voice.
- Keep 40-60% intentional negative space.
- Allow one short supporting line or source.
- Do not add decorative cards.

### `STATEMENT.INK`

Use for a decisive conclusion that earns emphasis.

- Use ink background, white statement text, and optional brass annotation.
- Keep geometry aligned with `STATEMENT.LIGHT`.
- Include a source when the statement contains a factual or measured claim.

### `CANVAS`

Use as the flexible default content slide.

- Reserve the standard title stack at the top.
- Expose one open 12-column content region.
- Require the slide source to declare a visual anchor.
- Do not use `CANVAS` as permission for arbitrary coordinates.

### `EVIDENCE.LEFT`

Use for explanation on the left and evidence on the right.

- Use a 5/7 or 4/8 split based on evidence density.
- Align both regions to the same top or bottom baseline deliberately.
- Keep `evidence` dominant.
- Place `caption` and `source` with the evidence.

### `EVIDENCE.RIGHT`

Use for evidence on the left and interpretation on the right.

- Use a 7/5 or 8/4 split.
- Keep the evidence region dominant.
- Use `takeaway` for interpretation rather than a second long narrative block.
- Preserve the same gutter and baseline logic as `EVIDENCE.LEFT`.

### `ARTIFACT.FULL`

Use for a large screenshot, conversation, diagram, document, or image.

- Reserve a compact title region.
- Give `media` or `evidence` most of the content area.
- Keep caption and source outside the artifact.
- Use stable screenshot ratios and framing.
- Do not float unrelated annotations around all four sides.

### `COMPARE`

Use only for genuine equivalent peers.

- Use a shared title and a 6/6 content split.
- Match the two regions' scale, crop, and internal hierarchy.
- Use the same measurement units and definitions.
- Do not use a symmetric comparison when one side is merely supporting detail.

### `DATA.FOCUS`

Use for one chart or metric plus interpretation.

- Use an 8/4 evidence-to-interpretation split or a large central data object.
- Keep the chart editable when practical.
- Show unit, period, comparison, and source.
- Use one dominant conclusion; do not turn it into four KPI cards.

### `TABLE.FULL`

Use for an evidence table or compact matrix.

- Reserve a standard title stack.
- Give the table the main content region.
- Reserve a narrow interpretation or source band below or beside it.
- Enforce table density and minimum text size from `visual-system.md`.

### `CLOSING.INK`

Use for the final statement and contact information.

- Use ink background with white text.
- Show the Codeer wordmark and `contact`.
- Keep the final statement dominant.
- Do not repeat the entire cover or add a generic "Thank you" as the only idea.

## 4. Master-slide boundaries

Put these elements in the PowerPoint theme or master:

- theme colors and Latin/East Asian theme fonts;
- slide size, safe margins, and layout placeholders;
- light, sage, ink, and evergreen background styles;
- page-number and source/caption positions;
- reading order and default paragraph behavior;
- logo placement on cover and closing layouts;
- non-editable background and footer elements.

Keep these elements out of the master:

- sample sales or investor copy;
- storyline, section order, or agenda logic;
- decorative card grids;
- icons, diagram arrows, charts, or fake data;
- product screenshots and customer logos;
- reusable explanatory components not yet proven by real slides;
- photographs, generated imagery, and ornamental lines.

Show the Codeer wordmark confidently on the cover and closing slide. Do not
repeat a large logo on every content slide. Keep content-slide chrome quiet.

## 5. Rhythm ledger

Record one ledger item per slide before rendering:

```yaml
- slide: 5
  layout: EVIDENCE.RIGHT
  surface: desk
  density: standard
  anchor: product
  scale: evidence
  accent: brass
```

Use these controlled values:

| Field | Values |
|---|---|
| `layout` | Any registered layout ID |
| `surface` | `desk`, `sage`, `ink`, `evergreen` |
| `density` | `open`, `standard`, `dense` |
| `anchor` | `type`, `product`, `data`, `table`, `diagram`, `photo` |
| `scale` | `statement`, `evidence`, `detail` |
| `accent` | `none`, `evergreen`, `brass`, `danger` |

Warn when:

```text
same_layout_run > 2
same_anchor_run > 3
dense_run > 3
dark_surface_run > 2
brass_dominant_share > 25%
evergreen_surface_share > 10%
missing_visual_anchor == true
style_override_count > 0
```

Treat these as warnings unless the exception is clearly unjustified. Allow a
stable screenshot sequence or matched comparison to repeat framing when that
continuity helps interpretation.

Hard-fail unregistered layouts, undeclared colors, theme-font drift, inconsistent
slide size, or manual geometry outside the safe area.

## 6. Layout selection and overflow

Select a layout from the evidence shape:

- one large product artifact -> `ARTIFACT.FULL`;
- evidence plus interpretation -> `EVIDENCE.LEFT` or `EVIDENCE.RIGHT`;
- equivalent peers -> `COMPARE`;
- one chart or decision-carrying metric -> `DATA.FOCUS`;
- compact records or criteria -> `TABLE.FULL`;
- one conclusion with deliberate space -> `STATEMENT.*`;
- content without a more specific shape -> `CANVAS`.

Do not select from storyline position alone. Do not use a statement layout to
hide missing evidence or a table layout to avoid editing overloaded prose.

When content overflows:

1. remove duplicate labels or repeated explanation;
2. crop or enlarge the real evidence region;
3. choose a better registered layout;
4. split the content across slides;
5. rewrite for clarity only when meaning remains intact.

Never shrink below the visual-system minimums. Never cross safe margins or
cover the source/footer region.

## 7. Future template architecture

When real slide work proves the system, build these resources:

```text
assets/
  codeer-deck-template.potx
  fonts/

scripts/
  theme.*
  layouts.*
  render-and-check.*

references/
  accepted-components.*
```

Keep a machine-readable layout definition as the canonical source. Treat the
`.potx` or `.pptx` as a compiled, human-usable artifact rather than the only
place where layout knowledge exists.

Add a component only after a real accepted slide establishes it and another
slide demonstrates recurrence. Keep the component's source, rendered reference,
intended use, and failure modes together.
