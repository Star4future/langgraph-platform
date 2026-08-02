/**
 * Console state machine.
 *
 * The reducer stores *facts observed on the wire* — validated AgentEvents,
 * accumulated answer text, completion metadata. It deliberately stores no
 * presentation state: pipeline node statuses are *derived* from those facts
 * by `derivePipeline`, because the protocol only carries completion events
 * (triage classified, tools recorded, tokens streaming) and never
 * node-started events. Deriving keeps the honest gap between "what the
 * stream tells us" and "what the panel shows" in one auditable place.
 *
 * Everything here is a pure function of (state, action) — no clocks, no
 * randomness, no I/O — so the whole machine is unit-testable without React.
 */
import type { AgentEvent, DoneEvent, TriageEvent } from "./protocol";

// ── Run state (one agent turn) ───────────────────────────────────────

export type RunPhase = "connecting" | "streaming" | "done" | "error" | "aborted";

export interface ToolInvocation {
  tool: string;
  args: Record<string, unknown> | null;
  /** Result payload; undefined until the paired tool_result arrives. */
  result?: unknown;
  settled: boolean;
}

/**
 * One resolver pass. The server flushes tool_call/tool_result pairs in a
 * batch when a resolver pass completes; a second batch after tokens have
 * started means the supervisor scored the draft low and routed back — a
 * retry round.
 */
export interface ResolverRound {
  tools: ToolInvocation[];
  /** Client arrival time of the pass's first tool_call (performance.now). */
  startAtMs?: number;
}

export interface RunState {
  phase: RunPhase;
  threadId: string | null;
  triage: TriageEvent | null;
  rounds: ResolverRound[];
  /** Token deltas concatenated in arrival order. */
  answer: string;
  sawToken: boolean;
  escalation: { reason: string; draftQuality: number } | null;
  completion: Pick<DoneEvent, "latency_ms" | "tokens" | "mode"> | null;
  /** Server-reported `error` event, or a client transport failure. */
  errorMessage: string | null;
  /**
   * Non-token events in arrival order, for the timeline. atMs is the
   * client's arrival clock (performance.now, supplied by the component —
   * the reducer itself stays clock-free and deterministic); cards render
   * offsets relative to the first entry.
   */
  timeline: { seq: number; event: AgentEvent; atMs?: number }[];
  nextSeq: number;
}

export const initialRun = (): RunState => ({
  phase: "connecting",
  threadId: null,
  triage: null,
  rounds: [],
  answer: "",
  sawToken: false,
  escalation: null,
  completion: null,
  errorMessage: null,
  timeline: [],
  nextSeq: 0,
});

// ── Conversation state ───────────────────────────────────────────────

export interface Turn {
  id: number;
  user: string;
  run: RunState;
}

export interface ConsoleState {
  turns: Turn[];
  nextTurnId: number;
}

export const initialConsoleState: ConsoleState = {
  turns: [],
  nextTurnId: 1,
};

export type ConsoleAction =
  | { type: "send"; message: string }
  /** A validated AgentEvent arrived on the active stream. */
  | { type: "event"; event: AgentEvent; atMs?: number }
  /** The transport failed (fetch threw, stream cut mid-flight). */
  | { type: "stream_failed"; message: string }
  /** The stream ended cleanly at the HTTP level. */
  | { type: "stream_closed" }
  /** The user cancelled the in-flight run. */
  | { type: "aborted" }
  /** Re-run the last turn after an error/abort, keeping its user message. */
  | { type: "retry" };

// ── Helpers ──────────────────────────────────────────────────────────

export const activeTurn = (state: ConsoleState): Turn | null => {
  const last = state.turns[state.turns.length - 1];
  if (!last) return null;
  return last.run.phase === "connecting" || last.run.phase === "streaming" ? last : null;
};

export const lastTurn = (state: ConsoleState): Turn | null =>
  state.turns[state.turns.length - 1] ?? null;

