---
description: Run a read-only Codeer pre-eval static audit
argument-hint: '[AGENT=<id-or-name>] [SCOPE="<optional focus>"]'
---

Use $$codeer-agent. Read and follow `modules/static-audit.md` from that skill.
When invoked inside a `codeer-skills` development checkout, prefer the
checkout's `codeer-agent/modules/static-audit.md` so an unmerged branch can be
tested.

Audit target/context: $ARGUMENTS

Perform the deterministic pre-eval audit only. Do not run an eval and do not
modify the agent, KB, FAQ routes, cases, rubrics, evaluators, repository, or
published state. Return the module's complete audit report. If the exact
agent/version cannot be identified safely, record or ask the minimum unresolved
question instead of guessing.
