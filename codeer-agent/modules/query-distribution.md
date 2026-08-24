# Customer Query Distribution

Use this module after Scope Alignment and before Consultative Customer Guidance
to build the persistent evidence model of what customer tasks and conversation
states are expected. Reuse it during History Analysis when production evidence
may have changed that model.

The Query Distribution is descriptive and probabilistic. The Behavior Contract
is normative. Keep them separate:

- `.codeer/design/query_distribution.csv` records expected demand, risk,
  evidence confidence, and the designed eval allocation;
- `.codeer/design/behavior_contract.md` records how the Agent is intended to
  behave; and
- eval cases instantiate both by sampling the portfolio and testing the
  accepted behavior.

Neither design artifact is a Codeer server object or runtime prompt. Persist
both across sessions. Do not delete the distribution after the initial eval
suite is built, and do not copy raw conversations into either file.

---

## Artifact rule

Draft new or revised distribution content in conversation or at
`.codeer/current/local_draft_query_distribution.csv`. Present the complete
artifact or before/after diff, including evidence limitations, and obtain user
acceptance before replacing the canonical
`.codeer/design/query_distribution.csv`.

Use the schema in
[../reference/query-distribution/output-schema.md](../reference/query-distribution/output-schema.md).
Validate a distribution and candidate pool with:

```bash
python <codeer-agent-skill-dir>/scripts/validate_eval_artifacts.py \
  .codeer/current/local_draft_query_distribution.csv \
  .codeer/current/local_draft_eval_input_candidates.csv
```

The candidate pool is a local design input for [eval-cases.md](eval-cases.md),
not a substitute for reviewed cases and rubrics.

---

## Step 1 — Frame the evidence scope

Start from Scope Alignment. Establish or infer the company, product, operating
models, journeys, channels, geography, language, customer segments, supported
Agent actions, exclusions, and consequence owner.

Record the evidence window and sampling scope. State which channels,
populations, dates, and exclusions are represented, and whether the evidence
contains all conversations or a selected subset such as escalations, feedback,
one campaign, or one customer segment.

Read
[../reference/query-distribution/methodology.md](../reference/query-distribution/methodology.md)
and classify the operation with
[../reference/query-distribution/operating-models.md](../reference/query-distribution/operating-models.md).
Use
[../reference/query-distribution/task-archetype-index.md](../reference/query-distribution/task-archetype-index.md)
to load only the relevant task families.

---

## Step 2 — Use the strongest available demand evidence

Prefer evidence in this order:

1. target first-party conversations;
2. target operational records such as tickets, dispositions, searches,
   escalation reasons, and CRM fields;
3. target public surfaces;
4. close industry proxies;
5. cross-industry structural sources;
6. expert construction; and
7. synthetic expansion after a supported base pattern exists.

### When first-party conversations exist

Use the conversation or customer task as the unit of demand rather than
counting every message as a separate query. Classify the base task, lifecycle
state or transition, meaningful complication, channel, and consequence risk.

- preserve full prior turns in candidate `input_display` when the evaluated
  query depends on them;
- keep the latest evaluated user message in `target_user_query`;
- deduplicate repeated contacts and semantic duplicates without erasing
  distinct lifecycle states or disclosure order;
- identify selection bias, missing channels, seasonality, campaigns, and
  automated or operational noise; and
- report the number of conversations, pages or files, and covered date range
  used for any distribution conclusion.

First-party histories are the strongest available evidence, not automatic
proof of the complete production distribution.

### When first-party conversations do not exist

Build a provisional estimate using current company, industry, operating-model,
channel, and locale evidence. Read
[../reference/query-distribution/public-web-research-playbook.md](../reference/query-distribution/public-web-research-playbook.md)
and browse current sources when required. Prefer ordinal representativeness
bands or ranges; leave `estimated_real_world_share` blank when evidence proves
existence but not frequency.

---

## Step 3 — Separate demand, risk, and eval allocation

Build distribution cells around base tasks and lifecycle transitions before
adding task complications or communication challenges. Keep these axes
independent:

- **estimated real-world demand** — the supported prevalence estimate or
  representativeness band;
- **industry-consequence risk** — severity if the Agent mishandles the task;
- **eval target allocation** — the designed share of the review budget; and
- **challenge** — an interaction mechanism likely to expose a failure.

Read the relevant task modules and
[../reference/query-distribution/patterns/industry-risk.md](../reference/query-distribution/patterns/industry-risk.md).
Apply only relevant patterns from
[../reference/query-distribution/patterns/cross-task-challenges.md](../reference/query-distribution/patterns/cross-task-challenges.md)
and
[../reference/query-distribution/patterns/channel-language.md](../reference/query-distribution/patterns/channel-language.md).

The eval portfolio need not mirror estimated traffic exactly. Preserve
representative core demand and intentionally reserve coverage for rare but
high-consequence cells. Record `overweight_reason` whenever eval allocation
exceeds supported demand.

When a rare or risky cell requires a stable, observable, and behaviorally
distinct policy—such as additional verification, uncertainty disclosure,
restricted action, consent, or handoff—surface that policy decision to
[consultative-guidance.md](consultative-guidance.md). Keep the concrete
scenario, phrasing, and challenge variant in eval coverage rather than turning
the Behavior Contract into an exception catalog.

---

## Step 4 — Review, persist, and hand off

Produce the distribution and a manageable input-candidate pool. Separate
observed facts, reasonable inferences, proposed allocation, and unresolved
gaps. Stop when additional candidates no longer cover a meaningful task,
lifecycle, risk, channel, language, challenge, or evidence-confidence gap.

After user acceptance, persist the canonical distribution. Then:

1. **consultative-guidance** uses it to prioritize likely journeys, default
   initiative and discovery depth, risk policies, and acceptable boundaries;
2. **eval-cases** uses `eval_target_share`, risks, and candidates to design the
   acceptance portfolio; and
3. **agent-settings** uses supported frequency and miss consequence when
   deciding what must remain on the operational hot path. Do not copy traffic
   percentages or speculative estimates into the runtime prompt.

---

## Production-history updates

History Analysis must read the current canonical distribution before claiming
drift. Analyze a declared evidence window and propose a revision only when new
evidence materially changes a task cell, representativeness band, supported
share, channel or segment scope, risk understanding, eval allocation, or an
open gap. One failure or negative conversation normally creates an eval probe,
not a distribution revision.

Present the evidence, sampling limits, and before/after distribution diff for
user acceptance. After an accepted update:

1. update eval allocation and candidate coverage when warranted;
2. revise the Behavior Contract only if the new demand model changes the
   appropriate customer experience or risk policy; and
3. revise Agent Settings, KB, or Tools only after any contract change is
   accepted and expressed in eval cases.

Keep Git history or another project revision history when available. The
canonical file should describe the current accepted model; do not silently
accumulate raw histories or stale snapshots inside it.
