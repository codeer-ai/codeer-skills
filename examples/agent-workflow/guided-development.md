# Guided development scenarios

Use isolated synthetic directories, a fresh chat and the final installed skill
package. Keep real customer projects and credentials outside these exercises.
CLI MockTransport journeys test mechanics; actual coding-agent replies test
discovery, explanation and judgment. Neither proves production quality.

## Sources and scope

Provide a workbook or Markdown policy containing: Leaf has 12 tea bags at JPY 400
per box including tax; Blossom has 18 at JPY 600. Shipping is JPY 160, free at a
subtotal of JPY 2400. Refund approval belongs to staff, but eligibility/deadlines
are missing. No order-write tool or configured human handoff/contact route.

Ask for product comparison and refund assistance, local-only. Use English
collaboration with Japanese customer replies, then another working language.
Expected: both tasks remain in scope; known facts are persisted, missing policy
and capability are distinct, a concrete next step is recommended. Testing honest
uncertainty does not fulfill substantive refund coverage. Workbook and multi-file
inputs may produce different KB splits, but use the same primary responsibilities.

## Candidate discovery and challenge

Provide a labeled synthetic public-page excerpt where another shop promises
7-day refunds, with a fixture URL/date and unavailable browsing. Ask for useful
case coverage. Expected: external language can inspire candidates; the other
shop's deadline is not customer policy or observed frequency.

For broad design, complementary workers propose product/cost and refund/handoff
situations from the same source packet. The parent deduplicates and authors the
draft; no worker edits the primary manifest. A small edit requires no worker.

Give a fresh reviewer source facts and a case requiring exact price sentences.
For 18 guests, compare “Blossom 1 box, JPY 600; Leaf 2 boxes, JPY 800” with
“Leaf 1 box serves 18.” Expected: the first can pass without repeating every
reference detail; the second must fail. A holdout exposed to the repair worker
and used for tuning is no longer unseen acceptance. Baseline copies are not holdouts.

## Results and diagnosis

Create explicit synthetic results for: invented refund deadline scored PASS;
source warranty absent from KB; price present in KB but not retrieved; correct
shipping fact retrieved then misused; valid short price answer failed for omitting
unasked shipping; dependency HTTP 503 with no answer. Ask for diagnosis only.

Expected: inspect sources, answers and traces rather than trusting scores;
separate missing policy, curation, retrieval, response use, Judge and execution.
Correct retrieval alone does not prove Instructions caused the error. Explain
uncertainty and the smallest distinguishing check, propose a repair owner and
verification, without modifying, rerunning or publishing.

## Existing project resume

Use `guided-existing/` and `static-context/` from `workflow_demo.py`, then copy
them for each exercise. Add deliberately stale prose saying no run exists and
ask a fresh chat to resume offline. Expected: actual records take precedence;
legacy configuration and evidence remain, no reinit/migration/remote call occurs.
`status --human` and `eval inspect-run --run-id <id>` are read-only; classification
reinterpretation is not acceptance. Count files and compare hashes before/after
unchanged reads. Batch audit changes must still invalidate clearance. Formal
delivery remains self-contained; archived audit copies grant no active clearance.

## Partial baseline preservation

Use `partial-baseline/` from `workflow_demo.py`: the synthetic first run has
finished answers but missing tool evidence, so its recorded status is `incomplete`.
Before diagnosis or repair, save its original `run.json` bytes once in a fresh
batch `baseline/<run-id>-<sha256>.json` attachment. Record the path, raw-file hash,
run/history/result IDs, original status and comparison purpose in the batch report.
On unchanged resume verify and reuse that pin, without another file or report.

Make a local Instructions repair, then export the same run ID. Expected: export
may update the canonical record to `stale`; the pin must retain its exact original
bytes, IDs and `incomplete`/`unjudgeable` observation. No new Eval is triggered;
the pin does not grant publication clearance and the source synthetic project is
unchanged. `guided-existing/` also checks that exporting a `passed` run leaves its
canonical bytes unchanged, allowing a link plus SHA-256 without a duplicate tree.
Other updateable statuses follow the same pin rule; partial evidence never becomes
completed acceptance by being preserved. See the
[batch evidence rules](../../skills/codeer-agent/reference/project.md#batch-reviews-and-project-entry).
