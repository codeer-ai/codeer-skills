# Channel and language patterns

Channel patterns modify presentation, timing, and available evidence. They are neither tasks nor industry risks.

## Chat and messaging

- `CHAN-FRAGMENTED-MESSAGES`: several short messages instead of one complete request.
- `CHAN-ASYNC-DELAY`: long gaps make state or time sensitivity change.
- `CHAN-QUOTE-REPLY`: quoted content may belong to another message or participant.
- `CHAN-EMOJI-PUNCTUATION`: emotion appears through emoji, repetition, or punctuation.
- `CHAN-READ-RECEIPT-PRESSURE`: user pressures based on perceived delay or read status.

## Email and long form

- `CHAN-OVERLONG-NARRATIVE`: relevant details are buried in history.
- `CHAN-THREAD-FORWARD`: multiple writers and forwarded text create uncertain authorship.
- `CHAN-MULTIPLE-REQUESTS`: several tasks appear in one message.

## Phone and transcription

- `CHAN-ASR-ERROR`: names, numbers, dates, or specialized terms may be transcribed incorrectly.
- `CHAN-INTERRUPTION`: turns overlap or end before confirmation.
- `CHAN-NO-VISUAL-EVIDENCE`: the customer assumes the representative can see an item or screen.

## Forms and widgets

- `CHAN-FIELD-MISMATCH`: structured fields cannot represent the user's real situation.
- `CHAN-MISSING-CONTEXT`: the Agent receives the form result without page or journey context.
- `CHAN-STALE-PAGE`: public page content and Agent knowledge differ.

## Attachments and multimodal inputs

- `CHAN-ATTACHMENT-ABSENT`: a referenced file is unavailable.
- `CHAN-ATTACHMENT-WRONG-ENTITY`: the file belongs to another case or date.
- `CHAN-LOW-QUALITY-MEDIA`: content is unreadable, partial, or ambiguous.

## Language and locale

- `LANG-COLLOQUIAL`: slang, shorthand, or local phrasing.
- `LANG-CODE-SWITCH`: mixed languages or English technical terms.
- `LANG-MISUSED-TERM`: customer uses a professional term incorrectly.
- `LANG-RELATIVE-TIME`: local or relative date expressions require clarification.
- `LANG-TRANSLATION-DISTANCE`: translated text may preserve task structure but not target-customer language.

## Use rules

- Add channel variants only for channels the target Agent will actually serve.
- Do not treat translated or synthetic language as target-frequency evidence.
- Preserve the same `variant_family_id` when only channel presentation changes.
- Use channel variants to test capability, not to inflate task coverage.
