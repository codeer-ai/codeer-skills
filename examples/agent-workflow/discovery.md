# Discovery and resume scenarios

These synthetic scenarios exercise `skills/codeer-agent/SKILL.md` locally. They
complement the [CLI journeys](README.md), which start from authored policy and
confirmation fixtures. No credentials, production data or remote operations
are needed. They are not fixed user questionnaires or required output wording.

## Running a scenario

Use a fresh temporary directory for each independent scenario. Put the source
excerpt under `sources/documents/`, or the specified settings/evidence at their
paths. Give a coding agent the skill, the directory and the user request below.
Do not give it the review checkpoints in advance. Let it perform local work;
when a user answer is needed, capture the question and current artifacts before
supplying an answer. Preserve the actual response and generated files for review.

For resume, use a fresh conversation with only the skill, generated project and
the stated follow-up. For local CLI operations use the installed development
CLI; see [development installation](../../codeer-cli/README.md#development-install).
Do not initialize or bind a real Agent for these exercises.

## Inputs

### A. SOP with an unresolved exception

Source `sop.md`: “現行售後流程：Agent 可依訂單編號查詢狀態。退款決定由人工負責。
產品保固一年。資料未規範查不到訂單時的處置。”

Request: “這份 SOP 是現行規範，幫我做售後 Agent，先做本機設計。”

### B. Explicit authority limits

Source `sop.md`: “訂單查詢可使用訂單編號。保固一年。退款由人工負責。”

Request: “幫我規劃售後 Agent，只能查訂單、不准修改；退款由人工決定。
先做本機設計。”

### C. Conflicting source and uncertain new information

Source `sop.md`: “售後 SOP v1：金額低於 500 元的退款可由 Agent 自動核准，
其他由人工決定。”

Request: “請依這份 SOP 規劃售後 Agent。我印象中最近所有退款都要人工核准，
但不確定文件有沒有更新。先整理本機設計。”

After reviewing the first response, follow up: “我確認今天起所有退款都由人工
核准，取代 SOP v1 的小額自動核准規則。請更新本機設計紀錄。”

### D. Multiple non-consultative tasks

Source `policy.md`: “任務一：依文字內容分類為帳務、技術或其他。任務二：抽取
工單中明確提供的訂單編號，未提供則留空。任務三：產出供內部員工檢閱的處理
摘要。不得更改工單狀態或向客戶發訊息。分類模糊時標示待人工確認。”

Request: “請依這份現行工單規範設計內部 Agent，分類、抽取訂單編號、處理摘要
三項都要。只做本機設計。”

### E. Resume interrupted discovery

Use the actual project generated in A without the prior chat. Request:
“接續這個專案，先告訴我目前做到哪裡，以及還需要我決定什麼。只處理本機資料。”

### F. Bounded diagnosis without historical design

Provide `agent/settings.json` with human handoff enabled and instructions
“Only transfer after collecting order number.” Provide `reviews/trace.json`:
request “請轉人工”, response “先提供訂單編號”, complete `tool_steps: []`, and
`human_handoff_available: true`. Do not provide a design document.

Request: “使用者明確要求真人時就應轉人工，不需訂單編號。只診斷這次為何
沒有轉接，先不要修改設定。”

### G. Missing capability and misleading score

Source `capabilities.md`: “訂單查詢工具僅供讀取訂單狀態。沒有修改地址工具，
也沒有轉人工工具。” Evidence `evals/failure.md`: “期望實際修改地址。Agent 回覆
已修改，但完整工具紀錄只有查詢，沒有修改。Judge 給予通過。”

Request: “這個 Agent 應該真的修改收件地址，這個要求不變。請檢查這次測試
結果並提出修正方向，先不要套用。”

## Review checkpoints

Compare actual decisions, necessary questions, source references, saved state
and operation scope. Wording and file length are not pass criteria.

| Scenario | Observable requirement |
| --- | --- |
| A | Reads the SOP first, records established rules and proposes how to handle the unresolved exception; user does not have to create or approve an internal template |
| B | Records explicit limits without reasking them; unconfirmed operational choices stay proposals |
| C | Exposes the conflict without guessing precedence; after the explicit replacement, updates the current rule with its source and retains the earlier evidence without another approval request |
| D | Covers all three requested tasks and the authority limits; does not impose sales discovery or reduce scope to one task |
| E | Recovers established intent, pending choices and next work from saved files; does not treat proposals as settled, repeat settled questions or claim execution evidence that does not exist |
| F | Diagnoses against the explicit instruction without requiring a complete historical design file; preserves supplied settings and does not claim causal certainty beyond the evidence |
| G | Distinguishes claims, real operations and score; reports capability/evidence gaps, preserves the address-change goal and proposes alternatives without silently adopting them |

Across scenarios, source facts, governing rules, observed behavior and builder
inferences must stay distinguishable. Established intent does not authorize
server writes, eval runs or publication. Record whether validation used actual
coding-agent output, a step-by-step semantic review, or constructed examples;
none alone establishes production quality or deterministic model behavior.
