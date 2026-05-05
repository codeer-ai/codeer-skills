# Codeer agent — design guide

Read this when the user is **deciding what to build**, not when they already
know what they want and just need it executed. Sister docs:

- `API_CHEATSHEET.md` — endpoint shapes + gotchas (the "how")
- `SKILL.md` — orientation + lifecycle (the "what to run when")
- This file — capabilities + design opinions (the "what to choose and why")

Source of truth — the public docs at **https://docs.codeer.ai**, plus
the `codeer-copilot` source repo if the user has access (ask them):
- Capabilities & wisdom: `user-docs/docs/agent-creation/` (in repo) or docs.codeer.ai
- Tool type enum + field shapes: `codeer/agents/types.py`
- Eval schemas: `codeer/eval/types.py`, `codeer/eval/api.py`
- Endpoint implementations: `codeer/agents/api.py`, `codeer/knowledge/api.py`
- Hard limits: 10 tools / 5 call_agent / 1 memory per agent.

**When uncertain about an API shape or backend behavior, check
docs.codeer.ai or read the actual source file** — don't guess from the
cheatsheet alone.

## 0. Scope alignment with the user (do this FIRST)

Before any role-writing, KB work, tool choice, or implementation, get
explicit confirmation from the user on **scope**. Use `AskUserQuestion`
(or equivalent direct conversation) to pin down four things:

1. **In-scope categories** — 3–6 concrete buckets the agent must handle.
   Frame them as visitor situations, not topics. Example for a career
   counselling brand:
   - A. Personal career confusion (transition, burnout)
   - B. Aspiring counsellor (training, certification)
   - C. Enterprise / HR (team training, hiring)
   - D. Card / self-tool curious (purchase, gifting)

2. **Out-of-scope** — what to deflect or escalate. Example:
   - Legal / medical / tax advice
   - Specific counsellor private contact
   - Pricing not in the KB
   - Sensitive personal disclosures

3. **Lead-capture goal** — what counts as a successful conversion
   *per category*. This shapes `system_prompt` allowed-outcomes and is
   the test the agent has to pass. Example:
   - A → 1-on-1 booking link or callback form
   - B → course enrolment URL or callback form
   - C → enterprise intake form (always)
   - D → product purchase URL

4. **Hard rules** — anything the agent must never do. These map 1:1 to
   eval rubric "max 0.3" clauses. Example:
   - Never quote a price not in the KB
   - Never invent a course slug; if unsure, give the root URL plus a
     search hint
   - Never give a counsellor's private contact

**Save the answers to `.codeer/scope.md` in the customer's directory.** The four
things above feed directly into:

