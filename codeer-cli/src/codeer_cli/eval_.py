"""Evaluation: cases, evaluators, trigger runs, read results.

'eval' is a Python builtin, so this module is named ``eval_`` — import it as such::

    from codeer_cli import eval_ as eval_mod
"""

from __future__ import annotations

from typing import Any, List, Optional

from .client import CodeerClient


class _UnsetType:
    pass


_UNSET = _UnsetType()


# --- cases ----------------------------------------------------------------

def create_case(
    client: CodeerClient,
    *,
    agent_id: str,
    input: str,
    expected_output: Optional[str] = None,
    rubric: Optional[str] = None,
    attachment_ids: Optional[List[str]] = None,
    label_ids: Optional[List[str]] = None,
    evaluators: Optional[List[dict[str, Any]]] = None,
    meta: Optional[dict] = None,
    note: Optional[str] = None,
) -> dict:
    """Create an eval case.

    IMPORTANT: the case-level ``rubric`` is a default and is NOT what the Test
    Suite's ``Standard`` column displays. That column reads the per-evaluator
    rubric set via ``POST /eval/rubric`` (:func:`set_rubric`). If you want a
    case to show a Standard for a given evaluator, also call :func:`set_rubric`
    for that (case, evaluator) pair — or use :func:`create_case_with_rubrics`
    which does both in one shot.
    """
    body: dict[str, Any] = {"agent_id": agent_id, "input": input}
    if expected_output is not None:
        body["expected_output"] = expected_output
    if rubric is not None:
        body["rubric"] = rubric
    if attachment_ids:
        body["attachment_ids"] = attachment_ids
    if label_ids is not None:
        body["label_ids"] = label_ids
    if evaluators is not None:
        body["evaluators"] = evaluators
    if meta:
        body["meta"] = meta
    if note is not None:
        body["note"] = note
    return client.post("/external/eval/cases", json=body)


def _unwrap_list_response(value: Any, *keys: str) -> list[dict]:
    """Normalize list endpoints that may return either a bare list or envelope."""
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in keys:
            rows = value.get(key)
            if isinstance(rows, list):
                return rows
    return []


def list_cases(client: CodeerClient, agent_id: str) -> list[dict]:
    return _unwrap_list_response(
        client.get(f"/external/eval/agents/{agent_id}/cases"),
        "cases",
        "evaluation_cases",
        "data",
        "items",
    )


def get_case(client: CodeerClient, case_id: str) -> dict:
    return client.get(f"/external/eval/cases/{case_id}")


def update_case(
    client: CodeerClient,
    case_id: str,
    *,
    input: Optional[str] = None,
    expected_output: Optional[str] = None,
    rubric: Optional[str] = None,
    attachment_ids: Optional[List[str]] = None,
    label_ids: Optional[List[str]] = None,
    meta: Optional[dict] = None,
    note: Optional[str] = None,
) -> dict:
    body: dict[str, Any] = {}
    if input is not None:
        body["input"] = input
    if expected_output is not None:
        body["expected_output"] = expected_output
    if rubric is not None:
        body["rubric"] = rubric
    if attachment_ids is not None:
        body["attachment_ids"] = attachment_ids
    if label_ids is not None:
        body["label_ids"] = label_ids
    if meta is not None:
        body["meta"] = meta
    if note is not None:
        body["note"] = note
    return client.put(f"/external/eval/cases/{case_id}", json=body)


def delete_case(client: CodeerClient, case_id: str) -> dict:
    return client.delete(f"/external/eval/cases/{case_id}")


# --- case/evaluator assignments ------------------------------------------

def get_case_evaluator_infos(client: CodeerClient, *, case_ids: List[str]) -> list[dict]:
    """Read assigned evaluator metadata for each case.

    Returns rows shaped like ``{"case_id": str, "evaluators": [...]}``, where
    each evaluator entry is the assigned ``{"evaluator_id", "rubric"}`` pair.
    """
    return client.post("/eval/case-evaluator-infos:batch", json={"case_ids": case_ids})


def replace_case_evaluator_infos(
    client: CodeerClient,
    *,
    case_id: str,
    evaluators: list[dict[str, Any]],
) -> dict:
    """Replace a case's assigned evaluators.

    This is intentionally separate from rubric upsert: replacing removes
    evaluator assignments that are not included in ``evaluators``.
    """
    return client.put(f"/eval/cases/{case_id}/case-evaluator-infos", json={"evaluators": evaluators})


