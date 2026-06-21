const FORMULA = [
  "R =",
  "  0.24 × gated_decision_accuracy",
  "+ 0.12 × gated_root_cause_accuracy",
  "+ 0.30 × evidence_recall",
  "+ 0.14 × evidence_precision",
  "+ 0.08 × non_redundancy",
  "+ 0.07 × citation_quality",
  "+ 0.05 × budget_discipline",
  "− 0.10 × unsupported_claim_penalty",
].join("\n");

export function TrainingTab() {
  return (
    <div style={{ display: "grid", gap: 12, maxWidth: 720, gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))" }}>
      <div className="ph-panel" style={{ padding: 16 }}>
        <div className="mono" style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--muted-3000)" }}>
          Model
        </div>
        <div className="mono" style={{ marginTop: 8, fontSize: 14, fontWeight: 500 }}>
          parliament-qwen36-35b
        </div>
        <p style={{ marginTop: 8, fontSize: 12, color: "var(--muted-3000)" }}>Base: Qwen/Qwen3.6-35B-A3B</p>
        <p style={{ marginTop: 4, fontSize: 12, color: "var(--muted-3000)" }}>
          Checkpoint mean reward: <span style={{ color: "var(--primary-3000)" }}>0.758</span>
        </p>
      </div>
      <div className="ph-panel" style={{ padding: 16 }}>
        <div className="mono" style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--muted-3000)" }}>
          Post-training loop
        </div>
        <ol style={{ marginTop: 8, paddingLeft: 18, fontSize: 12, color: "var(--color-text-secondary-3000)", lineHeight: 1.7 }}>
          <li>Roll out on HUD</li>
          <li>Grade deterministically</li>
          <li>GRPO step via train_step.py</li>
          <li>Eval again</li>
        </ol>
      </div>
      <div className="ph-panel" style={{ padding: 16, gridColumn: "1 / -1" }}>
        <div className="mono" style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--muted-3000)" }}>
          Reward formula
        </div>
        <pre
          className="mono"
          style={{
            marginTop: 8,
            overflowX: "auto",
            fontSize: 11,
            lineHeight: 1.7,
            color: "var(--color-text-secondary-3000)",
          }}
        >
          {FORMULA}
        </pre>
        <p style={{ marginTop: 12, fontSize: 11, color: "var(--muted-3000)" }}>
          500 worlds · 10 domains · MCP tools for bids, floor time, cross-examination, record review, and verdict submission.
        </p>
      </div>
    </div>
  );
}