- `system_prompt` (allowed outcomes + boundaries + hard rules)
- KB content scope (don't crawl out-of-scope material)
- Eval cases (one per in-scope category + one per hard rule + one
  hallucination trap per out-of-scope category)

Skipping this stage leads to: a KB that's too broad, a system prompt
written from intuition, and eval cases invented after the fact that
happen to pass — none of which is anchored to user intent.

## 1. The decision order — role first, tools last

After scope is locked (§0), build the agent itself in this order:

1. **Role** — one sentence: who is this agent, who are its users, what is the
   single job it does well? Should be a direct synthesis of the in-scope
   categories from §0.
2. **Allowed outcomes** — the small set of things the agent is allowed to
   produce (recommend X, hand off to Y, fill form Z). These are the
   per-category lead-capture goals from §0.
3. **Boundaries** — the hard-rules list from §0, plus anything else
   it must not guess (no invented prices, no tax advice, etc.).
4. **Knowledge sourcing** — for each piece of knowledge the agent needs,
   pick the right home using the table in §2.
5. **Tools** — only after 1–4 are clear. A tool that doesn't map to a real
   step in the role is overhead, not capability.
6. **Build → Eval cases (1 per category) → Eval run → Stop and report** —
   the lifecycle the skill drives. Live testing is a debugging tool used
   on individual failing cases, not a default validation step.

If the user starts at step 5, walk them back to step 1. If the user
starts at step 1 without §0 locked, walk them back to §0.

## 2. Where knowledge lives — Instructions vs Knowledge Base vs Web Search vs Memory

| Signal | Best home |
| --- | --- |
| Must apply on **every** turn (role, tone, outcome list, hard rules) | `system_prompt` (Instructions) |
| Sometimes-needed reference material, you have or can produce a clean file | `knowledge_base` tool |
| Answer depends on **today's** public information | `web_search` tool |
| Stable per-user **preference** the agent should remember next time | `memory` tool |
| One-time scheduling/intake detail just for this conversation | leave in the chat thread, don't persist |
| Sensitive info (passwords, PII, medical specifics) | NEVER memory; usually nowhere — defer to humans |

If a rule must apply *every* turn, keep it in `system_prompt` even if it
also lives in a KB file — the agent doesn't read its KB on every turn.

## 3. Tool-by-tool design notes

The 8 `UnifiedToolType` values. For each: what it's for, what it isn't,
the most common mistake, and a `When to Use` (`invocation_instruction`)
strong/weak example. Per-tool deep dives live in
`user-docs/docs/agent-creation/tools/<name>.md`.

### `knowledge_base`

**Use when** the agent needs to search stable reference material —
service definitions, SOPs, policies, FAQs, internal product docs. Files
live in `KnowledgeNode` trees scoped to the workspace (one level of
folders per KB; see API gotcha #10).

**Don't use for** live/changing info (use `web_search`), or for rules that
must fire every turn (put those in `system_prompt`).

**Common mistakes**
- Dumping every workspace doc into one folder — retrieval gets noisy and
  hard to debug. Split by use-case.
- Hiding load-bearing rules only in KB files — the agent reads KB on
  retrieval, not always. Keep core rules in `system_prompt` too.
- Vague trigger ("`Use the knowledge base when needed.`").

**Strong `invocation_instruction`**
> Use this knowledge base when the user asks about consultation types,
> routing rules, or handoff expectations that should stay consistent
> across conversations.

**Field hints**: `knowledge_node_ids` is a list of file/folder UUIDs from
the workspace KB (use `kb.list_nodes()` to gather). `name` is what the
agent sees as the tool's display name in its prompt.

### `web_search`

**Use when** the user explicitly needs the latest public information and
your team doesn't curate it internally.

**Don't use for** anything your KB should answer (slower, less consistent),
or as a generic "look stuff up" fallback.

**Common mistakes**
- Letting it replace internal knowledge ("just search the web") → answers
  drift, become inconsistent, slow.
- Leaving `domain` empty for high-stakes Q's → the agent ends up citing
  random sources. Constrain to trusted domains when answers matter.
- Vague trigger.

**Strong `invocation_instruction`**
> Only use Web Search when the user explicitly asks for the latest public
> guidance, and prefer official or medically reviewed sources before
> answering.

**Field hints**: `domain` is the allowlist (single domain string today —
check schema if multi-domain is needed). Cite sources in the answer when
verification matters.

### `call_agent`

**Use when** another (already-published) agent has a clearly narrower
specialty than the caller. Common pattern: front-door agent clarifies,
specialist agent executes (booking, deep diagnostics, language-specific
handoff).

**Don't use when** the split is cosmetic, the target agent is barely
different from the caller, or you can't explain when the handoff fires.

**Common mistakes**
- Pointing at an unpublished agent → there's no stable version to call.
  **The target agent must have at least one published version first.**
- Splitting too aggressively. Two agents with overlapping jobs → both fire
  and contradict each other.
- Recursive handoffs. Called agents can't keep calling other agents in a
  deep chain.

**Strong `invocation_instruction`**
> Use Scheduling Desk after you have identified that the user is ready to
> request a booking or callback and you need a more structured handoff.

**Field hints**: `agent_id` is the target. `version` is optional — omit
to follow the target's latest published version (right default during
iteration); set explicitly when you need a stable, predictable handoff.

**Limit**: 5 call_agent tools per agent.

### `image_generation`

**Use when** the user wants a brand-new visual created from text — concept
illustration, simple mockup, hero-image draft.

**Don't use for** approved brand assets that already exist, or final
production artwork that needs human review before sharing.

**Common mistakes**
- Using it where a real source asset already exists.
- Treating the model choice as a fix for weak instructions — the model
  matters, but the trigger and prompt matter more.

**Strong `invocation_instruction`**
> Use this tool when the user asks for a new visual concept, illustration,
> or simple mockup that can be created from a text description. Do not
> use it for factual questions or when an existing approved asset should
> be reused.

**Field hints**: `image_model` selects the generation model. The agent
controls the actual prompt + style direction at runtime, so the
`invocation_instruction` should focus on **when** and **what kind**, not
exact visual details.

### `request_form`

**Use when** the conversation has reached a stage where the next step
needs the same fields every time and structured intake beats free-text
chat (callback request, ticket creation, donation intake).

**Don't use** as the opening move. The form should appear after the user
has agreed to the next step — not as the first message.

**Common mistakes**
- Opening the form too early — feels transactional before the user
  understands the recommendation.
- Stuffing every possible field in. Start with the smallest set that
  unblocks the next operational step.
- Asking for fields the team doesn't actually use downstream.

**Strong `invocation_instruction`**
> Use this form only after the user agrees to a human callback, so you
> can collect contact details and a preferred follow-up window without
> asking everything manually in chat.

**Field hints**: `custom_form_schema = {id, title, description, fields: [...]}`.
Every field needs `id, type, name, label, question, required` non-empty.
Type enum is `shortText / longText / number / dropdown / radio /
checkbox / date` — see API gotcha #2. `dropdown` and `radio` need
`options: [{value, label}]`. Order fields the way a human operator would
ask them.

### `http_request`

**Use when** the agent needs to send/fetch structured data via an
external HTTPS endpoint with a stable contract. One narrowly-scoped
business action per tool ("Create Callback Lead", "Check Availability"),
not a generic "CRM Integration".

**Don't use** as an escape hatch when the contract is unclear, or for
data your KB should hold, or for irreversible actions without a human
approval step.

**Common mistakes**
- Generic catch-all configs — fragile, hard to debug.
- Firing too early in the flow, before the user has committed to the
  next step.
- Sending every available field "just in case".

**Strong `invocation_instruction`**
> Use this request only after the user agrees to a human callback and you
> have collected their preferred contact details. Send the callback
> request to the CRM so the operations team can follow up.

**Field hints**: `http_request = {method, url_template, auth, headers,
query_params, body}`. URL must be HTTPS. Templates support
`{{user.email}}`, `{{user.id}}`, `{{user.external_id}}`. Auth types:
`none / bearer / apiKey / basic / customHeader`. Name the tool after the
business action, not the API vendor.

### `memory`

**Use when** the agent should remember **stable, user-confirmed**
preferences across future conversations — preferred language, preferred
contact method, whether they prefer self-service vs callback.

**Don't use for** secrets/passwords, PII, sensitive medical or legal
detail, one-off scheduling notes, or long conversation summaries that
will go stale.

**Common mistakes**
- Letting it remember free-text. Memory becomes noisy, and answers start
  feeling overconfident or weirdly personalized.
- Storing PII because the user happened to mention it. Be explicit in the
  `invocation_instruction` about what's off-limits.
- Using memory in flows where the user identity isn't stable (anonymous
  web traffic without sign-in) — see channel table below.

