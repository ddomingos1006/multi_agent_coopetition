"""Run one GRPO step on traces from a HUD eval job."""

from __future__ import annotations

import argparse
import asyncio

from hud import TrainingClient
from hud.utils.platform import PlatformClient

DEFAULT_JOB_ID = "bf19ae88-281c-499b-8c14-aac795f74e9f"
MODEL = "parliament-qwen36-35b"
GROUP_SIZE = 8
LR = 1e-5
PAGE_SIZE = 1000
MIN_REWARD = 0.1
GROUPS_PER_BATCH = 20


def chunk_trace_ids(trace_ids: list[str], *, group_size: int, groups_per_batch: int) -> list[list[str]]:
    if len(trace_ids) % group_size != 0:
        raise ValueError(f"{len(trace_ids)} traces do not form complete groups of {group_size}")
    groups = [
        trace_ids[i : i + group_size] for i in range(0, len(trace_ids), group_size)
    ]
    batches: list[list[str]] = []
    for start in range(0, len(groups), groups_per_batch):
        batch_groups = groups[start : start + groups_per_batch]
        batches.append([trace_id for group in batch_groups for trace_id in group])
    return batches

def fetch_traces(job_id: str) -> list[dict]:
    client = PlatformClient.from_settings()
    items: list[dict] = []
    offset = 0
    while True:
        data = client.get(
            f"/jobs/{job_id}/traces",
            params={"limit": PAGE_SIZE, "offset": offset},
        )
        batch = data if isinstance(data, list) else (data.get("items") or [])
        if not batch:
            break
        items.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    # Preserve every trace position until after grouping. Removing failed traces here
    # would shift all later rows and mix samples from different GRPO groups.
    return [trace for trace in items if trace.get("id")]


def select_trace_ids(
    traces: list[dict],
    *,
    group_size: int,
    min_reward: float,
    max_groups: int | None,
) -> tuple[list[str], int]:
    groups = [traces[i : i + group_size] for i in range(0, len(traces), group_size)]
    incomplete = sum(1 for group in groups if len(group) != group_size)
    complete_groups = [group for group in groups if len(group) == group_size]

    terminal_groups = [
        group
        for group in complete_groups
        if all(
            trace.get("status") == "completed"
            and not trace.get("error")
            and trace.get("reward") is not None
            for trace in group
        )
    ]
    infrastructure_dropped = len(complete_groups) - len(terminal_groups)
    clean_groups = [
        group
        for group in terminal_groups
        if all(float(trace["reward"]) > min_reward for trace in group)
    ]
    reward_dropped = len(terminal_groups) - len(clean_groups)
    if max_groups is not None:
        clean_groups = clean_groups[:max_groups]

    trace_ids = [trace["id"] for group in clean_groups for trace in group]
    removed = len(traces) - len(trace_ids)
    print(
        f"Fetched {len(traces)} traces in {len(complete_groups)} complete groups "
        f"({incomplete} incomplete tail groups ignored)",
        flush=True,
    )
    print(
        f"Filtered out {infrastructure_dropped} groups with incomplete/error traces "
        f"({infrastructure_dropped * group_size} traces) and {reward_dropped} groups "
        f"with reward <= {min_reward} ({reward_dropped * group_size} traces)",
        flush=True,
    )
    return trace_ids, removed


async def train(
    job_id: str,
    *,
    group_size: int,
    learning_rate: float,
    max_groups: int | None,
    min_reward: float,
    groups_per_batch: int,
    model: str,
) -> None:
    traces = fetch_traces(job_id)
    if not traces:
        raise SystemExit(f"No traces found for job {job_id}")

    trace_ids, _removed = select_trace_ids(
        traces,
        group_size=group_size,
        min_reward=min_reward,
        max_groups=max_groups,
    )
    if not trace_ids:
        raise SystemExit(
            f"No clean groups remain for job {job_id} "
            f"(group_size={group_size}, min_reward={min_reward})"
        )

    n = len(trace_ids)
    num_groups = n // group_size
    print(f"Job {job_id}: training on {n} traces ({num_groups} groups)", flush=True)

    batches = chunk_trace_ids(
        trace_ids,
        group_size=group_size,
        groups_per_batch=groups_per_batch,
    )
    print(
        f"Accumulating {len(batches)} forward-backward batch(es) "
        f"of up to {groups_per_batch} groups before optim step",
        flush=True,
    )

    client = TrainingClient(model)
    for index, batch in enumerate(batches, start=1):
        batch_groups = len(batch) // group_size
        print(
            f"Batch {index}/{len(batches)}: {len(batch)} traces ({batch_groups} groups)",
            flush=True,
        )
        await client.forward_backward(
            batch,
            group_size=group_size,
        )
    result = await client.optim_step(learning_rate=learning_rate)
    print("Done.", flush=True)
    for field in ("checkpoint_id", "checkpoint_name", "mean_reward", "loss"):
        value = getattr(result, field, None)
        if value is not None:
            print(f"{field}: {value}", flush=True)
    if not any(getattr(result, field, None) for field in ("checkpoint_id", "checkpoint_name")):
        print(result, flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="GRPO train step from HUD eval traces")
    parser.add_argument(
        "job_id",
        nargs="?",
        default=DEFAULT_JOB_ID,
        help="HUD eval job id containing trainable traces",
    )
    parser.add_argument("--group-size", type=int, default=GROUP_SIZE)
    parser.add_argument("--learning-rate", type=float, default=LR)
    parser.add_argument("--model", default=MODEL)
    parser.add_argument(
        "--max-groups",
        type=int,
        default=None,
        help="Cap training to this many GRPO groups (default: all complete groups)",
    )
    parser.add_argument(
        "--min-reward",
        type=float,
        default=MIN_REWARD,
        help="Drop entire groups when any trace reward is at or below this value",
    )
    parser.add_argument(
        "--groups-per-batch",
        type=int,
        default=GROUPS_PER_BATCH,
        help="Forward-backward batch size in GRPO groups before one optim step",
    )
    args = parser.parse_args()
    asyncio.run(
        train(
            args.job_id,
            group_size=args.group_size,
            learning_rate=args.learning_rate,
            max_groups=args.max_groups,
            min_reward=args.min_reward,
            groups_per_batch=args.groups_per_batch,
            model=args.model,
        )
    )


if __name__ == "__main__":
    main()
