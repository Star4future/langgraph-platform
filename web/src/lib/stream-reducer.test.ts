/**
 * Behavioural tests for the console state machine.
 *
 * Event payloads mirror what core/api/main.py actually emits (captured off
 * the live wire), fed through the real reducer — the tests assert on the
 * states a user's UI would be in, not on implementation internals.
 */
import { describe, expect, it } from "vitest";
import type { AgentEvent } from "./protocol";
import {
  activeTurn,
  consoleReducer,
  initialConsoleState,
  lastTurn,
  type ConsoleAction,
  type ConsoleState,
} from "./stream-reducer";

// ── Wire fixtures (shapes observed from the deployed engine) ─────────

const thread: AgentEvent = { type: "thread", thread_id: "web-t1" };
const triage: AgentEvent = {
  type: "triage",
  intent: "billing_change",
  confidence: 0.91,
  urgency: "low",
};
const toolCall = (tool: string): AgentEvent => ({
  type: "tool_call",
  tool,
  arguments: { customer_id: "web_visitor" },
});
const toolResult = (tool: string): AgentEvent => ({
  type: "tool_result",
  tool,
  result: { ok: true },
});
const token = (delta: string): AgentEvent => ({ type: "token", delta });
const escalation: AgentEvent = {
  type: "human_escalation",
  session_id: "web-t1",
  reason: "policy_triggered",
  draft_quality: 0.82,
};
const done: AgentEvent = { type: "done", latency_ms: 214, tokens: 21, mode: "mock" };
const serverError: AgentEvent = { type: "error", message: "vertical exploded" };

function play(actions: ConsoleAction[], from: ConsoleState = initialConsoleState): ConsoleState {
  return actions.reduce(consoleReducer, from);
}

const send = (message = "switch my plan"): ConsoleAction => ({ type: "send", message });
const ev = (event: AgentEvent): ConsoleAction => ({ type: "event", event });

// ── Happy path ───────────────────────────────────────────────────────

describe("happy path", () => {
  const state = play([
    send(),
    ev(thread),
    ev(triage),
    ev(toolCall("lookup_subscription")),
    ev(toolResult("lookup_subscription")),
    ev(toolCall("switch_plan")),
    ev(toolResult("switch_plan")),
    ev(token("Done — ")),
    ev(token("your plan is updated.")),
    ev(done),
  ]);
  const run = lastTurn(state)!.run;

  it("finishes the run with completion metadata", () => {
    expect(run.phase).toBe("done");
    expect(run.completion).toEqual({ latency_ms: 214, tokens: 21, mode: "mock" });
    expect(activeTurn(state)).toBeNull();
  });

  it("stores the triage classification and thread id", () => {
    expect(run.threadId).toBe("web-t1");
    expect(run.triage?.intent).toBe("billing_change");
  });

  it("pairs tool results onto their calls within one pass", () => {
    expect(run.rounds).toHaveLength(1);
    expect(run.rounds[0].tools.map((t) => t.tool)).toEqual(["lookup_subscription", "switch_plan"]);
    expect(run.rounds[0].tools.every((t) => t.settled)).toBe(true);
  });

  it("accumulates token deltas into the answer and keeps them off the timeline", () => {
    expect(run.answer).toBe("Done — your plan is updated.");
    expect(run.timeline.some((t) => t.event.type === "token")).toBe(false);
  });
});

// ── Retry pass grouping ──────────────────────────────────────────────

describe("supervisor retry pass", () => {
  it("opens a second round when a tool batch arrives after tokens", () => {
    const state = play([
      send(),
      ev(thread),
      ev(triage),
      ev(toolCall("check_refund_eligibility")),
      ev(toolResult("check_refund_eligibility")),
      ev(token("First draft…")),
      ev(toolCall("calculate_prorated_refund")), // supervisor routed back
      ev(toolResult("calculate_prorated_refund")),
      ev(done),
    ]);
    const run = lastTurn(state)!.run;
    expect(run.rounds).toHaveLength(2);
    expect(run.rounds[1].tools[0].tool).toBe("calculate_prorated_refund");
  });
});

// ── Escalation ───────────────────────────────────────────────────────

describe("human escalation", () => {
  it("records the paused-for-human state", () => {
    const state = play([send(), ev(thread), ev(triage), ev(escalation), ev(done)]);
    const run = lastTurn(state)!.run;
    expect(run.escalation).toEqual({ reason: "policy_triggered", draftQuality: 0.82 });
    expect(run.phase).toBe("done");
  });
});

// ── Failure modes ────────────────────────────────────────────────────

describe("failure modes", () => {
  it("a server error event marks the run errored even though done follows", () => {
    const state = play([send(), ev(thread), ev(serverError), ev(done)]);
    const run = lastTurn(state)!.run;
    expect(run.phase).toBe("error");
    expect(run.errorMessage).toBe("vertical exploded");
    // done's metadata is still recorded for the meta line
    expect(run.completion?.mode).toBe("mock");
  });

  it("a clean close before done is surfaced as a failure, not a silent stop", () => {
    const state = play([send(), ev(thread), ev(triage), { type: "stream_closed" }]);
    const run = lastTurn(state)!.run;
    expect(run.phase).toBe("error");
    expect(run.errorMessage).toMatch(/ended before/i);
  });

  it("a transport failure mid-stream keeps everything already received", () => {
    const state = play([
      send(),
      ev(thread),
      ev(triage),
      ev(token("partial ")),
      { type: "stream_failed", message: "network changed" },
    ]);
    const run = lastTurn(state)!.run;
    expect(run.phase).toBe("error");
    expect(run.answer).toBe("partial ");
    expect(run.triage?.intent).toBe("billing_change");
  });

  it("abort marks the run cancelled and late events are dropped", () => {
    const aborted = play([send(), ev(thread), { type: "aborted" }]);
    expect(lastTurn(aborted)!.run.phase).toBe("aborted");
    // a straggler event after cancellation must not resurrect the run
    const after = consoleReducer(aborted, ev(token("ghost")));
    expect(lastTurn(after)!.run.answer).toBe("");
    expect(lastTurn(after)!.run.phase).toBe("aborted");
  });
});

// ── Retry semantics ──────────────────────────────────────────────────

describe("retry", () => {
  it("resets the failed run but keeps the user message for re-posting", () => {
    const failed = play([send("original question"), ev(thread), { type: "aborted" }]);
    const retried = consoleReducer(failed, { type: "retry" });
    const turn = lastTurn(retried)!;
    expect(turn.user).toBe("original question");
    expect(turn.run.phase).toBe("connecting");
    expect(turn.run.timeline).toHaveLength(0);
    expect(retried.turns).toHaveLength(1); // same turn, not a new one
  });

  it("does nothing while a run is still active or after success", () => {
    const active = play([send(), ev(thread)]);
    expect(consoleReducer(active, { type: "retry" })).toBe(active);
    const finished = play([send(), ev(thread), ev(done)]);
    expect(consoleReducer(finished, { type: "retry" })).toBe(finished);
  });
});

// ── Input guards ─────────────────────────────────────────────────────

describe("send guards", () => {
  it("ignores a second send while a run is in flight", () => {
    const state = play([send("first"), ev(thread), send("second")]);
    expect(state.turns).toHaveLength(1);
    expect(state.turns[0].user).toBe("first");
  });

  it("ignores blank messages", () => {
    expect(play([send("   ")]).turns).toHaveLength(0);
  });
});
