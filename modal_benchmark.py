from __future__ import annotations

import asyncio
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import modal

ROOT = Path(__file__).resolve().parent
REMOTE_ROOT = "/root/context-window-parliament"
HUD_SECRET = "context-window-parliament-hud"
TRAINED_MODEL = "parliament-qwen36-35b-clean"
BASE_MODEL = "Qwen/Qwen3.6-35B-A3B"
DEFAULT_WORLD = "incident-response-medium-004"

app = modal.App("context-window-parliament-benchmark")

image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install(
        "fastapi[standard]>=0.115.0",
        "fastmcp>=2.0",
        "hud-python==0.6.6",
        "pytest>=8.0",
    )
    .add_local_dir(ROOT / "parliament", f"{REMOTE_ROOT}/parliament")
    .add_local_dir(ROOT / "controller", f"{REMOTE_ROOT}/controller")
    .add_local_dir(ROOT / "environment", f"{REMOTE_ROOT}/environment")
    .add_local_file(ROOT / "env.py", f"{REMOTE_ROOT}/env.py")
    .add_local_file(ROOT / "tasks.py", f"{REMOTE_ROOT}/tasks.py")
    .add_local_file(ROOT / ".hud_eval.toml", f"{REMOTE_ROOT}/.hud_eval.toml")
    .workdir(REMOTE_ROOT)
)

LIVE_POLICY_LABELS = {
    "targeted_oracle": "Live Trained Speaker",
    "loud_capture": "Live Base Speaker",
    "uniform_floor": "Live Trained Speaker",
}

LIVE_POLICY_MODELS = {
    "targeted_oracle": TRAINED_MODEL,
    "loud_capture": BASE_MODEL,
    "uniform_floor": TRAINED_MODEL,
}

LIVE_COMPLETION_KWARGS = {
    "tool_choice": "required",
    "max_tokens": 2048,
    "temperature": 0.7,
    "extra_body": {
        "chat_template_kwargs": {
            "enable_thinking": False,
        },
    },
}


def _task_ids(start: int, count: int) -> str:
    if start < 0 or count < 1 or start + count > 500:
        raise ValueError("task range must stay within the 500 shipped worlds")
    return ",".join(str(index) for index in range(start, start + count))


def _parse_output(output: str) -> dict[str, Any]:
    patterns = {
        "runs": r"Runs:\s+(\d+)",
        "runtime_seconds": r"Time:\s+([\d.]+)s",
        "mean_reward": r"Mean reward:\s+([\d.]+)",
        "success_rate": r"Success rate:\s+([\d.]+)%",
        "errors": r"Errors:\s+(\d+)",
    }
    result: dict[str, Any] = {"output": output}
    url = re.search(r"https://hud\.ai/jobs/([a-f0-9]+)", output)
    if url:
        raw = url.group(1)
        result["job_id_compact"] = raw
        result["job_url"] = url.group(0)
    for key, pattern in patterns.items():
        match = re.search(pattern, output)
        if not match:
            continue
        value = float(match.group(1))
        result[key] = int(value) if key in {"runs", "errors"} else value
    if "success_rate" in result:
        result["success_rate"] /= 100
    result.setdefault("errors", 0)
    return result


def _find_task_row(world_id: str) -> dict[str, Any]:
    from parliament.worlds import shipped_task_specs

    for row in shipped_task_specs():
        if str(row["world_id"]) == world_id:
            return row
    raise ValueError(f"unknown world_id: {world_id}")


def _public_specialists(row: dict[str, Any]) -> list[dict[str, Any]]:
    from parliament.state import register_world, reset_worlds
    from parliament.tools import list_specialists
    from parliament.worlds import build_world

    reset_worlds()
    world = build_world(
        domain=str(row["domain"]),
        difficulty=str(row["difficulty"]),
        seed=int(row["seed"]),
        world_id=str(row["world_id"]),
    )
    register_world(world)
    return list_specialists(world.world_id)["specialists"]


