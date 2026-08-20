# Audience-Value Narrative Regression Fixtures

Use these fixtures only when revising or forward-testing the skill. Give a fresh
reviewer the raw task and artifact, not the expected findings. Score semantic
relationships rather than exact wording.

## Contents

1. Feature-heavy buyer deck
2. Click-by-click demo
3. Technical diligence exception
4. Governance-first exception
5. Unsupported outcome numbers
6. Generic CTA
7. Visual-only scope boundary
8. Evaluation rubric

## 1. Feature-heavy buyer deck

Raw artifact:

```text
Audience: customer-service director
Slide sequence:
1. Codeer Agent Platform
2. Prompt Management
3. Knowledge Base
4. Eval System
5. Version Control
6. Continuous Optimization
7. Contact Us
```

Expected behavior:

- Diagnose the sequence as an internal product inventory.
- Establish a recognizable service decision or blocked result before the
  architecture.
- Plan at least one real or clearly labeled representative conversation,
  decision, failure, or correction before generalizing into a product
  framework.
- Attach each retained mechanism to an already established customer question.
- Translate product terms through actors, artifacts, conditions, and decisions.
- Replace the generic closing with a claim-testing next step.

Do not require a fixed number of slides or a fixed customer-service storyline.

## 2. Click-by-click demo

Raw artifact:

```text
Audience: operations lead
Script: Open the Eval tab. Click New Case. Paste the input. Add the expected
answer. Press Run. Open the result. Compare the score. Publish the version.
```

Expected behavior:

- Preserve only interface actions needed to understand the proof.
- Add the audience question, concrete case, visible evidence, operational
  implication, and release condition.
- Avoid claiming time savings, conversion lift, or quality improvement beyond
  what the demonstrated artifact establishes.

## 3. Technical diligence exception

Raw task:

```text
Prepare a five-minute architecture walkthrough for an AI platform engineer who
already accepts the need for evaluation and is deciding whether Codeer's trace,
version, and deployment boundaries fit the existing stack.
```

Expected behavior:

- Permit an architecture- or boundary-first sequence.
- Record that stakes are already accepted and name the technical decision.
- Do not insert a generic emotional pain scene.
- Keep each mechanism tied to the integration or architecture decision.

## 4. Governance-first exception

Raw task:

```text
Draft an opening for a model-risk owner whose policy requires every behavior
change to be attributable, rerunnable, approved, and reversible.
```

Expected behavior:

- Permit control and validation as primary value because governance is the
  declared job-to-be-done.
- Explain the concrete release behavior rather than relying on abstract claims
  such as "complete control" or "zero risk."
- Preserve limitations and avoid absolute certainty.

## 5. Unsupported outcome numbers

Raw artifact:

```text
Codeer cuts response time by 80%, doubles conversion, and saves each agent ten
hours per week. No study, customer measurement, period, sample, or baseline is
available.
```

Expected behavior:

- Remove or explicitly mark all unsupported numbers as unavailable.
- Do not replace them with plausible estimates.
- Use only a bounded qualitative statement supported by visible mechanism or
  label measurement as a proposed next step.

## 6. Generic CTA

Raw artifact:

```text
Central claim: a team can turn its own service judgments into reviewable Agent
behavior before expanding use.
CTA: Contact us to learn more.
```

Expected behavior:

- Identify the CTA-to-claim mismatch.
- Propose a proportionate action using the prospect's cases or decision
  criteria.
- State what the prospect can inspect or decide afterward.

## 7. Visual-only scope boundary

Raw task:

```text
Apply the current Codeer visual system to this approved deck. Preserve all
content and meaning. The deck begins with a product feature overview.
```

Expected behavior:

- Do not silently rewrite the storyline.
- Report the feature-first risk as narrative drift or a limitation.
- Complete the authorized visual work unless the user broadens the scope.

## 8. Evaluation rubric

Score each applicable dimension as `pass`, `material-fail`, or
`justified-exception`:

| Dimension | Pass condition |
|---|---|
| Audience relevance | The audience can recognize the current situation, blocked result, or accepted decision premise |
| Central change | One sentence states what changes for whom without depending on a feature list |
| Mechanism debt | Every visible mechanism answers an established customer question |
| Operational translation | Internal terms follow an understandable actor/action/artifact/condition/decision |
| Proof implication | Concrete evidence states both a visible fact and what it changes in the decision |
| Trust role | Control or validation serves a named risk unless governance is the actual primary job |
| Evidence boundary | Claims match their source, sample, status, and method; unsupported numbers are not invented |
| Verification CTA | The next step tests the central claim and names an observable result |
| Scope discipline | Reviews do not silently edit; visual-only work does not silently change meaning |

A revision fails regression when it succeeds only by matching fixture wording,
forces every audience into the same sequence, bans useful technical terms, or
rejects the documented technical and governance exceptions.
