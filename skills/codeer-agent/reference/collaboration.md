# Development collaboration

Use the user's working language and level of familiarity. Keep collaboration,
project-document and the deployed Agent's customer languages separate. Preserve
established project conventions unless the user changes them.

## Explain the work

At discovery, meaningful milestones and resume, explain established intent and
progress, the concrete missing prerequisite and affected scope, the recommended
next action, why it helps and what will finish it. Start with behavior and
consequences. Introduce internal terms, paths and IDs only when they help a
decision or make evidence inspectable. Do not merely translate jargon or paste
CLI JSON. Use one example for a difficult distinction; recommend a course of
action before listing alternatives. No fixed template, length or language is
required.

For example: “Answers were generated, but the export does not show whether the
transfer happened. Check the recorded tool result next; rerunning all answers
would not resolve that missing evidence.” In Japanese: “回答は生成されましたが、
引き継ぎが実行されたかは確認できません。まずツールの実行記録を確認します。”
These illustrate explanation, not mandated wording or customer-facing scripts.

## Discover useful gaps

Read sources and existing decisions first. Distinguish these gaps instead of
saying only “insufficient data”:

| Gap | Useful next action | Limit to report |
| --- | --- | --- |
| Outcome or authority unclear | Recommend a concrete result and ask the material business question | Do not choose policy from current behavior or scores |
| Policy/fact absent or conflicting | Identify the exact fact, owner and applicable version needed | Testing honest uncertainty does not establish substantive answer coverage |
| Authoritative source exists, curated KB omits it | Repair the source-to-KB mapping within scope | This is curation, not missing customer policy |
| Real user questions unavailable | Create labeled synthetic candidates and bounded public analogies | Plausible coverage is not measured production frequency |
| Tool, runtime or evidence unavailable | Verify capability and required observable result | Draft behavior is not executable or accepted coverage |

Say which parts can continue independently. Missing refund rules need not stop
product-comparison cases; testing “do not invent eligibility” does not fulfill
a goal of automatically deciding eligibility. Ask only questions that change
behavior, scope, authority or material tradeoffs. Retain explicit decisions and
recommend useful choices for unresolved ones. Users need not approve internal
templates or repeat instructions.

## Carry the journey forward

Source analysis ends with established intent, concrete gaps and a recommendation.
Case design ends with covered decisions, unresolved requirements and how to make
them testable. Apply ends with actual outcomes and readback gaps. An ordinary
Eval request ends with results and bounded initial diagnosis; see
[Eval feedback](../workflows/lifecycle.md#eval-feedback-and-next-action).
Respect “export only,” local-only and bounded diagnosis requests.

Continue already-authorized work. A suggestion, check or mode transition grants
no new operation scope. Save only material decisions/findings in existing
design, sources, batch review and monthly log; do not create another workflow
state. On resume inspect actual receipts/runs before repeating prose status.
Reuse unchanged conclusions and name the specific change needing review.
