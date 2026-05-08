# Preview 環境操作指南

本文件說明如何在 Codeer PR preview 環境中使用 codeer-agent skill。
Preview 環境由 GitHub PR 自動部署，用於測試尚未合併到 production 的變更。

## 與 Production 的關鍵差異

| | Production | Preview |
| --- | --- | --- |
| Frontend | `https://app.codeer.ai` | `https://pr{N}.preview.codeer.ai` |
| **API** | `https://api.codeer.ai` | **`https://pr{N}.api.preview.codeer.ai`** |
| Cookie 來源 | `app.codeer.ai` devtools | `pr{N}.preview.codeer.ai` devtools |
| 資料庫 | Production DB | 每個 PR 獨立的 ephemeral DB |
| 預設帳號 | 你自己的帳號 | `Preview Admin` (`admin@preview.codeer.ai`) |

**最常見的錯誤**：把 `CODEER_API_BASE` 設成 `https://pr{N}.preview.codeer.ai`
（前端網址）。這會回傳 SPA HTML 而非 JSON。API 的 domain 是
`pr{N}.api.preview.codeer.ai`——中間多一個 `api.`。

## 檔案結構

Repo root 下有兩個 env 檔案，各自對應一個環境：

| 檔案 | 環境 | 用途 |
| --- | --- | --- |
| `session.env` | **Production** | 預設使用，client 自動偵測 |
| `preview_session.env` | **Preview** | 需透過 `CODEER_ENV_FILE` 明確指定 |

`session.env` 永遠指向 production，不需要來回切換。要操作 preview 環境時，
用 `CODEER_ENV_FILE` 環境變數指向 `preview_session.env` 即可。

## Setup

### 1. 取得 preview 環境的 session credentials

1. 在瀏覽器開啟 `https://pr{N}.preview.codeer.ai` 並登入
2. 開啟 DevTools → Application → Cookies → `pr{N}.preview.codeer.ai`
3. 複製 `sessionid` 和 `csrftoken` 的值

### 2. 建立或更新 preview_session.env

在 repo root（`codeer-skills/`）建立 `preview_session.env`：

```
CODEER_API_BASE=https://pr{N}.api.preview.codeer.ai
CODEER_SESSION_ID=<preview 環境的 sessionid>
CODEER_CSRF_TOKEN=<preview 環境的 csrftoken>
```

將 `{N}` 替換為實際的 PR 編號（例如 `1118`）。

### 3. 驗證連線

```bash
CODEER_ENV_FILE=preview_session.env $SKILL_DIR/scripts/codeer check
```

成功會印出目前的身份、workspace、organization 等資訊，並驗證 auth 是否有效。

若需要查看完整的 workspace / organization 對應，可用：

```bash
CODEER_ENV_FILE=preview_session.env $SKILL_DIR/scripts/codeer api get /accounts/me
```

回傳 JSON 中的 `profile.workspace_organization_map` 列出所有可用的
workspace ID（key）和 organization ID（value）。

## Preview 環境的特性

- **Ephemeral DB**：每個 PR 有自己的 Postgres，資料不與 production 共用。
  預設會有一組 seed data（Preview Admin 帳號、預設 org/workspace）。
- **Session 會過期**：跟 production 一樣，收到 401/403 時需要重新從
  devtools 取得 cookie。
- **PR 關閉即銷毀**：PR merge 或 close 後，preview 環境會被自動清理，
  所有資料都會消失。

## 常用操作範例

以下範例假設 `$SKILL_DIR` 已指向 skill 目錄。所有指令前綴
`CODEER_ENV_FILE=preview_session.env` 來指定 preview 環境。

### 查看帳號與 workspace

```bash
CODEER_ENV_FILE=preview_session.env $SKILL_DIR/scripts/codeer api get /accounts/me
```

從回傳的 `profile.workspace_organization_map` 取得 workspace ID（key）和
organization ID（value）。

### 列出所有 agents

```bash
CODEER_ENV_FILE=preview_session.env $SKILL_DIR/scripts/codeer agent list \
  --workspace <ws_id> --org <org_id>
```

> 注意：`agent list` 回傳所有 agent（包含 draft）。若要用 raw API，
> `/agents/all` 才能看到 draft 狀態的 agent，`/agents` 只回傳已 publish 的。

### 讀取單一 agent

```bash
CODEER_ENV_FILE=preview_session.env $SKILL_DIR/scripts/codeer api get /agents/<agent_id>
```

### 在 Cowork 中使用

Cowork 的 bash sandbox 每次呼叫都是獨立的，沒有 CWD/env 的 carryover。
建議在每次指令開頭同時設定 `SKILL_DIR` 和 `CODEER_ENV_FILE`：

```bash
SKILL_DIR=/sessions/<session_id>/mnt/codeer-skills/codeer-agent
CODEER_ENV_FILE=/sessions/<session_id>/mnt/codeer-skills/preview_session.env \
  $SKILL_DIR/scripts/codeer check
```

不帶 `CODEER_ENV_FILE` 時，client 按以下順序尋找 credentials：
`~/.codeer/session.env` → `<repo-root>/session.env` → `./.env`。
詳見 **SKILL.md** 的「Where to place `session.env`」段落。

## 切換環境

不需要搬檔案或改內容。差別只在有沒有設 `CODEER_ENV_FILE`：

```bash
# Production（預設，不需額外設定）
$SKILL_DIR/scripts/codeer check

# Preview（加上 CODEER_ENV_FILE）
CODEER_ENV_FILE=preview_session.env $SKILL_DIR/scripts/codeer check
```