const replaceLastRun = (state: ConsoleState, run: RunState): ConsoleState => {
  const turns = state.turns.slice();
  const last = turns[turns.length - 1];
  turns[turns.length - 1] = { ...last, run };
  return { ...state, turns };
};

// ── Event application (facts only) ───────────────────────────────────

const record = (run: RunState, event: AgentEvent, atMs?: number): RunState => ({
  ...run,
  timeline: [...run.timeline, { seq: run.nextSeq, event, atMs }],
  nextSeq: run.nextSeq + 1,
});

function applyEvent(run: RunState, event: AgentEvent, atMs?: number): RunState {
  switch (event.type) {
    case "thread":
      return { ...record(run, event, atMs), phase: "streaming", threadId: event.thread_id };

    case "triage":
      return { ...record(run, event, atMs), triage: event };

    case "tool_call": {
      const next = record(run, event, atMs);
      const rounds = next.rounds.slice();
      const last = rounds[rounds.length - 1];
      // The server flushes a whole resolver pass as one contiguous batch.
      // Tokens (or an escalation) arriving before another tool_call mean
      // any further batch belongs to a new pass — a retry round.
      const startNewRound = !last || next.sawToken || next.escalation !== null;
      const invocation: ToolInvocation = {
        tool: event.tool,
        args: event.arguments ?? null,
        settled: false,
      };
      if (startNewRound) {
        rounds.push({ tools: [invocation], startAtMs: atMs });
      } else {
        rounds[rounds.length - 1] = { ...last, tools: [...last.tools, invocation] };
      }
      return { ...next, rounds };
    }

    case "tool_result": {
      const next = record(run, event, atMs);
      const rounds = next.rounds.slice();
      const last = rounds[rounds.length - 1];
      if (!last) return next; // result without a call — record it, change nothing
      const tools = last.tools.slice();
      const idx = tools.findIndex((t) => !t.settled && t.tool === event.tool);
      if (idx === -1) return next;
      tools[idx] = { ...tools[idx], result: event.result, settled: true };
      rounds[rounds.length - 1] = { ...last, tools };
      return { ...next, rounds };
    }

    case "token":
      // Deltas fold into the answer; the timeline stays token-free so a
      // long response doesn't grow state by one entry per word.
      return { ...run, answer: run.answer + event.delta, sawToken: true };

    case "human_escalation":
      return {
        ...record(run, event, atMs),
        escalation: { reason: event.reason, draftQuality: event.draft_quality },
      };

    case "done": {
      const next = record(run, event, atMs);
      return {
        ...next,
        completion: {
          latency_ms: event.latency_ms,
          tokens: event.tokens,
          mode: event.mode,
        },
        // The server sends `done` even after `error`; an errored run stays
        // errored — completion metadata is recorded either way.
        phase: next.phase === "error" ? "error" : "done",
      };
    }

    case "error":
      return { ...record(run, event, atMs), errorMessage: event.message, phase: "error" };
  }
}

// ── Reducer ──────────────────────────────────────────────────────────