# --- case labels -----------------------------------------------------------

def list_case_labels(client: CodeerClient) -> list[dict]:
    return client.get("/external/eval/case-labels")


def create_case_label(
    client: CodeerClient,
    *,
    name: str,
    color: Optional[str] = None,
) -> dict:
    body: dict[str, Any] = {"name": name}
    if color is not None:
        body["color"] = color
    return client.post("/external/eval/case-labels", json=body)


def update_case_label(
    client: CodeerClient,
    *,
    label_id: str,
    name: Optional[str] = None,
    color: Optional[str] = None,
) -> dict:
    body: dict[str, Any] = {}
    if name is not None:
        body["name"] = name
    if color is not None:
        body["color"] = color
    return client.put(f"/external/eval/case-labels/{label_id}", json=body)


def delete_case_label(client: CodeerClient, *, label_id: str) -> dict:
    return client.delete(f"/external/eval/case-labels/{label_id}")



# --- evaluators -----------------------------------------------------------

def create_evaluator(
    client: CodeerClient,
    *,
    workspace_id: str,
    name: str,
    system_prompt_template: str,
    description: Optional[str] = None,
    judge_llm_model_id: Optional[str] = None,
) -> dict:
    body: dict[str, Any] = {
        "name": name,
        "system_prompt_template": system_prompt_template,
    }
    if description is not None:
        body["description"] = description
    if judge_llm_model_id is not None:
        body["judge_llm_model_id"] = judge_llm_model_id
    return client.post("/external/eval/evaluators", json=body)


def list_evaluators(client: CodeerClient, workspace_id: str) -> list[dict]:
    return client.get("/external/eval/evaluators")


def get_evaluator(client: CodeerClient, evaluator_id: str) -> dict:
    return client.get(f"/external/eval/evaluators/{evaluator_id}")


def update_evaluator(
    client: CodeerClient,
    evaluator_id: str,
    *,
    name: Optional[str] = None,
    system_prompt_template: Optional[str] = None,
    description: Optional[str] = None,
    judge_llm_model_id: str | None | _UnsetType = _UNSET,
) -> dict:
    body: dict[str, Any] = {}
    if name is not None:
        body["name"] = name
    if system_prompt_template is not None:
        body["system_prompt_template"] = system_prompt_template
    if description is not None:
        body["description"] = description
    if judge_llm_model_id is not _UNSET:
        body["judge_llm_model_id"] = judge_llm_model_id
    return client.put(f"/external/eval/evaluators/{evaluator_id}", json=body)



# --- runs + results -------------------------------------------------------

def trigger(
    client: CodeerClient,
    *,
    case_ids: List[str],
    evaluator_ids: List[str],
    agent_history_id: Optional[str] = None,
) -> dict:
    """Kick off an evaluation run.

    Pass ``agent_history_id`` to pin the run to a specific (possibly unpublished)
    agent version — this is the core of the apply → eval → publish loop.
    """
    if agent_history_id is None:
        raise ValueError("agent_history_id is required for external eval runs")
    body: dict[str, Any] = {
        "case_ids": case_ids,
        "evaluator_ids": evaluator_ids,
        "version_id": agent_history_id,
    }
    return client.post("/external/eval/runs", json=body)


def trigger_pairs(
    client: CodeerClient,
    *,
    case_evaluator_pairs: list[dict[str, str]],
    agent_history_id: str,
) -> dict:
    """Kick off evaluation for explicit assigned case/evaluator pairs."""
    return client.post(
        "/eval/trigger",
        json={
            "case_evaluator_pairs": case_evaluator_pairs,
            "agent_history_id": agent_history_id,
        },
    )


def stop(client: CodeerClient, *, case_id: str, evaluator_id: str) -> Any:
    return client.post("/external/eval/runs:stop", json={"case_id": case_id, "evaluator_id": evaluator_id})


