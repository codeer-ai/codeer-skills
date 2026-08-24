# Industry-consequence risk

Risk here means the severity of mishandling the case, not frequency and not interaction difficulty.

## Levels

- `normal`: ordinary inconvenience or reversible service friction.
- `elevated`: meaningful loss, delay, repeated effort, or deterioration requiring careful handling.
- `high`: serious financial, health, legal, privacy, security, or continuity consequence.
- `critical`: imminent or potentially irreversible severe harm requiring urgent escalation or strict boundaries.

Use the target industry's standards and policies to calibrate levels. Do not assign `critical` merely because a customer is angry.

## Risk families

### `RISK-HEALTH-SAFETY`

Physical injury, medical deterioration, unsafe use, self-harm, abuse, public safety, or delayed emergency action.

### `RISK-FINANCIAL`

Unauthorized loss, fraud, duplicate transaction, material charge, lost refund or dispute right, or harmful financial advice.

### `RISK-PRIVACY-SECURITY`

Identity exposure, confidential disclosure, account takeover, insecure transfer, or compromised credentials.

### `RISK-LEGAL-REGULATORY`

Missed statutory deadline, unlawful action, non-compliant advice, required disclosure failure, or improper record handling.

### `RISK-RIGHTS-ACCESS`

Loss of entitlement, benefit, appeal, essential access, accommodation, or service eligibility.

### `RISK-SERVICE-CONTINUITY`

Extended outage, interrupted care, failed handoff, missed follow-up, or operational disruption.

### `RISK-DATA-RECORD-INTEGRITY`

Deletion, corruption, misattribution, inaccurate record, or irreversible administrative error.

### `RISK-PHYSICAL-PROPERTY`

Damage, loss, unsafe delivery, hazardous installation, or incorrect handling of valuable property.

### `RISK-REPUTATION-TRUST`

Material loss of trust or public harm when it reflects an underlying service, safety, discrimination, or accountability failure. Do not assign high risk to a publicity threat alone.

## Risk analysis

For each task, record:

- harmful outcome;
- affected party;
- reversibility;
- time sensitivity;
- escalation threshold;
- prohibited Agent behavior;
- evidence source;
- reviewer or policy owner.

## Allocation rule

Keep rare high-risk cells even when their observed share is low. Record the deliberate difference between `estimated_real_world_share` and `eval_target_share`.

Create at least:

1. a clear baseline that tests recognition and safe handling;
2. a realistic challenge variant that could conceal or distort the risk.

Do not create many stylistic variants unless empirical testing shows a meaningful failure mode.
