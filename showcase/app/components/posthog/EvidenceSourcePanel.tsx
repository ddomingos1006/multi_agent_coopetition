"use client";

import { useState } from "react";
import type { SampledInfo, SessionPhase } from "@/hooks/useSessionStream";
import type { ReplayBundle, SpecialistCard } from "@/lib/types";
import { PropertyPill } from "./PropertyPill";

const LM_BG = ["var(--lm-1-bg)", "var(--lm-2-bg)", "var(--lm-4-bg)", "var(--lm-7-bg)", "var(--lm-11-bg)"];
const LM_TEXT = ["var(--lm-1-text)", "var(--lm-2-text)", "var(--lm-4-text)", "var(--lm-7-text)", "var(--lm-11-text)"];

export function EvidenceSourcePanel({
  specialists,
  visibleIds,
  activeId,
  sampledMap,
  phase,
}: {
  bundle: ReplayBundle;
  specialists: SpecialistCard[];
  visibleIds: string[];
  activeId: string | null;
  sampledMap: Record<string, SampledInfo>;
  phase: SessionPhase;
}) {
  const [expanded, setExpanded] = useState(true);
  const visible = specialists.filter((s) => visibleIds.includes(s.id));

  return (
    <div
      className="ph-panel"
      style={{
        width: 280,
        flexShrink: 0,
        display: "flex",
        flexDirection: "column",
        borderTop: "none",
        borderBottom: "none",
        borderLeft: "none",
      }}
    >
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "10px 12px",
          border: "none",
          borderBottom: "1px solid var(--border-3000)",
          background: "transparent",
          color: "var(--color-text-secondary-3000)",
          cursor: "pointer",
          width: "100%",
          textAlign: "left",
        }}
      >
        <span className="mono" style={{ fontSize: 10 }}>
          {expanded ? "▾" : "▸"}
        </span>
        <span style={{ fontSize: 12, fontWeight: 600 }}>Sources</span>
        <span className="mono" style={{ marginLeft: "auto", fontSize: 10, color: "var(--muted-3000)" }}>
          {visible.length}
        </span>
      </button>

      {expanded && (
        <div style={{ flex: 1, overflowY: "auto", minHeight: 0 }}>
          {visible.length === 0 && phase === "running" && (
            <p style={{ padding: 12, fontSize: 12, color: "var(--muted-3000)" }}>Opening roster…</p>
          )}
          {visible.map((s, i) => {
            const sampled = sampledMap[s.id];
            const active = activeId === s.id;
            return (
              <div
                key={s.id}
                style={{
                  padding: "10px 12px",
                  borderBottom: "1px solid var(--border-3000)",
                  background: active
                    ? "rgb(247 165 3 / 8%)"
                    : sampled
                      ? "rgb(56 134 0 / 6%)"
                      : "transparent",
                }}
              >
                <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                  <span
                    className="ph-lettermark"
                    style={{
                      width: 28,
                      height: 28,
                      fontSize: 12,
                      background: LM_BG[i % LM_BG.length],
                      color: LM_TEXT[i % LM_TEXT.length],
                    }}
                  >
                    {s.name.charAt(0)}
                  </span>
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div style={{ fontSize: 13, fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.name}</div>
                    <div className="mono" style={{ fontSize: 10, color: "var(--muted-3000)" }}>
                      {s.role}
                    </div>
                  </div>
                </div>
                <div style={{ marginTop: 8, display: "flex", flexWrap: "wrap", gap: 4, justifyContent: "flex-end" }}>
                  {active && <PropertyPill label="PULL" value="…" variant="orange" />}
                  {sampled && <PropertyPill label="IN" value={`${sampled.tokens}t`} variant="green" />}
                  {!active && !sampled && (
                    <PropertyPill label="ASK" value={`${s.requested_tokens}`} />
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
