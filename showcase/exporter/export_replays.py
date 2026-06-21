from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from parliament.policies import loud_capture, targeted_oracle, uniform_floor
from parliament.state import register_world, reset_worlds
from parliament.tools import list_specialists
from parliament.worlds import build_world, shipped_task_specs

OUTPUT = ROOT / "showcase" / "app" / "public" / "replays"
POLICIES = {
    "targeted_oracle": ("Trained Speaker", "Cross-examines the right people", targeted_oracle),
    "loud_capture": ("Loud Capture", "Believes the loudest bids", loud_capture),
    "uniform_floor": ("Uniform Floor", "Gives everyone a turn", uniform_floor),
}


def presets() -> list[dict[str, Any]]:
    rows = shipped_task_specs()
    wanted = [
        ("incident-response-medium-004", "Incident Response"),
        ("product-rollback-easy-001", "Product Rollback"),
    ]
    security = next(
        row
        for row in rows
        if row["domain"] == "security_access_review" and row["difficulty"] == "medium"
    )
    wanted.append((str(security["world_id"]), "Security Review"))
    by_id = {str(row["world_id"]): row for row in rows}
    return [{"label": label, **by_id[world_id]} for world_id, label in wanted]


def make_world(row: dict[str, Any]):
    return build_world(
        domain=str(row["domain"]),
        difficulty=str(row["difficulty"]),
        seed=int(row["seed"]),
        world_id=str(row["world_id"]),
    )


def replay(row: dict[str, Any], policy_id: str) -> dict[str, Any]:
    reset_worlds()
    initial_world = make_world(row)
    register_world(initial_world)
    specialists = list_specialists(initial_world.world_id)["specialists"]
    reset_worlds()
    world = make_world(row)
    policy_label, _subtitle, policy = POLICIES[policy_id]
    reward = policy(world)

    events: list[dict[str, Any]] = [
        {
            "index": 0,
            "type": "session_start",
            "payload": {
                "narrative": world.narrative,
                "specialists": specialists,
                "budget_total": world.token_budget,
                "max_interactions": world.max_interactions,
            },
        }
    ]
    interactions = 0
    for index, log in enumerate(world.call_log, 1):
        if log.ok and log.tool in {"grant_floor", "cross_examine"}:
            interactions += 1
        record = world.official_record[: log.record_len_after]
        testimony = None
        if log.record_len_after > log.record_len_before:
            block = world.official_record[log.record_len_after - 1]
            testimony = block.visible_dict(world.specialists[block.specialist_id])
        events.append(
            {
                "index": index,
                "type": "tool_call",
                "tool": log.tool,
                "ok": log.ok,
                "message": log.message,
                "args": log.args,
                "budget_used": sum(block.token_count for block in record),
                "budget_remaining": world.token_budget
                - sum(block.token_count for block in record),
                "budget_total": world.token_budget,
                "interactions_used": interactions,
                "max_interactions": world.max_interactions,
                "testimony_added": testimony,
                "verdict": (
                    world.final_verdict.normalized()
                    if log.ok and log.tool == "submit_verdict" and world.final_verdict
                    else None
                ),
            }
        )

    return {
        "meta": {
            "world_id": world.world_id,
            "domain": world.domain,
            "difficulty": world.difficulty,
            "policy_id": policy_id,
            "policy_label": policy_label,
            "generated_at": datetime.now(UTC).isoformat(),
        },
        "world": {
            "world_id": world.world_id,
            "domain": world.domain,
            "difficulty": world.difficulty,
            "narrative": world.narrative,
            "token_budget": world.token_budget,
            "max_interactions": world.max_interactions,
            "decision_options": world.decision_options,
            "root_cause_options": world.root_cause_options,
            "ground_truth": {
                "decision": world.truth_decision,
                "root_cause": world.truth_root_cause,
            },
        },
        "reward": {
            "reward": reward.reward,
            "subscores": reward.subscores,
            "metadata": {
                key: reward.metadata[key]
                for key in (
                    "budget_used",
                    "budget_total",
                    "num_interactions",
                    "final_decision",
                    "final_root_cause",
                    "confidence",
                    "total_record_tokens",
                    "relevant_tokens",
                    "decoy_tokens",
                    "fluff_tokens",
                    "duplicate_tokens",
                    "cited_testimony_ids",
                    "valid_citation_ids",
                )
                if key in reward.metadata
            },
        },
        "timeline": events,
        "final_record": {
            "budget_used": world.budget_used,
            "budget_remaining": world.budget_remaining,
            "testimony": [
                block.visible_dict(world.specialists[block.specialist_id])
                for block in world.official_record
            ],
        },
    }


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    files: list[dict[str, str]] = []
    preset_rows = presets()
    for row in preset_rows:
        for policy_id, (label, subtitle, _policy) in POLICIES.items():
            filename = f"{row['world_id']}__{policy_id}.json"
            (OUTPUT / filename).write_text(
                json.dumps(replay(row, policy_id), indent=2), encoding="utf-8"
            )
            files.append(
                {
                    "world_id": str(row["world_id"]),
                    "policy_id": policy_id,
                    "policy_label": label,
                    "policy_subtitle": subtitle,
                    "file": filename,
                }
            )
    index = {
        "presets": [
            {
                "world_id": str(row["world_id"]),
                "label": str(row["label"]),
                "domain": str(row["domain"]),
                "difficulty": str(row["difficulty"]),
            }
            for row in preset_rows
        ],
        "policies": [
            {"id": key, "label": value[0], "subtitle": value[1]}
            for key, value in POLICIES.items()
        ],
        "files": files,
    }
    (OUTPUT / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