def get_results(
    client: CodeerClient,
    *,
    case_ids: List[str],
    evaluator_id: str,
    agent_history_id: str,
    workspace_id: str,
    include_output: bool = True,
    include_reasoning_steps: bool = True,
) -> list[dict]:
    """Fetch scored results for a batch of cases under one evaluator + agent version."""
    return client.post(
        "/external/eval/results:batch",
        json={
            "case_ids": case_ids,
            "evaluator_id": evaluator_id,
            "version_id": agent_history_id,
            "include_output": include_output,
            "include_reasoning_steps": include_reasoning_steps,
        },
    )


def set_rubric(client: CodeerClient, *, evaluation_case_id: str, evaluator_id: str, rubric: str) -> Any:
    """Set the per-evaluator rubric (the ``Standard`` the UI displays) for a case."""
    return client.put(
        f"/external/eval/cases/{evaluation_case_id}/rubrics/{evaluator_id}",
        json={"rubric": rubric},
    )


# --- reading rubrics back -------------------------------------------------
#
# Rubrics are per-(case, evaluator) and version-independent. The proper read
# endpoint is ``POST /eval/rubrics/batch`` — it returns the rubric string
# directly out of the ``CaseEvaluatorInfo`` table (the same row that
# ``set_rubric`` writes to). It does NOT require an ``agent_history_id``.
#
# Do not try to scrape rubrics out of past eval ``reason`` text — the judge
# paraphrases and reformats them, and a case with a rubric set but never
# evaluated will look indistinguishable from a case with no rubric. The
# legacy ``parse_rubrics_from_reason()`` helper still ships in ``parse.py``
# but it's a fallback for analyzing already-fetched judge output, not a
# discovery tool for current rubrics.

def get_rubrics_batch(
    client: CodeerClient,
    *,
    case_ids: List[str],
    evaluator_id: str,
) -> list[dict]:
    """Read rubric strings for a batch of (case, evaluator) pairs in one call.

    Returns a list of ``{"case_id", "evaluator_id", "rubric"}`` dicts in the
    same order as ``case_ids``. Cases without a rubric set come back with
    ``rubric == ""`` — they're not omitted from the response.
    """
    return client.post(
        "/external/eval/rubrics:batch",
        json={"case_ids": case_ids, "evaluator_id": evaluator_id},
    )


def get_case_rubrics(
    client: CodeerClient,
    *,
    agent_id: str,
    workspace_id: str,
    evaluator_ids: Optional[List[str]] = None,
    case_ids: Optional[List[str]] = None,
) -> dict[str, dict[str, str]]:
    """Read every (case, evaluator) rubric for an agent, in one nested dict.

    Returns ``{case_id: {evaluator_id: rubric_str}, ...}``. An evaluator with
    no rubric set for a given case still appears in the inner dict with
    ``rubric_str == ""`` — that's the convention; treat empty string as
    "no rubric currently set" (the case is being judged with no constraints).

    If ``evaluator_ids`` is omitted, scans every evaluator in the workspace.
    If ``case_ids`` is omitted, scans every case under the agent.
    """
    if evaluator_ids is None:
        evaluator_ids = [e["id"] for e in list_evaluators(client, workspace_id)]
    if case_ids is None:
        case_ids = [c["id"] for c in list_cases(client, agent_id)]
    if not evaluator_ids or not case_ids:
        return {}

    out: dict[str, dict[str, str]] = {cid: {} for cid in case_ids}
    for ev_id in evaluator_ids:
        rows = get_rubrics_batch(client, case_ids=case_ids, evaluator_id=ev_id)
        for row in rows:
            cid = row.get("case_id")
            if cid in out:
                out[cid][ev_id] = row.get("rubric") or ""
    return out


