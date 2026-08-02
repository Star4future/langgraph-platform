/**
 * Browser transport for the agent stream.
 *
 * Uses the shared zod-validated parser (readAgentStream) over a fetch the
 * console controls, because cancellation needs an AbortSignal on the
 * request — tools/sse-client.ts's higher-level streamChat helper doesn't
 * take one, and the protocol module stays untouched (it is shared with the
 * CLI and the Node test suite). Parsing and validation still happen in
 * exactly one place: tools/sse-client.ts.
 */
import { readAgentStream, type AgentEvent, type ChatRequest } from "./protocol";

export interface StreamCallbacks {
  onEvent: (event: AgentEvent) => void;
}

/**
 * POST /api/chat (same origin) and pump validated events to the caller.
 *
 * Resolves when the stream ends cleanly; rejects on HTTP failure, a
 * mid-stream network cut, or abort (DOMException "AbortError").
 */
export async function streamAgentChat(
  req: ChatRequest,
  { onEvent }: StreamCallbacks,
  signal: AbortSignal,
): Promise<void> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "content-type": "application/json", accept: "text/event-stream" },
    body: JSON.stringify(req),
    signal,
  });
  if (!res.ok || !res.body) {
    throw new Error(`chat request failed: HTTP ${res.status} ${res.statusText}`);
  }
  for await (const event of readAgentStream(res.body)) {
    onEvent(event);
  }
}
