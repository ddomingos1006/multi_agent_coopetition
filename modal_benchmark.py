from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

import modal

ROOT = Path(__file__).resolve().parent
REMOTE_ROOT = "/root/context-window-parliament"
HUD_SECRET = "context-window-parliament-hud"
TRAINED_MODEL = "parliament-qwen36-35b-clean"
BASE_MODEL = "Qwen/Qwen3.6-35B-A3B"

app = modal.App("context-window-parliament-benchmark")

image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install("fastmcp>=2.0", "hud-python==0.6.6", "pytest>=8.0")
    .add_local_dir(ROOT / "parliament", f"{REMOTE_ROOT}/parliament")
    .add_local_dir(ROOT / "controller", f"{REMOTE_ROOT}/controller")
    .add_local_dir(ROOT / "environment", f"{REMOTE_ROOT}/environment")
    .add_local_file(ROOT / "env.py", f"{REMOTE_ROOT}/env.py")
    .add_local_file(ROOT / "tasks.py", f"{REMOTE_ROOT}/tasks.py")
    .add_local_file(ROOT / ".hud_eval.toml", f"{REMOTE_ROOT}/.hud_eval.toml")
    .workdir(REMOTE_ROOT)
)


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
    secrets=[modal.Secret.from_name(HUD_SECRET, required_keys=["HUD_API_KEY"])],
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
    secrets=[modal.Secret.from_name(HUD_SECRET, required_keys=["HUD_API_KEY"])],
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
