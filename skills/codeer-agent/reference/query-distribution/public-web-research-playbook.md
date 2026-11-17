# Public web research playbook

Use live web research for each target project. This file describes source classes and query strategies, not a permanent database catalog.

## Search by purpose

| Purpose | Preferred public sources | What they can support |
|---|---|---|
| Base tasks and official boundaries | official FAQ, help center, forms, policy pages, onboarding, service descriptions | task existence, prerequisites, stated policy |
| Customer language and friction | reviews, forums, public Q&A, community posts, app-store feedback | phrasing, misunderstandings, repeated friction |
| Industry risk | regulators, professional bodies, court decisions, recalls, incident reports, complaint boards | consequence types, escalation thresholds |
| Task lifecycle | workflow documentation, user guides, competitor help centers, public APIs | state transitions, deadlines, handoffs |
| Challenge mechanisms | public conversation datasets, dialogue research, complaint transcripts | multi-turn and communication structures |
| Coverage sanity check | comparable providers, trade publications, benchmark taxonomies | missing task families; not target frequency |

## Query construction

Combine:

`industry/company + customer action + failure state + source type`

Examples of action terms:

- book, change, cancel, refund, dispute, track, renew, verify, diagnose, escalate;
- local-language equivalents and colloquial variants.

Examples of failure-state terms:

- cannot, wrong, missing, delayed, rejected, charged, locked, expired, urgent, complaint;
- regulator, court, recall, incident, ombudsman, review, forum, FAQ.

Search both customer language and official terminology. Search the target geography and language before expanding to close proxies.

## Evidence discipline

- Cite the exact page and access date.
- Record whether evidence proves existence, prevalence, consequence, or merely plausibility.
- Do not infer traffic frequency from search ranking, a single review, or synthetic data.
- Do not treat public accessibility as permission to redistribute a corpus.
- Store downloads only in the active project and follow its privacy and licensing constraints.
- Prefer paraphrased findings over copied customer text.
- Mark unavailable, stale, gated, or legally unclear sources.

## Sampling discipline

When first-party frequency is unavailable:

1. sample multiple source classes;
2. avoid allowing one prolific site to dominate;
3. deduplicate syndicated or copied content;
4. report uncertainty;
5. use ordinal representativeness bands or ranges;
6. separate observed demand from the chosen eval allocation.

## Research output

Produce a compact evidence table with:

- source URL and date;
- source class and population;
- task or risk supported;
- observation type;
- evidence strength and limitations;
- downstream use: distribution, case language, risk design, or challenge design.
