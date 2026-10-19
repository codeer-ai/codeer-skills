# Agent 開發管理

[English](README.md) | 繁體中文

本資料夾搭配 `codeer-agent` skill 與 Codeer CLI，集中管理多個 Agent 開發專案。共用協作規則放在 [AGENTS.md](AGENTS.md)，每個專案各自保存來源、設計、設定、評量與驗證證據。

## 建立自己的管理資料夾

將整份範本複製到自己的工作位置，目錄可自行命名，例如 `my-agents/`、`team-agents/`。複製後：

1. 將 README 的標題與介紹改成團隊或自己的用途，保留英文 README 的共用專案索引作為入口。
2. 檢查 `AGENTS.md`，依協作語言、資料保存與團隊規則調整；沿用標準檔名，方便 coding agent 讀取。
3. 安裝 Codeer CLI 0.1.17 或更新版本及相配的 `codeer-agent` skill。CLI 以 PyPI 安裝為主；若需原始碼版本，依該版本的 CLI 文件設定入口。先以 `codeer init --help` 核對本機專案命令是否可用。範本本身不包含工具或憑證。
4. 按需求建立第一個專案；需要版本管理時，再自行初始化 Git。

初始結構如下，`projects/` 只有保留空目錄的 `.gitkeep`：

```text
my-agents/                  # 可自行命名的管理資料夾
  README.md                 # 英文指南與共用專案索引
  README.zh-TW.md           # 繁體中文指南
  AGENTS.md                 # 給 coding agent 讀取的共用協作規則
  .gitignore                # 個人狀態與原始資料的預設保護
  projects/                 # 按需建立各個 Agent 開發專案
```

管理根目錄負責共用文件及索引，不建立根層 `project.toml`；個別專案內容放在 `projects/`。每個 `projects/<slug>/` 對應一個主要 Agent，建議使用穩定、具業務意義的英文小寫連字號名稱。各專案的本機內容應能獨立搬走；遠端共用資源依 skill／CLI 的規則管理。

## 文件與工具的分工

| 入口 | 負責內容 |
| --- | --- |
| 管理資料夾的 README、AGENTS.md | 使用導航、專案索引與跨專案協作約定 |
| `codeer-agent` skill | 來源分析、設計、評量、審查與遠端操作的工作流程及授權邊界 |
| Codeer CLI | 專案初始化、結構檢查、狀態與證據紀錄，以及實際平台命令的執行與讀回 |

管理文件不另定義平台命令、驗收條件或證據格式。各專案的路徑以 `project.toml` 為準，詳細工作流程及命令以實際使用的 skill／CLI 文件為準。

## 新增專案

在管理根目錄開啟 coding agent，提供專案名稱、目標與資料位置即可，例如：

```text
請使用 codeer-agent skill，在 projects/support-agent 建立客服 Agent 開發專案。
來源資料位於我指定的資料夾。先讀取資料、整理理解與待確認問題，
保存本機設計及下一步；這輪只做本機工作。
```

若自行初始化，從管理根目錄執行以下命令，將 `support-agent` 換成實際名稱；目錄已有工作時使用接續流程：

```bash
codeer init projects/support-agent
cd projects/support-agent
codeer status
codeer validate
```

上述命令可離線使用，不需要 API key，也不會建立遠端 Agent。初始化後，把專案用途與 README 連結加入[共用專案索引](README.md#project-index)。來源原件預設保存在專案 `sources/`，也可在來源索引登記指定的外部位置；其他內容隨工作產生，不需先填完所有模板。

## 專案索引

專案索引統一維護於 [README.md 的 Project index](README.md#project-index)，兩種語言使用同一份索引。新增時填入專案 README 的相對連結與用途；實際狀態以專案文件及 CLI 證據為準，進度紀錄留在專案內。

## 接續工作

指定 `projects/<slug>/` 與本次目標，讓 coding agent 依 skill 的接續流程，讀取已存在且與本次工作相關的專案文件，再核對 `codeer status`、`codeer validate` 與相關證據。缺少尚未產生的設計或紀錄，不代表要重建專案。`validate` 執行本機檢查；業務語意由 coding agent 依 skill 審查。

下表是常見預設位置，內容隨工作產生；既有專案沿用設定及紀錄路徑：

| 位置 | 責任 |
| --- | --- |
| `project.toml`、專案 README | 一個主要 Agent 的本機設定與導航 |
| `sources/` | 原件、來源索引與 History／AI Draft 匯出 |
| `design/` | 已確認行為、待確認草稿及驗收範圍 |
| `kb/`、`agent/`、`evals/` | 知識、Instructions／設定與 Case／Tester／Rubric 設計 |
| `reviews/`、`logs/YYYY-MM.md` | 審查、確認依據、理由及結果；既有 `log.md` 繼續沿用 |
| `runs/`、`releases/` | 實際評量與發布證據 |
| `.codeer/` | 本機 binding、同步基準及恢復回執，不提交 Git |

## 遠端操作與資料保存

需要遠端操作時，依 skill 的連線、binding、匯入及授權流程進行；單純本機整理不需先配置遠端 Agent。憑證依 CLI 文件保存在使用者設定，不寫入專案。

根目錄 `.gitignore` 預設排除個人環境檔、各層 `.codeer/`，以及 `projects/*/` 下預設的原始 History、runs 與 releases，與 CLI 初始化的私人輸出規則一致。自訂路徑或團隊共享需求需另行檢查忽略範圍；未被忽略不代表適合共享。

`.codeer/` 含恢復所需資訊，不能當快取直接刪除，也不能假設 clone 可還原全部操作狀態。需要共同保存證據時，依 skill／CLI 文件選取共享範圍。
