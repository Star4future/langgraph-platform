"use client";

/**
 * The console's single interactive boundary.
 *
 * Owns the reducer, the session id and the AbortController; everything it
 * renders (run timeline, pipeline panel) is presentational and ships in
 * this client bundle without needing its own 'use client' directive.
 */
import { useEffect, useReducer, useRef, useState } from "react";
import {
  activeTurn,
  consoleReducer,
  derivePipeline,
  initialConsoleState,
  lastTurn,
} from "@/lib/stream-reducer";
import { streamAgentChat } from "@/lib/transport";
import { PipelinePanel } from "@/components/pipeline-panel";
import { RunView } from "@/components/run-view";

/** Example prompts tuned to the education vertical's mock responses. */
const EXAMPLES = [
  { icon: "💰", label: "Pricing", q: "How much is the AMC monthly plan?" },
  {
    icon: "🔄",
    label: "Plan change + refund",
    q: "I want to switch from M3 to M4 and refund the difference",
  },
  {
    icon: "👨‍👩‍👧",
    label: "Family discount",
    q: "Do you offer a discount for two children?",
  },
  {
    icon: "🆘",
    label: "Escalation",
    q: "My child is struggling, can I speak to a teacher?",
  },
  {
    icon: "↩️",
    label: "Refund",
    q: "I want to cancel and get my money back, I've only had it 3 days",
  },
];

function newSessionId(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? `web-${crypto.randomUUID()}`
    : `web-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

export function Console() {
  const [state, dispatch] = useReducer(consoleReducer, initialConsoleState);
  const [draft, setDraft] = useState("");
  const sessionRef = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const logRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const wasBusyRef = useRef(false);

  const busy = activeTurn(state) !== null;
  const last = lastTurn(state);

  // Keep the newest event in view while a run streams — but only when the
  // reader is already at the bottom. Someone scrolled up inspecting an
  // earlier tool result must not be yanked down by every token.
  useEffect(() => {
    const el = logRef.current;
    if (!el) return;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    if (nearBottom) el.scrollTop = el.scrollHeight;
  }, [state]);

  // Cancel the in-flight stream if the console unmounts mid-run (client
  // navigation away) — otherwise the reader pumps a dead component.
  useEffect(() => () => abortRef.current?.abort(), []);

  // Sending disables the input, which drops focus to <body>; hand it back
  // when the run settles.
  useEffect(() => {
    if (wasBusyRef.current && !busy) inputRef.current?.focus();
    wasBusyRef.current = busy;
  }, [busy]);

  async function pump(message: string) {
    // The session id survives retries and follow-ups on purpose: the
    // engine keys its checkpointed thread on it. How much actually
    // carries across runs depends on the deployment's checkpointer —
    // the default MemorySaver is per-process, so on serverless the
    // guarantee is "same thread key", not durable memory. The UI copy
    // promises only the former.
    sessionRef.current ??= newSessionId();
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      await streamAgentChat(
        { message, session_id: sessionRef.current, customer_id: "web_visitor" },
        {
          onEvent: (event) =>
            dispatch({ type: "event", event, atMs: performance.now() }),
        },
        controller.signal,
      );
      dispatch({ type: "stream_closed" });
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        dispatch({ type: "aborted" });
      } else {
        dispatch({
          type: "stream_failed",
          message: err instanceof Error ? err.message : String(err),
        });
      }
    } finally {
      abortRef.current = null;
    }
  }

  function send(message: string) {
    const trimmed = message.trim();
    // abortRef doubles as the in-flight gate: the reducer would drop a
    // second turn anyway, but without this check the second pump() would
    // still run and orphan the first AbortController.
    if (busy || abortRef.current || !trimmed) return;
    dispatch({ type: "send", message: trimmed });
    setDraft("");
    void pump(trimmed);
  }

  function stop() {
    abortRef.current?.abort();
  }

  function retry() {
    const turn = lastTurn(state);
    if (!turn || (turn.run.phase !== "error" && turn.run.phase !== "aborted")) return;
    if (abortRef.current) return;
    dispatch({ type: "retry" });
    void pump(turn.user);
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
      {/* ── Chat column ─────────────────────────────────────────── */}
      <section className="flex min-h-[520px] flex-col rounded-xl border border-line bg-surface">
        <div className="flex items-center gap-2 border-b border-line px-4 py-3">
          <span className="h-2 w-2 rounded-full bg-ok" />
          <h2 className="text-sm font-medium">
            Education vertical — parent support
          </h2>
          <span className="ml-auto font-mono text-[11px] text-ink-dim">
            POST /api/chat · text/event-stream
          </span>
        </div>

        <div ref={logRef} className="log-scroll flex-1 space-y-4 overflow-y-auto px-4 py-4">
          {state.turns.length === 0 && (
            <div className="rounded-lg border border-line bg-surface-2 px-4 py-3 text-sm leading-6 text-ink-dim">
              Hi — this console drives the engine&apos;s education vertical.
              Ask about subscriptions, plans, refunds or family discounts, or
              start from an example below. Every event you&apos;ll see arrives
              over a real server-sent stream.
            </div>
          )}

          {state.turns.map((turn) => (
            <div key={turn.id} className="space-y-3">
              <div className="flex justify-end">
                <div className="max-w-[85%] rounded-lg border-l-2 border-accent bg-accent/10 px-3.5 py-2.5 text-sm leading-6">
                  {turn.user}
                </div>
              </div>
              <RunView run={turn.run} onRetry={retry} />
            </div>
          ))}
        </div>

        {state.turns.length === 0 && (
          <div className="flex flex-wrap gap-2 border-t border-line px-4 py-3">
            {EXAMPLES.map((ex) => (
              <button
                key={ex.label}
                type="button"
                onClick={() => send(ex.q)}
                className="rounded-full border border-line bg-surface-2 px-3 py-1.5 text-xs text-ink-dim transition-colors hover:border-accent hover:text-ink"
              >
                {ex.icon} {ex.label}
              </button>
            ))}
          </div>
        )}

        <form
          className="flex gap-2 border-t border-line px-4 py-3"
          onSubmit={(e) => {
            e.preventDefault();
            send(draft);
          }}
        >
          <input
            ref={inputRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={busy ? "Streaming…" : "Ask a question…"}
            aria-label="Message the education support agent"
            disabled={busy}
            className="min-w-0 flex-1 rounded-lg border border-line bg-surface-2 px-3.5 py-2.5 text-sm outline-none transition-colors placeholder:text-ink-dim/70 focus:border-accent disabled:opacity-60"
          />
          {busy ? (
            <button
              type="button"
              onClick={stop}
              className="rounded-lg border border-err/50 bg-err/10 px-4 py-2.5 text-sm font-medium text-err transition-colors hover:bg-err/20"
            >
              Stop
            </button>
          ) : (
            <button
              type="submit"
              disabled={!draft.trim()}
              className="rounded-lg bg-accent px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-accent-soft disabled:cursor-not-allowed disabled:opacity-50"
            >
              Send
            </button>
          )}
        </form>
      </section>

      {/* ── Pipeline column ─────────────────────────────────────── */}
      <PipelinePanel
        view={last ? derivePipeline(last.run) : null}
        run={last?.run ?? null}
      />
    </div>
  );
}
