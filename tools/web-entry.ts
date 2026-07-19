/**
 * Browser entry point. esbuild bundles this (+ zod) into ../web/sse-client.mjs,
 * which the shipping demo page (index.html) imports as an ES module. This makes
 * the deployed page a real consumer of the typed, zod-validated SSE client —
 * not a hand-rolled parser that duplicates (and drifts from) the protocol.
 */
export {
  streamChat,
  readAgentStream,
  parseSSEBlock,
  asAgentEvent,
  AGENT_EVENT_TYPES,
} from "./sse-client.js";
export type { AgentEvent, ChatRequest } from "./sse-client.js";
