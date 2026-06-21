"use client";

import { useState } from "react";
import type { SessionPhase } from "@/hooks/useSessionStream";
import type { ReplayBundle } from "@/lib/types";
import { SCORE_FOOTNOTE, SCORE_LABELS } from "@/lib/copy";
import { PropertyPill } from "./PropertyPill";

export function TokenAnalyticsPanel({
  bundle,
  budgetUsed,
  budgetTotal,
  budgetRemaining,
  naiveStack,
  interactionsUsed,
  maxInteractions,
  phase,
}: {
  bundle: ReplayBundle;
  budgetUsed: number;
  budgetTotal: number;
  budgetRemaining: number;
  naiveStack: number;
  interactionsUsed: number;
  maxInteractions: number;
  phase: SessionPhase;
}) {
  const [showScore, setShowScore] = useState(false);

  const speakerPct = Math.min(100, (budgetUsed / budgetTotal) * 100);
  const naivePct = Math.min(100, (naiveStack / budgetTotal) * 100);
  const naiveOver = naivePct >= 100;

  return (
    <div
      className="ph-panel"
      style={{
        width: 260,
        flexShrink: 0,
        display: "flex",
        flexDirection: "column",
        borderTop: "none",
        borderBottom: "none",
        borderRight: "none",
      }}
    >
      <div
        style={{
          padding: "10px 12px",
          borderBottom: "1px solid var(--border-3000)",
          fontSize: 12,
          fontWeight: 600,
        }}
      >
        Budget
      </div>

      <div style={{ padding: 12, display: "flex", flexDirection: "column", gap: 18 }}>
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
            <span style={{ fontSize: 11, color: "var(--muted-3000)" }}>Naive stack</span>
            <PropertyPill label="Σ" value={`${naiveStack}`} variant={naiveOver ? "orange" : "default"} />
          </div>
          <div
            style={{
              height: 10,
              borderRadius: 4,
              border: "1px solid var(--border-3000)",
              background: "var(--color-accent-3000)",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                height: "100%",
                width: `${naivePct}%`,
                background: naiveOver ? "var(--brand-red)" : "rgb(219 55 7 / 55%)",
                transition: "width 0.4s ease",
              }}
            />
          </div>
        </div>

        <div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
            <span style={{ fontSize: 11, color: "var(--muted-3000)" }}>Speaker</span>
            <PropertyPill label="USED" value={`${budgetUsed}`} variant="green" />
          </div>
          <div
            style={{
              height: 10,
              borderRadius: 4,
              border: "1px solid var(--border-3000)",
              background: "var(--color-accent-3000)",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                height: "100%",
                width: `${speakerPct}%`,
                background: speakerPct > 85 ? "var(--brand-red)" : "var(--success)",
                transition: "width 0.4s ease",
              }}
            />
          </div>
          <p className="mono" style={{ marginTop: 6, fontSize: 10, color: "var(--muted-3000)" }}>
            {budgetRemaining} left · {interactionsUsed}/{maxInteractions}
          </p>
        </div>

        {phase === "complete" && (
          <div style={{ borderTop: "1px solid var(--border-3000)", paddingTop: 14 }}>
            <div className="mono" style={{ fontSize: 10, color: "var(--muted-3000)", textTransform: "uppercase" }}>
              Reward
            </div>
            <div style={{ marginTop: 4, fontSize: 28, fontWeight: 600, letterSpacing: "-0.03em" }}>
              {bundle.reward.reward.toFixed(2)}
            </div>
            <button
              type="button"
              onClick={() => setShowScore(!showScore)}
              className="mono"
              style={{
                marginTop: 8,
                fontSize: 10,
                color: "var(--link)",
                background: "none",
                border: "none",
                cursor: "pointer",
                padding: 0,
                textDecoration: "underline",
                textUnderlineOffset: 2,
              }}
            >
              {showScore ? "Hide breakdown" : "Show breakdown"}
            </button>
            {showScore && (
              <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 6 }}>
                {Object.entries(bundle.reward.subscores).map(([key, val]) => (
                  <div key={key} className="mono" style={{ display: "flex", justifyContent: "space-between", fontSize: 10 }}>
                    <span style={{ color: "var(--muted-3000)" }}>{SCORE_LABELS[key] ?? key}</span>
                    <span style={{ color: key.includes("penalty") && val > 0 ? "var(--brand-red)" : undefined }}>
                      {val.toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>
            )}
            <p style={{ marginTop: 10, fontSize: 10, lineHeight: 1.45, color: "var(--muted-3000)" }}>
              {SCORE_FOOTNOTE}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