def list_runs_for_case(
    client: CodeerClient,
    *,
    case_id: str,
    agent_id: str,
    workspace_id: str,
    evaluator_id: str,
    include_output: bool = False,
) -> list[dict]:
    """Score history for ONE case across every version of the agent.

    Use this when investigating regressions: "this case scored 1.0 on v38 but
    0 on v42 — when did it break?". Iterates ``/agents/{id}/histories`` and
    asks ``/eval/results/batch`` per version, keeping only the rows that match
    ``case_id``. Returns most-recent version first.

    Returns a list of dicts:
        {
            "history_id": str,
            "version_number": int,
            "version_note": str,
            "status": str,                 # 'draft' | 'published'
            "was_published": bool,
            "created_at": str,
            "score": float | None,         # None if the case wasn't run on this version
            "reason": str | None,
            "output": str | None,          # only when include_output=True
        }

    Versions where the case was never evaluated come back with ``score=None``
    rather than being omitted — useful for spotting "we forgot to add this
    case to the run" alongside true regressions.
    """
    versions = client.get(f"/external/agents/{agent_id}/versions")
    if not versions:
        return []
    out: list[dict] = []
    for v in versions:
        hid = v.get("id")
        if not hid:
            continue
        score: Optional[float] = None
        reason: Optional[str] = None
        output: Optional[str] = None
        try:
            rows = get_results(
                client, case_ids=[case_id], evaluator_id=evaluator_id,
                agent_history_id=hid, workspace_id=workspace_id,
                include_output=include_output,
            )
        except Exception:
            rows = []
        for r in rows or []:
            cid = r.get("evaluation_case_id") or r.get("case_id")
            if cid != case_id:
                continue
            score = r.get("score")
            reason = r.get("reason")
            output = r.get("output")
            break
        out.append({
            "history_id": hid,
            "version_number": v.get("version_number"),
            "version_note": v.get("version_note") or "",
            "status": v.get("status"),
            "was_published": bool(v.get("was_published")),
            "created_at": v.get("created_at"),
            "score": score,
            "reason": reason,
            "output": output,
        })
    return out


def list_results_across_versions(
    client: CodeerClient,
    *,
    agent_id: str,
    workspace_id: str,
    evaluator_id: str,
    case_ids: Optional[List[str]] = None,
) -> list[dict]:
    """Fetch every eval result for an agent across ALL of its versions.

    ``/eval/results/batch`` is per-version (``agent_history_id`` is required),
    so this helper iterates every version of the agent and concatenates the
    results. Use it when you want score history over time or want to find a
    specific past judge ``reason`` — NOT for fetching current rubrics
    (use :func:`get_case_rubrics` instead, which goes through the proper
    ``/eval/rubrics/batch`` endpoint).

    If ``case_ids`` is omitted, fetches results for every case under the agent.
    """
    versions = client.get(f"/external/agents/{agent_id}/versions")
    if case_ids is None:
        case_ids = [c["id"] for c in list_cases(client, agent_id)]
    if not case_ids or not versions:
        return []
    out: list[dict] = []
    for v in versions:
        hid = v.get("id")
        if not hid:
            continue
        try:
            rows = get_results(
                client, case_ids=case_ids, evaluator_id=evaluator_id,
                agent_history_id=hid, workspace_id=workspace_id,
                include_output=False,
            )
        except Exception:
            continue
        if rows:
            out.extend(rows)
    return out


def set_rubric_bulk(
    client: CodeerClient,
    *,
    evaluation_case_id: str,
    rubrics_by_evaluator: dict[str, str],
) -> list[Any]:
    """Set rubrics for one case across multiple evaluators in a single call."""
    return [
        set_rubric(client, evaluation_case_id=evaluation_case_id, evaluator_id=ev_id, rubric=r)
        for ev_id, r in rubrics_by_evaluator.items()
    ]


def create_case_with_rubrics(
    client: CodeerClient,
    *,
    agent_id: str,
    input: str,
    rubrics_by_evaluator: dict[str, str],
    expected_output: Optional[str] = None,
    attachment_ids: Optional[List[str]] = None,
    label_ids: Optional[List[str]] = None,
    meta: Optional[dict] = None,
    note: Optional[str] = None,
) -> dict:
    """Create a case AND populate the per-evaluator rubrics in one step.

    This is the shape you almost always want — a case whose ``Standard`` column
    is filled in for every evaluator it will be judged by.

    ``rubrics_by_evaluator`` maps ``evaluator_id → rubric_text``. Each entry
    becomes a case/evaluator assignment on create. Use different rubric wording
    per evaluator when the evaluators judge different aspects (e.g. Style/Tone
    vs Content Compliance).
    """
    case = create_case(
        client,
        agent_id=agent_id,
        input=input,
        expected_output=expected_output,
        attachment_ids=attachment_ids,
        label_ids=label_ids,
        evaluators=[
            {"evaluator_id": ev_id, "rubric": rubric}
            for ev_id, rubric in rubrics_by_evaluator.items()
        ],
        meta=meta,
        note=note,
    )
    return case
