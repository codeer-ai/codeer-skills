# Common Errors and Recovery

Run `codeer check` first — it catches most setup problems.

---

## Error table

| Error | Cause | Fix |
| --- | --- | --- |
| HTTP 401 or 403 | API key missing, invalid, expired, revoked, or under-scoped | Create an admin workspace API key, update the active CLI profile with `codeer profile add <name>` and `codeer profile use <name>`, then run `codeer check`. |
| HTTP 400 "Organization ID is required" | API-key virtual user profile did not expose `default_organization_id` | Run `codeer check`; the API key may not be a workspace API key. |
| KB upload returns `status: FAILED`, `node_id: null`, no error message | Wrong or missing Content-Type on the uploaded file | Pass `(filename, file_handle, content_type)` as a 3-tuple. Image files (JPEG, PNG, etc.) are not accepted for KB uploads. |
| KB upload returns HTTP 422 `"Field required"` on `form` | `parent_id` sent as a top-level form field instead of JSON-encoded `form` field | The multipart body needs `form: {"parent_id": "..."}` as a single JSON-encoded field. |
| Agent saves but form fields render blank in UI | Invalid form field `type` value (e.g. `"text"`, `"email"`, `"select"`) | Valid types: `shortText`, `longText`, `number`, `dropdown`, `radio`, `checkbox`, `date`. Use `shortText` for email/text, `dropdown` for select. |
| Eval results show `score: null` for some cases | Cases haven't been evaluated on that agent version yet | `null` means "not yet run", not "failed". Trigger eval for those cases, or check that the correct `agent_history_id` was passed. |
| Changes land in the wrong workspace | Wrong CLI profile or API key is active | Switch to the intended profile with `codeer profile use <name>` and run `codeer check`. |
| `codeer check` can't find credentials | No CLI profile is selected and no fallback `CODEER_API_KEY` is present | Configure a profile with `codeer profile add <name>` and `codeer profile use <name>`. See **onboarding.md**. |
