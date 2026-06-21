"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { loadReplay } from "@/lib/replay";
import type { PolicyId, ReplayBundle, SpecialistCard, TimelineEvent } from "@/lib/types";

export type SessionPhase = "loading" | "ready" | "running" | "complete";

export interface LiveEventRow {
  id: string;
  eventIndex: number;
  tool: string;
  source: string;
  tokenDelta: number;
  budgetRemaining: number;
  decisionLog: string;
  args?: Record<string, unknown>;
  testimony?: NonNullable<TimelineEvent["testimony_added"]>;
  verdict?: NonNullable<TimelineEvent["verdict"]>;
  question?: string;
  flash?: boolean;
}

export interface TransferState {
  specialistId: string;
  specialistName: string;
  testimonyId: string;
  tokenCount: number;
  phase: "lift" | "fly" | "land";
  preview: string;
}

export interface SampledInfo {
  tokens: number;
  count: number;
}

function jitter(min = 40, max = 120) {
  return min + Math.random() * (max - min);
}

function sleep(ms: number, signal: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    const timer = setTimeout(resolve, ms);
    signal.addEventListener(
      "abort",
      () => {
        clearTimeout(timer);
        reject(new DOMException("Aborted", "AbortError"));
      },
      { once: true },
    );
  });
}

function toolLabel(tool: string) {
  const labels: Record<string, string> = {
    list_specialists: "list_specialists",
    grant_floor: "grant_floor",
    cross_examine: "cross_examine",
    view_record: "view_record",
    submit_verdict: "submit_verdict",
  };
  return labels[tool] ?? tool;
}

function decisionLogFor(event: TimelineEvent): string {
  if (event.verdict) return `verdict → ${event.verdict.decision}`;
  if (event.testimony_added) {
    return event.testimony_added.mode === "cross_exam" ? "targeted pull" : "floor testimony";
  }
  if (event.tool === "list_specialists") return "roster scan";
  if (event.tool === "view_record") return "record review";
  return event.message ?? "ok";
}

function emptySessionState(budgetTotal: number) {
  return {
    liveEvents: [] as LiveEventRow[],
    transfer: null as TransferState | null,
    budgetUsed: 0,
    budgetRemaining: budgetTotal,
    interactionsUsed: 0,
    activeSpecialistId: null as string | null,
    visibleSpecialistIds: [] as string[],
    sampledMap: {} as Record<string, SampledInfo>,
    expandedId: null as string | null,
  };
}

