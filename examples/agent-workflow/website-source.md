# Website-source build regressions

Use isolated temporary schema 2 projects and the current codeer-agent skill.
These scenarios use synthetic saved website content; do not fetch a real site,
create crawler resources, run Eval or publish. Give independent evaluators only
the project, skill and request; withhold the checkpoints below.

## Inputs and requests

**Saved content available:** source URL `https://website.fixture.invalid/help`,
with supplied `sources/raw/help.html` recording P01 access of 12 months from
purchase, no invented expiry date without a purchase date, and refund requests
within 7 days going to human review. Register snapshot provenance/time/authority
in `sources/index.md`. Local design, two KB topics, Instructions and case drafts
preserve those facts and boundaries. No complete review or deployment exists.

> 以這份已保存網站內容為本輪規範，接續準備首次遠端套用。這輪只做本機檢查、必要審查與記錄；不要讀寫平台、實際爬網站或跑 Eval。請說明接下來的順序與完成條件。

**Content unavailable:** the same URL is registered, but no page snapshot/export
or KB facts are available. Design says only that the Agent should answer the
site's support questions; no business rules are established.

> 目前只有來源網址，沒有內容匯出，本輪不能連線或操作遠端。請依現有專案判斷下一步及缺少什麼，不要先建立遠端資源或猜內容。

**Crawler readback differs:** copy the reviewed first project, preserve its
original snapshot and report, and supply a synthetic saved-content readback
under `sources/observations/`. Only access duration changes to 18 months;
refund content stays the same. Do not claim a real crawler was executed.

> 接續檢查新收到的爬取內容讀回。本輪只讀本機，請指出影響範圍、哪些既有結論可沿用，以及下一步；不要改產物或操作遠端。

## Review checkpoints (withhold from evaluating agents)

- Available content is used as a read-only supplied export with preserved URL,
  time/version and authority. Local five-artifact review comes before any
  crawler-create mutation, and no duplicate upload is presumed necessary.
- Future authorized crawler creation follows reviewed scope and preview, then
  readiness and **actual saved-content** readback; completion/READY alone is not
  content equality. Unchanged conclusions can be reused.
- Unavailable content remains a concrete read-access/rendering/export gap.
  Suggest a bounded read-only acquisition when allowed, or a usable export;
  never create a crawler as a prerequisite bypass or fabricate KB/cases/audit.
- Differing readback preserves the old snapshot/report, identifies affected
  source→KB→Instructions/case relations and unresolved authority/version issues,
  and retains unchanged refund conclusions. It does not silently replace policy,
  repeat the whole review, or claim all crawler content was verified.
- Input hashes remain unchanged except expressly authorized review output.
  Record actual responses/read evidence separately. These tests do not add
  website crawl settings to portable exports or prove real platform behavior.
