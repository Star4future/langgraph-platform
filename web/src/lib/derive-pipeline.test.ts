/**
 * The pipeline panel's contract: node statuses are a pure projection of
 * wire facts. These tests walk a run through its stages and assert what
 * the panel would show at each point — including the honest edges (running
 * is inferred, retry passes, cancelled runs).
 */
import { describe, expect, it } from "vitest";
import type { AgentEvent } from "./protocol";
import {
  consoleReducer,
  derivePipeline,
  initialConsoleState,
  lastTurn,
  type ConsoleAction,
  type ConsoleState,
} from "./stream-reducer";

const thread: AgentEvent = { type: "thread", thread_id: "web-t1" };
const triage: AgentEvent = { type: "triage", intent: "refund_request", confidence: 0.88, urgency: "medium" };
const toolCall: AgentEvent = { type: "tool_call", tool: "check_refund_eligibility", arguments: {} };
const toolResult: AgentEvent = { type: "tool_result", tool: "check_refund_eligibility", result: { eligible: true } };
const token: AgentEvent = { type: "token", delta: "Refund approved." };
const escalation: AgentEvent = { type: "human_escalation", session_id: "web-t1", reason: "policy_triggered", draft_quality: 0.62 };
const done: AgentEvent = { type: "done", latency_ms: 180, tokens: 12, mode: "mock" };

function at(actions: ConsoleAction[]): ReturnType<typeof derivePipeline> {
  const state: ConsoleState = actions.reduce(consoleReducer, initialConsoleState);
  return derivePipeline(lastTurn(state)!.run);
}

const send: ConsoleAction = { type: "send", message: "refund please" };
const ev = (event: AgentEvent): ConsoleAction => ({ type: "event", event });

describe("derivePipeline", () => {
  it("stream open → triage is the inferred-running node", () => {
    expect(at([send, ev(thread)])).toMatchObject({
      triage: "running",
      resolver: "idle",
      supervisor: "idle",
      human: "idle",
    });
  });

  it("triage classified → resolver inferred running", () => {
    expect(at([send, ev(thread), ev(triage)])).toMatchObject({
      triage: "done",
      resolver: "running",
      supervisor: "idle",
    });
  });

  it("tool batch arrived → supervisor scoring is what's left", () => {
    expect(at([send, ev(thread), ev(triage), ev(toolCall), ev(toolResult)])).toMatchObject({
      resolver: "running",
      supervisor: "running",
    });
  });

  it("tokens streaming → resolver and supervisor behind us", () => {
    expect(
      at([send, ev(thread), ev(triage), ev(toolCall), ev(toolResult), ev(token)]),
    ).toMatchObject({ resolver: "done", supervisor: "done", human: "idle" });
  });

  it("a post-token tool batch reads as a retry pass with the supervisor re-scoring", () => {
    const view = at([
      send,
      ev(thread),
      ev(triage),
      ev(toolCall),
      ev(toolResult),
      ev(token),
      ev(toolCall),
    ]);
    expect(view.resolver).toBe("retrying");
    expect(view.supervisor).toBe("running");
    expect(view.retries).toBe(1);
  });

  it("escalation lights the human node; completion marks the rest done", () => {
    expect(
      at([send, ev(thread), ev(triage), ev(toolCall), ev(toolResult), ev(escalation), ev(done)]),
    ).toMatchObject({
      triage: "done",
      resolver: "done",
      supervisor: "done",
      human: "escalated",
    });
  });

  it("a clean run ends with the human node explicitly not needed", () => {
    expect(at([send, ev(thread), ev(triage), ev(token), ev(done)])).toMatchObject({
      human: "skipped",
    });
  });

  it("an aborted run keeps unobserved stages idle — no invented completion", () => {
    expect(at([send, ev(thread), ev(triage), { type: "aborted" }])).toMatchObject({
      triage: "done",
      resolver: "idle", // no tool batch, tokens or escalation ever arrived
      supervisor: "idle",
      human: "skipped",
    });
  });
});
