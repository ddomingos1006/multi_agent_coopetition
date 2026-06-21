"""Public tool functions for the Context Window Parliament."""

from __future__ import annotations

from typing import Any

from parliament.models import ToolCallLog, Verdict, World
from parliament.specialists import DEFAULT_BACKEND, SpecialistBackend, apply_testimony_to_specialist
from parliament.state import get_world


def _error(world: World | None, tool: str, message: str, args: dict[str, Any]) -> dict[str, Any]:
    if world is not None:
        world.call_log.append(
            ToolCallLog(
                tool=tool,
                ok=False,
                message=message,
                args=args,
                record_len_before=len(world.official_record),
                record_len_after=len(world.official_record),
            )
        )
    return {"ok": False, "error": message}


def _world_or_error(world_id: str, tool: str, args: dict[str, Any]) -> tuple[World | None, dict[str, Any] | None]:
    try:
        return get_world(world_id), None
    except KeyError as exc:
        return None, {"ok": False, "error": str(exc)}


def _tokens_by_specialist(world: World, specialist_id: str) -> int:
    return sum(block.token_count for block in world.official_record if block.specialist_id == specialist_id)


def _next_action(world: World) -> str:
    if world.hearing_closed:
        return "Call submit_verdict now using a native tool call. Do not output analysis or markup."
    return (
        "Your next response must be native tool calls only. If the evidence is sufficient, "
        "call submit_verdict now; otherwise call an evidence tool."
    )


def _ensure_open(world: World, tool: str, args: dict[str, Any]) -> dict[str, Any] | None:
    world.close_if_exhausted()
    if world.hearing_closed:
        return _error(
            world,
            tool,
            "The hearing is closed; evidence tools are no longer available. submit_verdict is still allowed.",
            args,
        )
    return None


def list_specialists(world_id: str) -> dict[str, Any]:
    """Return public specialist cards without private evidence or labels."""

    world, err = _world_or_error(world_id, "list_specialists", {"world_id": world_id})
    if err:
        return err
    assert world is not None
    return {
        "ok": True,
        "world_id": world.world_id,
        "budget_remaining": world.budget_remaining,
        "interactions_remaining": world.interactions_remaining,
        "specialists": [
            specialist.public_card(_tokens_by_specialist(world, specialist.id))
            for specialist in world.specialists.values()
        ],
        "next_action": _next_action(world),
    }


def grant_floor(
    world_id: str,
    specialist_id: str,
    token_budget: int,
    backend: SpecialistBackend = DEFAULT_BACKEND,
) -> dict[str, Any]:
    """Grant floor time to a specialist, consuming official-record tokens."""

    args = {"world_id": world_id, "specialist_id": specialist_id, "token_budget": token_budget}
    world, err = _world_or_error(world_id, "grant_floor", args)
    if err:
        return err
    assert world is not None
    closed = _ensure_open(world, "grant_floor", args)
    if closed:
        return closed
    if specialist_id not in world.specialists:
        return _error(world, "grant_floor", f"Unknown specialist_id: {specialist_id}", args)
    if not isinstance(token_budget, int) or token_budget <= 0:
        return _error(world, "grant_floor", "token_budget must be a positive integer.", args)
    if token_budget > world.budget_remaining:
        return _error(
            world,
            "grant_floor",
            f"Requested {token_budget} tokens but only {world.budget_remaining} remain.",
            args,
        )

    before = len(world.official_record)
    specialist = world.specialists[specialist_id]
    block = backend.generate_testimony(world, specialist, "floor", token_budget, None)
    world.official_record.append(block)
    world.interaction_count += 1
    apply_testimony_to_specialist(specialist, block, token_budget)
    world.close_if_exhausted()
    world.call_log.append(
        ToolCallLog("grant_floor", True, "testimony recorded", args, before, len(world.official_record))
    )
    return _testimony_result(world, block)