**Strong `invocation_instruction`**
> Remember only stable, user-confirmed preferences such as preferred
> language, preferred contact method, and whether the user prefers a
> callback over self-service. Do not store medical details, secrets, or
> one-time scheduling notes.

**Field hints**: no schema fields beyond `id`, `type`, `name`,
`invocation_instruction`. The instruction does all the work.

**Limit**: 1 memory tool per agent.

**Channel reliability for memory**:
| Channel | Memory works? | What you need |
| --- | --- | --- |
| Web Client | Cookie/local-storage based; fully stable **after sign-in**. | Require sign-in for memory-dependent flows. |
| Web Widget | Same default; pass `User_ID` at widget init for stability across devices. | Pass your product's user id when initializing the widget. |
| LINE | Yes, always (stable LINE ID). | Nothing. |
| Slack | Yes, but Slack treats a thread as the **first** user. Plan for DMs over channels when memory matters. | Prefer DM channels. |

### `payment`

Documented in the enum but not covered by user-docs design guidance —
treat as advanced/experimental. Don't recommend unless the user
specifically asks. Confirm the current product status before use.

## 4. Writing strong `system_prompt` (Instructions)

A strong instruction block covers five things explicitly:

1. **Role** — who/what the agent is, in one sentence.
2. **Clarifying step** — what to ask before recommending anything.
3. **Allowed outcomes** — the small list of legal next steps.
4. **Handoff rule** — when to escalate to a human / specialist agent.
5. **Hard boundaries** — what it must never invent or guess.

