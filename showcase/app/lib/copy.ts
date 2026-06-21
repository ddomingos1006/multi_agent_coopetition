export const APP_SUBTITLE = "Run a hearing under a token budget.";
export const SESSION_WAITING = "Loading hearing…";
export const BUDGET_WARNING = "Budget's almost gone. Cross-examine once more, or call the verdict.";
export const SCORE_FOOTNOTE =
  "Decision accuracy only counts if the important facts made it onto the record.";
export const TOOL_LABELS: Record<string, string> = {
  list_specialists: "Check who's available",
  grant_floor: "Give the floor",
  cross_examine: "Cross-examine",
  view_record: "Read the record",
  submit_verdict: "Submit verdict",
};
export const SCORE_LABELS: Record<string, string> = {
  evidence_recall: "Facts on record",
  evidence_precision: "Signal vs noise",
  gated_decision_accuracy: "Right call",
  gated_root_cause_accuracy: "Right cause",
  citation_quality: "Citations hold up",
  non_redundancy: "Didn't repeat itself",
  budget_discipline: "Stayed in budget",
  unsupported_claim_penalty: "Unsupported claims",
};
