## Sub-agent orchestration

Use sub-agents when the environment supports them and either the work contains
at least two independent units that can share one pinned evidence set and be
meaningfully synthesized, or one bounded review materially benefits from an
independent, context-isolated perspective. Do not delegate a small scoped read
merely to use parallelism. If sub-agents are unavailable or the work is too
coupled, perform the same module sequentially.

The parent Agent remains the decision owner. It must:

- establish the outcome, scope, analysis unit, and exact Agent/version target;
- read or export server state once when practical, then give workers the same
  immutable local evidence and object fingerprints;
- keep user communication, cross-workstream synthesis, final ownership and
  causal judgments, canonical artifact writes, and every server mutation; and
- resolve disagreements from evidence rather than worker votes.

Workers are read-only investigators. They must not mutate Codeer server state,
edit canonical project artifacts, broaden the accepted scope, rewrite the
Agent design, or apply a repair. Give each worker only the shared anchors,
its bounded assignment, and any common coding or judgment guide. For an
independent audit or challenge, do not preload the parent's suspected diagnosis
or proposed repair. Workers should return findings through their handoff rather
than shared files. If a large intermediate artifact is unavoidable, the parent
must assign a unique non-canonical path that no other worker will edit.

A worker handoff may use any reviewable format, but it must preserve the
assigned scope, evidence inspected, observations, consequence, likely owner,
material alternatives or counterexamples, uncertainty, and the smallest next
evidence needed. The parent must reconcile overlap, calibration differences,
and missing units before making a whole-system or population-level claim.

The module-specific sections below define safe work units for History, Static
Audit, Eval Debug, version-aware triage, and Eval-portfolio optimization.

---

