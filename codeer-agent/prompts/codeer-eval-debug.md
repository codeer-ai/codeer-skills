---
description: Diagnose existing Codeer eval evidence and plan regression
---

Use $$codeer-agent. Read and follow `modules/eval-debug.md` from that skill.
When invoked inside a `codeer-skills` development checkout, prefer the
checkout's `codeer-agent/modules/eval-debug.md` so an unmerged branch can be
tested.

Optional natural-language context: $ARGUMENTS

Diagnose existing response, tool, retrieval, judge, or platform evidence. This
invocation authorizes diagnosis only; follow the skill's diff and mutation
guardrails before any later change. If no dynamic evidence exists, stop the
diagnosis and route to `modules/static-audit.md`; do not invent a failure
mechanism. Ask before running any new eval needed to collect evidence.
