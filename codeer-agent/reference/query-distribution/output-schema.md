# Persistent Query Distribution and candidate schema

Produce one persistent canonical distribution and a local candidate pool:

- `.codeer/design/query_distribution.csv`
- `.codeer/current/local_draft_eval_input_candidates.csv`

The canonical file contains the current accepted model across sessions. Keep
its prior revisions in Git or another project revision history when available;
do not append raw histories or stale snapshots to the CSV.

## `.codeer/design/query_distribution.csv`

Required columns:

| Column | Meaning |
|---|---|
| `distribution_cell_id` | Stable unique identifier |
| `operating_model` | Support operating model |
| `task_family` | Canonical task family |
| `task_id` | Base task or state transition |
| `task_complication_id` | Optional lifecycle-specific complication |
| `representativeness_band` | `core`, `common`, `occasional`, `rare`, or `unknown` |
| `estimated_real_world_share` | Optional decimal estimate; leave blank when unsupported |
| `eval_target_share` | Designed decimal allocation |
| `industry_risk_level` | `normal`, `elevated`, `high`, or `critical` |
| `risk_type_ids` | Pipe-delimited consequence categories |
| `evidence_tier` | Evidence ladder tier |
| `evidence_confidence` | `low`, `medium`, or `high` |
| `source_population` | Population represented by the evidence |
| `adaptation_distance` | How far the evidence is from the target company and channel; blank for direct target evidence |
| `evidence_window` | Date range or checked date supporting the cell |
| `source_channels` | Pipe-delimited channels represented by the evidence |
| `sample_scope` | Conversation, record, public-source, or constructed sampling scope |
| `sample_size` | Optional count when a defined sample exists |
| `exclusions` | Material exclusions or known sampling bias |
| `evidence_basis` | Concise rationale |
| `source_urls` | Pipe-delimited URLs |
| `overweight_reason` | Required when risk intentionally raises eval allocation |
| `open_gap` | Remaining uncertainty or missing evidence |
| `last_reviewed_at` | Date the accepted cell was last reviewed |

`eval_target_share` must total 1 within a complete distribution. Do not force `estimated_real_world_share` to total 1 when material demand is unknown.

## `.codeer/current/local_draft_eval_input_candidates.csv`

Required columns:

| Column | Meaning |
|---|---|
| `candidate_id` | Unique stable identifier |
| `distribution_cell_id` | Parent distribution cell |
| `input_display` | Full single- or multi-turn input |
| `target_user_query` | Latest user message being evaluated |
| `task_id` | Base task |
| `task_complication_id` | Optional task complication |
| `industry_risk_level` | Consequence severity |
| `risk_type_ids` | Pipe-delimited risk types |
| `challenge_pattern_ids` | Pipe-delimited cross-task challenges |
| `channel_pattern_ids` | Pipe-delimited channel or language forms |
| `designed_challenge_level` | `baseline`, `moderate`, or `stress` |
| `evidence_basis` | `observed`, `adapted`, `expert_constructed`, or `synthetic_variant` |
| `evidence_confidence` | `low`, `medium`, or `high` |
| `cluster_id` | Semantic cluster |
| `variant_family_id` | Shared base scenario |
| `review_status` | `generated`, `evidence_checked`, `domain_reviewed`, or `approved` |
| `source_urls` | Pipe-delimited URLs |

Do not include expected answers or rubrics in phase 1.

## Candidate rules

- Keep `input_display` and `target_user_query` identical for a single-turn case.
- For multi-turn cases, preserve roles and place the evaluated user message last.
- Do not invent a source URL for constructed cases; cite the source that supports the base task or risk.
- Use the same `variant_family_id` for baseline and challenge variants of one situation.
- Use different candidates only when state, disclosure order, channel, risk, or failure mechanism materially changes.

## Optional `.codeer/current/query_distribution_research_notes.md`

Include scope, assumptions, evidence limitations, unresolved gaps, and proposed findings. Do not use it as a raw data dump.
