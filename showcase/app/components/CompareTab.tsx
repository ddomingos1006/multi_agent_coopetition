"use client";

import { useEffect, useState } from "react";
import { loadStrategySummary } from "@/lib/replay";
import type { PolicyId, StrategySummary } from "@/lib/types";
import { PropertyPill } from "./posthog/PropertyPill";

export function CompareTab({ replayAs }: { replayAs: (p: PolicyId) => void }) {
  const [data, setData] = useState<StrategySummary | null>(null);
  const [raw, setRaw] = useState(false);
  useEffect(() => {
    loadStrategySummary().then(setData);
  }, []);
  if (!data) {
    return <p className="mono" style={{ fontSize: 12, color: "var(--muted-3000)" }}>Loading strategy runs…</p>;
  }
  const trained = data.strategies.find((x) => x.policy_id === "targeted_oracle")!;
  const loud = data.strategies.find((x) => x.policy_id === "loud_capture")!;

  return (
    <div className="ph-panel" style={{ maxWidth: 640, padding: 20 }}>
      <p style={{ fontSize: 14, color: "var(--color-text-secondary-3000)", marginBottom: 20 }}>
        Trained Speaker averages <strong style={{ color: "var(--primary-3000)" }}>{trained.mean_reward.toFixed(2)}</strong> on{" "}
        {data.world_count} worlds. Loud Capture sits at {loud.mean_reward.toFixed(2)}.
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {data.strategies.map((s) => (
          <div key={s.policy_id}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
              <span style={{ fontSize: 13, fontWeight: 500 }}>{s.label}</span>
              <PropertyPill label="MEAN" value={s.mean_reward.toFixed(3)} variant={s.policy_id === "targeted_oracle" ? "green" : "default"} />
            </div>
            <div
              style={{
                height: 8,
                borderRadius: 4,
                border: "1px solid var(--border-3000)",
                background: "var(--color-accent-3000)",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  height: "100%",
                  width: `${s.mean_reward * 100}%`,
                  background: s.policy_id === "targeted_oracle" ? "var(--primary-3000)" : "var(--brand-red)",
                  opacity: s.policy_id === "targeted_oracle" ? 1 : 0.45,
                }}
              />
            </div>
            <p className="mono" style={{ marginTop: 4, fontSize: 10, color: "var(--muted-3000)" }}>
              recall {s.subscore_means.evidence_recall.toFixed(2)} · {s.mean_budget_used.toFixed(0)} tokens
            </p>
          </div>
        ))}
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 20 }}>
        <button type="button" className="ph-btn-primary ph-btn-primary-accent" onClick={() => replayAs("targeted_oracle")}>
          Run as Trained Speaker
        </button>
        <button type="button" className="ph-btn-ghost" onClick={() => replayAs("loud_capture")}>
          Run as Loud Capture
        </button>
        <button
          type="button"
          className="mono"
          onClick={() => setRaw(!raw)}
          style={{
            fontSize: 11,
            color: "var(--muted-3000)",
            background: "none",
            border: "none",
            cursor: "pointer",
            textDecoration: "underline",
            textUnderlineOffset: 2,
          }}
        >
          Raw numbers
        </button>
      </div>
      {raw && (
        <pre
          className="mono"
          style={{
            marginTop: 16,
            overflowX: "auto",
            border: "1px solid var(--border-3000)",
            background: "var(--color-accent-3000)",
            padding: 12,
            fontSize: 10,
            color: "var(--muted-3000)",
            borderRadius: "var(--radius)",
          }}
        >
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  );
}
