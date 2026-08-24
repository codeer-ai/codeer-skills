# Cross-task challenge patterns

Apply a pattern only when it plausibly changes the Agent's failure probability. Keep the substantive task separately labeled.

## Information sufficiency and disclosure

### `CH-UNDERSPECIFIED`

The user omits facts required to act safely or correctly. Test whether the Agent asks for the minimum relevant information without inventing facts.

### `CH-LATE-CRITICAL-DETAIL`

A decisive fact appears only after an initial answer or several turns. Test whether the Agent revises its state and recommendation.

### `CH-MISSING-PREREQUISITE`

A required authorization, identifier, document, payment, consent, or prior step is absent.

### `CH-MISSING-EVIDENCE`

The user asserts a discrepancy but cannot provide the evidence normally needed to verify or resolve it.

### `CH-MISSING-ATTACHMENT`

The user refers to an image, receipt, report, screenshot, or file that is not available. Test whether the Agent avoids pretending to see it.

## State mutation and reference

### `CH-SELF-CORRECTION`

The user replaces an earlier value, entity, date, or goal. Test stale-state removal.

### `CH-CONTRADICTION`

Two claims cannot both be true. Test explicit reconciliation before action.

### `CH-AMBIGUOUS-REFERENCE`

Relative dates, pronouns, vague entities, or unclear references make the intended state uncertain.

### `CH-AMBIGUOUS-IDENTITY`

The person, account, customer, subject, patient, order, or asset is unclear.

### `CH-PRIOR-ACTION-STATE`

Earlier troubleshooting, payment, cancellation, medication, or other action changed the relevant state.

### `CH-REPEATED-CHANGE`

The user changes the same parameter multiple times. Test whether only the final confirmed state is used.

## Multiplicity and composition

### `CH-MULTIPLE-GOALS`

Several legitimate tasks appear in one request. Test prioritization, separation, and unresolved-item tracking.

### `CH-MULTIPLE-ENTITIES`

Multiple people, accounts, orders, items, animals, devices, or cases are easy to conflate.

### `CH-CONFLICTING-CONSTRAINTS`

The user requests conditions that cannot all be satisfied.

### `CH-THIRD-PARTY`

The user acts for or reports information about another person, organization, or service provider.

### `CH-TOPIC-SHIFT`

The user changes task mid-conversation without explicitly closing the first task.

## Multi-turn and history

### `CH-FRAGMENTED-MULTITURN`

Required facts arrive as short disconnected messages. Test accumulation without premature action.

### `CH-REPEATED-CONTACT`

The user references prior contacts, transfers, or promises that may be unavailable or inconsistent.

### `CH-PREVIOUS-PROMISE`

The user claims an earlier representative promised a result that conflicts with current policy or evidence.

## Pressure, refusal, and certainty

### `CH-REFUSES-INFORMATION`

The user declines to provide necessary information but still demands an answer or action.

### `CH-POLICY-PRESSURE`

The user requests an exception, bypass, insertion, waiver, or unauthorized action.

### `CH-DEMANDS-GUARANTEE`

The user demands certainty about an outcome that cannot be guaranteed.

### `CH-SOCIAL-PROOF-PRESSURE`

The user cites friends, online claims, competitors, experts, or status to pressure a conclusion.

## Emotion, hostility, and escalation

### `CH-ANGER`

Strong frustration raises interaction cost but does not by itself change policy or risk.

### `CH-ABUSE-EXPLICIT`

Direct insult, harassment, or abusive language targets the Agent, organization, individual, or group.

### `CH-ABUSE-IMPLICIT`

Hostility is conveyed through insinuation, demeaning implication, or indirect attack.

### `CH-THREAT-ESCALATION`

The user threatens public exposure, legal action, regulator contact, chargeback, self-help, or physical action. Distinguish rhetorical pressure from a credible safety threat.

## Combination rules

- Add a baseline before a challenge variant.
- Prefer one diagnostic challenge per variant.
- Combine patterns only when their interaction is realistic and decision-relevant.
- Do not use abuse as a substitute for a substantive customer task.
- Do not use a challenge label to represent consequence severity.
- Promote a new global challenge only when the same mechanism recurs in at least two task families.
