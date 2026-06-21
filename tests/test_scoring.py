from __future__ import annotations

from copy import deepcopy

from parliament.models import Verdict
from parliament.policies import loud_capture, targeted_oracle
from parliament.scoring import parse_raw_verdict, score_world
from parliament.state import register_world, reset_worlds
from parliament.tools import cross_examine, grant_floor, submit_verdict
from parliament.worlds import build_world


def _fresh(domain: str = "product_rollback", difficulty: str = "medium", seed: int = 2):
    reset_worlds()
    world = build_world(domain=domain, difficulty=difficulty, seed=seed, world_id=f"{domain}-{difficulty}-{seed}")
    return register_world(world)


def test_oracle_strategy_high_reward() -> None:
    reset_worlds()
    world = build_world(domain="investment_committee", difficulty="hard", seed=5, world_id="oracle")
    result = targeted_oracle(world)
    assert result.reward > 0.80
    assert result.subscores["evidence_recall"] > 0.80


def test_loud_capture_low_reward() -> None:
    reset_worlds()
    world = build_world(domain="investment_committee", difficulty="hard", seed=5, world_id="loud")
    result = loud_capture(world)
    assert result.reward < 0.45


def test_lucky_guess_capped() -> None:
    world = _fresh()
    submit_verdict(
        world.world_id,
        world.truth_decision,
        0.99,
        world.truth_root_cause,
        [],
        "guessing without testimony",
    )
    result = score_world(world)
    assert result.reward < 0.40
    assert result.subscores["evidence_recall"] == 0.0


def test_parse_fenced_or_embedded_json_verdict() -> None:
    world = _fresh()
    payload = {
        "decision": world.truth_decision,
        "confidence": 0.85,
        "root_cause": world.truth_root_cause,
        "citation_ids": ["T1"],
        "rationale": "grounded answer",
    }
    encoded = __import__("json").dumps(payload)
    for answer in (f"```json\n{encoded}\n```", f"Here is the verdict:\n{encoded}\nDone."):
        verdict = parse_raw_verdict(answer, world)
        assert verdict is not None
        assert verdict.decision == world.truth_decision
        assert verdict.root_cause == world.truth_root_cause


def test_wrong_root_cause_penalized() -> None:
    reset_worlds()
    base = build_world(domain="incident_response", difficulty="medium", seed=4, world_id="root-base")
    targeted_oracle(base)
    good = score_world(base)

    wrong = deepcopy(base)
    wrong.world_id = "root-wrong"
    wrong.final_verdict = Verdict(
        decision=wrong.truth_decision,
        confidence=0.95,
        root_cause=next(root for root in wrong.root_cause_options if root != wrong.truth_root_cause),
        citations=[block.id for block in wrong.official_record[:2]],
        rationale="same record but wrong root cause",
    )
    bad = score_world(wrong)
    assert bad.reward < good.reward
    assert bad.subscores["gated_root_cause_accuracy"] < good.subscores["gated_root_cause_accuracy"]


def test_citations_matter() -> None:
    reset_worlds()
    world = build_world(domain="product_rollback", difficulty="medium", seed=2, world_id="cite")
    targeted_oracle(world)
    good = score_world(world)

    missing = deepcopy(world)
    missing.final_verdict = Verdict(
        decision=world.truth_decision,
        confidence=0.95,
        root_cause=world.truth_root_cause,
        citations=[],
        rationale="same answer with no citations",
    )
    bad = score_world(missing)
    assert good.subscores["citation_quality"] > bad.subscores["citation_quality"]
    assert good.reward > bad.reward


def test_precision_matters() -> None:
    reset_worlds()
    concise = build_world(domain="product_rollback", difficulty="easy", seed=1, world_id="concise")
    targeted_oracle(concise)
    concise_score = score_world(concise)

    reset_worlds()
    bloated = register_world(build_world(domain="product_rollback", difficulty="easy", seed=1, world_id="bloated"))
    for specialist in bloated.specialists.values():
        if specialist.persona_policy == "verbose_lobbyist":
            grant_floor(bloated.world_id, specialist.id, min(140, bloated.budget_remaining))
    targeted_oracle(bloated)
    bloated_score = score_world(bloated)
    assert bloated_score.subscores["evidence_precision"] < concise_score.subscores["evidence_precision"]
    assert bloated_score.reward < concise_score.reward


def test_redundancy_matters() -> None:
    world = _fresh("incident_response", "medium", 4)
    owner = next(
        specialist
        for specialist in world.specialists.values()
        if set(specialist.private_fact_ids) & set(world.required_fact_ids)
    )
    fact_id = next(fid for fid in owner.private_fact_ids if fid in world.required_fact_ids)
    question = f"What concrete evidence about {world.facts[fact_id].short_text}?"
    cross_examine(world.world_id, owner.id, question, 90)
    one = deepcopy(world)
    one.final_verdict = Verdict(
        decision=one.truth_decision,
        confidence=0.8,
        root_cause=one.truth_root_cause,
        citations=[block.id for block in one.official_record],
        rationale="one answer",
    )
    one_score = score_world(one)

    cross_examine(world.world_id, owner.id, question, 90)
    submit_verdict(
        world.world_id,
        world.truth_decision,
        0.8,
        world.truth_root_cause,
        [block.id for block in world.official_record],
        "repeated answer",
    )
    repeat_score = score_world(world)
    assert repeat_score.subscores["non_redundancy"] < one_score.subscores["non_redundancy"]


def test_budget_overrun_denied() -> None:
    world = _fresh("investment_committee", "medium", 7)
    before = len(world.official_record)
    denied = grant_floor(world.world_id, next(iter(world.specialists)), world.token_budget + 1)
    assert not denied["ok"]
    assert len(world.official_record) == before
    submit_verdict(
        world.world_id,
        world.truth_decision,
        0.9,
        world.truth_root_cause,
        [],
        "no over-budget evidence was added",
    )
    assert score_world(world).subscores["budget_discipline"] == 1.0
