---
name: codeer-agent
description: Drive the full Codeer agent lifecycle (author, knowledge base, live test, evaluation, publish, post-release analysis) over the internal API from any directory, AND advise on agent design (which tools to pick, how to write system prompts, when to switch LLM models, common composition patterns). Use when the user wants to brainstorm a Codeer agent's design, build or iterate on one with local customer materials, create/update agents, upload files to a knowledge base, add eval cases with rubrics, run live test chats pinned to a draft version, publish a version, or pull conversation histories with feedback filters. Trigger phrases include "design a codeer agent", "what tools should my codeer agent have", "should I add knowledge base / web search / memory", "how should I structure this codeer agent", "create a codeer agent", "update my codeer agent", "upload files to codeer knowledge base", "add eval cases for my codeer agent", "set rubric on codeer case", "run codeer eval", "live test codeer agent", "publish codeer agent version", "analyze codeer history", "pull codeer feedback", "list agents in my codeer workspace".
---

# Codeer Agent Lifecycle — skill

Everything you need to build, evaluate, and improve a Codeer agent against
whatever files the user has in their current directory. Authenticates as the
user via a session cookie, so whatever the user can do in the Codeer UI, this
skill can do over the API.

## Working pattern with the user (read this first)

This skill controls real customer agents — wrong moves cost money and trust.
The user's preference is **heavy planning, minimal execution**: invest more
in thinking, exploring, and surfacing tradeoffs *before* you act, then make
the smallest possible change once a plan is agreed.

Concretely:

- **Plan → Confirm → Act.** For any non-trivial request, state the plan
  before executing: which artifacts you will touch (file paths, case IDs,
  endpoints), what each change is, and what you expect the outcome to be.
  Wait for explicit go-ahead. Treat the user's "OK" as authorising the
  specific plan you just stated, not your interpretation of next steps.

- **Be brave during planning.** Surface alternatives, edge cases, and
  uncomfortable angles ("the rubric might be the issue, not the prompt").
  Multi-option proposals beat pre-selected ones when there's a real choice.

- **Be minimal during execution.** Smallest diff that satisfies the agreed
  plan. No bonus refactors, no helper functions added "while you're in
  there", no extra files. Stop after the minimum and report.

- **Surface sub-choices, don't answer them yourself.** If a request
  requires picking which N cases / which severity / which evaluator,
  ask — don't decide on the user's behalf.

## Setup (one time, per user)

1. Create `~/.codeer/session.env` with **auth only**:
   ```
   CODEER_API_BASE=http://localhost:8000         # or your staging/prod base
   CODEER_SESSION_ID=<from browser devtools>
   CODEER_CSRF_TOKEN=<from browser devtools>
   ```
2. `chmod 600 ~/.codeer/session.env`
3. Cookies are found in the Codeer UI's devtools → Application → Cookies, after logging in.
4. Sessions expire. If calls start returning 401/403, re-grab the cookies.

The only prerequisite is `uv` on PATH — the skill's wrapper resolves httpx
through uv's cache, no installs.

### Per-project workspace / org (multi-workspace pattern)

`CODEER_WORKSPACE_ID` and `CODEER_ORGANIZATION_ID` deliberately do **not**
live in the global `session.env` — that would make "which workspace am I in"
shared mutable state across every Claude Code session, and concurrent sessions
on different orgs would silently collide.

Instead, set them per project in `.claude/settings.json` at the customer
materials directory's root:

```json
{
  "env": {
    "CODEER_WORKSPACE_ID": "<ws_id>",
    "CODEER_ORGANIZATION_ID": "<org_id>"
  }
}
```

Claude Code exports these into every command run inside that project, and
shell env beats the dotenv file in `client.py:_load_dotenv` (it skips keys
already in `os.environ`). So opening Claude Code in `~/customers/acme/` vs
`~/customers/initech/` automatically pins each session to its own workspace,
even though both share the same auth cookie.

**Same Codeer login across all orgs** is assumed. If you ever need to switch
to a different Codeer account, set `CODEER_ENV_FILE=~/.codeer/<alt>.env` in
that project's `.claude/settings.json` env block and put a full alternate
auth set there.

**At the start of any Codeer-skill session, call `GET /accounts/me`** and
state the active workspace/org name to the user — this catches a missing or
wrong per-project setting before any KB upload or agent edit lands in the
wrong place.

## Invocation

