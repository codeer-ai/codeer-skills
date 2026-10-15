# Codeer platform basics

Read this compact reference at entry. These are platform contracts, not evidence
that a customer's environment supports or has configured them. Use registered
CLI capabilities and actual readback; never infer a command from an internal API.

## Objects and versions

An Agent is the configuration entry point. An AgentHistory is a saved **Agent
version**, whereas a conversation History records a conversation. Keep these
identities distinct. Apply saves a working version; publish selects the version
for external use. Saving, testing, publishing an Agent and publishing/configuring
a channel are separate actions. External chat uses the published Agent version;
internal Live Test can target a version. Eval must identify the exact version,
case and Tester pair; a passing draft is not automatically live.

## Knowledge and retrieval

“Uploaded,” “READY,” “selected by this Agent,” “retrieved this time” and “enough
to answer” are separate facts. Runtime needs configured files with ready
snapshots. A connected copy does not prove continuous synchronization. Empty
search does not prove the source lacks the answer: check originals, saved text,
readiness, selection, query and returned passages before assigning a cause.

Search returns excerpts; use returned node IDs and ranges for supported original
text reads. Tool-facing line ranges are 1-based inclusive; persisted raw citation
coordinates are 0-based. Unverified source coordinates do not prove excerpt/text
agreement. `truncated` alone does not distinguish the read cap from EOF or prove
that the entire file was read. Search and line reads may observe different KB
snapshots; fingerprints and READY status do not freeze mutable external sources.

## Tools, interaction and people

Distinguish requested tool, valid arguments, actual invocation, returned outcome
and business completion. Request Form, Payment and Human Handoff have interaction
lifecycles: showing a form, creating checkout or requesting transfer is not a
submitted form, successful payment or a person handling the case.

Human handoff uses the versioned Agent-level `human_handoff` setting, not a
normal `unified_tools` instance. Eligible live conversations need an identifiable
external user. A valid handoff terminates the turn; the platform supplies a fixed
message and switches to human mode. Do not invent summary/recipient arguments
or keep answering after the terminal call. Invalid arguments are not a transfer.
Contact instructions alone do not switch mode. Mode switch, notification delivery
and a person actually responding each need their own evidence. In human mode,
messages remain recorded while AI replies stop; idle timeout or an operator can
restore AI mode. `Human replies only` is an Agent-wide external response policy,
distinct from conditional handoff.

Codeer Call Agent delegates inside the deployed AI workflow, using latest
published or a fixed version. It is distinct from the coding agent's development
workers and cannot substitute for a human taking responsibility. Imported
sub-Agent references remain subject to the CLI's current deployment limitations.

## What testing can establish

Live Test is useful for exploration; independent situations need independent
history. Eval binds cases/pairs to a version for comparison. Form, payment and
handoff are dry-run interactions in Eval: it records a synthetic requested
interaction and stops, without the real human/payment/form lifecycle. It cannot
prove human mode, notifications or post-submission continuation. General HTTP
tools are **not** globally dry-run: check side effects and authorization before
execution. Channel verification additionally needs real publishing, identity,
access, delivery and presentation evidence.

History native parts expose persisted messages, tool arguments/results/outcomes
and ordering within the export contract. They omit system prompts and provider
raw traces. Missing parts do not prove no call; a legacy outcome not recorded
stays unknown. Full diagnostic export needs a compatible server and appropriate
workspace permissions; do not silently substitute another identity or legacy
route after 403/404. See [concepts](concepts.md) and
[project evidence](project.md#audit-and-run-evidence) for operational detail.

## Basis and freshness

Compiled from Codeer `docs/`, checked against source at
`8aa90eb412167ba0f24b0504fe6afa4a3e49670d` (2026-10-14 review):

| Subject | Codeer repo sources |
| --- | --- |
| Version, identity, History limits | `docs/architecture/history-cli-api-audit-20260916.md`; `agents/api.py`; `conversations/api/chats_v2.py`, `histories.py` under `codeer/` |
| KB coordinates and remaining snapshot/read limits | `docs/architecture/kb-source-coordinates.md`; `codeer/retrieval/retriever/context.py`; `codeer/llm/assistants/tools/get_context_obj_lines.py` |
| Interaction lifecycle | `docs/architecture/hitl-interaction-types.md`; `codeer/llm/assistants/tools/core.py`, `request_human_handoff.py`; `codeer/eval/tests/test_human_handoff.py` |
| Eval assignments and preserved history | `docs/integrations/external-eval-assignments.md`; `codeer/external_api.py` |
| Handoff/channel/Call Agent details absent from docs | `user-docs/docs/agent-creation/human-handoff.md`, `tools/call-agent.md`; `user-docs/docs/getting-started/publish.md`; `codeer/llm/assistants/tools/call_agent.py` |

The old `docs/index.md` developer-copilot description is not the current product
basis. Later KB coordinate repairs supersede that audit's older coordinate bug,
but do not prove remote indexes were rebuilt. Live availability, deployment,
notification destinations, staffing and provider behavior require project-specific
verification. Maintain this reference when those contracts change; customers do
not need the Codeer checkout to read it.
