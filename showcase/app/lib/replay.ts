import type { PolicyId, ReplayBundle, ReplayIndex, StrategySummary } from "./types";

function liveReplayEnabled() {
  if (process.env.NEXT_PUBLIC_PARLIAMENT_LIVE === "1") return true;
  if (typeof window === "undefined") return false;
  return new URLSearchParams(window.location.search).get("live") === "1";
}

async function loadStaticReplay(worldId: string, policy: PolicyId): Promise<ReplayBundle> {
  const replay = await fetch(`/replays/${worldId}__${policy}.json`);
  if (!replay.ok) throw new Error("Replay not found");
  return replay.json();
}

export async function loadReplay(worldId: string, policy: PolicyId): Promise<ReplayBundle> {
  if (!liveReplayEnabled()) return loadStaticReplay(worldId, policy);

  try {
    const replay = await fetch("/api/live-run", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ world_id: worldId, policy_id: policy }),
      cache: "no-store",
    });
    if (replay.ok) return replay.json();
    console.warn("Live replay unavailable; falling back to bundled replay.");
  } catch (error) {
    console.warn("Live replay failed; falling back to bundled replay.", error);
  }

  return loadStaticReplay(worldId, policy);
}

export async function loadReplayIndex(): Promise<ReplayIndex> {
  return fetch("/replays/index.json").then((r) => r.json());
}

export async function loadStrategySummary(): Promise<StrategySummary> {
  return fetch("/strategy-summary.json").then((r) => r.json());
}
