# Common Errors and Recovery

Run `codeer check` first — it catches most setup problems.

---

## Error table

| Error | Cause | Fix |
| --- | --- | --- |
| Resource export API unavailable | Environment lacks metadata/download or integrated KB text/FAQ export | Record capability gap; require the supported API. Do not fetch source_url, use internal routes, or label text as original. |
| Target saved text differs | Target extraction cannot support the reviewed FAQ coordinates | Preserve originals/proposal, review target text and ranges before rebuilding. |
| Unmapped target FAQ / missing mapped FAQ | Clone lacks identity evidence or platform FAQ was removed/moved | Supply explicit complete `--ids` mapping or adopt remote deletion; never match questions or auto-create replacements. |
| FAQ write unresolved | Interrupted mutation, possibly committed | `kb faq-sync --reconcile` verifies known IDs; unknown creates require investigated IDs supplied with `--ids`. No blind retry. |
| HTTP 401 or 403 | Credential or access rejection; status alone cannot prove expiration | Inspect `profile current`, API/workspace and permissions. Explicitly update the actual key setting if invalid, then `check`; correct/remove environment overrides directly. |
| HTTP 400 "Organization ID is required" | API-key virtual user profile did not expose `default_organization_id` | Run `codeer check`; the API key may not be a workspace API key. |
| KB upload returns `status: FAILED`, `node_id: null`, no error message | Wrong or missing Content-Type on the uploaded file | Pass `(filename, file_handle, content_type)` as a 3-tuple. Image files (JPEG, PNG, etc.) are not accepted for KB uploads. |
| KB upload returns HTTP 422 `"Field required"` on `form` | `parent_id` sent as a top-level form field instead of JSON-encoded `form` field | The multipart body needs `form: {"parent_id": "..."}` as a single JSON-encoded field. |
| Agent saves but form fields render blank in UI | Invalid form field `type` value (e.g. `"text"`, `"email"`, `"select"`) | Valid types: `shortText`, `longText`, `number`, `dropdown`, `radio`, `checkbox`, `date`. Use `shortText` for email/text, `dropdown` for select. |
| Eval results show `score: null` for some cases | Cases haven't been evaluated on that agent version yet | `null` means "not yet run", not "failed". Trigger eval for those cases, or check that the correct `agent_history_id` was passed. |
| Wrong workspace/API | Effective configuration scope differs from the deployment | Inspect source and environment overrides; correct those or select the intended profile, then `check`. Never rebind the deployment automatically. |
| Credentials unavailable | Missing configuration, unselected/unknown profile, or missing key | Reuse existing parent/global/environment config; run `profile use` only for an unselected existing profile, add explicitly if missing, update its actual setting for missing key. See **onboarding.md**. |
| Timeout, network failure or 5xx during check | Connection cannot yet be verified | Keep existing configuration; verify network/service and retry check. Do not infer expired credentials. |
| Request timed out while creating or sending a history turn | The server did not respond before the per-message timeout | Run `codeer history conversations <history_id> --out sources/history/<collection-id>/history-<history_id>.json` before retrying. The write outcome is uncertain and retrying blindly can duplicate a turn. |
| Request failed with a connection or DNS error | The configured `CODEER_API_BASE` is unavailable or incorrect | Verify the active profile/API base and service availability, then rerun `codeer check`. |
