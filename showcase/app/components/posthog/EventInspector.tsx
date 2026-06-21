import type { LiveEventRow } from "@/hooks/useSessionStream";

export function EventInspector({ row }: { row: LiveEventRow }) {
  return (
    <div
      style={{
        borderTop: "1px solid var(--border-3000)",
        background: "var(--color-accent-3000)",
        padding: "12px 16px",
      }}
    >
      <div
        className="mono"
        style={{
          marginBottom: 8,
          fontSize: 10,
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          color: "var(--muted-3000)",
        }}
      >
        Properties
      </div>
      <pre
        className="mono"
        style={{
          margin: 0,
          overflowX: "auto",
          fontSize: 11,
          lineHeight: 1.55,
          color: "var(--color-text-secondary-3000)",
        }}
      >
        {JSON.stringify(
          {
            tool: row.tool,
            args: row.args ?? {},
            testimony_id: row.testimony?.id,
            token_count: row.testimony?.token_count,
            visible_text: row.testimony?.visible_text,
            question: row.question,
            verdict: row.verdict,
          },
          null,
          2,
        )}
      </pre>
    </div>
  );
}