If any of those is missing, the agent will sound plausible while still
making the wrong decision.

**Weak**
> You are a helpful consultation assistant. Ask questions and help users
> find the right service.

**Strong**
> You are Consultation Desk, the first point of contact for people who
> need help with pain, mobility, or recovery questions.
>
> Before recommending anything, ask 2 or 3 clarifying questions about the
> issue, its duration, and any previous treatment.
>
> Choose exactly one next step:
> - Initial Consultation
> - Specialist Consultation
> - Human Callback
>
> Never invent services, prices, timelines, or guaranteed outcomes. If
> the case is urgent, sensitive, or unclear, recommend Human Callback.

The strong version gives the model something to **execute**, not just
something to imitate.

## 5. LLM model selection

Default → switch only when testing reveals a specific failure you can
name. Don't switch because a stronger model "exists".

| Observed problem | What to try |
| --- | --- |
| Too slow for a routing/front-door conversation | Faster model |
| Misses nuance, makes weak routing decisions | Stronger reasoning model |
| Sounds unnatural in target language | Model with better quality for that language |

When comparing models: same 3–5 prompts, change only the model, record
what improved/regressed, save with a `version_note` that says why.

## 6. Composition patterns (common stacks)

These compose into useful agents. Adapt — don't copy.

**Front-door routing agent (e.g. Consultation Desk)**
- `system_prompt`: role + 2–3 clarifying Q's + outcome list + handoff rule + boundaries
- `knowledge_base`: workspace-scoped reference (services, routing, SLAs)
- `request_form`: only after user commits to the next step
- `call_agent`: handoff to a specialist (Scheduling Desk) once route is clear
- `memory`: language + contact preference, narrow

**KB-driven Q&A (e.g. customer-docs assistant, 接待員)**
- `system_prompt`: role + tone + "always cite a source" + boundaries
- `knowledge_base`: the KB itself (often pre-flattened via `kb-indexing` skill)
- Optional `web_search` for explicit "what's new today?" queries

**Donation/intake desk** (the donation_agent.json example)
- `system_prompt`: warm role + when-to-form rule + don't-guess-tax boundary
- `request_form`: 4-field intake (name/email/amount/cause)
- `memory`: language + cause preference, no PII

**External action agent**
- `system_prompt`: when the action fires + what data is needed first
- `request_form`: collect needed fields if not already in chat
- `http_request`: one tool per business action (`Create Lead`, `Check Availability`)
- `call_agent`: hand off to a follow-up agent if the action triggers a workflow

## 7. Operator habits worth surfacing

- **Start with one tool**, add the next only after testing reveals the gap.
  Most weak agents are over-tooled, not under-tooled.
- **Save real failures as eval cases.** When the user says "we should
  never miss this again", that's an eval case. Use the skill's
  `eval_.create_case_with_rubrics()`.
- **Use `version_note`** that explains *why*, not what changed. Six
  months later, the diff shows what; only the note shows why.
