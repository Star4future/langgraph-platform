/**
 * Live view of the Triage → Resolver → Supervisor → (Human) graph for the
 * current run. Driven by the same reducer facts as the chat timeline — no
 * timers, no choreographed animations; a node only changes state because an
 * event arrived. Presentational; rendered inside the Console boundary.
 */
import type { NodeStatus, PipelineView, RunState } from "@/lib/stream-reducer";

// Routing rules mirrored from core/graph_builder.py's
// route_after_supervisor, in its evaluation order: the human checks run
// before the quality gate, and exhausted retries also escalate.
// Defaults: quality_threshold 0.7, max_retries 2, confidence_floor 0.5.
const EDGE_RULES = [
  "flagged / conf < 0.5 → human",
  "score ≥ 0.7 → reply",
  "score < 0.7 → retry (≤2), then human",
];

const STATUS_STYLE: Record<NodeStatus, { dot: string; text: string; label: string }> = {
  idle: { dot: "bg-line", text: "text-ink-dim", label: "idle" },
  running: { dot: "bg-accent node-running", text: "text-ink", label: "running…" },
  done: { dot: "bg-ok", text: "text-ink", label: "done" },
  retrying: { dot: "bg-warn node-running", text: "text-warn", label: "retrying" },
  escalated: { dot: "bg-warn", text: "text-warn", label: "escalated" },
  skipped: { dot: "bg-line", text: "text-ink-dim", label: "not needed" },
};

function Node({
  name,
  status,
  detail,
  last,
}: {
  name: string;
  status: NodeStatus;
  detail?: string | null;
  last?: boolean;
}) {
  const s = STATUS_STYLE[status];
  return (
    <li className="relative pl-6">
      {!last && (
        <span className="absolute left-[5px] top-5 h-[calc(100%-8px)] w-px bg-line" aria-hidden />
      )}
      <span
        className={`absolute left-0 top-1.5 inline-block h-[11px] w-[11px] rounded-full ${s.dot}`}
        aria-hidden
      />
      <div className="flex items-baseline gap-2">
        <span className={`text-sm font-medium ${s.text}`}>{name}</span>
        <span className="font-mono text-[10px] text-ink-dim">{s.label}</span>
      </div>
      {detail && <p className="mt-0.5 text-xs leading-5 text-ink-dim">{detail}</p>}
      <div className="pb-4" />
    </li>
  );
}

export function PipelinePanel({ view, run }: { view: PipelineView | null; run: RunState | null }) {
  // Derived aggregates come from the projection; `run` is only read for
  // presentational detail (intent text, draft score, reason strings).
  const toolCount = view?.toolCount ?? 0;

  return (
    <aside className="h-fit rounded-xl border border-line bg-surface lg:sticky lg:top-16">
      <div className="border-b border-line px-4 py-3">
        <h2 className="text-sm font-medium">Run pipeline</h2>
        <p className="mt-0.5 text-xs text-ink-dim">
          Derived from the event stream — the protocol carries completion events, so “running” is an
          inference, never an animation.
        </p>
      </div>

      <ul className="px-4 pt-4">
        <Node
          name="Triage"
          status={view?.triage ?? "idle"}
          detail={
            run?.triage
              ? `${run.triage.intent} · ${run.triage.urgency} · conf ${run.triage.confidence.toFixed(2)}`
              : "intent + urgency classification"
          }
        />
        <Node
          name="Resolver"
          status={view?.resolver ?? "idle"}
          detail={
            toolCount > 0
              ? `${toolCount} tool call${toolCount === 1 ? "" : "s"}${
                  view && view.retries > 0 ? ` · ${view.retries + 1} passes` : ""
                }`
              : "tool calls + draft"
          }
        />
        <Node
          name="Supervisor"
          status={view?.supervisor ?? "idle"}
          detail={
            run?.escalation
              ? `draft scored ${run.escalation.draftQuality.toFixed(2)}`
              : "quality score gate"
          }
        />
        <Node
          name="Human"
          status={view?.human ?? "idle"}
          detail={
            run?.escalation
              ? `paused on checkpoint (${run.escalation.reason})`
              : "HITL — only on escalation"
          }
          last
        />
      </ul>

      <div className="border-t border-line px-4 py-3">
        <p className="mb-1.5 font-mono text-[10px] uppercase tracking-wider text-ink-dim">
          supervisor routing
        </p>
        <ul className="space-y-1">
          {EDGE_RULES.map((r) => (
            <li key={r} className="font-mono text-[11px] text-ink-dim">
              {r}
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
}
