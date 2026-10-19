"""Connection diagnostics without exposing or persisting credentials."""
import os

from .client import AuthError, TransportError


def diagnostic(error=None):
    from .commands.profile import resolve_profile, _read_profiles
    profile = resolve_profile()
    result = {"source": profile.get("source"), "profile": profile.get("name"),
              "overrides": [k for k in ("CODEER_API_KEY", "CODEER_API_BASE", "CODEER_PROFILE", "CODEER_AGENT_ID") if k in os.environ]}
    data = _read_profiles()
    name = profile.get("name")
    if profile.get("source") == "environment":
        repair = "Correct or remove CODEER_API_KEY/CODEER_API_BASE overrides, then run codeer check; profile use does not override them"
    elif name:
        repair = f"Explicitly update codeer profile add {name}, then run codeer check"
    else:
        repair = "Run codeer profile add <name> (use --api-base for another platform), then codeer check"
    if "CODEER_API_BASE" in os.environ and profile.get("source") != "environment":
        repair = "Verify/correct the CODEER_API_BASE override first; profile switching does not remove it. If credentials are confirmed invalid, explicitly update their actual source and run codeer check"
    if error is None or isinstance(error, AuthError) and error.status == 0:
        if not profile.get("api_key"):
            if name and name not in data.get("profiles", {}) and profile.get("source") != "environment":
                result.update(status="unknown_profile", next_step="Select an existing profile with codeer profile use <name> or explicitly add this name; then codeer check")
            elif not name and data.get("profiles") and profile.get("source") != "environment":
                result.update(status="profile_not_selected", next_step="Run codeer profile list, codeer profile use <name>, then codeer check")
            else:
                result.update(status="missing_key" if name or profile.get("source") else "missing_configuration", next_step=repair)
        else:
            result.update(status="configured_unverified", next_step="Run codeer check; then explicitly create or take over a deployment")
    elif isinstance(error, TransportError) or error.status >= 500:
        result.update(status="connection_unverified", next_step="Connection could not be verified; check network/service and retry codeer check. Keep existing configuration")
    elif isinstance(error.body, dict) and error.body.get("error_code") == 10001:
        result.update(status="permission_denied", next_step="Verify API/workspace access and permissions; keep existing credentials until the cause is confirmed")
    elif error.status in (401, 403):
        result.update(status="authentication_or_access_rejected", next_step=f"Cause is uncertain; verify key validity, API/workspace and permissions. {repair}")
    else:
        result.update(status="scope_or_api_error", next_step="Verify API/workspace and target with codeer check; do not change deployment bindings automatically")
    return result
