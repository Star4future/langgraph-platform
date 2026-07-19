/**
 * Typed SSE client for the LangGraph Platform agent stream.
 *
 * `POST /api/chat` returns `text/event-stream` — a sequence of
 * `data: {json}\n\n` blocks emitted by the Triage → Resolver → Supervisor
 * graph (see core/api/sse.py). This module turns that untyped wire format into
 * a **zod-validated discriminated union**, so a TypeScript consumer (the web
 * front-end) can `switch (event.type)` with the compiler guaranteeing every
 * case is handled — and a malformed payload is *rejected at runtime*, not
 * silently trusted. "Typed" here means validated, not merely cast.
 *
 * Coverage note: every variant below is a event the server actually emits
 * (verified against core/api/main.py). The `citations` helper that exists in
 * core/api/sse.py is intentionally NOT modelled — the customer-support graph
 * never emits it; it is reserved for a future source-grounded vertical. We
 * type what ships, not what is merely declared.
 */
import { z } from "zod";

// ── The event protocol as zod schemas (one per emitted `type`) ───────

export const ThreadEvent = z.object({
  type: z.literal("thread"),
  thread_id: z.string(),
});
export const TriageEvent = z.object({
  type: z.literal("triage"),
  intent: z.string(),
  confidence: z.number(),
  urgency: z.string(),
});
export const ToolCallEvent = z.object({
  type: z.literal("tool_call"),
  tool: z.string(),
  arguments: z.record(z.string(), z.unknown()),
});
export const ToolResultEvent = z.object({
  type: z.literal("tool_result"),
  tool: z.string(),
  result: z.unknown(),
});
export const TokenEvent = z.object({
  type: z.literal("token"),
  delta: z.string(),
});
export const HumanEscalationEvent = z.object({
  type: z.literal("human_escalation"),
  session_id: z.string(),
  reason: z.string(),
  draft_quality: z.number(),
});
export const DoneEvent = z.object({
  type: z.literal("done"),
  latency_ms: z.number(),
  tokens: z.number(),
  mode: z.string(),
});
export const ErrorEvent = z.object({
  type: z.literal("error"),
  message: z.string(),
});

/** The full agent event stream as a validated discriminated union. */
export const AgentEventSchema = z.discriminatedUnion("type", [
  ThreadEvent,
  TriageEvent,
  ToolCallEvent,
  ToolResultEvent,
  TokenEvent,
  HumanEscalationEvent,
  DoneEvent,
  ErrorEvent,
]);

/** Types are inferred from the schemas — a single source of truth. */
export type AgentEvent = z.infer<typeof AgentEventSchema>;
export type ThreadEvent = z.infer<typeof ThreadEvent>;
export type TriageEvent = z.infer<typeof TriageEvent>;
export type ToolCallEvent = z.infer<typeof ToolCallEvent>;
export type ToolResultEvent = z.infer<typeof ToolResultEvent>;
export type TokenEvent = z.infer<typeof TokenEvent>;
export type HumanEscalationEvent = z.infer<typeof HumanEscalationEvent>;
export type DoneEvent = z.infer<typeof DoneEvent>;
export type ErrorEvent = z.infer<typeof ErrorEvent>;

/** Every event `type` the stream can carry, in protocol order. */
export const AGENT_EVENT_TYPES = [
  "thread",
  "triage",
  "tool_call",
  "tool_result",
  "token",
  "human_escalation",
  "done",
  "error",
] as const;

export type AgentEventType = (typeof AGENT_EVENT_TYPES)[number];

/**
 * Validate an already-parsed object against the event schema.
 * Returns a fully-typed AgentEvent, or null if it fails validation
 * (unknown type, missing/mistyped field, keep-alive, etc.).
 */
export function asAgentEvent(obj: unknown): AgentEvent | null {
  const result = AgentEventSchema.safeParse(obj);
  return result.success ? result.data : null;
}

/**
 * Parse one SSE block (the text between two blank-line separators) into a
 * validated AgentEvent. Returns null for keep-alives, comments, malformed
 * JSON, or payloads that don't match the schema.
 */
export function parseSSEBlock(block: string): AgentEvent | null {
  const dataLines = block
    .split(/\r?\n/)
    .filter((l) => l.startsWith("data:"))
    .map((l) => l.slice(5).trim());
  if (dataLines.length === 0) return null;
  const payload = dataLines.join("\n");
  try {
    return asAgentEvent(JSON.parse(payload));
  } catch {
    return null;
  }
}

/**
 * Turn a byte stream of SSE into an async iterator of validated events.
 * Handles blocks that arrive split across chunk boundaries.
 */
export async function* readAgentStream(
  stream: ReadableStream<Uint8Array>,
): AsyncGenerator<AgentEvent> {
  const decoder = new TextDecoder();
  const reader = stream.getReader();
  let buffer = "";
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let sep: number;
      // SSE separates events with a blank line (\n\n or \r\n\r\n).
      while ((sep = firstSeparator(buffer)) !== -1) {
        const block = buffer.slice(0, sep);
        buffer = buffer.slice(sep + separatorLength(buffer, sep));
        const ev = parseSSEBlock(block);
        if (ev) yield ev;
      }
    }
    const tail = parseSSEBlock(buffer);
    if (tail) yield tail;
  } finally {
    reader.releaseLock();
  }
}

function firstSeparator(s: string): number {
  const a = s.indexOf("\n\n");
  const b = s.indexOf("\r\n\r\n");
  if (a === -1) return b;
  if (b === -1) return a;
  return Math.min(a, b);
}
function separatorLength(s: string, at: number): number {
  return s.startsWith("\r\n\r\n", at) ? 4 : 2;
}

// ── High-level request helper ────────────────────────────────────────

export interface ChatRequest {
  message: string;
  session_id: string;
  customer_id?: string;
  vertical?: string;
}

/**
 * POST a chat message and yield the agent's validated event stream.
 * `baseUrl` is the deployment root, e.g. the Cloud Run URL.
 */
export async function* streamChat(baseUrl: string, req: ChatRequest): AsyncGenerator<AgentEvent> {
  const res = await fetch(`${baseUrl.replace(/\/$/, "")}/api/chat`, {
    method: "POST",
    headers: { "content-type": "application/json", accept: "text/event-stream" },
    body: JSON.stringify({ customer_id: "cli-demo", ...req }),
  });
  if (!res.ok || !res.body) {
    throw new Error(`chat request failed: HTTP ${res.status} ${res.statusText}`);
  }
  yield* readAgentStream(res.body);
}
