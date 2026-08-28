# Eval Portfolio Value Optimization

Use this module when the Agent needs a deliberate decision about which cases,
case/evaluator pairs, or evaluators create enough evidence to justify their run
and maintenance cost. Its objective is to maximize decision value while
preserving accepted outcomes and material risk boundaries—not to maximize pass
rate, evaluator count, suite size, or the number of deleted cases.

This is a read-only design and governance module. It may propose a keep, merge,
retire, add, reassign, or recalibrate target state, but it does not author the
final cases, mutate server state, or declare its own proposal valid. Use
[eval-cases.md](eval-cases.md) for case and rubric authoring,
[repair-planner.md](repair-planner.md) for a maintained-suite diff, and
[static-audit.md](static-audit.md) before the next applicable run.

---

## When to use

Use Eval Portfolio Optimization when a named decision requires one or more of:

- evaluator architecture for a material behavior that current evaluators
  cannot observe or distinguish;
- a minimum-sufficient acceptance or regression portfolio across several
  scenarios, boundaries, or evaluator dimensions;
- removal or consolidation of redundant cases and pairs;
- review of false passes, false failures, evaluator saturation, judge
  instability, or low incremental information;
- production History or Query Distribution evidence that changes allocation or
  exposes drift;
- a focused impact set for a material change; or
- periodic maintenance because suite size, review effort, or run cost has
  become consequential.

Do not require this module for the first small core-scenario acceptance set when
[eval-cases.md](eval-cases.md) can select it directly. Monitoring here means an
evidence review when invoked; it does not create a background daemon or
authorize unattended changes.

---

## Evidence packet

Use the smallest evidence set that supports the portfolio decision:

- accepted Behavior Contract outcomes, decision policies, alternative
  outcomes, guardrails, and material boundaries;
- optional accepted Query Distribution, concrete examples, evidence window,
  and allocation when representativeness or drift is in scope;
- current cases, expected outputs, rubrics, labels, evaluator assignments,
  templates, judge-model fingerprints, and actual evidence variables;
- comparable baseline, focused, regression, and calibration results, including
  false-pass or false-fail findings from Eval Debug;
- selected production failures and successful patterns with their sampling
  limits;
- Tool, retrieval, output, and platform evidence contracts; and
- known run cost, reviewer effort, or maintenance burden when available.

Do not infer evaluator value, production frequency, or redundancy from names or
one aggregate score. Missing evidence is a limitation, not permission to invent
precision. Without actual run-cost, reviewer-effort, or maintenance evidence,
recommend only relative simplification; do not quantify monetary or labor
savings.

---

## Step 1 — Define the decision and coverage universe

Name the decision the portfolio must support, such as first-publish acceptance,
repair verification, release regression, evaluator calibration, production
drift review, or maintenance reduction.

Define coverage in terms of material **decision consequences**, not document
length, wording variants, or a cross-product of every query and challenge. The
universe may include:

- core decision policies and acceptable alternative outcomes;
- high-consequence consent, authority, Tool, handoff, or source boundaries;
- distinct failure mechanisms that need reproduction protection;
- successful behaviors that a planned change could regress;
- common or allocated customer tasks supported by an accepted distribution;
  and
- nearby boundaries or generalization probes needed for a current causal
  hypothesis.

Keep challenge, channel, tone, disclosure order, and paraphrase variation only
when it tests generalization, a distinct failure mechanism, or a meaningful
boundary. Do not multiply every behavior by every variation.

---

## Step 2 — Evaluate evaluator value

For every existing or proposed evaluator dimension, ask:

1. Which material behavior or failure consequence can it detect?
2. Which exact input—such as `{output}` or `{tool_steps}`—carries the evidence?
3. Can the runtime produce that evidence and can the evaluator observe it?
4. Which current pair already detects the same consequence?
5. Would its result change a repair, publish, rollback, routing, or monitoring
   decision?
6. What calibration, judge-noise, maintenance, and model-call cost does it add?

Recommend a more specific or custom evaluator only when an important distinct
failure is not observable through the existing evaluator contracts. Prefer a
self-sufficient rubric, correct assignment, visible criterion, or better
calibration when those solve the problem without a new evaluator.

Review evidence of:

- false passes and false failures confirmed against source truth and the
  Behavior Contract;
