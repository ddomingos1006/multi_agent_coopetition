"""Deterministic hidden-world scoring."""

from __future__ import annotations

import json
import re
from typing import Any

from parliament.models import RewardBreakdown, Verdict, World
from parliament.parsing import extract_tags

SUBSCORE_NAMES = [
    "gated_decision_accuracy",
    "gated_root_cause_accuracy",
    "evidence_recall",
    "evidence_precision",
    "non_redundancy",
    "citation_quality",
    "budget_discipline",
    "unsupported_claim_penalty",
]


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def parse_raw_verdict(raw_answer: str | None, world: World) -> Verdict | None:
    """Parse a raw, fenced, or prose-embedded JSON verdict as a fallback."""

    if not raw_answer:
        return None
    decoder = json.JSONDecoder()
    candidates: list[dict[str, Any]] = []
    try:
        parsed = json.loads(raw_answer)
        if isinstance(parsed, dict):
            candidates.append(parsed)
    except json.JSONDecodeError:
        for index, char in enumerate(raw_answer):
            if char != "{":
                continue
            try:
                parsed, _end = decoder.raw_decode(raw_answer[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                candidates.append(parsed)

    for data in reversed(candidates):
        decision = data.get("decision")
        root_cause = data.get("root_cause")
        confidence = data.get("confidence", 0.0)
        citations = data.get("citation_ids", data.get("citations", []))
        rationale = data.get("rationale", "")
        if decision not in world.decision_options or root_cause not in world.root_cause_options:
            continue
        if not isinstance(confidence, (int, float)):
            continue
        return Verdict(
            decision=decision,
            confidence=clamp(float(confidence)),
            root_cause=root_cause,
            citations=[str(item) for item in citations] if isinstance(citations, list) else [],
            rationale=str(rationale),
        )
    return None


def score_world(world: World, raw_answer: str | None = None) -> RewardBreakdown:
    """Compute deterministic decomposed reward for a completed hearing."""

    verdict = world.final_verdict or parse_raw_verdict(raw_answer, world)
    if verdict is None:
        metadata = _base_metadata(world)
        metadata["error"] = "missing_or_unparsable_verdict"
        return RewardBreakdown(
            reward=0.05,
            subscores={name: 0.0 for name in SUBSCORE_NAMES},
            metadata=metadata,
        )

    public_leak = detect_public_leakage(world)
    total_record_tokens = world.budget_used
    seen_fact_ids = {fid for block in world.official_record for fid in block.hidden_fact_ids}
    required_seen = set(world.required_fact_ids) & seen_fact_ids
    required_total = sum(world.facts[fid].weight for fid in world.required_fact_ids)
    required_seen_weight = sum(world.facts[fid].weight for fid in required_seen)
    evidence_recall = required_seen_weight / required_total if required_total > 0 else 0.0

    if required_total <= 0:
        evidence_error = "world_has_no_required_facts"
    else:
        evidence_error = None

    p = clamp(verdict.confidence)
    if verdict.decision == world.truth_decision:
        decision_accuracy_raw = 0.5 + 0.5 * p
    else:
        decision_accuracy_raw = 0.5 * (1.0 - p)
    gated_decision_accuracy = decision_accuracy_raw * (0.25 + 0.75 * evidence_recall)

    root_raw = _root_cause_accuracy_raw(verdict.root_cause, world.truth_root_cause)
    truth_root_tags = extract_tags(world.truth_root_cause)
    root_fact_ids = [
        fid
        for fid in [*world.required_fact_ids, *world.supporting_fact_ids]
        if world.facts[fid].root_cause_tags & truth_root_tags
    ]
    if root_fact_ids:
        root_total = sum(world.facts[fid].weight for fid in root_fact_ids)
        root_seen = sum(world.facts[fid].weight for fid in root_fact_ids if fid in seen_fact_ids)
        root_evidence_recall = root_seen / root_total if root_total else evidence_recall
        root_fallback = False
    else:
        root_total = required_total
        root_seen = required_seen_weight
        root_evidence_recall = evidence_recall
        root_fallback = True
    gated_root_cause_accuracy = root_raw * (0.25 + 0.75 * root_evidence_recall)

    relevant_tokens = sum(block.relevant_tokens for block in world.official_record)
    decoy_tokens = sum(block.decoy_tokens for block in world.official_record)
    fluff_tokens = sum(block.fluff_tokens for block in world.official_record)
    duplicate_tokens = sum(block.duplicate_tokens for block in world.official_record)
    evidence_precision = relevant_tokens / max(1, total_record_tokens)
    non_redundancy = clamp(1.0 - duplicate_tokens / max(1, total_record_tokens))

    valid_citation_ids = {block.id for block in world.official_record} & set(verdict.citations)
    cited_blocks = [block for block in world.official_record if block.id in valid_citation_ids]
    cited_fact_ids = {fid for block in cited_blocks for fid in block.hidden_fact_ids}
    cited_required = cited_fact_ids & set(world.required_fact_ids)
    cited_required_weight = sum(world.facts[fid].weight for fid in cited_required)
    citation_quality = cited_required_weight / required_total if required_total > 0 else 0.0

    budget_discipline = (
        1.0
        if world.budget_used <= world.token_budget
        else max(0.0, 1.0 - (world.budget_used - world.token_budget) / max(1, world.token_budget))
    )
    unsupported_claim_penalty = _unsupported_claim_penalty(world, verdict, seen_fact_ids, cited_fact_ids)

    subscores = {
        "gated_decision_accuracy": clamp(gated_decision_accuracy),
        "gated_root_cause_accuracy": clamp(gated_root_cause_accuracy),
        "evidence_recall": clamp(evidence_recall),
        "evidence_precision": clamp(evidence_precision),
        "non_redundancy": clamp(non_redundancy),
        "citation_quality": clamp(citation_quality),
        "budget_discipline": clamp(budget_discipline),
        "unsupported_claim_penalty": clamp(unsupported_claim_penalty),
    }
    reward = (
        0.24 * subscores["gated_decision_accuracy"]
        + 0.12 * subscores["gated_root_cause_accuracy"]
        + 0.30 * subscores["evidence_recall"]
        + 0.14 * subscores["evidence_precision"]
        + 0.08 * subscores["non_redundancy"]
        + 0.07 * subscores["citation_quality"]
        + 0.05 * subscores["budget_discipline"]
        - 0.10 * subscores["unsupported_claim_penalty"]
    )
    reward = clamp(reward)

    if total_record_tokens == 0:
        reward = min(reward, 0.30)
    if verdict.decision == world.truth_decision and evidence_recall < 0.15:
        reward = min(reward, 0.40)
    if public_leak:
        reward = 0.0

    metadata = _base_metadata(world)
    metadata.update(
        {
            "final_decision": verdict.decision,
            "truth_decision": world.truth_decision,
            "final_root_cause": verdict.root_cause,
            "truth_root_cause": world.truth_root_cause,
            "confidence": p,
            "required_fact_ids_seen_count": len(required_seen),
            "required_fact_weight_seen": required_seen_weight,
            "required_fact_weight_total": required_total,
            "root_cause_evidence_weight_seen": root_seen,
            "root_cause_evidence_weight_total": root_total,
            "root_cause_evidence_fallback": root_fallback,
            "total_record_tokens": total_record_tokens,
            "relevant_tokens": relevant_tokens,
            "decoy_tokens": decoy_tokens,
            "fluff_tokens": fluff_tokens,
            "duplicate_tokens": duplicate_tokens,
            "cited_testimony_ids": list(verdict.citations),
            "valid_citation_ids": sorted(valid_citation_ids),
            "facts_supported_by_citations": sorted(cited_fact_ids),
            "budget_used": world.budget_used,
            "budget_total": world.token_budget,
            "num_interactions": world.interaction_count,
            "public_leakage_detected": public_leak,
        }
    )
    if evidence_error:
        metadata["error"] = evidence_error
    return RewardBreakdown(round(reward, 6), subscores, metadata)


def _root_cause_accuracy_raw(submitted: str, truth: str) -> float:
    if submitted == truth:
        return 1.0
    if submitted in {"unknown", "uncertain"} and truth in {"unknown", "uncertain"}:
        return 1.0
    if submitted in {"unknown", "uncertain"} and truth not in {"unknown", "uncertain"}:
        return 0.25
    return 0.0


def _unsupported_claim_penalty(
    world: World,
    verdict: Verdict,
    seen_fact_ids: set[str],
    cited_fact_ids: set[str],
) -> float:
    penalty = 0.0
    if verdict.root_cause != world.truth_root_cause and world.truth_root_cause not in {"unknown", "uncertain"}:
        penalty = max(penalty, 0.4)
    submitted_tags = extract_tags(verdict.root_cause)
    record_has_submitted_root = any(world.facts[fid].root_cause_tags & submitted_tags for fid in seen_fact_ids)
    cited_has_submitted_root = any(world.facts[fid].root_cause_tags & submitted_tags for fid in cited_fact_ids)
    if verdict.root_cause == world.truth_root_cause and not record_has_submitted_root:
        penalty = max(penalty, 0.6)
    if not (set(world.required_fact_ids) & seen_fact_ids):
        penalty += 0.2
    if not cited_has_submitted_root:
        penalty += 0.2
    valid_ids = {block.id for block in world.official_record}
    invalid_count = len([citation for citation in verdict.citations if citation not in valid_ids])
    penalty += min(0.2, 0.05 * invalid_count)

    rationale = verdict.rationale.lower().replace("-", "_")
    cited_tags = set()
    for fid in cited_fact_ids:
        cited_tags |= world.facts[fid].root_cause_tags
    unsupported_mentions = 0
    for option in world.root_cause_options:
        option_text = option.lower()
        option_words = option_text.replace("_", " ")
        if option_text in rationale or option_words in rationale:
            if not (extract_tags(option) & cited_tags):
                unsupported_mentions += 1
    penalty += min(0.2, 0.1 * unsupported_mentions)
    return clamp(penalty)


def detect_public_leakage(world: World) -> bool:
    """Detect hidden IDs or exact numeric evidence in public bids."""

    public = "\n".join(
        f"{sp.id} {sp.name} {sp.role} {sp.public_bid} {sp.claimed_priority}"
        for sp in world.specialists.values()
    )
    for fact in world.facts.values():
        for phrase in fact.leak_guard_phrases:
            if phrase and _contains_exact_marker(public, phrase):
                return True
    return False


def _contains_exact_marker(text: str, marker: str) -> bool:
    """Return true when a hidden ID or numeric marker appears as its own token."""

    pattern = rf"(?<![A-Za-z0-9_]){re.escape(marker)}(?![A-Za-z0-9_])"
    return re.search(pattern, text) is not None


def _base_metadata(world: World) -> dict[str, Any]:
    return {
        "world_id": world.world_id,
        "domain": world.domain,
        "difficulty": world.difficulty,
        "seed": world.seed,
        "budget_used": world.budget_used,
        "budget_total": world.token_budget,
        "num_interactions": world.interaction_count,
    }