All paths below use `$SKILL_DIR` to refer to this skill's installation
directory. Claude: resolve this once at the start of a session — if installed
as a Claude Code skill it is typically `~/.claude/skills/codeer-agent`;
otherwise ask the user for the actual path.

The wrapper at `scripts/codeer` inside this skill works from any CWD:

```bash
$SKILL_DIR/scripts/codeer get /accounts/me
$SKILL_DIR/scripts/codeer get /agents/all --param wid=<ws> --param oid=<org>
$SKILL_DIR/scripts/codeer post /agents --json-file ./my_agent.json
$SKILL_DIR/scripts/codeer stream post /chats/42/messages --json '{"message":"hi","agent_history_id":"..."}'
```

Claude: always use the resolved absolute path; the wrapper keeps the caller's
CWD so `--json-file` and upload paths resolve relative to the user's project.

For scripted workflows, import the package directly (the wrapper puts it on
PYTHONPATH):

```python
# Run via:  uv run --with 'httpx>=0.27' python your_script.py
# with PYTHONPATH pointing at the skill's scripts/ dir.
import sys, os
SKILL_DIR = os.environ.get("SKILL_DIR", os.path.expanduser("~/.claude/skills/codeer-agent"))
sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))
from codeer_cli import CodeerClient, agents, kb, chats, histories
from codeer_cli import eval_ as eval_mod

with CodeerClient.from_env() as c:
    agent = agents.create(c, workspace_id=..., name=..., system_prompt=..., use_search=False)
    ...
```

## Reusable scripts (use these — don't write per-customer .py files)

Common operations are wrapped as standalone scripts that take JSON / args, so
the customer's directory only needs **data files** (KB content,
`.codeer/agent_payload.json`, `.codeer/eval_cases.json`) — not bespoke Python.

### Output directory convention

All generated files — payloads, ID maps, eval results, ad-hoc scripts —
go under **`.codeer/`** in the customer's project root. Create the
directory at the start of a session if it doesn't exist (`mkdir -p .codeer`).
This keeps the project root clean; only `kb/` (source content for upload)
stays at root level.

```bash
# 1. Build KB and upload all files in a directory
uv run --with 'httpx>=0.27' python $SKILL_DIR/scripts/kb_upload.py \
    --kb-dir ./kb --name "<KB display name>" \
    --workspace <ws_id> --org <org_id> --out .codeer/kb_ids.json

# 2. Create or update an agent (PUT auto-forks a new draft history)
uv run --with 'httpx>=0.27' python $SKILL_DIR/scripts/agent_apply.py \
    --payload .codeer/agent_payload.json [--agent-id <id> --note "..."] --out .codeer/agent_ids.json

# 3. Create eval cases with per-evaluator rubrics from JSON
#    Add --attachments-dir <dir> when any case has attachment_files: [...]
uv run --with 'httpx>=0.27' python $SKILL_DIR/scripts/eval_cases_apply.py \
    --cases .codeer/eval_cases.json --agent <agent_id> --out .codeer/case_ids.json

# 4. Trigger an eval run; auto-pick the newest draft and diff vs the previous history
uv run --with 'httpx>=0.27' python $SKILL_DIR/scripts/eval_run.py \
    --agent <agent_id> --latest-draft --workspace <ws_id> \
    --diff-vs <prev_history_id> --out .codeer/eval_results.json

# 5. Show a system-prompt + tools diff between two AgentHistory versions
uv run --with 'httpx>=0.27' python $SKILL_DIR/scripts/agent_diff.py \
    --agent <agent_id> --from-version 41 --to-version 42

# 6. Read current rubrics for all (case, evaluator) pairs
uv run --with 'httpx>=0.27' python $SKILL_DIR/scripts/eval_rubrics.py \
    --agent <agent_id> --workspace <ws_id> --out .codeer/rubrics.json

# 7. Apply rubric edits (read → edit → apply cycle with #6)
uv run --with 'httpx>=0.27' python $SKILL_DIR/scripts/eval_rubrics_apply.py \
    --rubrics .codeer/rubrics.json [--dry-run] [--out .codeer/changes.json]
```

Per-project env (set once in `.claude/settings.json` `env` block) makes
`<ws_id>` and `<agent_id>` injectable so you don't re-pass them every call:
`CODEER_WORKSPACE_ID`, `CODEER_ORGANIZATION_ID`, `CODEER_AGENT_ID`. Only auth
(`CODEER_API_BASE`, `CODEER_SESSION_ID`, `CODEER_CSRF_TOKEN`) lives globally
in `~/.codeer/session.env`.

