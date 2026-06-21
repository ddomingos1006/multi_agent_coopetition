"use client";

import { useEffect, useState } from "react";
import { CompareTab } from "@/components/CompareTab";
import { TrainingTab } from "@/components/TrainingTab";
import { DocketBriefing } from "@/components/posthog/DocketBriefing";
import { EvidenceSourcePanel } from "@/components/posthog/EvidenceSourcePanel";
import { LiveRecordTable } from "@/components/posthog/LiveRecordTable";
import { ParliamentShell } from "@/components/posthog/ParliamentShell";
import { TokenAnalyticsPanel } from "@/components/posthog/TokenAnalyticsPanel";
import { TransferOverlay } from "@/components/posthog/TransferOverlay";
import { useSessionStream } from "@/hooks/useSessionStream";
import { loadReplayIndex } from "@/lib/replay";
import type { PolicyId, ReplayIndex } from "@/lib/types";

type Tab = "hearing" | "compare" | "training";

export default function Page() {
  const [catalog, setCatalog] = useState<ReplayIndex | null>(null);
  const [world, setWorld] = useState("incident-response-medium-004");
  const [policy, setPolicy] = useState<PolicyId>("targeted_oracle");
  const [tab, setTab] = useState<Tab>("hearing");
  const [deskOpen, setDeskOpen] = useState(false);

  useEffect(() => {
    loadReplayIndex().then(setCatalog);
  }, []);

  const session = useSessionStream(world, policy);

  useEffect(() => {
    setDeskOpen(false);
  }, [world, policy]);

  const runAs = (next: PolicyId) => {
    setPolicy(next);
    setTab("hearing");
    setDeskOpen(false);
  };

  const conveneHearing = () => {
    session.dismiss();
    setDeskOpen(true);
  };

  const startSession = () => {
    session.start();
  };

  const newDocket = () => {
    setDeskOpen(false);
    session.dismiss();
  };

  const preset = catalog?.presets.find((p) => p.world_id === world);
  const inDesk = tab === "hearing" && deskOpen;
  const showBriefing = tab === "hearing" && !deskOpen;

  const windowTitle = inDesk
    ? `Live Record — ${preset?.label ?? "Hearing"}`
    : "New docket";

  const windowSubtitle = inDesk
    ? `${session.policyLabel} · ${preset?.world_id ?? world}`
    : "Context Window Parliament";

  return (
    <ParliamentShell
      tab={tab}
      onTabChange={setTab}
      windowTitle={windowTitle}
      windowSubtitle={windowSubtitle}
      windowBadge={
        inDesk ? (
          <div className="ac-window-badges">
            {session.phase === "complete" && (
              <span className="ph-tag ph-tag-green">Adjourned</span>
            )}
            {session.phase === "running" && (
              <span className="ph-tag ph-tag-orange">Speaker active</span>
            )}
            {session.phase === "ready" && deskOpen && (
              <span className="ph-tag ph-tag-blue">Awaiting start</span>
            )}
          </div>
        ) : undefined
      }
      toolbar={
        inDesk ? (
          <div className="ac-toolbar-inner">
            {session.bundle?.world.narrative && (
              <p className="ac-toolbar-problem">{session.bundle.world.narrative}</p>
            )}
            <div className="ac-toolbar-actions">
              {session.phase === "ready" && (
                <button
                  type="button"
                  className="ph-btn-primary ph-btn-primary-accent"
                  onClick={startSession}
                >
                  Start session ▶
                </button>
              )}
              <button type="button" className="ph-btn-ghost" onClick={newDocket}>
                New docket
              </button>
            </div>
          </div>
        ) : undefined
      }
    >
      {showBriefing && catalog && (
        <DocketBriefing
          catalog={catalog}
          world={world}
          policy={policy}
          narrative={session.bundle?.world.narrative}
          tokenBudget={session.bundle?.world.token_budget}
          maxInteractions={session.bundle?.world.max_interactions}
          onWorldChange={setWorld}
          onPolicyChange={setPolicy}
          onConvene={conveneHearing}
          loading={session.phase === "loading"}
        />
      )}

      {inDesk && session.bundle && (
        <div className="ac-desk">
          <TransferOverlay transfer={session.transfer} />
          <EvidenceSourcePanel
            bundle={session.bundle}
            specialists={session.specialists}
            visibleIds={session.visibleSpecialistIds}
            activeId={session.activeSpecialistId}
            sampledMap={session.sampledMap}
            phase={session.phase}
          />
          <LiveRecordTable
            events={session.liveEvents}
            expandedId={session.expandedId}
            onToggle={(id) =>
              session.setExpandedId(session.expandedId === id ? null : id)
            }
            phase={session.phase}
            waiting={session.phase === "ready"}
          />
          <TokenAnalyticsPanel
            bundle={session.bundle}
            budgetUsed={session.budgetUsed}
            budgetTotal={session.bundle.world.token_budget}
            budgetRemaining={session.budgetRemaining}
            naiveStack={session.naiveTokenStack}
            interactionsUsed={session.interactionsUsed}
            maxInteractions={session.bundle.world.max_interactions}
            phase={session.phase}
          />
        </div>
      )}

      {tab === "compare" && (
        <div className="ac-tab-pad">
          <CompareTab replayAs={runAs} />
        </div>
      )}

      {tab === "training" && (
        <div className="ac-tab-pad">
          <TrainingTab />
        </div>
      )}
    </ParliamentShell>
  );
}