export function useSessionStream(worldId: string, policy: PolicyId) {
  const [bundle, setBundle] = useState<ReplayBundle | null>(null);
  const [runToken, setRunToken] = useState(0);
  const [phase, setPhase] = useState<SessionPhase>("loading");
  const [liveEvents, setLiveEvents] = useState<LiveEventRow[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [transfer, setTransfer] = useState<TransferState | null>(null);
  const [budgetUsed, setBudgetUsed] = useState(0);
  const [budgetRemaining, setBudgetRemaining] = useState(0);
  const [interactionsUsed, setInteractionsUsed] = useState(0);
  const [activeSpecialistId, setActiveSpecialistId] = useState<string | null>(null);
  const [visibleSpecialistIds, setVisibleSpecialistIds] = useState<string[]>([]);
  const [sampledMap, setSampledMap] = useState<Record<string, SampledInfo>>({});

  const resetToReady = useCallback((loaded: ReplayBundle) => {
    const blank = emptySessionState(loaded.world.token_budget);
    setLiveEvents(blank.liveEvents);
    setTransfer(blank.transfer);
    setBudgetUsed(blank.budgetUsed);
    setBudgetRemaining(blank.budgetRemaining);
    setInteractionsUsed(blank.interactionsUsed);
    setActiveSpecialistId(blank.activeSpecialistId);
    setVisibleSpecialistIds(blank.visibleSpecialistIds);
    setSampledMap(blank.sampledMap);
    setExpandedId(blank.expandedId);
    setPhase("ready");
  }, []);

  useEffect(() => {
    setPhase("loading");
    setRunToken(0);
    loadReplay(worldId, policy).then((loaded) => {
      setBundle(loaded);
      resetToReady(loaded);
    });
  }, [worldId, policy, resetToReady]);

  const start = useCallback(() => {
    if (!bundle || phase === "running" || phase === "loading") return;
    const blank = emptySessionState(bundle.world.token_budget);
    setLiveEvents(blank.liveEvents);
    setTransfer(blank.transfer);
    setBudgetUsed(blank.budgetUsed);
    setBudgetRemaining(blank.budgetRemaining);
    setInteractionsUsed(blank.interactionsUsed);
    setActiveSpecialistId(blank.activeSpecialistId);
    setVisibleSpecialistIds(blank.visibleSpecialistIds);
    setSampledMap(blank.sampledMap);
    setExpandedId(blank.expandedId);
    setRunToken((t) => t + 1);
  }, [bundle, phase]);

  const dismiss = useCallback(() => {
    if (!bundle) return;
    resetToReady(bundle);
  }, [bundle, resetToReady]);

  useEffect(() => {
    if (!bundle || runToken === 0) return;

    const controller = new AbortController();
    const { signal } = controller;

    const applyBudget = (event: TimelineEvent) => {
      if (event.budget_used !== undefined) setBudgetUsed(event.budget_used);
      if (event.budget_remaining !== undefined) setBudgetRemaining(event.budget_remaining);
      if (event.interactions_used !== undefined) setInteractionsUsed(event.interactions_used);
    };

    const pushEvent = (row: LiveEventRow) => {
      setLiveEvents((prev) => [...prev, row]);
      setTimeout(() => {
        setLiveEvents((prev) =>
          prev.map((r) => (r.id === row.id ? { ...r, flash: false } : r)),
        );
      }, 900);
    };

    const runTransfer = async (
      testimony: NonNullable<TimelineEvent["testimony_added"]>,
    ) => {
      setActiveSpecialistId(testimony.specialist_id);
      setTransfer({
        specialistId: testimony.specialist_id,
        specialistName: testimony.specialist_name,
        testimonyId: testimony.id,
        tokenCount: testimony.token_count,
        phase: "lift",
        preview: testimony.visible_text.slice(0, 120),
      });
      await sleep(280 + jitter(40, 100), signal);
      setTransfer((t) => (t ? { ...t, phase: "fly" } : null));
      await sleep(520 + jitter(60, 140), signal);
      setTransfer((t) => (t ? { ...t, phase: "land" } : null));
      await sleep(180, signal);
      setTransfer(null);
      setSampledMap((prev) => {
        const cur = prev[testimony.specialist_id] ?? { tokens: 0, count: 0 };
        return {
          ...prev,
          [testimony.specialist_id]: {
            tokens: cur.tokens + testimony.token_count,
            count: cur.count + 1,
          },
        };
      });
      setActiveSpecialistId(null);
    };

    const run = async () => {
      setPhase("running");

      const roster = bundle.timeline[0]?.payload?.specialists ?? [];

      for (const event of bundle.timeline) {
        if (signal.aborted) return;

        if (event.type === "session_start") {
          for (let i = 0; i < roster.length; i++) {
            await sleep(40 + i * 48, signal);
            setVisibleSpecialistIds((ids) => [...ids, roster[i].id]);
          }
          await sleep(240 + jitter(), signal);
          continue;
        }

        const tool = event.tool ?? "unknown";
        const testimony = event.testimony_added;
        const verdict = event.verdict;
        const rowId = `evt-${event.index}`;

        if (testimony && (tool === "grant_floor" || tool === "cross_examine")) {
          const question =
            tool === "cross_examine" && typeof event.args?.question === "string"
              ? event.args.question
              : undefined;

          await runTransfer(testimony);

          pushEvent({
            id: rowId,
            eventIndex: event.index,
            tool: toolLabel(tool),
            source: testimony.specialist_name,
            tokenDelta: testimony.token_count,
            budgetRemaining: event.budget_remaining ?? budgetRemaining,
            decisionLog: decisionLogFor(event),
            args: event.args,
            testimony,
            question,
            flash: true,
          });
          applyBudget(event);
          await sleep(220 + jitter(), signal);
          continue;
        }

        if (tool === "submit_verdict" && verdict) {
          pushEvent({
            id: rowId,
            eventIndex: event.index,
            tool: toolLabel(tool),
            source: "speaker",
            tokenDelta: 0,
            budgetRemaining: event.budget_remaining ?? budgetRemaining,
            decisionLog: decisionLogFor(event),
            args: event.args,
            verdict,
            flash: true,
          });
          applyBudget(event);
          await sleep(400 + jitter(), signal);
          continue;
        }

        pushEvent({
          id: rowId,
          eventIndex: event.index,
          tool: toolLabel(tool),
          source: "—",
          tokenDelta: 0,
          budgetRemaining: event.budget_remaining ?? budgetRemaining,
          decisionLog: decisionLogFor(event),
          args: event.args,
          flash: true,
        });
        applyBudget(event);
        await sleep(160 + jitter(30, 90), signal);
      }

      setPhase("complete");
    };

    run().catch((err) => {
      if (err?.name !== "AbortError") console.error(err);
    });

    return () => controller.abort();
  }, [bundle, runToken, budgetRemaining]);

  const rosterPreview = bundle?.timeline[0]?.payload?.specialists ?? [];

  const specialists = useMemo(() => {
    const base = rosterPreview.map((s) => ({ ...s }));
    for (const [id, info] of Object.entries(sampledMap)) {
      const row = base.find((s) => s.id === id);
      if (row) {
        row.has_spoken = true;
        row.times_heard = info.count;
        row.total_tokens_used = info.tokens;
      }
    }
    return base as SpecialistCard[];
  }, [rosterPreview, sampledMap]);

  const naiveTokenStack = useMemo(
    () => specialists.reduce((sum, s) => sum + s.requested_tokens, 0),
    [specialists],
  );

  const canStart = phase === "ready" || phase === "complete";
  const locked = phase === "running";

  return {
    bundle,
    phase,
    liveEvents,
    expandedId,
    setExpandedId,
    transfer,
    budgetUsed,
    budgetRemaining,
    interactionsUsed,
    activeSpecialistId,
    visibleSpecialistIds,
    specialists,
    rosterPreview,
    sampledMap,
    naiveTokenStack,
    start,
    dismiss,
    canStart,
    locked,
    policyLabel: bundle?.meta.policy_label ?? policy,
  };
}
