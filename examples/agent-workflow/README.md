# Synthetic Agent project journeys

For source-to-design interaction and interrupted discovery, use the separate
[discovery and resume scenarios](discovery.md). They exercise the skill with
raw material and natural-language requests; the CLI journeys below start with
synthetic design/confirmation artifacts and do not measure discovery quality.
For progression from authored material or an execution-blocked run, use the
[continuation scenarios](continuation.md), including fresh-conversation checks.
For the first-apply semantic prerequisite and reuse of unchanged findings, use
the [local alignment scenarios](local-alignment.md).
For read-only website acquisition before crawler creation, unavailable content,
and changed-content readback, use the [website-source scenarios](website-source.md).
For multi-angle cases, independent challenge, plain-language feedback and legacy
compatibility, use [guided development scenarios](guided-development.md).

Run from the development checkout with a fresh output directory:

```bash
cd codeer-cli
uv run python tests/workflow_demo.py --out-dir /tmp/codeer-workflow-demo
```

This uses the real CLI parser and `httpx.MockTransport`, without credentials,
network requests or real customer resources. It retains ten inspectable projects:

- `new-agent/`: offline design, preview/create Draft, one shared tool Tester and
  two Case/Rubric pairs, synthetic acceptance/audit, failed run, reviewed repair,
  new h2 Draft, focused check, covering regression, publication and exact readback.
- `existing-agent/`: separate h1 Draft/h0 Published import without accepted
  Agent design, local/web prompt conflict, preserved local proposal, History parts
  and AI Draft exports, de-identified candidate provenance/protection variants,
  pending behavior proposal and unchanged Published state.
- `kb-faq-portability/`: conditioned original import, exact CRLF text/FAQ, another
  API environment with new FAQ IDs, then independent local/platform FAQ proposals
  retained as undecided; website crawl settings remain an explicit gap.
- `portable-deployments/`: schema 2 original PDF/KB uploads and FAQ rebuilding, Agent and shared
  Tester/Case deployment to two API environments, exact run/publication evidence,
  formal delivery export/verification and missing-file/newer-result counterexamples.
  The deliberately tampered delivery bundle remains as a failing verification
  example. The selected final target is intentionally mismatched; offline status
  must not borrow the first environment's passing run.
- `platform-resume/`: schema 2 Draft h1/Published h0 observations, explicitly
  adopted platform description and an undecided local/platform prompt conflict.
  No platform mutation; use this for the natural-language resume scenario.
- `unverified-contracts/`: synthetic support-project continuation with existing
  source/KB/Instructions and 52 authored candidates / 71 proposed pairs. Eight
  unverified shared contracts produce 238 per-pair references. Validation stays
  nonzero, apply/run remain blocked, and status groups the contracts. It preserves
  an unresolved existing manifest to exercise diagnosis, not recommended authoring.
- `execution-errors/`: Agent/Eval readback, current pre-eval audit and an exact
  run with execution errors. Error outcomes are distinct from quality failures;
  no particular infrastructure cause is established by the fixture.
- `guided-existing/`: a copy of a synthetic existing project, batch audit,
  readable offline resume, mock run/publication and verified delivery. The
  final report is intentionally changed to demonstrate stale audit rejection;
  the original synthetic project remains unchanged.
- `partial-baseline/`: a synthetic existing-project copy with finished answers
  but missing evidence. A single original JSON byte snapshot plus SHA-256 survives
  a later same-run export changing the canonical status from `incomplete` to `stale`.
  Unchanged resume reuses the pin, no new Eval is triggered, publication remains
  blocked, and the source project stays unchanged. Fixed `passed` runs instead
  retain their canonical bytes through export and can be linked without a copy.
- `static-context/`: input/rubric from the exact snapshot and output from bound
  results. The saved run is deliberately relabeled with the legacy unjudgeable
  state; `eval inspect-run` gives a separate derived interpretation without
  rewriting it. Swapped legitimate results and omitted rows are counterexamples.

Start a fresh chat with the installed skill and one project directory. Ask it to
identify the target, accepted versus proposed decisions, applied versus verified
work, run/release evidence, blockers and next step. `logs/YYYY-MM.md` (legacy
`log.md`) provides context;
the structured artifacts establish actual fixture operations.

For `platform-resume/`, ask: “平台有人改了，幫我接回。description 採平台的決定已確認，prompt 還沒決定；先核對目前狀態，不要寫平台或推其他環境。”
Expected: recognize the already-adopted description without asking again, retain
the prompt conflict, distinguish Draft/Published and cached/live observations,
identify the adoption preview needed after a prompt decision, and preserve
source/confirmation/history gaps. Do not claim business acceptance or passing
quality from the imported platform state.

All policy, confirmation and audit reports are explicitly synthetic. The fixture
Judge supplies deterministic scores; it does not validate real model quality.
A complete empty tool trace can support a negative call criterion; an absent
trace is insufficient evidence. A falsely favorable Judge score must still be
challenged by semantic review of actual traces and configured capabilities.

The suite separately covers old result contamination, incomplete/skipped/error
runs, missing delivery reports, stale audit, shared Tester changes, unknown writes,
readback mismatch, stable IDs and package installation:

```bash
uv run python -m unittest discover -s tests -p 'test_*.py'
```

No fixture result establishes production deployment, transactionality, fixed KB
or external tool state, or an API's ability to replace existing KB file content.
