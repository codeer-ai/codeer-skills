# Codeer Server Concepts

A reference for how the Codeer platform works. Use this to reason about
agent behavior, retrieval issues, and evaluation results.

---

## Knowledge Base (KB)

A KB is a collection of files (markdown, text) organized in a tree of
**KnowledgeNodes** (folders and files). Each file node has a status:

- **READY** — indexed and available for retrieval
- **PROCESSING** — upload accepted, indexing in progress
- **FAILED** — upload or indexing failed

Files are chunked into **ContextChunkRecords**, each with a 3072-dimension
embedding vector stored in an HNSW index for fast similarity search.

### KB query tools (used by the Codeer agent at runtime)

The agent queries KB content using three tools. Understanding how they work
helps diagnose retrieval failures.

#### `list_kb_files`

- **What it does**: Lists files in a KB whose names match a regex pattern.
- **Parameters**: `pattern` (POSIX regex), `tool_instance_id`, `max_results` (default 50, cap 200)
- **Returns**: Matched file names/paths, ordered alphabetically.
- **Use case**: Agent discovers which files exist before doing semantic search.
- **Failure mode**: Bad regex, or agent guesses wrong filename pattern.

#### `retrieve_context_objs`

- **What it does**: Semantic search across KB chunks.
- **Parameters**: `knowledge_node_ids` (scope), `question`, `keywords`, `max_results` (default 5), `filter_to_node_ids` (optional, intersect with discovered files)
- **Returns**: Ranked list of relevant chunks (semantic similarity + reranking).
- **Key behavior**:
  - Combines question + keywords for hybrid search
  - Supports FAQ-reserved items (see Context Object FAQ below)
  - Can be scoped to specific files via `filter_to_node_ids`
- **Failure modes**: Wrong question/keywords, relevant file not in scope, chunk boundaries split the answer.

#### `get_context_obj_lines`

- **What it does**: Fetches a specific line range from a KB file.
- **Parameters**: `knowledge_node_id` (file UUID), `line_start`, `line_end`
- **Returns**: Text content with location metadata.
- **Constraints**: Max 500 lines per call.
- **Use case**: Agent reads surrounding context after finding a relevant chunk.

### Typical retrieval flow

1. Agent calls `list_kb_files` with a pattern to find relevant files
2. Agent calls `retrieve_context_objs` with a question, optionally filtering to discovered files
3. Agent calls `get_context_obj_lines` to read more context from promising results

---

## Context Object FAQ

A mechanism for routing specific questions directly to a canonical KB file.

### How it works

- A FAQ entry pairs a **question** (with its own embedding) with a **ContextObj** (KB file)
- During `retrieve_context_objs`, FAQ embeddings are matched against the user's query
- Matched FAQ items are flagged as `retrieval_route="faq_reserved"` and prioritized in results
- Optional FAQ line ranges reserve chunks that overlap a stable passage in the target file
- This gives retrieval a direct question-to-source signal, bypassing pure semantic similarity
- In CLI KB output, the FAQ target `ContextObj.id` appears as the file node's
  `snapshot_object_id`

### When to use

- The canonical file is already uploaded, attached, and indexed (status: READY)
- The agent's query is reasonable, but semantic search often misses or ranks the target file too low
- A high-value question must reliably land on one source of truth
- The relevant passage has stable line numbers, if using line ranges

### When NOT to use

