# Technical support tasks

## Lifecycle

`identify environment → reproduce/diagnose → isolate cause → apply safe step → verify → escalate/repair → monitor`

## Base tasks

- `TECH-SETUP-CONFIGURE`: install, connect, configure, or migrate.
- `TECH-HOWTO`: perform a supported operation.
- `TECH-DIAGNOSE`: identify likely cause and collect diagnostics.
- `TECH-RECOVER`: restore access, service, data, or device operation.
- `TECH-COMPATIBILITY`: determine version, platform, integration, or requirement fit.
- `TECH-INCIDENT-STATUS`: understand outage, degradation, or known issue.
- `TECH-ESCALATE-REPAIR`: create a repair, bug, or specialist handoff.
- `TECH-VERIFY-CLOSE`: confirm resolution and prevent recurrence.

## Task-specific complications

- environment, version, or device is unknown;
- issue cannot be reproduced;
- multiple changes happened before failure;
- proposed step is destructive or irreversible;
- workaround masks a security or data-integrity risk;
- third-party integration owns part of the failure;
- customer lacks permission or physical access;
- outage and local configuration failure look similar;
- prior troubleshooting changed the state.

## Common composites

- access recovery + security;
- setup + compatibility;
- outage status + workaround;
- diagnosis + billing or service-level complaint;
- repair + data backup or warranty.

## Risk hooks

- data loss or corruption;
- security compromise;
- physical device or safety damage;
- prolonged service interruption;
- unauthorized configuration change;
- false outage or resolution claim.

## Recommended cross-task challenges

`CH-UNDERSPECIFIED`, `CH-SELF-CORRECTION`, `CH-MISSING-ATTACHMENT`, `CH-MULTIPLE-ENTITIES`, `CH-PRIOR-ACTION-STATE`, `CH-FRAGMENTED-MULTITURN`, `CH-POLICY-PRESSURE`, `CH-REPEATED-CONTACT`

## Public research signals

Search official troubleshooting, release notes, status pages, security advisories, issue trackers, compatibility matrices, app reviews, and repair complaints.
