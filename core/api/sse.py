"""Server-Sent Events helpers.

The platform streams 4-6 event types per chat request:
    thread       — once at start, with thread_id
    triage       — after triage classification
    tool_call    — each time the resolver invokes a tool
    tool_result  — after each tool returns
    token        — N times during draft streaming
    citations    — after supervisor approves draft (if any)
    done         — once at end, with latency_ms / tokens / mode
"""
from __future__ import annotations

import json
from typing import Any


def sse_event(event_type: str, payload: dict[str, Any]) -> str:
    """Format a single SSE event line.

    Returns a properly terminated SSE data block:
        data: {"type":"...","...":...}\\n\\n
    """
    body = {"type": event_type, **payload}
    return f"data: {json.dumps(body)}\n\n"


def thread_event(thread_id: str) -> str:
    return sse_event("thread", {"thread_id": thread_id})


def triage_event(intent: str, confidence: float, urgency: str) -> str:
    return sse_event(
        "triage",
        {"intent": intent, "confidence": confidence, "urgency": urgency},
    )


def tool_call_event(name: str, args: dict) -> str:
    return sse_event("tool_call", {"tool": name, "arguments": args})


def tool_result_event(name: str, result: Any) -> str:
    return sse_event("tool_result", {"tool": name, "result": result})


def token_event(delta: str) -> str:
    return sse_event("token", {"delta": delta})


def citations_event(citations: list[dict]) -> str:
    return sse_event("citations", {"citations": citations})


def done_event(*, latency_ms: int, tokens: int, mode: str) -> str:
    return sse_event(
        "done",
        {"latency_ms": latency_ms, "tokens": tokens, "mode": mode},
    )


def error_event(message: str) -> str:
    return sse_event("error", {"message": message})


__all__ = [
    "sse_event",
    "thread_event",
    "triage_event",
    "tool_call_event",
    "tool_result_event",
    "token_event",
    "citations_event",
    "done_event",
    "error_event",
]
