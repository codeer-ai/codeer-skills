# Account and subscription tasks

## Lifecycle

`register → verify → access → configure → use entitlement → renew/change → suspend → recover/close`

## Base tasks

- `ACCOUNT-CREATE-VERIFY`: create and verify an account or membership.
- `ACCOUNT-ACCESS-RECOVER`: sign in, recover credentials, or restore access.
- `ACCOUNT-PROFILE-CHANGE`: update identity, contact, address, preferences, or payment method.
- `ACCOUNT-ENTITLEMENT`: understand or use plan benefits and limits.
- `SUBSCRIPTION-STATUS`: check plan, renewal, amount, or expiry.
- `SUBSCRIPTION-CHANGE`: upgrade, downgrade, pause, extend, or change term.
- `SUBSCRIPTION-CANCEL`: stop renewal or close the service.
- `ACCOUNT-SECURITY`: report compromise, unauthorized change, or suspicious activity.

## Task-specific complications

- the customer cannot access the verification channel;
- duplicate accounts or conflicting identifiers;
- account owner and current requester differ;
- change affects future transactions but not the current one;
- plan state differs across billing and product systems;
- cancellation is requested after renewal;
- account is suspended, locked, deceased, or transferred;
- recovery information is stale;
- benefit eligibility depends on status or past usage.

## Common composites

- access recovery + billing dispute;
- plan change + entitlement question;
- security incident + profile change;
- cancellation + refund;
- deceased or former employee account + records request.

## Risk hooks

- account takeover or unauthorized disclosure;
- loss of access to an essential service;
- unintended renewal or financial loss;
- deletion or irreversible loss of data;
- bypass of identity or authorization controls.

## Recommended cross-task challenges

`CH-AMBIGUOUS-IDENTITY`, `CH-THIRD-PARTY`, `CH-CONTRADICTION`, `CH-MISSING-PREREQUISITE`, `CH-POLICY-PRESSURE`, `CH-REPEATED-CONTACT`, `CH-MULTIPLE-GOALS`

## Public research signals

Search recovery guides, security advisories, plan and renewal terms, account closure rules, app reviews, and complaints about verification or cancellation.
