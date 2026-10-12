# Synthetic Agent project journeys

For source-to-design interaction and interrupted discovery, use the separate
[discovery and resume scenarios](discovery.md). They exercise the skill with
raw material and natural-language requests; the CLI journeys below start with
synthetic design/confirmation artifacts and do not measure discovery quality.

Run from the development checkout with a fresh output directory:

```bash
cd codeer-cli
uv run python tests/workflow_demo.py --out-dir /tmp/codeer-workflow-demo
```

This uses the real CLI parser and `httpx.MockTransport`, without credentials,
network requests or real customer resources. It retains two inspectable projects:

- `new-agent/`: offline design, preview/create Draft, one shared tool Tester and
  two Case/Rubric pairs, synthetic acceptance/audit, failed run, reviewed repair,
  new h2 Draft, focused check, covering regression, publication and exact readback.
- `existing-agent/`: separate h1 Draft/h0 Published import without accepted
  Agent design, local/web prompt conflict, preserved local proposal, History parts
  and AI Draft exports, de-identified candidate provenance/protection variants,
  pending behavior proposal and unchanged Published state.

Start a fresh chat with the installed skill and one project directory. Ask it to
identify the target, accepted versus proposed decisions, applied versus verified
work, run/release evidence, blockers and next step. `log.md` provides context;
the structured artifacts establish actual fixture operations.

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
