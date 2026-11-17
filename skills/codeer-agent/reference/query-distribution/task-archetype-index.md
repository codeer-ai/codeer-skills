# Task archetype index

## Definitions

- **Task family**: a reusable customer outcome area.
- **Base task**: a specific desired outcome.
- **Lifecycle state**: the current business state.
- **State transition**: the intended move between states.
- **Task-specific complication**: a blocked, invalid, ambiguous, or exception state inside that lifecycle.
- **Composite task**: two tasks that customers realistically combine.

Treat a modification such as rescheduling as a task or state transition, not automatically as a challenge.

## Modules

| Task family | Module | Typical operating models |
|---|---|---|
| Appointment and access | `tasks/appointment-access.md` | appointment, field service, advice/triage |
| Order and fulfillment | `tasks/order-fulfillment.md` | commerce, logistics, marketplace |
| Account and subscription | `tasks/account-subscription.md` | SaaS, membership, regulated services |
| Billing, refunds, disputes | `tasks/billing-refunds-disputes.md` | nearly all transactional models |
| Advice, triage, eligibility | `tasks/advice-triage-eligibility.md` | healthcare, professional services, benefits |
| Technical support | `tasks/technical-support.md` | software, devices, field repair |
| Records, privacy, administration | `tasks/records-privacy-administration.md` | regulated, professional, account-based |
| Complaint, escalation, recovery | `tasks/complaint-escalation-recovery.md` | all models |

## Promotion rule

Keep a pattern inside a task module when it depends on that lifecycle. Promote it to `patterns/cross-task-challenges.md` only when it appears in at least two task families and causes the same Agent failure mechanism.

Keep channel presentation separate from both task and challenge. Keep failure consequence separate as industry risk.
