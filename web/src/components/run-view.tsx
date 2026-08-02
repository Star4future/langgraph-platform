/**
 * One agent run rendered as its event timeline: triage classification,
 * resolver tool rounds, the streamed answer, escalation, completion meta.
 * Purely presentational — imported by the Console client boundary, so it
 * needs no 'use client' of its own.
 */
import type { ResolverRound, RunState } from "@/lib/stream-reducer";

function Pre({ value }: { value: unknown }) {
  return (
    <pre className="mt-1 overflow-x-auto rounded-md bg-bg/60 px-2.5 py-2 font-mono text-[11px] leading-5 text-ink-dim">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

function urgencyTone(urgency: string): string {
  if (urgency === "high") return "border-err/50 text-err";
  if (urgency === "medium") return "border-warn/50 text-warn";
  return "border-ok/50 text-ok";
}

function EventShell({
  tag,
  tone,
  children,
}: {
  tag: string;
  tone: string;
  children: React.ReactNode;
}) {
  return (
    <div className={`rounded-lg border px-3.5 py-2.5 text-sm ${tone}`}>
      <span className="float-right ml-3 font-mono text-[10px] uppercase tracking-wider text-ink-dim">
        {tag}
      </span>
      {children}
    </div>
  );
}

function ToolRound({ round, index, total }: { round: ResolverRound; index: number; total: number }) {
  return (
    <EventShell
      tag={total > 1 ? `resolver · pass ${index + 1}` : "resolver"}
      tone="border-line bg-surface-2"
    >
      <div className="space-y-1.5">
        {index > 0 && (
          <p className="text-xs text-warn">
            Supervisor scored the previous draft below threshold — retry pass.
          </p>
        )}
        {round.tools.map((t, i) => (
          <details key={i} className="group">
            <summary className="cursor-pointer list-none font-mono text-xs text-ink">
              <span className="mr-1.5 inline-block w-3 text-center text-ink-dim group-open:rotate-90 group-open:transition-transform">
                ▸
              </span>
              🛠 {t.tool}
              <span className="ml-2 text-[10px] text-ink-dim">
                {t.settled ? "→ result received" : "…"}
              </span>
            </summary>
            <div className="ml-4">
              {t.args !== null && Object.keys(t.args).length > 0 && (
                <>
                  <span className="mt-1 block text-[10px] uppercase tracking-wider text-ink-dim">
                    arguments
                  </span>
                  <Pre value={t.args} />
                </>
              )}
              {t.settled && (
                <>
                  <span className="mt-1 block text-[10px] uppercase tracking-wider text-ink-dim">
                    result
                  </span>
                  <Pre value={t.result ?? null} />
                </>
              )}
            </div>
          </details>
        ))}
      </div>
    </EventShell>
  );
}

export function RunView({ run, onRetry }: { run: RunState; onRetry: () => void }) {
  const failed = run.phase === "error" || run.phase === "aborted";

  return (
    <div className="space-y-2">
      {/* Connection meta */}
      {run.threadId ? (
        <p className="font-mono text-[10px] text-ink-dim">
          stream open · thread {run.threadId}
        </p>
      ) : run.phase === "connecting" ? (
        <div className="space-y-2" aria-label="connecting">
          <div className="h-9 w-2/3 animate-pulse rounded-lg bg-surface-2" />
          <div className="h-9 w-1/2 animate-pulse rounded-lg bg-surface-2" />
        </div>
      ) : null}

      {/* Triage classification */}
      {run.triage && (
        <EventShell tag="triage" tone="border-line bg-surface-2">
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="font-mono text-ink">{run.triage.intent}</span>
            <span
              className={`rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-wide ${urgencyTone(run.triage.urgency)}`}
            >
              {run.triage.urgency}
            </span>
            <span className="flex items-center gap-1.5 text-ink-dim">
              confidence
              <span className="inline-block h-1.5 w-20 overflow-hidden rounded-full bg-bg/70">
                <span
                  className="block h-full rounded-full bg-accent"
                  style={{ width: `${Math.round(run.triage.confidence * 100)}%` }}
                />
              </span>
              <span className="font-mono">{run.triage.confidence.toFixed(2)}</span>
            </span>
          </div>
        </EventShell>
      )}

      {/* Resolver tool rounds */}
      {run.rounds.map((round, i) => (
        <ToolRound key={i} round={round} index={i} total={run.rounds.length} />
      ))}

      {/* Streamed answer */}
      {(run.answer || run.sawToken) && (
        <div className="rounded-lg border-l-2 border-ok bg-surface-2 px-3.5 py-2.5 text-sm leading-6">
          <span className="mb-1 block font-mono text-[10px] uppercase tracking-wider text-ink-dim">
            assistant
          </span>
          <span
            className={`whitespace-pre-wrap ${run.phase === "streaming" ? "stream-caret" : ""}`}
          >
            {run.answer}
          </span>
        </div>
      )}

      {/* Human escalation */}
      {run.escalation && (
        <EventShell tag="human_escalation" tone="border-warn/40 bg-warn/10">
          <p className="text-xs leading-5">
            Routed to a person ({run.escalation.reason}). The reviewer picks up
            a draft scored{" "}
            <span className="font-mono text-warn">
              {run.escalation.draftQuality.toFixed(2)}
            </span>{" "}
            — the graph is paused on its checkpoint until an operator resumes
            it.
          </p>
        </EventShell>
      )}

      {/* Failure states */}
      {run.phase === "error" && (
        <EventShell tag="error" tone="border-err/40 bg-err/10">
          <p className="text-xs leading-5 text-err">
            {run.errorMessage ?? "The run failed."}
          </p>
        </EventShell>
      )}
      {run.phase === "aborted" && (
        <EventShell tag="cancelled" tone="border-line bg-surface-2">
          <p className="text-xs leading-5 text-ink-dim">
            Run cancelled before the stream finished.
          </p>
        </EventShell>
      )}
      {failed && (
        <button
          type="button"
          onClick={onRetry}
          className="rounded-lg border border-accent/60 bg-accent/10 px-3.5 py-2 text-xs font-medium text-accent-soft transition-colors hover:bg-accent/20"
        >
          ↻ Retry — same session, context kept
        </button>
      )}

      {/* Completion meta */}
      {run.completion && (
        <p className="font-mono text-[10px] text-ink-dim">
          done · {run.completion.latency_ms} ms · {run.completion.tokens} tokens
          · mode:{" "}
          <span className={run.completion.mode === "mock" ? "text-warn" : "text-ok"}>
            {run.completion.mode}
          </span>
        </p>
      )}
    </div>
  );
}
