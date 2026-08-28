# Optional Customer Query Distribution

Use this module only when an active decision requires a separate model of what
customers ask, how often, how consequential mistakes are, or how a larger Eval
budget should be allocated. Typical triggers are supported first-party demand
evidence, traffic-weighted quality reporting, capacity or latency planning,
hot-path residency, portfolio prioritization across several scenarios, or
production-drift analysis. Do not require a Query Distribution to create the
first Behavior Contract or its core-scenario Evals.

It may be used after Scope Alignment to inform core-scenario selection, after a
Behavior Contract to allocate broader coverage, or during History Analysis when
production evidence may have changed a previously accepted model.

The Query Distribution is descriptive. The Behavior Contract is normative:

- `.codeer/design/query_distribution.csv` records query types, demand bands,
  risk, and target eval-case counts;
- `.codeer/design/query_examples.csv` records concrete customer inputs linked
  to those query types;
- `.codeer/design/behavior_contract.md` records how the Agent is intended to
  behave; and
- eval cases select from and extend the accepted model to test observable
  behavior.

These optional design artifacts are not Codeer server objects or runtime
prompts. Persist them across sessions once accepted. Their absence is not a
design gap when no current decision needs demand or allocation evidence. Do not
copy raw sensitive conversations into them.

---

## Minimum-sufficient rule

First decide whether demand or allocation analysis itself has a named
downstream use. If not, stop and proceed with the core Scenario and Behavior
Contract. If it does, choose the analysis-only or persistent path below. When a
persistent distribution is justified, the default schema is intentionally
small. Do not add a field because it might be useful later. Add one only when a
named downstream decision, review, or tool will use it now.

Keep document-level scope, evidence limits, exclusions, or review dates in the
optional `.codeer/current/query_distribution_notes.md` rather than repeating
them on every row. Add optional row fields such as `observed_share`, `channel`,
`source_ref`, or `notes` only when available evidence and an active decision
make them useful.

---

## Analysis-only versus persistent model

If the current decision needs only a bounded one-off estimate or comparison,
state the evidence scope, method, uncertainty, and result in the analysis. Do
not create canonical CSVs merely because this module was used.

Persist a Query Distribution only when later sessions, Eval allocation,
capacity or hot-path planning, weighted reporting, or drift comparison need a
reusable accepted model. In that case, follow the artifact rule below.

## Persistent artifact rule

Draft new or revised content at:

- `.codeer/current/local_draft_query_distribution.csv`
- `.codeer/current/local_draft_query_examples.csv`

Present both complete artifacts or a clear before/after diff and obtain user
acceptance before replacing either canonical file.

Use the schema in
[../reference/query-distribution/output-schema.md](../reference/query-distribution/output-schema.md).
Validate the pair with:

```bash
python <codeer-agent-skill-dir>/scripts/validate_eval_artifacts.py \
  .codeer/current/local_draft_query_distribution.csv \
  .codeer/current/local_draft_query_examples.csv
```

The examples are design inputs for [eval-cases.md](eval-cases.md), not reviewed
eval cases and not expected answers or rubrics.

---

## Step 1 — Frame only the material scope

Start from Scope Alignment and any accepted Behavior Contract. Name the demand,
allocation, capacity, hot-path, or drift decision the model must support.
Establish or infer the company, product, operating model, customer journeys,
locale, supported Agent actions, exclusions, and consequence owner. Persist a
separate notes file only when material evidence limits or scope boundaries need
to survive the session.

Read
[../reference/query-distribution/methodology.md](../reference/query-distribution/methodology.md)
and classify the operation with
[../reference/query-distribution/operating-models.md](../reference/query-distribution/operating-models.md).
Use
[../reference/query-distribution/task-archetype-index.md](../reference/query-distribution/task-archetype-index.md)
to load only relevant task families.

---

## Step 2 — Define behaviorally distinct query types

Use one row per customer task and journey state that materially changes the
correct answer, next move, Tool choice, authority boundary, or risk policy.
Customer-outcome language describes the task here; it does not establish a
normative runtime outcome or guardrail before the Behavior Contract is
accepted.

- Write `customer_task` in plain customer-outcome language.
- Fill `journey_state` only when state changes the correct handling; otherwise
  leave it blank.
- Use `demand_band` for ordinal demand: `core`, `common`, `occasional`, `rare`,
  or `unknown`.
- Use `risk_level` for consequence severity: `normal`, `elevated`, `high`, or
  `critical`.