Only fall back to ad-hoc Python via the `codeer_cli` package when one of
these scripts genuinely can't express what you need (rare). Common helpers
worth knowing about:
- `histories.list_production(agent_id, internal_user_emails=…)` — filter
  out internal testing accounts, return only real visitors.
- `histories.list_negative_feedback_turns(agent_id, …)` — walk every
  conversation and surface assistant turns flagged with `sys_improve`. The
  one-call answer to "what's failing in production?".
- `eval_mod.list_runs_for_case(case_id, agent_id, workspace_id, evaluator_id)`
  — score history of one case across every version. Use to identify when a
  regression first appeared.
- `agents.get_latest_draft_history_id(agent_id)` — find the newest
  unpublished version (the one your last `agent_apply.py` PUT created).

## The 9-stage lifecycle

Source of truth for endpoints: **`API_CHEATSHEET.md`** inside this skill dir.
Read it before writing payloads by hand — the **Gotchas** section at the end
captures the non-obvious traps.

| Stage | Purpose | Primary helpers |
| --- | --- | --- |
| 0. Scope alignment | Confirm in-scope categories, out-of-scope, lead goal, hard rules with the user | `AskUserQuestion` → save to `.codeer/scope.md` |
| 1. Author | Create/update agent + tools | `scripts/agent_apply.py`; `agents.create()` / `agents.update()` |
| 2. Knowledge base | Create KB, folders, upload files | `scripts/kb_upload.py`; `kb.create_kb()` / `kb.upload_files()` |
| 3. Live Test (debug only) | Chat against a specific draft version — used to investigate a failing eval, not as a default validation step | `chats.create()`, `chats.send_message(agent_history_id=…)` |
| 4. Version | List/inspect `AgentHistory` snapshots | `agents.list_versions()`, `agents.get_version()` |
| 5. Eval cases | Create cases with per-evaluator rubrics — **one per scope category from stage 0**, plus reverse / out-of-scope / hallucination-trap cases | `scripts/eval_cases_apply.py`; `eval_mod.create_case_with_rubrics()` |
| 6. Eval run | Trigger + read results per version, then **STOP and report non-perfect cases**. Use `--diff-vs <prev_hid>` after every prompt change to catch regressions in unrelated cases. | `scripts/eval_run.py`; `eval_mod.trigger()`, `eval_mod.get_results()`, `eval_mod.list_runs_for_case()` for per-case score history |
| 7. Publish | Promote a specific version (only after explicit user direction) | `agents.publish_version()`, `agents.check_impact()` |
| 8. Post-release | Read histories + feedback. Filter to real visitors and surface flagged turns. | `histories.list_production()`, `histories.list_negative_feedback_turns()`, `histories.get_conversations()` |
| 9. Rollback | Re-publish an older version | `agents.publish_version()` on older `history_id` |

## Top gotchas (quickref — full list in API_CHEATSHEET.md)

1. **`/agents` is published-only.** Use `/agents/all` with both `wid` **and**
   `oid` while iterating on drafts. Server returns `400 Organization ID is
   required` if you omit `oid`. Look up org-for-workspace via
   `/accounts/me` → `profile.workspace_organization_map`.

2. **Form field `type` has a fixed enum.** Valid: `shortText`, `longText`,
   `number`, `dropdown`, `radio`, `checkbox`, `date`. There is **no** `text`,
   `email`, or `select`. The backend validator is lenient and will save broken
   tools that render as blank fields in the UI. The skill's
   `codeer_cli/_validate.py` catches this before POST/PUT — **don't bypass
   validation**.

3. **The UI's `Standard` column is a per-(case, evaluator) rubric.** The
   `rubric` arg on `POST /eval/cases` is a default, not what the UI reads.
   Always use `eval_mod.create_case_with_rubrics(rubrics_by_evaluator={...})`
   or call `eval_mod.set_rubric()` for each evaluator explicitly. Different
   evaluators should get differently-worded rubrics (Style/Tone judges **how**;
   Content Compliance judges **what**).

4. **Apply (PUT) already forks a new version.** Every `PUT /agents/{id}`
   auto-creates a new `AgentHistory` with status=`draft`. Test that draft via
   `chats.send_message(agent_history_id=<draft id>)` or
   `eval_mod.trigger(agent_history_id=<draft id>)` — never by mutating the
   live version.

