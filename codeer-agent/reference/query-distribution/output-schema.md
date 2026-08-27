# Optional Query Distribution and examples schema

Use these two persistent canonical files only when an active demand or
allocation decision justifies the optional Query Distribution:

- `.codeer/design/query_distribution.csv`
- `.codeer/design/query_examples.csv`

Draft revisions under `.codeer/current/` and replace canonical files only after
user acceptance. Keep prior revisions in Git or another project history when
available.

## `query_distribution.csv`

Required columns:

| Column | Meaning |
|---|---|
| `query_type_id` | Stable unique identifier |
| `customer_task` | The outcome or help the customer is seeking |
| `journey_state` | State or transition that changes correct handling; blank when unnecessary |
| `demand_band` | `core`, `common`, `occasional`, `rare`, or `unknown` |
| `risk_level` | `normal`, `elevated`, `high`, or `critical` |
| `target_cases` | Non-negative integer acceptance-eval allocation |

`target_cases` is an eval design count, not a production traffic estimate. The
sum must be greater than zero.

## `query_examples.csv`

Required columns:

| Column | Meaning |
|---|---|
| `example_id` | Stable unique identifier |
| `query_type_id` | Parent query type |
| `input` | Full single- or multi-turn customer input |
| `provenance` | `observed`, `adapted`, or `constructed` |
| `purpose` | `representative`, `boundary`, or `risk` |

Every query type must have at least one example. Every query type with
`target_cases > 0` must have at least one `representative` example.

For multi-turn examples, preserve roles and place the evaluated user turn last.
Deidentify observed inputs. Do not include expected answers or rubrics here.

## Optional fields

Additional columns are allowed but are not part of the default. Add one only
when a current downstream decision or review will use it. Common examples are:

| Optional column | Use only when |
|---|---|
| `observed_share` | A defined first-party sample supports a numeric estimate |
| `channel` | Channel materially changes behavior or planned coverage |
| `source_ref` | A reviewer needs traceability to a source artifact |
| `notes` | A row-specific caveat cannot be expressed in the required fields |

If the purpose of a field is uncertain, omit it.

## Optional notes artifact

Use `.codeer/current/query_distribution_notes.md` only when document-level
scope, evidence window, sampling limits, exclusions, unresolved gaps, or
allocation rationale must be persisted. Do not repeat those values on every
CSV row and do not use the notes file as a raw-data dump.
