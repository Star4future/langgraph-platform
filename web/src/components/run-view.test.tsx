/** @vitest-environment jsdom */
/**
 * Rendering contract tests. States are produced by the real reducer (not
 * hand-built objects), so these lock the user-visible behaviour of a run:
 * error → retry affordance, escalation copy, completion meta, tool detail.
 */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { AgentEvent } from "@/lib/protocol";
import {
  consoleReducer,
  derivePipeline,
  initialConsoleState,
  lastTurn,
  type ConsoleAction,
  type RunState,
} from "@/lib/stream-reducer";
import { PipelinePanel } from "./pipeline-panel";
import { RunView } from "./run-view";

const ev = (event: AgentEvent): ConsoleAction => ({ type: "event", event });

function runFrom(actions: ConsoleAction[]): RunState {
  const state = actions.reduce(consoleReducer, initialConsoleState);
  return lastTurn(state)!.run;
}

const base: ConsoleAction[] = [
  { type: "send", message: "refund please" },
  ev({ type: "thread", thread_id: "web-t9" }),
  ev({ type: "triage", intent: "refund_request", confidence: 0.88, urgency: "medium" }),
  ev({ type: "tool_call", tool: "check_refund_eligibility", arguments: { days: 3 } }),
  ev({ type: "tool_result", tool: "check_refund_eligibility", result: { eligible: true } }),
];

afterEach(cleanup);

describe("RunView", () => {
  it("renders the streamed answer and completion meta of a finished run", () => {
    const run = runFrom([
      ...base,
      ev({ type: "token", delta: "Refund " }),
      ev({ type: "token", delta: "approved." }),
      ev({ type: "done", latency_ms: 180, tokens: 12, mode: "mock" }),
    ]);
    render(<RunView run={run} onRetry={() => {}} />);
    expect(screen.getByText("Refund approved.")).toBeTruthy();
    expect(screen.getByText(/180 ms/)).toBeTruthy();
    expect(screen.getByText("mock")).toBeTruthy();
    // tool detail is reachable
    expect(screen.getByText(/check_refund_eligibility/)).toBeTruthy();
  });

  it("shows the error state with a retry affordance that fires", () => {
    const run = runFrom([...base, { type: "stream_failed", message: "network changed" }]);
    const onRetry = vi.fn();
    render(<RunView run={run} onRetry={onRetry} />);
    expect(screen.getByText(/network changed/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("keeps partial output visible after a cancellation", () => {
    const run = runFrom([
      ...base,
      ev({ type: "token", delta: "partial answer" }),
      { type: "aborted" },
    ]);
    render(<RunView run={run} onRetry={() => {}} />);
    expect(screen.getByText(/partial answer/)).toBeTruthy();
    expect(screen.getByText(/cancelled before the stream finished/i)).toBeTruthy();
  });

  it("explains an escalation in checkpoint terms with the draft score", () => {
    const run = runFrom([
      ...base,
      ev({
        type: "human_escalation",
        session_id: "web-t9",
        reason: "policy_triggered",
        draft_quality: 0.62,
      }),
      ev({ type: "done", latency_ms: 90, tokens: 0, mode: "mock" }),
    ]);
    render(<RunView run={run} onRetry={() => {}} />);
    expect(screen.getByText(/routed to a person/i)).toBeTruthy();
    expect(screen.getByText("0.62")).toBeTruthy();
  });
});

describe("PipelinePanel", () => {
  it("reflects a mid-run state without inventing progress", () => {
    const run = runFrom(base); // tools arrived, no tokens yet
    render(<PipelinePanel view={derivePipeline(run)} run={run} />);
    expect(screen.getByText("Triage").parentElement?.textContent).toContain("done");
    expect(screen.getByText("Resolver").parentElement?.textContent).toContain("running");
    expect(screen.getByText("Supervisor").parentElement?.textContent).toContain("running");
    expect(screen.getByText(/1 tool call/)).toBeTruthy();
  });

  it("marks the human lane escalated when the event arrives", () => {
    const run = runFrom([
      ...base,
      ev({
        type: "human_escalation",
        session_id: "web-t9",
        reason: "policy_triggered",
        draft_quality: 0.62,
      }),
    ]);
    render(<PipelinePanel view={derivePipeline(run)} run={run} />);
    expect(screen.getByText("Human").parentElement?.textContent).toContain("escalated");
  });
});