5. **CSRF is enforced on every non-GET.** The wrapper and client handle this,
   but if you curl by hand, send both the `csrftoken` cookie **and** the same
   value as an `X-CSRFToken` header.

6. **KB `POST /nodes` has no `type` field.** `parent_id=null` creates a KB root;
   `parent_id=<id>` creates a folder under it. Files never come through this
   endpoint — only through `/files/upload`. Use `kb.create_kb()` and
   `kb.create_folder()` for clarity.

7. **KB upload needs a single JSON-encoded form field called `form`** (Django
   Ninja quirk) and an explicit `Content-Type` per file (httpx's
   `application/octet-stream` default gets silently rejected with
   `status=FAILED, node_id=null`). `kb.upload_file()` / `kb.upload_files()`
   handle both.

8. **A KB has exactly ONE level of folders.** KB root → files OR folders →
   files (inside folders). The backend will silently create grandchild
   folders but the UI won't render them. Always pass the **KB root id** as
   `parent_id` to `kb.create_folder()`. For deeply-nested source material,
   flatten first with the `kb-indexing` skill (it encodes the path into the
   filename).

## Joining an existing agent mid-flight (iteration loop)

The 9-stage lifecycle above is the greenfield path. Most real work starts
with an agent that **already exists and has production traffic**. The task
is to tighten rubrics, fix prompt regressions, or add coverage for newly
observed failures — not to build from scratch.

### Entry point: reconnaissance

1. **Read the current version.** `GET /agents/{id}` + inspect the
   `system_prompt` and `unified_tools`. Use `agent_diff.py` if you need
   to compare against a prior version the user references.
2. **Pull production feedback.** `histories.list_negative_feedback_turns()`
   surfaces every assistant turn flagged with `sys_improve` — this is the
   fastest path to "what's failing." Filter out internal emails via
   `internal_user_emails`.
3. **Read existing eval rubrics.** `eval_rubrics.py` dumps the current
   (case, evaluator) rubric table. Understand what the eval suite is
   already checking before adding or changing anything.

### The iteration loop

Once you know what's failing and what the eval suite currently covers:

```
  ┌─────────────────────────────────────────────────────┐
  │  Diagnose: for each failing case, classify          │
  │    agent issue → fix system_prompt or KB             │
  │    rubric issue → fix rubric (eval_rubrics_apply.py) │
  │    judge noise → refine rubric wording or re-run     │
  ├─────────────────────────────────────────────────────┤
  │  Apply the fix (smallest diff)                       │
  │    prompt change → agent_apply.py (forks new draft)  │
  │    rubric change → eval_rubrics_apply.py             │
  │    new case → eval_cases_apply.py                    │
  ├─────────────────────────────────────────────────────┤
  │  Re-run ALL cases with --diff-vs <prev_history_id>  ���
  │    catches regressions in unrelated cases             │
  ├─────────────────────────────────────────────────────┤
  │  STOP and report — user decides next move            │
  └─────────────────────────────────────────────────────┘
```

**Key differences from the greenfield path:**

- You skip stages 0–2 (scope, KB, author) — those are done.
- You start at stage 8 (post-release analysis), then loop through
  stages 6 → 1 → 6 until the user is satisfied.
- New eval cases come from **production failures**, not from the scope
  doc. Each `sys_improve`-flagged turn is a candidate eval case. Use
  `eval_cases_apply.py` with `meta.previous_conversations` when the
  failure requires multi-turn context (see DESIGN_GUIDE.md §8.5).
- Rubric edits are the most common change — more common than prompt
  edits. Use the `eval_rubrics.py` → edit → `eval_rubrics_apply.py`
  cycle instead of writing one-off scripts.
- The per-case diagnosis (agent vs rubric vs judge) is mandatory before
  any fix. See the `feedback_eval_diagnosis` methodology.

## Customer-materials workflow

The default flow when the user drops you in a directory of customer files.
**Confirm with the user at every "→ ASK" gate before continuing — don't
race past these into implementation.**

### Stage 0 — Scope alignment (→ ASK)

**Do this before any KB or agent work.** Use `AskUserQuestion` to nail
down four things:

