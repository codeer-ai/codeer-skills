---
description: Diagnose existing Codeer eval evidence and plan regression
argument-hint: '[AGENT=<id-or-name>] [CASE=<id-or-label>] [RESULT=<path-or-id>]'
---

Use $$codeer-agent. Within that skill, read and follow
`modules/eval-debug.md` for this task.

Evidence target/context: $ARGUMENTS

Diagnose existing response, tool, retrieval, judge, or platform evidence. This
invocation authorizes diagnosis only; follow the skill's diff and mutation
guardrails before any later change. If no dynamic evidence exists, stop the
diagnosis and route to `modules/static-audit.md`; do not invent a failure
mechanism. Ask before running any new eval needed to collect evidence.