- repeated score instability under a stable response and harness;
- criteria that cannot see their required evidence;
- saturation where an evaluator no longer distinguishes meaningful behavior;
- overlap where two pairs catch no distinct material failure; and
- evaluator disagreement caused by incompatible requirements.

Do not collapse genuinely distinct evidence dimensions merely to reduce pair
count. Do not label an evaluator unreliable from one disputed result; route the
pair through Eval Debug or plan calibration evidence when needed. An evaluator
template or judge-model change establishes a new baseline and must be separated
from an Agent change if Agent-effect attribution matters.

---

## Step 3 — Optimize cases and pairs

Map each candidate case/evaluator pair to the decision consequences it can
observe. Then propose the smallest set that preserves the required universe and
the evidence quality needed for the named decision.

Prefer to keep:

- a stable core acceptance path;
- material risk and nearby-boundary sentinels;
- a distinct historical failure mechanism that could recur;
- successful protection behavior exposed to the planned change;
- supported common-demand coverage and deliberate high-consequence reserves;
  and
- pairs with unique observable failure value.

Candidates to merge or retire include wording duplicates, pairs with no unique
decision consequence, obsolete exploratory probes, cases whose source truth is
no longer valid, and assignments whose evaluator cannot observe the criterion.
A case may cover more than one consequence only when the expected behavior and
rubrics remain clear and judgeable. Preserve the provenance and reason for any
historical sentinel proposed for retirement so the user can assess recurrence
risk.

Keep portfolio layers distinct when useful:

| Layer | Purpose | Typical lifecycle |
| --- | --- | --- |
| Core acceptance | Accepted core behavior and alternative outcome | Stable |
| Risk boundaries | Consent, authority, Tool, source, and handoff consequences | Stable while the risk exists |
| Distribution slice | Supported common-demand or cohort coverage | Revisit when evidence drifts |
| Change impact | Reproduction, generalization, boundary, controls, and protected passes | Per material change |
| Exploratory probes | Distinguish a new History or Eval Debug hypothesis | Promote, merge, or retire after learning |

Do not keep every exploratory probe in every full sweep. Conversely, a focused
impact set does not replace the required full assigned-pair regression before a
release decision.

### Representativeness boundary

Use traffic-weighted or cohort-representative language only when a supported
sampling frame or accepted Query Distribution justifies it. Without that
evidence, call the result a **minimum-sufficient coverage set** and report it by
meaningful slices such as core, boundary, risk, or exploratory. Never infer
production prevalence from case counts, labels, or balanced-looking categories.
This module does not estimate or persist a new demand model; use
[query-distribution.md](query-distribution.md) when the decision requires that
evidence.

---

## Parallel portfolio review

The parent Agent may delegate the whole bounded review to one read-only
Eval-portfolio worker. For a larger suite, independent workers may inspect:

- Behavior Contract and optional distribution coverage;
- evaluator signal, observability, and calibration evidence; and
- case/pair redundancy, historical sentinel value, and maintenance cost.

All workers receive the same suite snapshot, comparison fingerprints, coverage
universe, and decision objective. They return evidence-backed keep, merge,
retire, add, or recalibrate candidates with unique value, lost-coverage risk,
uncertainty, and required validation. The parent reconciles overlaps and checks
that the proposed union still covers every material consequence. Savings are
not valid if they silently remove an accepted outcome or high-consequence
boundary.

---

## Present the proposal and hand off

Make the current and proposed portfolio reviewable. Show, when material:

- the decision objective and evidence scope;
- current versus proposed case and assigned-pair counts;
- evaluator dimensions and observable evidence contracts;
- keep, merge, retire, add, reassign, and recalibrate proposals;
- unique coverage preserved, coverage intentionally changed, and risks;
- expected run or maintenance savings without unsupported precision;
- comparison breaks and new-baseline requirements; and
- the smallest validation needed.

For a first portfolio, send the accepted design to **eval-cases** for concrete
case and rubric review. For a maintained suite, send accepted findings to
**repair-planner**, then use **eval-cases** or the evaluator-owning CLI flow to
produce a reviewable diff. After any approved change, run Static Audit and the
planned focused or full checks. Use
[regression-triage.md](regression-triage.md) only across comparable contexts;
do not present a cheaper or smaller suite as better until it still supports the
named decision.