def cross_examine(
    world_id: str,
    specialist_id: str,
    question: str,
    token_budget: int,
    backend: SpecialistBackend = DEFAULT_BACKEND,
) -> dict[str, Any]:
    """Ask a targeted question, consuming official-record tokens."""

    args = {
        "world_id": world_id,
        "specialist_id": specialist_id,
        "question": question,
        "token_budget": token_budget,
    }
    world, err = _world_or_error(world_id, "cross_examine", args)
    if err:
        return err
    assert world is not None
    closed = _ensure_open(world, "cross_examine", args)
    if closed:
        return closed
    if specialist_id not in world.specialists:
        return _error(world, "cross_examine", f"Unknown specialist_id: {specialist_id}", args)
    if not isinstance(token_budget, int) or token_budget <= 0:
        return _error(world, "cross_examine", "token_budget must be a positive integer.", args)
    if not question or not question.strip():
        return _error(world, "cross_examine", "question must be non-empty.", args)
    if token_budget > world.budget_remaining:
        return _error(
            world,
            "cross_examine",
            f"Requested {token_budget} tokens but only {world.budget_remaining} remain.",
            args,
        )

    before = len(world.official_record)
    specialist = world.specialists[specialist_id]
    block = backend.generate_testimony(world, specialist, "cross_exam", token_budget, question)
    world.official_record.append(block)
    world.interaction_count += 1
    apply_testimony_to_specialist(specialist, block, token_budget)
    world.close_if_exhausted()
    world.call_log.append(
        ToolCallLog("cross_examine", True, "testimony recorded", args, before, len(world.official_record))
    )
    return _testimony_result(world, block)


def _testimony_result(world: World, block: Any) -> dict[str, Any]:
    return {
        "ok": True,
        "world_id": world.world_id,
        "testimony_id": block.id,
        "specialist_id": block.specialist_id,
        "mode": block.mode,
        "visible_text": block.visible_text,
        "used_tokens": block.token_count,
        "remaining_budget": world.budget_remaining,
        "interactions_remaining": world.interactions_remaining,
        "hearing_closed": world.hearing_closed,
        "next_action": _next_action(world),
    }


def view_record(world_id: str) -> dict[str, Any]:
    """Return the visible official record without grader metadata."""

    world, err = _world_or_error(world_id, "view_record", {"world_id": world_id})
    if err:
        return err
    assert world is not None
    return {
        "ok": True,
        "world_id": world.world_id,
        "budget_used": world.budget_used,
        "budget_remaining": world.budget_remaining,
        "max_interactions": world.max_interactions,
        "interactions_used": world.interaction_count,
        "hearing_closed": world.hearing_closed,
        "testimony": [
            block.visible_dict(world.specialists[block.specialist_id])
            for block in world.official_record
        ],
        "next_action": _next_action(world),
    }


def submit_verdict(
    world_id: str,
    decision: str,
    confidence: float,
    root_cause: str,
    citation_ids: list[str],
    rationale: str,
) -> dict[str, Any]:
    """Submit and record the final verdict. Invalid citations are kept for scoring."""

    args = {
        "world_id": world_id,
        "decision": decision,
        "confidence": confidence,
        "root_cause": root_cause,
        "citation_ids": citation_ids,
        "rationale": rationale,
    }
    world, err = _world_or_error(world_id, "submit_verdict", args)
    if err:
        return err
    assert world is not None
    if decision not in world.decision_options:
        return _error(
            world,
            "submit_verdict",
            f"decision must be one of: {', '.join(world.decision_options)}",
            args,
        )
    if root_cause not in world.root_cause_options:
        return _error(
            world,
            "submit_verdict",
            f"root_cause must be one of: {', '.join(world.root_cause_options)}",
            args,
        )
    if not isinstance(confidence, (int, float)) or not 0 <= float(confidence) <= 1:
        return _error(world, "submit_verdict", "confidence must be a number in [0, 1].", args)
    if not isinstance(citation_ids, list):
        return _error(world, "submit_verdict", "citation_ids must be a list of testimony IDs.", args)
    before = len(world.official_record)
    verdict = Verdict(
        decision=decision,
        confidence=float(confidence),
        root_cause=root_cause,
        citations=[str(item) for item in citation_ids],
        rationale=str(rationale or ""),
    )
    world.final_verdict = verdict
    world.hearing_closed = True
    world.call_log.append(
        ToolCallLog("submit_verdict", True, "verdict recorded", args, before, len(world.official_record))
    )
    return {
        "ok": True,
        "world_id": world.world_id,
        "verdict": verdict.normalized(),
        "message": "Verdict recorded. The task is complete; do not repeat or reconsider it.",
    }
