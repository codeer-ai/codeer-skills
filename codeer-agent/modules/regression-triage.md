# Version-Aware Result and Regression Triage

Use this module after an Eval run has produced results that need organization
or comparison. It connects an exact Agent-version diff and a predeclared impact
hypothesis with observed case/evaluator deltas. It identifies expected
improvements, residual failures, new regressions, stable controls, comparison
breaks, and useful failure clusters before deeper diagnosis.

This module does not assign the final causal owner, design a repair, launch an
additional run, or authorize a change. Send every non-perfect dynamic result to
[eval-debug.md](eval-debug.md). Send accepted causal findings that warrant a
change to [repair-planner.md](repair-planner.md).

---

## When to use

Use triage:

- after the first full baseline to organize result clusters; because no prior
  comparable Agent exists, call this **baseline result triage**, not regression
  attribution;
- after a post-change focused impact run;
- after a full assigned-pair regression; or
- across established batches when a common prior comparison point exists.

For a small run whose results fit one coherent diagnosis, Eval Debug may perform
the organization inline. Do not create a separate triage step when it would add
handoff cost without changing the decision.

---

## Step 1 — Pin both comparison contexts

Read or recover the prior and current evidence packets:

- exact Agent ID, AgentHistory/version, status, model, `response_mode`, system
  prompt, Tools, handoff settings, KB attachments and snapshot IDs;
- the reviewable Agent/configuration diff, grouped by changed owner;
- case IDs and inputs, expected outputs, rubrics, evaluator assignments,
  evaluator templates, judge-model fingerprints, and run selection;
- generated responses, completion state, Tool and retrieval traces, evaluator
  scores and reasons, and planned-versus-completed pair counts; and
- the pinned baseline or focused pre-change export used as the comparison.

Do not compare labels, aggregate scores, or "latest" objects without resolving
them to exact versions and pairs. Missing prior evidence permits current-run
triage but lowers or removes change attribution.

### Comparison validity

Record whether each pair is directly comparable, qualitatively comparable, or
not comparable.

- A judge-model or evaluator-template change establishes a new baseline.
- Changing the Agent and evaluator together removes Agent-effect attribution.
- A changed case, expected output, rubric, or assignment may still support a
  qualitative behavior comparison, but its score delta is not a clean
  regression measure.
- Missing, duplicated, or incomplete pairs are execution or coverage findings,
  not passes.
- Stochastic behavior may require repeated trials planned by Repair Planner;
  one flip does not establish a stable improvement or regression.

---

## Step 2 — Read the pre-change impact hypothesis

Before a repair is applied, [repair-planner.md](repair-planner.md) should state:

- the changed owner and intended Agent decision or action-policy change;
- the observable result expected to move and in which direction;
- the affected cases and evaluator pairs;
- nearby boundaries and previously passing impacted cases; and
- negative controls or protected behaviors expected to remain stable.

Use that map as the primary comparison frame. If it does not exist, reconstruct
the smallest plausible map from the approved diff, label it post hoc, and lower
attribution confidence. Do not redefine the expected impact after seeing the
scores merely to make the change appear successful.

---

## Step 3 — Match and classify result deltas

Match exact case/evaluator pairs first, then compare the response and trace
evidence rather than relying only on score changes. Useful classifications are:

- **expected improvement** — a predicted failure resolves and the relevant
  behavior or trace changes in the expected direction;
- **residual failure** — the targeted mechanism or consequence remains;
- **new regression** — a previously passing or acceptable pair now fails;
- **stable protected behavior** — a control or impacted passing pair remains
  acceptable;
- **behavior delta without score delta** — the output or trace changed but the
  evaluator score did not, which may expose evaluator insensitivity;
- **score delta without supported behavior delta** — possible judge noise,
  rubric ambiguity, or hidden evidence;
- **incomplete or mismatched result** — the planned pair is absent, duplicated,
  or bound to a different version or evaluator context; and
- **not comparable** — the harness changed enough to require a new baseline.

Cluster deltas by the Agent decision, changed owner, failure signature, Tool or
retrieval path, source family, boundary, or evaluator evidence contract. Do not
group them only because their topics or numeric scores look similar.

---

## Step 4 — State attribution at the supported level

Keep three levels distinct:

1. **Observed delta** — state the exact Agent/configuration change and exact
   result difference without claiming that one caused the other.
2. **Supported attribution** — use only when the impact was predicted, the test
   harness is comparable, the changed owner plausibly controls the behavior,
   relevant response or trace evidence shows the mechanism, protected controls
   remain stable, and material alternatives have been checked.
3. **Unresolved attribution** — use when multiple owners changed, evaluator or
   judge context changed, controls also moved, evidence is incomplete, or
   stochastic variation remains plausible.

Even supported Eval attribution establishes an effect on the tested immediate
behavior, not a delayed production outcome such as conversion, retention,
revenue, or long-term task success. Name the production or experimental evidence
needed for that stronger claim.

---

## Parallel triage

When there are several independent impact areas or delta clusters, the parent
Agent may give read-only sub-agents the same version diff, impact hypothesis,
comparison fingerprints, and matched result table. Partition by impact area or
failure mechanism, not arbitrary row count. Reserve selected controls or
possible evaluator-noise cases for cross-cutting review when useful.

Each worker reports matched pairs, observed deltas, trace evidence, comparison
validity, classification, attribution level, alternatives, and the cluster it
should enter for Eval Debug. The parent reconciles shared causes, checks that
every planned pair is accounted for exactly once, and verifies high-consequence
claims against the original evidence. Worker agreement does not make an
uncontrolled comparison causal.

---

## Report and route

Lead with the comparison scope and whether the run supports baseline triage,
qualitative change analysis, or Agent-effect attribution. Then make the Agent
diff, expected impact, observed delta, control behavior, comparison breaks, and
remaining uncertainty reviewable in the clearest format for the task.

Route:

- non-perfect responses, Tool/retrieval traces, or evaluator results—and
  suspicious perfect scores whose behavior or trace delta exposes evaluator
  insensitivity—to **eval-debug**;
- suite-wide static mismatches to **static-audit**;
- accepted implementation or eval-system findings to **repair-planner**;
- broader keep, merge, retire, allocation, representativeness, or evaluator
  value questions to [eval-portfolio.md](eval-portfolio.md); and
- a clean focused comparison to the required full regression rather than
  treating the focused set as release evidence.
