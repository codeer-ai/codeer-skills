# Consultative Guidance Methods

Use this reference while drafting a Behavior Contract in
[../modules/consultative-guidance.md](../modules/consultative-guidance.md). The
methods can be combined. Select them from the customer's decision, available
evidence, cost of error, and conversational burden rather than treating one
framework as a universal script.

## Core control principles

### Mixed-Initiative Dialogue

Use this as the conversation-control layer. The user and agent may each move
the task forward: the agent can answer, ask, retrieve, recommend, or propose an
action, while the user can redirect, supply preferences, reject options, or
request a transaction.

The key design problem is not alternating turns; it is allocating initiative.
Let the user lead when intent and next action are clear. Let the agent lead
more when an important information gap, hidden dependency, or costly mistake
would otherwise block progress. Make agent initiative easy to understand,
decline, or redirect.

### Adaptive Selling

Use this as a meta-principle, not a standalone script. Adapt only from
observable signals such as the user's stated goal, knowledge, urgency,
constraints, feedback, and readiness. The adaptable dimensions include:

- initiative: answer-first versus guided discovery;
- discovery depth: one clarification versus a deeper needs exploration;
- option breadth: one recommendation versus a small comparison set;
- explanation depth: concise direction versus evidence and tradeoffs; and
- progression: continue advising versus offer an action or human handoff.

Do not infer sensitive traits, use opaque persuasion tactics, or change factual
standards to increase conversion.

## Discovery and narrowing choices

| Method | Best fit | Avoid or shorten when | Contract contribution |
| --- | --- | --- | --- |
| Direct answer + optional refinement | Clear factual or support query; user already knows the desired outcome | A wrong answer would be costly or a key constraint is missing | Answer first, then offer one relevant way to narrow or act |
| SPIN-light | The underlying problem, consequence, or value of change is genuinely unclear | The task is simple, the user is ready, or implication questions would manufacture anxiety | Draw selectively from Situation, Problem, Implication, and Need-payoff; never require all four or a fixed order |
| Jobs to Be Done | Product category language hides the outcome the user is trying to achieve | Eligibility or exact attributes already determine the answer | Ask about the progress sought, context, current workaround, and success condition |
| Usage-related preference elicitation | The user cannot translate needs into technical attributes | The user has already supplied precise constraints | Ask about intended use, frequency, environment, experience, or workflow, then map those answers to supported attributes |
| Attribute and constraint elicitation | Search space is structured by budget, date, size, level, compatibility, or other explicit filters | Preference is experiential or the user does not understand the attributes | Identify must-haves, exclusions, and flexible preferences; ask the highest-information unresolved constraint first |
| Example-critiquing | The user can react more easily to concrete options than abstract questions | No credible initial options can yet be grounded | Offer a small diverse set, ask what they like or dislike, and use the critique to refine |
| Structured guided selling | Eligibility, safety, compliance, scheduling, or irreversible action requires a dependable sequence | Low-stakes browsing would be burdened by a form-like flow | Use a short decision tree or form with clear purpose, progress, and consent; allow questions and handoff |

SPIN is a discovery-question design aid in this scope. It is not a full sales
stage model, and implication questions should surface real consequences rather
than create pressure. Jobs to Be Done, usage questions, constraints, and
example-critiquing are often better alternatives for product or course
selection.

## Common compositions

- **Simple support or factual guidance:** direct answer, supported retrieval
  when needed, then an optional next step.
- **Ambiguous product or course choice:** Jobs to Be Done or a usage-related
  question, an initial grounded shortlist, then example-critiquing.
- **Constraint-heavy choice:** attribute/constraint elicitation, recommendation
  with tradeoffs, then confirmation before action.
- **High-consequence or eligibility flow:** structured guided selling with
  selective SPIN-light questions, explicit uncertainty boundaries, and human
  handoff.
- **Returning or highly informed user:** validate the decisive constraint,
  answer or recommend quickly, and avoid repeating discovery already present in
  the conversation or memory.

These are defaults, not mandatory flows or required contract sections. Put a
switching signal in the Behavior Contract only when it changes a material,
observable customer-experience decision and is not already clear from a
higher-level principle. Keep method mechanics and concrete variants in the
implementation or eval portfolio instead of expanding the customer-reviewed
contract.

## Foundational sources

- Eric Horvitz, *Principles of Mixed-Initiative User Interfaces* (CHI 1999):
  https://www.microsoft.com/en-us/research/wp-content/uploads/2016/11/chi99horvitz.pdf
- Rosann Spiro and Barton Weitz, *Adaptive Selling: Conceptualization,
  Measurement, and Nomological Validity* (1990):
  https://journals.sagepub.com/doi/10.1177/002224379002700106
- Huthwaite International, SPIN methodology overview:
  https://www.huthwaiteinternational.com/spin-methodology
- Google Research, usage-related preference questions in conversational
  recommender systems:
  https://research.google/pubs/soliciting-user-preferences-in-conversational-recommender-systems-via-usage-related-questions/
- Harvard Business Review, *Know Your Customers' “Jobs to Be Done”*:
  https://hbr.org/2016/09/know-your-customers-jobs-to-be-done
- Chen and Pu, *Evaluating Critiquing-based Recommender Agents* (AAAI 2006):
  https://cdn.aaai.org/AAAI/2006/AAAI06-033.pdf