- **Live Test on the draft**, not on prod. The skill pins
  `agent_history_id` for both chat and eval — see API gotcha #4.
- **Publish intentionally.** Run `agents.check_impact()` first if other
  agents `call_agent` this one.

## 8. Writing rubrics that don't backfire

LLM-judged rubrics are policy statements the judge interprets, not regex
matchers. They fail in characteristic ways. Internalize these before
writing your fifth rubric:

### Pitfall 1 — Substring blacklists also match the negated form

❌ Rubric says: "Forbidden phrase: 「我看到您上傳的…」"
The judge will fire on **「沒有看到您上傳的」** too — same content words,
opposite meaning. Real example from the 心傳 vet agent: the agent correctly
said "目前**沒有**看到您附上的報告" (truthful no-attachment reply) and the
judge marked it critical because the rubric listed "我看到您上傳的…" as a
forbidden phrase.

✅ Phrase by **behavior**, not by string. Show ✓/✗ examples both inline:
```
嚴禁假裝已收到/正在處理任何不存在的上傳檔案。
- ✗ 違規 (假裝收到)：「我已收到您的報告」「我正在為您辨識」
- ✓ 合規 (如實否認)：「目前沒有看到您附上的檔案」「請您再上傳一次」
```

### Pitfall 2 — Same noun, different referent

In the 心傳 agent, "確認您的資料" can mean:
(a) Memory tool reading basic contact info — **allowed** (the agent has Memory)
(b) Looking up medical records — **forbidden** (no such system access)

A rubric that says "嚴禁同步確認之前的資料" overgeneralizes (a) into (b).
The judge fires on (a) and you waste a fix-cycle re-tightening the prompt
when the prompt was fine.

✅ Always specify the referent class:
```
✓ Allowed: basic contact info (姓名/電話/聯絡資料/基本建檔資料).
✗ Forbidden: medical records (就診紀錄/病歷/診斷/藥單/檢驗報告/分期).
判別法: 句子目的是「聯絡/預約」→ ✓；目的是「醫療判斷/病史」→ ✗.
```

### Pitfall 3 — No ✓/✗ examples → judge improvises

LLM judges anchor on examples. Without them, marginal phrases get scored by
the judge's own ad-hoc reasoning, which drifts run-to-run. Always include
both compliant and non-compliant example phrases in the rubric body — the
judge cites them in `reason`, which makes drift visible and debuggable.

### Pitfall 4 — Critical-zero rules need to say "→ 0"

If certain violations should mark the case 0 regardless of partial compliance
elsewhere, write that explicitly:

```
評分原則：第 X 條任一觸發即直接 0 分（critical）。其餘違規每項扣 0.2。
```

Otherwise the judge averages partial compliance and you get 0.7 on a case
that contained a hallucinated diagnosis — technically "mostly compliant"
but the one critical violation was the only thing that mattered.

### Pitfall 5 — Per-evaluator differentiation

Style/Tone judges *how* the agent talked. Content Compliance judges *what*
it said. Don't paste the same rubric into both — the judge compares Actual
Output to the rubric strictly, and tone clauses confuse a content judge
about whether to score factuality. Different evaluators get differently
**worded** rubrics even when they cover the same behavior.

### Pitfall 6 — System-prompt fix that backfires somewhere else

Tightening "no hallucination" → model becomes self-conscious about its
limits → starts narrating its internal actions ("我會幫您查記憶") → trips
a different rubric. Tightening "be conservative on medication" → model
swings to over-warning ("不要餵") on supplement questions → trips the
"no negative verdicts" rubric.

After every prompt change, **rerun the entire eval suite**, not just the
case you targeted. Trigger the new version with `POST /eval/runs`, read
results with `POST /eval/results:batch`, and compare every case whose score
moved up or down vs the previous version. The Tier-N regression list catches
these side effects before publish.

### Pitfall 7 — "Don't say X" rubric without an alternative

If you forbid a phrase, tell the agent (via system prompt) what to say
instead. A pure-prohibition rubric leaves the model groping for substitutes
and frequently lands on the next-worst thing. Pair every "✗ never say X"
rubric with "✓ standard reply: …" in the system prompt.