def _world_payload(row: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    from parliament.worlds import build_world

    world = build_world(
        domain=str(row["domain"]),
        difficulty=str(row["difficulty"]),
        seed=int(row["seed"]),
        world_id=str(row["world_id"]),
    )
    return (
        {
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
        {
            "budget_total": world.token_budget,
            "max_interactions": world.max_interactions,
        },
    )


def _result_payload(result: Any) -> dict[str, Any]:
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict):
        inner = structured.get("result")
        if isinstance(inner, dict):
            return inner
        return structured

    for item in getattr(result, "content", []) or []:
        text = getattr(item, "text", None)
        if not isinstance(text, str):
            continue
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return {}


def _subscores_from_evaluation(evaluation: dict[str, Any]) -> dict[str, float]:
    raw = evaluation.get("subscores") or evaluation.get("info", {}).get("subscores")
    if isinstance(raw, dict):
        return {str(key): float(value) for key, value in raw.items()}
    if isinstance(raw, list):
        subscores: dict[str, float] = {}
        for item in raw:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            score = item.get("score")
            if name is not None and score is not None:
                subscores[str(name)] = float(score)
        return subscores
    return {}


def _metadata_from_evaluation(evaluation: dict[str, Any]) -> dict[str, Any]:
    candidates = [
        evaluation.get("metadata"),
        evaluation.get("info", {}).get("metadata")
        if isinstance(evaluation.get("info"), dict)
        else None,
        evaluation.get("info"),
    ]
    for candidate in candidates:
        if isinstance(candidate, dict):
            return dict(candidate)
    return {}


def _tool_name(name: str) -> str:
    known = {
        "list_specialists",
        "grant_floor",
        "cross_examine",
        "view_record",
        "submit_verdict",
    }
    if name in known:
        return name
    for suffix in known:
        if name.endswith(suffix):
            return suffix
    return name


def _replay_from_run(
    *,
    run: Any,
    row: dict[str, Any],
    policy_id: str,
    policy_label: str,
    model: str,
) -> dict[str, Any]:
    world, limits = _world_payload(row)
    specialists = _public_specialists(row)
    specialists_by_id = {str(item["id"]): item for item in specialists}
    budget_total = int(limits["budget_total"])
    max_interactions = int(limits["max_interactions"])
    budget_remaining = budget_total
    interactions_used = 0
    final_record: list[dict[str, Any]] = []

    events: list[dict[str, Any]] = [
        {
            "index": 0,
            "type": "session_start",
            "payload": {
                "narrative": world["narrative"],
                "specialists": specialists,
                "budget_total": budget_total,
                "max_interactions": max_interactions,
            },
        }
    ]

    for step in getattr(run.trace, "steps", []):
        if getattr(step, "source", None) != "tool":
            continue
        call = getattr(step, "call", None)
        result = getattr(step, "result", None)
        if call is None:
            continue
        tool = _tool_name(str(getattr(call, "name", "")))
        if tool not in {
            "list_specialists",
            "grant_floor",
            "cross_examine",
            "view_record",
            "submit_verdict",
        }:
            continue

        args = getattr(call, "arguments", {}) or {}
        if not isinstance(args, dict):
            args = {}
        payload = _result_payload(result)
        ok = bool(payload.get("ok", not bool(getattr(result, "isError", False))))
        message = str(payload.get("message") or payload.get("error") or ("ok" if ok else "error"))
        testimony = None
        verdict = None

        if tool in {"grant_floor", "cross_examine"} and ok and payload.get("testimony_id"):
            specialist_id = str(payload.get("specialist_id") or args.get("specialist_id") or "")
            specialist = specialists_by_id.get(specialist_id, {})
            token_count = int(payload.get("used_tokens") or args.get("token_budget") or 0)
            testimony = {
                "id": str(payload["testimony_id"]),
                "specialist_id": specialist_id,
                "specialist_name": str(specialist.get("name") or specialist_id),
                "role": str(specialist.get("role") or specialist_id),
                "mode": str(
                    payload.get("mode")
                    or ("cross_exam" if tool == "cross_examine" else "floor")
                ),
                "question": args.get("question") if tool == "cross_examine" else None,
                "visible_text": str(payload.get("visible_text") or ""),
                "token_count": token_count,
            }
            final_record.append(testimony)
            interactions_used += 1

        if tool == "view_record" and isinstance(payload.get("testimony"), list):
            final_record = list(payload["testimony"])

        if tool == "submit_verdict" and ok and isinstance(payload.get("verdict"), dict):
            verdict = payload["verdict"]

        if "remaining_budget" in payload:
            budget_remaining = int(payload["remaining_budget"])
        elif "budget_remaining" in payload:
            budget_remaining = int(payload["budget_remaining"])

        if "interactions_remaining" in payload:
            interactions_used = max_interactions - int(payload["interactions_remaining"])
        elif "interactions_used" in payload:
            interactions_used = int(payload["interactions_used"])

        budget_used = budget_total - budget_remaining
        events.append(
            {
                "index": len(events),
                "type": "tool_call",
                "tool": tool,
                "ok": ok,
                "message": message,
                "args": args,
                "budget_used": budget_used,
                "budget_remaining": budget_remaining,
                "budget_total": budget_total,
                "interactions_used": interactions_used,
                "max_interactions": max_interactions,
                "testimony_added": testimony,
                "verdict": verdict,
            }
        )

    evaluation = run.evaluation if isinstance(run.evaluation, dict) else {}
    metadata = _metadata_from_evaluation(evaluation)
    metadata.setdefault("budget_used", budget_total - budget_remaining)
    metadata.setdefault("budget_total", budget_total)
    metadata.setdefault("num_interactions", interactions_used)
    metadata.setdefault("model", model)
    if run.trace_id:
        metadata.setdefault("trace_id", run.trace_id)
    if run.job_id:
        metadata.setdefault("job_id", run.job_id)

    return {
        "meta": {
            "world_id": world["world_id"],
            "domain": world["domain"],
            "difficulty": world["difficulty"],
            "policy_id": policy_id,
            "policy_label": policy_label,
            "generated_at": datetime.now(UTC).isoformat(),
            "live": True,
            "model": model,
        },
        "world": world,
        "reward": {
            "reward": float(run.reward),
            "subscores": _subscores_from_evaluation(evaluation),
            "metadata": metadata,
        },
        "timeline": events,
        "final_record": {
            "budget_used": budget_total - budget_remaining,
            "budget_remaining": budget_remaining,
            "testimony": final_record,
        },
    }


async def _run_live_replay_async(
    *,
    world_id: str,
    policy_id: str,
    model: str,
    max_steps: int,
    rollout_timeout: float,
) -> dict[str, Any]:
    from hud.agents.openai_compatible import OpenAIChatAgent
    from hud.agents.types import OpenAIChatConfig
    from hud.eval import LocalRuntime, Taskset
    from hud.utils.gateway import build_gateway_client

    row = _find_task_row(world_id)
    taskset = Taskset.from_file(Path("tasks.py")).filter([world_id])
    if len(taskset) != 1:
        raise ValueError(f"could not load HUD task for world_id: {world_id}")

    agent = OpenAIChatAgent(
        config=OpenAIChatConfig(
            model=model,
            max_steps=max_steps,
            model_client=build_gateway_client("openai"),
            completion_kwargs=LIVE_COMPLETION_KWARGS,
        )
    )
    job = await taskset.run(
        agent,
        runtime=LocalRuntime(Path("env.py")),
        group=1,
        max_concurrent=1,
        rollout_timeout=rollout_timeout,
    )
    if not job.runs:
        raise RuntimeError("HUD returned no runs")
    return _replay_from_run(
        run=job.runs[0],
        row=row,
        policy_id=policy_id,
        policy_label=LIVE_POLICY_LABELS.get(policy_id, "Live Speaker"),
        model=model,
    )


def _run_live_replay(
    *,
    world_id: str,
    policy_id: str,
    model: str | None = None,
    max_steps: int = 100,
    rollout_timeout: float = 600.0,
) -> dict[str, Any]:
    selected_model = model or LIVE_POLICY_MODELS.get(policy_id, TRAINED_MODEL)
    return asyncio.run(
        _run_live_replay_async(
            world_id=world_id,
            policy_id=policy_id,
            model=selected_model,
            max_steps=max_steps,
            rollout_timeout=rollout_timeout,
        )
    )


def _eval(
    model: str,
    *,
    task_start: int,
    task_count: int,
    rollouts_per_task: int,
    max_concurrent: int,
) -> dict[str, Any]:
    command = [
        "hud",
        "eval",
        "tasks.py",
        "openai_compatible",
        "--model",
        model,
        "--task-ids",
        _task_ids(task_start, task_count),
        "--group",
        str(rollouts_per_task),
        "--max-concurrent",
        str(max_concurrent),
        "--max-steps",
        "100",
        "--yes",
    ]
    completed = subprocess.run(
        command,
        cwd=REMOTE_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=3300,
    )
    print(completed.stdout, flush=True)
    result = _parse_output(completed.stdout)
    result.update({"model": model, "exit_code": completed.returncode})
    if completed.returncode != 0:
        raise RuntimeError(json.dumps(result))
    return result


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name(
            HUD_SECRET,
            required_keys=["HUD_API_KEY", "ANTHROPIC_API_KEY"],
        )
    ],
    timeout=3600,
    max_containers=1,
)
def paired_benchmark(
    task_start: int = 200,
    task_count: int = 30,
    rollouts_per_task: int = 2,
    max_concurrent: int = 4,
) -> dict[str, Any]:
    if max_concurrent > 4:
        raise ValueError("max_concurrent is capped at 4 to protect the Tinker endpoint")
    trained = _eval(
        TRAINED_MODEL,
        task_start=task_start,
        task_count=task_count,
        rollouts_per_task=rollouts_per_task,
        max_concurrent=max_concurrent,
    )
    baseline = _eval(
        BASE_MODEL,
        task_start=task_start,
        task_count=task_count,
        rollouts_per_task=rollouts_per_task,
        max_concurrent=max_concurrent,
    )
    return {
        "trained": trained,
        "baseline": baseline,
        "mean_reward_delta": trained.get("mean_reward", 0)
        - baseline.get("mean_reward", 0),
        "success_rate_delta": trained.get("success_rate", 0)
        - baseline.get("success_rate", 0),
    }


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name(
            HUD_SECRET,
            required_keys=["HUD_API_KEY", "ANTHROPIC_API_KEY"],
        )
    ],
    timeout=3600,
    max_containers=1,
)
def eval_model(
    model: str = TRAINED_MODEL,
    task_start: int = 200,
    task_count: int = 30,
    rollouts_per_task: int = 2,
    max_concurrent: int = 4,
) -> dict[str, Any]:
    if max_concurrent > 4:
        raise ValueError("max_concurrent is capped at 4 to protect the Tinker endpoint")
    return _eval(
        model,
        task_start=task_start,
        task_count=task_count,
        rollouts_per_task=rollouts_per_task,
        max_concurrent=max_concurrent,
    )


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name(
            HUD_SECRET,
            required_keys=["HUD_API_KEY", "ANTHROPIC_API_KEY"],
        )
    ],
    timeout=900,
    max_containers=2,
)
@modal.fastapi_endpoint(method="POST")
def live_replay(payload: dict[str, Any]) -> dict[str, Any]:
    world_id = str(payload.get("world_id") or payload.get("worldId") or DEFAULT_WORLD)
    policy_id = str(payload.get("policy_id") or payload.get("policy") or "targeted_oracle")
    model = payload.get("model")
    max_steps = int(payload.get("max_steps") or payload.get("maxSteps") or 100)
    rollout_timeout = float(payload.get("rollout_timeout") or payload.get("rolloutTimeout") or 600)
    return _run_live_replay(
        world_id=world_id,
        policy_id=policy_id,
        model=str(model) if model else None,
        max_steps=max_steps,
        rollout_timeout=rollout_timeout,
    )


@app.local_entrypoint()
def main(
    task_start: int = 200,
    task_count: int = 30,
    rollouts_per_task: int = 2,
    max_concurrent: int = 4,
) -> None:
    result = paired_benchmark.remote(
        task_start=task_start,
        task_count=task_count,
        rollouts_per_task=rollouts_per_task,
        max_concurrent=max_concurrent,
    )
    print(json.dumps(result, indent=2))
