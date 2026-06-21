"use client";

import type { PolicyId, ReplayIndex } from "@/lib/types";

const LM = [
  { bg: "var(--lm-1-bg)", text: "var(--lm-1-text)" },
  { bg: "var(--lm-2-bg)", text: "var(--lm-2-text)" },
  { bg: "var(--lm-4-bg)", text: "var(--lm-4-text)" },
  { bg: "var(--lm-7-bg)", text: "var(--lm-7-text)" },
  { bg: "var(--lm-11-bg)", text: "var(--lm-11-text)" },
];

export function DocketBriefing({
  catalog,
  world,
  policy,
  narrative,
  tokenBudget,
  maxInteractions,
  onWorldChange,
  onPolicyChange,
  onConvene,
  loading,
}: {
  catalog: ReplayIndex;
  world: string;
  policy: PolicyId;
  narrative?: string;
  tokenBudget?: number;
  maxInteractions?: number;
  onWorldChange: (id: string) => void;
  onPolicyChange: (id: PolicyId) => void;
  onConvene: () => void;
  loading: boolean;
}) {
  const preset = catalog.presets.find((p) => p.world_id === world);
  const policyMeta = catalog.policies.find((p) => p.id === policy);

  return (
    <div className="ac-briefing">
      <div className="ac-briefing-hero">
        <p className="mono ac-briefing-kicker">Establish the problem</p>
        <h2 className="ac-briefing-headline">
          What happened — and who gets to speak?
        </h2>
        <p className="ac-briefing-lede">
          Pick a docket, assign a Speaker, then convene. Nothing runs until you say so.
        </p>
      </div>

      <section className="ac-briefing-section">
        <h3 className="ac-briefing-label">Docket</h3>
        <div className="ac-docket-grid">
          {catalog.presets.map((p, i) => {
            const lm = LM[i % LM.length];
            const selected = world === p.world_id;
            return (
              <button
                key={p.world_id}
                type="button"
                onClick={() => onWorldChange(p.world_id)}
                className={`ac-docket-card${selected ? " ac-docket-card-on" : ""}`}
              >
                <span className="ph-lettermark ac-docket-mark" style={{ background: lm.bg, color: lm.text }}>
                  {p.label.charAt(0)}
                </span>
                <div className="ac-docket-meta">
                  <span className="ac-docket-name">{p.label}</span>
                  <span className="mono ac-docket-id">
                    {p.difficulty} · {p.domain.replaceAll("_", "-")}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </section>

      <section className="ac-briefing-section">
        <h3 className="ac-briefing-label">Speaker policy</h3>
        <div className="ac-speaker-row">
          {catalog.policies.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => onPolicyChange(item.id)}
              className={`ac-speaker-pill${policy === item.id ? " ac-speaker-pill-on" : ""}`}
            >
              <span className="ac-speaker-dot" />
              {item.label}
            </button>
          ))}
        </div>
        {policyMeta && <p className="ac-speaker-hint">{policyMeta.subtitle}</p>}
      </section>

      {preset && (
        <section className="ac-problem-card">
          <div className="ac-problem-tags">
            <span className="ph-tag ph-tag-blue">{preset.world_id}</span>
            {tokenBudget != null && (
              <span className="ph-tag ph-tag-orange">{tokenBudget} tokens</span>
            )}
            {maxInteractions != null && (
              <span className="ph-tag">{maxInteractions} interactions max</span>
            )}
          </div>
          <p className="mono ac-problem-label">The problem</p>
          <blockquote className="ac-problem-quote">
            {loading ? "Loading docket…" : narrative ?? "Select a docket to load the scenario."}
          </blockquote>
        </section>
      )}

      <div className="ac-briefing-actions">
        <button
          type="button"
          className="ph-btn-primary ph-btn-primary-accent ac-convene-btn"
          disabled={loading || !narrative}
          onClick={onConvene}
        >
          Convene hearing →
        </button>
        <p className="ac-briefing-footnote mono">
          Opens the live desk. You start the session from there.
        </p>
      </div>
    </div>
  );
}
