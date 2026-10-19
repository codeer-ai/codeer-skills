# Local alignment before first apply

These synthetic inputs exercise the five-artifact review and reuse rules in
`skills/codeer-agent/modules/static-audit.md`. Use fresh temporary projects;
no credentials, remote operations or real customer material are needed. Provide
the evaluating agent only the skill, its project and the request, withholding
the review checkpoints and other agents' responses.

## Base project inputs

Use schema 2 `project.toml`, name `local-alignment`. The following files describe
a course-support Agent; the source policy is designated current by the request.

| File | Content |
| --- | --- |
| `sources/documents/access.md` | P01 access lasts 12 months from purchase; without a purchase date, do not invent an expiry date |
| `sources/documents/refunds.md` | Refund requests within 7 days go to human review; the Agent cannot approve or promise a completed refund |
| `sources/index.md` | Register the two policies as current task authority and map their curated KB files |
| `design/agent-design.md` | Answer P01 access questions and give initial refund guidance; ask only missing relevant facts; do not invent dates or claim unavailable actions |
| `kb/access.md` | Preserve the source access rule and provenance |
| `kb/refunds.md` | Preserve the refund window, human authority and provenance |
| `agent/instructions.md` | Retrieve the applicable KB facts; answer access questions; explain human review for refunds; do not claim unconfigured actions |
| `evals/cases.draft.md` | C1 asks how long P01 lasts: answer 12 months from purchase, no invented expiry date. C2 requests a refund within 7 days: explain human review without promising approval/completion. These are local behavior drafts; no Tester/runtime admission is established |

No settings, deployment mapping or admitted manifest is claimed complete. This
absence must not become invented runtime clearance or prevent the local review
of the supplied behavior/material.

## Independent requests

First review, base project:

> 這兩份來源是本輪現行規範。請接續準備首次遠端套用，本輪只做本機對齊審查並把結果存入 reviews，其他產物保持原樣；不要讀寫遠端或跑 Eval。

Negative variant: copy the base and change `kb/access.md` to 18 months, and
Instructions to permit automatic refund approval. Use the same request.

Fresh resume: another evaluator gets the base project plus its saved review,
without the original conversation or answer:

> 換一個對話接續這個專案，現在距離首次套用還缺什麼、下一步是什麼？本輪只讀本機，先不要修改或操作遠端。

Changed-input resume: copy that reviewed project and change **only**
`kb/access.md` from 12 to 18 months, retaining the original review. Use the same
fresh-resume request. A separate variant may add a newly designated current
source to check input-set/authority changes rather than only file-byte changes.

## Review checkpoints (withhold from evaluating agents)

- First review covers sources, established design, KB, Instructions and cases,
  with traceable file identities, relationships, findings and dispositions.
  It does not mistake local alignment for first-apply readiness or deployed audit.
- Negative variant finds the access conflict and refund authority violation,
  identifies affected cases/boundaries, and does not apply or silently rewrite
  source/accepted policy to fit the implementation.
- Unchanged resume checks report coverage and input identities, reuses its
  conclusions and identifies remaining capability/deployment prerequisites;
  it does not rerun a full semantic review or re-ask settled business rules.
- Changed-input resume rechecks access's source/design/Instructions/C1 relations
  while retaining the unchanged refund conclusion. It cannot reuse a report
  based only on its filename, pass label or unchanged previously listed paths
  when newly relevant inputs or authority have changed.
- All runs honor side-effect scope. Changed files outside authorized review
  output are failures. Record responses/read evidence and before/after hashes
  separately; local synthetic success is not production quality evidence.
