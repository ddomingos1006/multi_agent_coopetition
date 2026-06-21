from train_step import select_trace_ids


def _trace(index: int, *, status: str = "completed", reward: float | None = 0.5, error=None):
    return {"id": str(index), "status": status, "reward": reward, "error": error}


def test_error_drops_whole_group_without_shifting_later_groups() -> None:
    traces = [_trace(index) for index in range(24)]
    traces[3] = _trace(3, status="error", reward=0.05, error="503")

    selected, removed = select_trace_ids(
        traces, group_size=8, min_reward=-1, max_groups=None
    )

    assert selected == [str(index) for index in range(8, 24)]
    assert removed == 8


def test_running_or_missing_reward_drops_whole_group() -> None:
    traces = [_trace(index) for index in range(16)]
    traces[9] = _trace(9, status="running", reward=None)

    selected, removed = select_trace_ids(
        traces, group_size=8, min_reward=-1, max_groups=None
    )

    assert selected == [str(index) for index in range(8)]
    assert removed == 8
