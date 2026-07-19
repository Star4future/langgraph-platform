/**
 * Unit tests for the typed SSE parser — no network, deterministic, CI-safe.
 * They prove: (1) the discriminated union covers every event the server emits,
 * (2) the stream reader reassembles events split across byte-chunk boundaries,
 * and (3) zod validation actually rejects malformed payloads — so "typed" means
 * validated, not merely cast.
 */
import { describe, expect, it } from "vitest";

import {
  AGENT_EVENT_TYPES,
  parseSSEBlock,
  readAgentStream,
  type AgentEvent,
} from "../sse-client.js";

// One valid wire block per event type (matches core/api/sse.py + main.py output).
const SAMPLES: Record<string, string> = {
  thread: `data: {"type":"thread","thread_id":"s1"}`,
  triage: `data: {"type":"triage","intent":"refund_request","confidence":0.92,"urgency":"medium"}`,
  tool_call: `data: {"type":"tool_call","tool":"lookup_subscription","arguments":{"user_email":"a@b.com"}}`,
  tool_result: `data: {"type":"tool_result","tool":"lookup_subscription","result":{"found":true}}`,
  token: `data: {"type":"token","delta":"Yes"}`,
  human_escalation: `data: {"type":"human_escalation","session_id":"s1","reason":"policy_triggered","draft_quality":0.4}`,
  done: `data: {"type":"done","latency_ms":123,"tokens":5,"mode":"mock"}`,
  error: `data: {"type":"error","message":"boom"}`,
};

function streamFrom(text: string): ReadableStream<Uint8Array> {
  const bytes = new TextEncoder().encode(text);
  return new ReadableStream({
    start(controller) {
      // Emit one byte at a time to prove chunk-boundary reassembly.
      for (const b of bytes) controller.enqueue(new Uint8Array([b]));
      controller.close();
    },
  });
}

describe("parseSSEBlock", () => {
  it("parses and narrows every event type the server emits", () => {
    for (const t of AGENT_EVENT_TYPES) {
      const ev = parseSSEBlock(SAMPLES[t] as string);
      expect(ev, `sample for ${t}`).not.toBeNull();
      expect((ev as AgentEvent).type).toBe(t);
    }
  });

  it("covers exactly the eight emitted event types with no gaps", () => {
    expect(new Set(AGENT_EVENT_TYPES).size).toBe(8);
    expect(Object.keys(SAMPLES).sort()).toEqual([...AGENT_EVENT_TYPES].sort());
  });

  it("ignores keep-alives, comments and unknown types", () => {
    expect(parseSSEBlock(": keep-alive")).toBeNull();
    expect(parseSSEBlock("")).toBeNull();
    expect(parseSSEBlock(`data: {"type":"mystery","x":1}`)).toBeNull();
    // citations is declared in sse.py but never emitted by this vertical — not modelled:
    expect(parseSSEBlock(`data: {"type":"citations","citations":[]}`)).toBeNull();
  });

  it("REJECTS malformed payloads at runtime (zod validation, not a bare cast)", () => {
    // right type, missing required field:
    expect(parseSSEBlock(`data: {"type":"triage","intent":"x","urgency":"low"}`)).toBeNull();
    // right type, wrong field type (latency should be a number):
    expect(
      parseSSEBlock(`data: {"type":"done","latency_ms":"slow","tokens":5,"mode":"mock"}`),
    ).toBeNull();
    // tool_call missing the tool name:
    expect(parseSSEBlock(`data: {"type":"tool_call","arguments":{}}`)).toBeNull();
    // valid one still passes (guards against over-strict rejection):
    expect(parseSSEBlock(SAMPLES.triage as string)).not.toBeNull();
  });
});

describe("readAgentStream", () => {
  it("reassembles events split across byte-chunk boundaries", async () => {
    const wire = `${SAMPLES.thread}\n\n${SAMPLES.triage}\n\n${SAMPLES.tool_call}\n\n${SAMPLES.tool_result}\n\n${SAMPLES.token}\n\n${SAMPLES.done}\n\n`;
    const got: AgentEvent[] = [];
    for await (const ev of readAgentStream(streamFrom(wire))) got.push(ev);
    expect(got.map((e) => e.type)).toEqual([
      "thread",
      "triage",
      "tool_call",
      "tool_result",
      "token",
      "done",
    ]);
    // Type narrowing is real, not a cast:
    const done = got.find((e) => e.type === "done");
    if (done?.type === "done") expect(done.mode).toBe("mock");
    const call = got.find((e) => e.type === "tool_call");
    if (call?.type === "tool_call") expect(call.tool).toBe("lookup_subscription");
  });
});