export function consoleReducer(state: ConsoleState, action: ConsoleAction): ConsoleState {
  switch (action.type) {
    case "send": {
      if (activeTurn(state)) return state; // one run at a time
      const message = action.message.trim();
      if (!message) return state;
      return {
        turns: [...state.turns, { id: state.nextTurnId, user: message, run: initialRun() }],
        nextTurnId: state.nextTurnId + 1,
      };
    }

    case "event": {
      const turn = lastTurn(state);
      if (!turn) return state;
      const phase = turn.run.phase;
      // Aborted and completed runs accept nothing further. An errored run
      // still accepts the server's epilogue — the engine always follows an
      // `error` event with `done` — so completion metadata is recorded.
      if (phase === "aborted" || phase === "done") return state;
      if (phase === "error" && action.event.type !== "done") return state;
      return replaceLastRun(state, applyEvent(turn.run, action.event, action.atMs));
    }

    case "stream_failed": {
      const turn = activeTurn(state);
      if (!turn) return state;
      return replaceLastRun(state, {
        ...turn.run,
        phase: "error",
        errorMessage: action.message,
      });
    }

    case "stream_closed": {
      // The server always terminates a run with `done` (even after `error`),
      // so a clean close while we still think we're streaming means the
      // connection was cut — surface it as a failure, not a silent stop.
      const turn = activeTurn(state);
      if (!turn) return state;
      return replaceLastRun(state, {
        ...turn.run,
        phase: "error",
        errorMessage: "The stream ended before the run completed.",
      });
    }

    case "aborted": {
      const turn = activeTurn(state);
      if (!turn) return state;
      return replaceLastRun(state, { ...turn.run, phase: "aborted" });
    }

    case "retry": {
      const last = lastTurn(state);
      if (!last) return state;
      if (last.run.phase !== "error" && last.run.phase !== "aborted") return state;
      // Same turn, same user message, fresh run — the transport re-posts
      // with the same session id, so the engine keeps its thread context.
      return replaceLastRun(state, initialRun());
    }
  }
}

// ── Derived pipeline view ────────────────────────────────────────────

export type PipelineNodeId = "triage" | "resolver" | "supervisor" | "human";

export type NodeStatus =
  | "idle" // nothing observed yet
  | "running" // inferred in progress
  | "done"
  | "retrying" // resolver only: a post-token batch arrived
  | "escalated" // human only
  | "skipped"; // human only: run finished without escalation

export interface PipelineView {
  triage: NodeStatus;
  resolver: NodeStatus;
  supervisor: NodeStatus;
  human: NodeStatus;
  /** Resolver passes beyond the first. */
  retries: number;
}

/**
 * Project wire facts onto the Triage → Resolver → Supervisor → (Human)
 * graph. The stream carries completion signals only (see core/api/main.py:
 * triage/tool events are emitted on each node's on_chain_end), so
 * "running" is always an inference from the previous node having finished
 * — that honesty lives here, in one place, instead of being scattered
 * through components.
 */
export function derivePipeline(run: RunState): PipelineView {
  const { phase, triage, rounds, sawToken, escalation, completion } = run;
  const finished = phase === "done" || phase === "error" || phase === "aborted";
  const settled = finished || escalation !== null || completion !== null;
  const retries = Math.max(0, rounds.length - 1);

  // Triage: running once the stream opens, classified on the triage event.
  const triageStatus: NodeStatus =
    triage !== null ? "done" : phase === "streaming" ? "running" : "idle";

  // Resolver. A second tool batch after tokens means the supervisor
  // routed back — the run is in a retry pass even though a draft already
  // streamed (mock mode replays the first pass's draft only once).
  // Evidence that the resolver/supervisor stages actually ran: tool
  // batches, streamed tokens, or an escalation (which the graph only
  // reaches after supervisor scoring). An aborted run without any of
  // these leaves the stages idle — we don't claim work we never saw.
  const stagesRan = rounds.length > 0 || sawToken || escalation !== null;

  let resolver: NodeStatus = "idle";
  if (settled) resolver = stagesRan ? "done" : "idle";
  else if (retries > 0) resolver = "retrying";
  else if (sawToken) resolver = "done";
  else if (triage !== null) resolver = "running";

  // Supervisor: scores after each resolver pass; during a retry pass it is
  // about to score again, so it reads as running until the run settles.
  let supervisor: NodeStatus = "idle";
  if (settled) supervisor = stagesRan ? "done" : "idle";
  else if (retries > 0) supervisor = "running";
  else if (sawToken) supervisor = "done";
  else if (rounds.length > 0) supervisor = "running";

  // Human: only lit by an explicit escalation event.
  let human: NodeStatus = "idle";
  if (escalation !== null) human = "escalated";
  else if (finished) human = "skipped";

  return { triage: triageStatus, resolver, supervisor, human, retries };
}
