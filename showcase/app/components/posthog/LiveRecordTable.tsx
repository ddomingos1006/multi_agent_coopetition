"use client";

import { ChevronDown } from "lucide-react";
import type { LiveEventRow, SessionPhase } from "@/hooks/useSessionStream";
import { EventInspector } from "./EventInspector";
import { cn } from "@/lib/utils";

export function LiveRecordTable({
  events,
  expandedId,
  onToggle,
  phase,
  waiting = false,
}: {
  events: LiveEventRow[];
  expandedId: string | null;
  onToggle: (id: string) => void;
  phase: SessionPhase;
  waiting?: boolean;
}) {
  return (
    <div
      className="ph-panel"
      style={{
        flex: 1,
        minWidth: 0,
        display: "flex",
        flexDirection: "column",
        borderTop: "none",
        borderBottom: "none",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "10px 12px",
          borderBottom: "1px solid var(--border-3000)",
        }}
      >
        <span style={{ fontSize: 12, fontWeight: 600 }}>Live record</span>
        {phase === "running" && (
          <span className="ph-tag ph-tag-orange" style={{ fontSize: 10 }}>
            LIVE
          </span>
        )}
      </div>

      <div
        className="mono"
        style={{
          display: "grid",
          gridTemplateColumns: "1.2fr 1fr 64px 72px 1fr",
          fontSize: 10,
          textTransform: "uppercase",
          letterSpacing: "0.04em",
          color: "var(--muted-3000)",
          borderBottom: "1px solid var(--border-3000)",
          background: "var(--color-accent-3000)",
        }}
      >
        {["Event", "Source", "Δ tok", "Left", "Note"].map((h, i) => (
          <div
            key={h}
            style={{
              padding: "8px 12px",
              borderLeft: i > 0 ? "1px solid var(--border-3000)" : undefined,
            }}
          >
            {h}
          </div>
        ))}
      </div>

      <div style={{ flex: 1, overflowY: "auto", minHeight: 0 }}>
        {events.length === 0 && (
          <p style={{ padding: 20, fontSize: 13, color: "var(--muted-3000)" }}>
            {waiting
              ? "Press Start session when you're ready. The Speaker won't move until you do."
              : phase === "running"
                ? "Speaker is routing testimony…"
                : "—"}
          </p>
        )}

        {events.map((row) => {
          const open = expandedId === row.id;
          return (
            <div
              key={row.id}
              className={cn(row.flash && "ph-row-flash")}
              style={{ borderBottom: "1px solid var(--border-3000)" }}
            >
              <button
                type="button"
                onClick={() => onToggle(row.id)}
                style={{
                  display: "grid",
                  gridTemplateColumns: "1.2fr 1fr 64px 72px 1fr",
                  width: "100%",
                  textAlign: "left",
                  border: "none",
                  background: "transparent",
                  color: "inherit",
                  cursor: "pointer",
                  fontSize: 12,
                }}
                className="ac-live-row-btn"
              >
                <div style={{ display: "flex", alignItems: "center", gap: 4, padding: "8px 12px" }}>
                  <ChevronDown
                    size={12}
                    style={{
                      opacity: 0.4,
                      transform: open ? "rotate(180deg)" : undefined,
                      transition: "transform 0.15s",
                    }}
                  />
                  <span className="mono" style={{ color: "var(--link)" }}>
                    {row.tool}
                  </span>
                </div>
                <div
                  style={{
                    padding: "8px 12px",
                    borderLeft: "1px solid var(--border-3000)",
                    color: "var(--color-text-secondary-3000)",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {row.source}
                </div>
                <div
                  className="mono"
                  style={{
                    padding: "8px 12px",
                    borderLeft: "1px solid var(--border-3000)",
                    color: "var(--muted-3000)",
                  }}
                >
                  {row.tokenDelta > 0 ? `+${row.tokenDelta}` : "—"}
                </div>
                <div
                  className="mono"
                  style={{
                    padding: "8px 12px",
                    borderLeft: "1px solid var(--border-3000)",
                    color: "var(--muted-3000)",
                  }}
                >
                  {row.budgetRemaining}
                </div>
                <div
                  style={{
                    padding: "8px 12px",
                    borderLeft: "1px solid var(--border-3000)",
                    color: "var(--muted-3000)",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {row.decisionLog}
                </div>
              </button>
              {open && <EventInspector row={row} />}
            </div>
          );
        })}
      </div>
    </div>
  );
}
