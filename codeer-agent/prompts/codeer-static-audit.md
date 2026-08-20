---
description: Run a read-only Codeer pre-eval static audit
argument-hint: '[AGENT=<id-or-name>] [SCOPE="<optional focus>"]'
---

Use $$codeer-agent. Within that skill, read and follow
`modules/static-audit.md` for this task.

Audit target/context: $ARGUMENTS

Perform the deterministic pre-eval audit only. Do not run an eval and do not
modify the agent, KB, FAQ routes, cases, rubrics, evaluators, repository, or
published state. Return the module's complete output contract. If the exact
agent/version cannot be identified safely, record or ask the minimum unresolved
question instead of guessing.