- Missing KB content (FAQ can't route to what doesn't exist)
- Unclear file structure or bad naming (fix the content first)
- Bad tool-use instructions in the prompt (agent isn't querying at all)
- Rubric/source-of-truth conflicts (human decision needed first)
- Frequently regenerated files with drifting line numbers, unless you are prepared to refresh the ranges

---

## Evaluators

An evaluator is an LLM judge that scores agent responses. Each evaluator has a
**system prompt template** with placeholder variables filled at runtime.

### Template variables

| Variable | Content |
| --- | --- |
| `{input}` | The user's question (eval case input) |
| `{output}` | The agent's generated response |
| `{rubric}` | Per-case evaluation criteria (written by the skill operator) |
| `{expected_output}` | Reference answer (if provided) |
| `{tool_steps}` | Formatted tool-use steps: type, arguments, results |

### What the evaluator does NOT have access to

- The agent's system prompt
- The agent's KB content
- The agent's settings or tool configuration
- Any diagnosis notes or context from the skill operator

This means rubrics must be **self-sufficient** — they carry all the criteria
the judge needs to score correctly.

### Scoring

Default range: 0.0–1.0. A score of 1.0 means the rubric criteria are fully met.
The evaluator outputs a score and a `reason` text explaining the judgment.

### Common evaluator types

- **Content Compliance** — judges _what_ the agent said (factual correctness, completeness, adherence to rules)
- **Style/Tone** — judges _how_ the agent said it (language, formality, empathy, brand voice)

### Tool type identifiers in evaluator context

When an evaluator's template includes `{tool_steps}`, tool calls appear with
these canonical type names:

| Tool type | Meaning |
| --- | --- |
| `consultant_retrieve_context_objs` | Search Knowledge Base |
| `consultant_list_kb_files` | List Knowledge Base Files |
| `consultant_get_context_obj_lines` | Read Knowledge Base File Lines |
| `consultant_search_web` | Search Web |
| `consultant_fetch_web_content` | Fetch Web Page Content |
| `consultant_call_agent` | Call Agent |
| `consultant_request_form` | Request Form |
| `consultant_payment` | Payment |
| `consultant_memory` | Memory |
| `consultant_http_request` | HTTP Request |
| `consultant_generate_image` | Generate Image |

---

## Agent Versions

An agent maintains a version history via **AgentHistory** records.

### Version states

| Status | Meaning |
| --- | --- |
| **DRAFT** | Working version, not yet live. Created by `codeer agent apply`. |
| **PUBLISHED** | Currently live across all channels. One published version at a time. |
| **ARCHIVED** | Previously published, preserved for rollback. |

### Key behaviors

- `codeer agent apply` always creates a new DRAFT (auto-forks from current state)
- Publishing promotes a DRAFT to PUBLISHED; the previous published version becomes ARCHIVED
- Rollback re-publishes an ARCHIVED version (non-destructive; nothing is deleted)
- Each version stores: system prompt, tools config, KB attachments, LLM model settings, version note

### Eval and versions

- `codeer eval run --latest` evaluates the newest draft (default behavior)
- `codeer eval run --history <uuid>` pins evaluation to a specific version
- These are mutually exclusive flags
- `--evaluator <uuid>` is the common path for many cases with one tester
- If no evaluator is supplied, eval runs the assigned case/evaluator pairs

---

## Available Agent Tools

Each agent can have up to 10 tool instances (max 5 Call Agent, max 1 Memory).

| Tool | Purpose |
| --- | --- |
| **Knowledge Base** | Search stable reference documents |
| **Web Search** | Fetch latest public information |
| **Image Generation** | Create visuals from text descriptions |
| **Call Agent** | Hand off to other specialized agents |
| **Request Form** | Collect structured user input |
| **HTTP Request** | Send/fetch data from external APIs |
| **Payment** | Request approved payments before proceeding |
| **Memory** | Remember stable user preferences across conversations |

### Tool configuration

Each tool instance has:

- **When to Use** (`invocation_instruction`): Tells the agent when to invoke this tool. Critical for correctness — a vague instruction leads to missed or spurious tool calls.
- **Tool-specific settings**: KB node IDs, API endpoints, form fields, etc.
- **Instance ID**: Scopes the tool to specific resources (e.g., which KB to search).

### Request Form field types

Valid `type` values for form fields: `shortText`, `longText`, `number`,
`dropdown`, `radio`, `checkbox`, `date`. Using invalid types (e.g. `"text"`,
`"email"`, `"select"`) causes the UI to render blank.
