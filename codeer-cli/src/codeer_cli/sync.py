"""Conservative three-way resource changes and crash-recoverable receipts.

Preflight/readback are not a server-side compare-and-swap or a transaction.
"""
from copy import deepcopy
import uuid

from .project import ProjectError, fingerprint, now, save_json


def merge(base, local, remote, local_base=None):
    """Omitted local keys retain the remote value; arrays are indivisible.

    In particular, tool IDs/order and rubric text never undergo semantic merging.
    """
    result = deepcopy(remote)
    conflicts = []
    for key, desired in local.items():
        previous = base.get(key)
        current = remote.get(key)
        if desired == (local_base if local_base is not None else base).get(key):
            continue
        if current != previous and current != desired:
            conflicts.append(key)
        else:
            result[key] = deepcopy(desired)
    return result, conflicts


def normalize(key, value):
    if key == "agent":
        from .project_agent import canonical
        return canonical(value)
    if key.startswith(("case:", "tester:")):
        from .project_eval import CASE_FIELDS, TESTER_FIELDS, select
        return select(value, CASE_FIELDS if key.startswith("case:") else TESTER_FIELDS)
    return value


def checkpoint(entry, key, *, local=False):
    return normalize(key, entry.get("local_base", entry.get("base", {})) if local else entry.get("base", {}))


def effective_change(entry, key, local, remote):
    desired, conflicts = merge(checkpoint(entry, key), local, remote, checkpoint(entry, key, local=True))
    return bool(conflicts) or desired != remote


def payload_matches(plan, actual):
    if plan["resource"].startswith("pairs:"):
        return actual == plan["payload"]  # Replacement must also prove absence.
    return all(actual.get(k) == v for k, v in plan["payload"].items())


def plan_change(project, key, server_id, base, local, remote):
    state = project.state()
    entry = state.get("resources", {}).get(key, {})
    base = normalize(key, base)
    local_base = normalize(key, entry.get("local_base", base))
    payload, conflicts = merge(base, local, remote, local_base)
    if entry.get("status") in ("pending", "outcome_unknown", "readback_mismatch"):
        conflicts.append("unreconciled_previous_operation")
    plan = {"resource": key, "server_id": server_id, "base": base, "local_base": local_base, "local": local,
            "remote": remote, "payload": payload, "conflicts": conflicts,
            "changed": payload != remote}
    plan["token"] = fingerprint(plan)
    return plan


def apply_change(project, plan, expected, mutation, readback):
    if plan["conflicts"]:
        raise ProjectError(f"Resolve conflicts before apply: {plan['conflicts']}")
    if expected != plan["token"]:
        raise ProjectError("Preview changed or missing --expect token; review the current dry-run")
    state = project.state()
    key = plan["resource"]
    entry = state.setdefault("resources", {}).setdefault(key, {})
    if not plan["changed"] and plan["server_id"]:
        entry.update(base=plan["remote"], local_base=plan["local"])
        record_removals(entry, plan)
        project.save_state(state)
        return {"status": "unchanged", "server_id": plan["server_id"]}
    receipt_id = f"{now().replace(':', '-')}-{uuid.uuid4().hex[:8]}"
    receipt_path = project.root / ".codeer/receipts" / f"{receipt_id}.json"
    receipt = {"id": receipt_id, "time": now(), "scope": plan.get("scope", project.target),
               "plan": plan, "status": "pending"}
    entry.update(status="pending", receipt=str(receipt_path.relative_to(project.root)))
    if "scope" in plan:
        entry["scope"] = plan["scope"]
    save_json(receipt_path, receipt)
    project.save_state(state)
    try:
        response = mutation(plan["payload"])
        receipt["response"] = response
        save_json(receipt_path, receipt)
        server_id = plan["server_id"] or response.get("id") or response.get("node_id")
        if not server_id:
            raise ProjectError("Mutation returned no resource identity")
        # Preserve identity before readback: an interrupted create must not repeat.
        entry["server_id"] = server_id
        project.save_state(state)
        actual = readback(server_id)
        receipt["readback"] = actual
        if not payload_matches(plan, actual):
            receipt["status"] = "readback_mismatch"
        else:
            receipt["status"] = "applied"
            entry["base"] = actual
            entry["local_base"] = plan["local"]
            record_removals(entry, plan)
        entry.update(status=receipt["status"], server_id=server_id)
    except BaseException as exc:
        # Even interruption and transport failure may follow a committed write.
        receipt.update(status="outcome_unknown", error=str(exc))
        entry["status"] = "outcome_unknown"
        raise
    finally:
        save_json(receipt_path, receipt)
        project.save_state(state)
    return receipt


def reconcile_entry(project, entry, actual):
    """Observe known identity; accept local checkpoint only for proven receipt payload."""
    from .project import read_json
    previous = entry.get("local_base", entry.get("base", {}))
    receipt = read_json(project.root / entry["receipt"], {}) if entry.get("receipt") else {}
    plan = receipt.get("plan", {})
    recovering = entry.get("status") in ("pending", "outcome_unknown", "readback_mismatch")
    matched = recovering and bool(plan) and payload_matches(plan, actual)
    entry.update(base=actual, local_base=plan.get("local", previous) if matched else previous,
                 status="imported_unvalidated")
    if matched:
        record_removals(entry, plan)
    if receipt:
        receipt.update(reconciled_at=now(), reconciliation={"readback": actual, "payload_matches": matched})
        save_json(project.root / entry["receipt"], receipt)


def record_removals(entry, plan):
    if "removed_ids" in plan:
        entry["removed_ids"] = sorted((set(entry.get("removed_ids", [])) | set(plan["removed_ids"])) - set(plan["local"]))
