import type { PolicyId, ReplayBundle, ReplayIndex, StrategySummary } from "./types";
export async function loadReplay(worldId:string, policy:PolicyId):Promise<ReplayBundle>{ const r=await fetch(`/replays/${worldId}__${policy}.json`); if(!r.ok) throw new Error("Replay not found"); return r.json(); }
export async function loadReplayIndex():Promise<ReplayIndex>{ return fetch("/replays/index.json").then(r=>r.json()); }
export async function loadStrategySummary():Promise<StrategySummary>{ return fetch("/strategy-summary.json").then(r=>r.json()); }