1. **In-scope categories** — 3–6 concrete categories the agent must handle
   (e.g. "B2C consultation routing", "course recommendation", "enterprise
   intake", "card product Q&A"). Each becomes an eval case in stage 5.
2. **Out-of-scope** — what to deflect or escalate (legal advice, medical,
   competitor pricing, sensitive personal data, etc.). Each becomes a
   reverse / hallucination-trap eval case.
3. **Lead-capture goal** — what counts as a successful conversion per
   category (booking link click, form submission, purchase URL, callback
   request). This shapes `system_prompt` allowed-outcomes.
4. **Hard rules** — anything the agent must never do (never quote a price
   not in the KB, never give a counsellor's personal contact, never
   invent a course slug, etc.).

Save the answers to `.codeer/scope.md` in the customer's directory.
Reference it when writing the `system_prompt` and the eval rubrics —
those are the two artifacts that have to embody scope.

### Stage 1 — KB plan (→ ASK)

Before crawling or writing any content files, confirm:

- **One KB or several?** Default is one per agent. Multiple KBs make sense
  only when the user has truly distinct knowledge domains AND wants
  separate `invocation_instruction` triggers per domain.
- **Folder layout** — flat root, or one level of folders? (KB UI only
  renders one level; see gotcha #10.)
- **Source coverage** — which URLs / docs / sources are in, which are out
  (out-of-scope from stage 0 should map to KB exclusions too).
- **Naming convention** — descriptive `NN_topic.md` filenames vs. opaque
  IDs. If sources are a deep tree of opaque names, use the `kb-indexing`
  skill's `flatten` + `enrich` + `index` modes.

### Stage 2 — Prep KB content

Crawl / write `kb/*.md` files. Keep filenames descriptive (the KB tool
exposes them to the agent). Include a `22_服務地圖` style file that maps
visitor categories from stage 0 → KB content → next-step URL or tool —
this is the agent's decision aid.

### Stage 3 — Build KB in Codeer

```bash
uv run --with 'httpx>=0.27' python $SKILL_DIR/scripts/kb_upload.py \
    --kb-dir kb/ --name "<KB display name>" \
    --workspace <ws_id> --org <org_id> --out .codeer/kb_ids.json
```

`.codeer/kb_ids.json` now contains `kb_id`, `node_ids`, `name_to_id` —
feed those into the agent payload.

### Stage 4 — Build agent

Write `.codeer/agent_payload.json` (see `examples/donation_agent.json`
for the shape). Pull `system_prompt` allowed-outcomes and boundaries from
`.codeer/scope.md`; copy the KB node_ids from `.codeer/kb_ids.json`.

```bash
uv run --with 'httpx>=0.27' python $SKILL_DIR/scripts/agent_apply.py \
    --payload .codeer/agent_payload.json --out .codeer/agent_ids.json
```

### Stage 5 — Build eval cases (one per scope category)

Write `.codeer/eval_cases.json` with **one case per in-scope category**
from stage 0, plus boundary cases for each hard rule and a
hallucination-trap case for each out-of-scope category. Each case carries
per-evaluator rubrics — Style/Tone judges *how*, Content Compliance
judges *what*.

```bash
uv run --with 'httpx>=0.27' python $SKILL_DIR/scripts/eval_cases_apply.py \
    --cases .codeer/eval_cases.json --agent <agent_id> --out .codeer/case_ids.json
```

### Stage 6 — Run evals → STOP and report

**Do not run live test chats as a default validation step.** Skip
straight from build → eval. Run:

```bash
uv run --with 'httpx>=0.27' python $SKILL_DIR/scripts/eval_run.py \
    --agent <agent_id> --history <hid> --workspace <ws_id> --out .codeer/eval_results.json
```

Then:
1. Print the per-(case, evaluator) score table.
2. For every score < 1.0, surface the case label, evaluator name, score,
   and the evaluator's `reason` text.
3. **Stop. Wait for explicit user direction** before iterating the prompt,
   editing the KB, or publishing. Do not assume the next move; the user
   may want to fix the prompt, fix the KB, edit the rubric, or accept
   the score as-is.

Live Test is for *debugging a specific failing case after eval* — not for
"sanity-checking" an agent before evals. Use `chats.send_message()` only
when you've identified a case to investigate.

### Stage 7+ — Publish, monitor, rollback

Only after the user gives an explicit go on stage 6 results.

## What lives in this skill dir

```
codeer-agent/
├── SKILL.md                  ← you are here — orientation + lifecycle
├── DESIGN_GUIDE.md           ← read when designing/brainstorming an agent (now includes §0 scope alignment)
├── API_CHEATSHEET.md         ← endpoint reference + gotchas (the "how")
├── examples/                 ← reusable JSON payloads (donation_agent.json, eval cases)
└── scripts/
    ├── codeer                ← shell wrapper for raw GET/POST against the API
    ├── kb_upload.py          ← stage 3: build KB + upload + poll (reusable CLI)
    ├── agent_apply.py        ← stage 4: POST or PUT agent from JSON payload
    ├── eval_cases_apply.py   ← stage 5: bulk-create eval cases with rubrics
    ├── eval_run.py           ← stage 6: trigger eval, print non-perfect analysis
    ├── agent_diff.py         ← compare system_prompt + tools between two versions
    ├── eval_rubrics.py       ← read per-(case, evaluator) rubrics
    ├── eval_rubrics_apply.py ← apply rubric edits (pairs with eval_rubrics.py)
    └── codeer_cli/           ← Python package, importable
        ├── client.py  constants.py  _validate.py
        ├── agents.py  kb.py  chats.py  eval_.py  histories.py
        ├── parse.py          ← typed views over response shapes (use this)
        └── cli.py
```

**Pick which doc to read based on what's happening:**
- User is brainstorming an agent ("what should it do? which tools?") → **DESIGN_GUIDE.md**
- User wants to execute a specific change (create, upload, update, eval) → **API_CHEATSHEET.md** + this file's lifecycle table
- Either way, **DESIGN_GUIDE.md** owns the wisdom on tool choice, instruction-writing, and composition patterns; the cheatsheet owns the request shapes.

## Parsing return shapes

Raw API responses are dict-shaped and inconsistent (uppercase enums in some
places, nested feedback structures, tool calls hidden inside `content` text).
Use the parsers in `codeer_cli.parse` instead of unwrapping by hand:

```python
from codeer_cli import (
    parse_agent,           # raw -> AgentSummary  (tools_by_type, kb nodes, form fields)
    summarize_history,     # (history, conversations) -> HistorySummary  (tool counts, tokens, feedback)
    parse_conversations,   # raw list -> list[ConversationTurn]  (text + tool_calls + sources)
    parse_tool_calls,      # content str -> list[ToolCall]  (name, call_id, tokens)
    strip_tool_markers,    # content str -> assistant final text without <tool …> markers
    parse_eval_result,     # raw -> EvalResultSummary  (score, reason, output)
    parse_kb_node,         # raw -> KBNode  (node_type lowercased)
)
```

Tool calls inside an assistant turn live as `<tool id=call_xxx>name</tool>`
markers in `content`. `parse_tool_calls()` extracts them (in order) and
attaches per-call token usage from `meta.token_usage`. Tool **arguments**
and **outputs** are not persisted on the Conversation row — see Gotcha #11
in the cheatsheet for what is vs isn't recoverable from a history read.

## Keeping this skill accurate

The canonical reference for Codeer's API and capabilities is the public
documentation at **https://docs.codeer.ai**. Check it when this skill's
cheatsheet feels out of date.

If you have access to the `codeer-copilot` source repo (ask the user),
the backend + frontend enums this skill validates against live in:
- `codeer/agents/types.py` — `UnifiedToolType`, `PublishState`, `HttpRequestConfig`.
- `web/src/types/requestForm.ts` — `FormFieldType`, `FormField`.
- `codeer/eval/types.py` — eval case/evaluator/rubric schemas.
- `codeer/config/urls.py` + per-app `api.py` — routes.
- `codeer/agents/api.py` — agent CRUD endpoint implementations.
- `codeer/eval/api.py` — eval trigger/results/rubric endpoint implementations.
- `codeer/knowledge/api.py` — KB node/file endpoints.

**When uncertain about an API shape, parameter name, enum value, or
backend behavior, check docs.codeer.ai or read the actual source file
before guessing.** The cheatsheet and this skill doc are summaries that
can lag behind the code. For example, if you're unsure whether
`POST /eval/results/batch` takes `evaluator_id` (singular) or
`evaluator_ids` (plural), check `codeer/eval/api.py` — the function
signature is the ground truth.

When a new tool type or field type is added, update
`codeer_cli/constants.py` here and add a Gotcha note to `API_CHEATSHEET.md` if
the backend and frontend disagree (they have before).
