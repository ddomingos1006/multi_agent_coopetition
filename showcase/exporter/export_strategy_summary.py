from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from parliament.policies import loud_capture, random_policy, targeted_oracle, uniform_floor
from parliament.state import reset_worlds
from parliament.worlds import build_world, shipped_task_specs

OUTPUT = ROOT / "showcase" / "app" / "public" / "strategy-summary.json"
POLICIES = {
    "targeted_oracle": ("Trained Speaker", targeted_oracle),
    "uniform_floor": ("Uniform Floor", uniform_floor),
    "loud_capture": ("Loud Capture", loud_capture),
    "random": ("Random", random_policy),
}


def main() -> None:
    rows = shipped_task_specs()
    strategies = []
    for policy_id, (label, policy) in POLICIES.items():
        results = []
        for row in rows:
            reset_worlds()
            world = build_world(
                domain=str(row["domain"]),
                difficulty=str(row["difficulty"]),
                seed=int(row["seed"]),
                world_id=str(row["world_id"]),
            )
            results.append(policy(world))
        subscore_keys = results[0].subscores
        strategies.append(
            {
                "policy_id": policy_id,
                "label": label,
                "mean_reward": mean(result.reward for result in results),
                "subscore_means": {
                    key: mean(result.subscores[key] for result in results)
                    for key in subscore_keys
                },
                "mean_budget_used": mean(
                    float(result.metadata["budget_used"]) for result in results
                ),
            }
        )
    by_id = {item["policy_id"]: item for item in strategies}
    output = {
        "world_count": len(rows),
        "strategies": strategies,
        "separation": {
            "trained_vs_loud": by_id["targeted_oracle"]["mean_reward"]
            - by_id["loud_capture"]["mean_reward"],
            "trained_vs_uniform": by_id["targeted_oracle"]["mean_reward"]
            - by_id["uniform_floor"]["mean_reward"],
        },
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
