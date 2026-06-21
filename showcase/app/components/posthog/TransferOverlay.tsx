"use client";

import type { TransferState } from "@/hooks/useSessionStream";
import { PropertyPill } from "./PropertyPill";

export function TransferOverlay({ transfer }: { transfer: TransferState | null }) {
  if (!transfer) return null;

  return (
    <div className={`ph-transfer ph-transfer-${transfer.phase}`} aria-hidden>
      <div className="ph-transfer-card">
        <div
          className="mono"
          style={{
            fontSize: 10,
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            color: "var(--brand-red)",
          }}
        >
          Pulling testimony
        </div>
        <div style={{ marginTop: 4, fontSize: 13, fontWeight: 600 }}>{transfer.specialistName}</div>
        <div className="mono" style={{ marginTop: 4, fontSize: 10, color: "var(--muted-3000)" }}>
          {transfer.testimonyId}
        </div>
        <p
          style={{
            marginTop: 8,
            fontSize: 12,
            lineHeight: 1.5,
            color: "var(--color-text-secondary-3000)",
            display: "-webkit-box",
            WebkitLineClamp: 3,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
          }}
        >
          {transfer.preview}
        </p>
        <div style={{ marginTop: 8 }}>
          <PropertyPill label="SAMPLED" value={`${transfer.tokenCount}`} variant="green" />
        </div>
      </div>
    </div>
  );
}