### Iteration cadence (this works in practice)

1. Write rubric with ✓ and ✗ examples + critical-zero rule if applicable.
2. Run eval. Read `reason` for every <1.0 case.
3. If the **agent answer was actually correct** but rubric scored 0 → fix
   the rubric (this happens more than you'd think — it was the closing
   move on 心傳 Case 4).
4. If the agent answer was wrong → fix the system prompt, then re-run
   ALL cases with `--diff-vs` to catch regressions.
5. Don't chase a single case to 1.0 in isolation. Look at the whole table.

## 8.5. Multi-turn eval cases — when and how

Single-turn cases (`input` = one user message) cover most scenarios. But
some failures only surface when the agent has prior conversation context —
e.g. the owner already said their pet's name in turn 2, so the agent
should use it in turn 8 without re-asking.

### When to use multi-turn

- The failure you're testing depends on **information from earlier turns**
  (pet name, stated symptoms, previously agreed next step).
- The agent's behavior on the test input **changes based on conversation
  state** — it should refuse a duplicate form, remember a preference, or
  not re-ask a question.
- You're reproducing a **production failure** where the context of the
  full conversation was load-bearing. Single-turn reproduction would miss
  the bug.

If the test input is self-contained and the agent's correct response
doesn't depend on prior turns, use a single-turn case — it's cheaper
and easier to reason about.

### How it works

`eval_cases_apply.py` supports a `meta.previous_conversations` field:

```json
{
  "input": "那上次的心超報告結果是什麼？",
  "meta": {
    "previous_conversations": {
      "source_history_id": 10197,
      "target_conversation_id": 43350,
      "previous_conversation_count": 6
    }
  },
  "rubrics": { ... }
}
```

| Field | Meaning |
| --- | --- |
| `source_history_id` | The History.id (from `/histories`) of the real conversation to replay |
| `target_conversation_id` | The Conversation.id of the turn where `input` replaces the original user message |
| `previous_conversation_count` | Number of user+assistant turns to replay before `input` fires |

The eval engine replays the first N turns from the source conversation,
then injects your `input` as the next user message and evaluates the
agent's response. This means the agent has the full prior context
(tool calls, KB lookups, memory reads) as if the real conversation had
happened up to that point.

### Practical tips

- **Find the source conversation first.** Use `GET /histories` with an
  improvement feedback filter, then browse `/histories/{id}/conversations`
  to identify the exact turn where the failure occurred. Note the
  `history_id` and the `conversation_id` of the turn you want to replace.
- **Count turns carefully.** `previous_conversation_count` counts
  individual conversation rows (each user message and each assistant
  response is one), not round-trips. A 3-round exchange has 6 turns.
- **Multi-turn cases are more expensive.** The agent replays the full
  conversation prefix on every eval run. Use them only when the test
  genuinely requires context — don't default to multi-turn.
- **Pair with single-turn versions.** If a multi-turn case tests
  "agent uses pet name from turn 2," also have a single-turn case
  that tests the same behavior when the pet name is in the input
  itself. This separates "can the agent do X?" from "does the agent
  remember context?"

## 9. Quick decision tree (when the user is brainstorming)

```
What does the agent need to do?
├── Answer questions from stable internal docs
│   → knowledge_base + system_prompt with citation rule
├── Answer with the latest public info
│   → web_search + domain allowlist
├── Generate a visual concept
│   → image_generation
├── Hand off to a specialist (already exists, published)
│   → call_agent
├── Collect structured intake at a known stage
│   → request_form (after the next step is agreed)
├── Send/fetch via an external HTTPS endpoint
│   → http_request, one per business action
├── Remember a stable preference for next time
│   → memory + narrow rule + don't-store-PII guard
└── A rule that applies every turn
    → system_prompt, NOT a tool
```

If two boxes apply, the agent probably needs two tools — but always
start with the one most central to the role and add the next after Live
Test reveals it's needed.