- Set `target_cases` to the intended integer allocation in the acceptance eval
  portfolio. It is not a traffic estimate.

Do not create a taxonomy column for every possible axis. Split a query type
only when the distinction changes correct handling. Put challenge, fairness,
or sampling variation that does not change the intended policy in examples,
Eval metadata, or the relevant analysis design instead.

### Entry conditions and operational profiles

Do not create Personas or profile categories by default. Distinguish the
customer's current intention, the observable condition in which they enter this
task, and any more persistent profile claim:

- **intention** — the customer work to complete now;
- **entry condition** — currently supplied context, existing work object,
  journey or readiness state, urgency, constraint, risk, or authority; and
- **operational profile** — a repeatable customer distinction supported by
  evidence across tasks or conversations.

Promote an entry condition or operational profile into the distribution only
when an observable distinction changes correct handling. Use
`journey_state` when the state is part of a behaviorally distinct task row. If
the same task and policy still apply, keep concrete variation in
`query_examples.csv` or the Eval portfolio instead of multiplying every query
type by every possible profile. When a distinction matters only for comparing
outcomes, fairness, or heterogeneous effects, treat it as an analytic stratum
in that analysis or sampling design; it is not an operational profile, Query
Type, or Behavior Contract branch.

Treat Persona narratives, inferred personality, motivation, sophistication,
demographics, or stylistic preference as product-research context rather than
operational distribution fields unless first-party evidence establishes an
observable distinction that changes correct handling. One user may enter
different tasks in different states, so a persistent profile never substitutes
for the current entry condition.

Prefer evidence in this order:

1. target first-party conversations;
2. target operational records;
3. target public surfaces;
4. close industry proxies;
5. cross-industry structural sources;
6. expert construction; and
7. synthetic expansion after a supported base pattern exists.

Use public-web research only when local or first-party evidence does not
sufficiently establish an important task, boundary, or consequence. Evidence
that proves a query exists does not prove its production frequency; use
`unknown` when demand is not supportable.

---

## Step 3 — Add concrete query examples

Keep examples in the separate one-to-many `query_examples.csv`. Every query
type must have at least one concrete example, and every type with
`target_cases > 0` must have at least one `representative` example.

- `observed`: deidentified from target first-party data.
- `adapted`: grounded in a real source but rewritten for the target context.
- `constructed`: deliberately authored to cover a supported task or boundary.

Use `purpose` to distinguish `representative`, `boundary`, and `risk` examples.
Preserve full prior turns in `input` when the latest user message cannot be
interpreted correctly on its own. Deidentify sensitive data and do not retain
more source text than needed.

Use examples to preserve materially different observable entry conditions
without prematurely creating new query types or profiles. An example variation
is useful when it tests whether the same policy generalizes, identifies a
nearby decision boundary, or provides evidence that handling should actually
diverge.

Do not infer demand from example count. Do not multiply every task by every
channel, tone, risk, and challenge. Add an example only when it supplies a
meaningfully different input, state, boundary, or failure mechanism.

---

## Step 4 — Review, persist, and hand off

Review whether:

- the query types cover the material customer work without redundant taxonomy;
- demand and risk are independently judged;
- target case counts preserve core demand and deliberate high-consequence
  coverage;
- each query type has concrete examples; and
- material uncertainty is visible without becoming unused row metadata.

After user acceptance, persist both canonical CSVs. Then use them only in the
downstream decisions that justified their creation:

1. **consultative-guidance** may use query types, states, risks, and examples to
   choose or expand behaviorally distinct scenarios;
2. **eval-cases** uses `target_cases` and examples to design the acceptance
   portfolio; and
3. **agent-settings** uses supported demand and miss consequence for hot-path
   decisions. Do not copy allocation counts or speculative frequency into the
   runtime prompt.

---

## Production-history updates

History Analysis must read both canonical CSVs before claiming drift against an
existing distribution. When they do not exist, create them only if the current
analysis needs a persistent demand or allocation model; do not reconstruct them
merely to analyze behavior. A new conversation may justify an Eval probe
without creating or changing a distribution. Revise a distribution row only
when evidence materially changes the customer task, journey state, demand band,
risk level, or target case allocation.

Present the evidence limits and before/after diff for user acceptance. Revise
the Behavior Contract only when the appropriate customer experience or stable
risk policy changes. Revise Agent Settings, KB, or Tools only after any
contract change is accepted and expressed in eval cases.

Keep revision history in Git or another project history when available. The
canonical files describe the current accepted model; do not accumulate raw
histories or stale snapshots inside them.
