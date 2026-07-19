"""FastAPI app factory for the LangGraph Platform.

Usage (per deploy):

    from core.api import create_app
    app = create_app(default_vertical="education")

The app exposes:
    POST  /api/chat            — SSE stream of agent events
    POST  /api/resume          — resume a paused (HITL) graph
    GET   /api/pending-human   — list sessions awaiting human input
    POST  /api/eval            — run a vertical's eval harness
    GET   /api/health          — status + config + loaded verticals

INDUSTRY-AGNOSTIC. All domain knowledge lives in verticals/.
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from core import __version__
from core.api.models import (
    ChatRequest,
    EvalRequest,
    HealthResponse,
    PendingHumanResponse,
    PendingItem,
    ResumeRequest,
)
from core.api.sse import (
    done_event,
    error_event,
    sse_event,
    thread_event,
    token_event,
    tool_call_event,
    tool_result_event,
    triage_event,
)
from core.state import initial_state

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# In-memory session store (replace with Redis for multi-instance)
# ─────────────────────────────────────────────────────────────────────

_PENDING_HUMAN: dict[str, dict] = {}


# ─────────────────────────────────────────────────────────────────────
# App factory
# ─────────────────────────────────────────────────────────────────────

def create_app(*, default_vertical: str | None = None) -> FastAPI:
    """Create a configured FastAPI app.

    Args:
        default_vertical: Vertical name to use when /api/chat doesn't specify one.
                          Falls back to ``$VERTICAL`` env var, then "education".

    Returns:
        FastAPI app ready to be served by uvicorn or Vercel.
    """
    # NOTE: no hard-coded vertical default in core — deploys pass it explicitly,
    # or set the VERTICAL env var. Falls back to first registered vertical.
    if not default_vertical:
        default_vertical = os.getenv("VERTICAL")
    if not default_vertical:
        from verticals import VERTICALS
        default_vertical = next(iter(VERTICALS.keys()), "")
    mode = "real" if os.getenv("OPENAI_API_KEY") else "mock"

    app = FastAPI(
        title="LangGraph Platform",
        description="Multi-vertical AI customer workflow engine",
        version=__version__,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    # CORS: restrict by env var in production (comma-separated).  Default "*" is fine
    # for a local demo but must be set to your actual domain(s) for any real deploy.
    # Example: CORS_ORIGINS="https://acmeacademy.com.au,https://demo.yourbrand.com"
    _cors_origins_raw = os.getenv("CORS_ORIGINS", "*")
    _cors_origins = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    # ── lazy vertical loading (avoids import at module load) ────────
    def load_vertical(name: str) -> dict:
        from verticals import get_vertical
        return get_vertical(name)

    # ── /api/health ─────────────────────────────────────────────────
    @app.get("/api/health", response_model=HealthResponse, tags=["system"])
    async def health() -> HealthResponse:
        from verticals import VERTICALS
        return HealthResponse(
            status="ok",
            version=__version__,
            mode=mode,
            loaded_verticals=list(VERTICALS.keys()),
            default_vertical=default_vertical,
            config={
                "quality_threshold": float(os.getenv("QUALITY_THRESHOLD", "0.7")),
                "max_retry_count": int(os.getenv("MAX_RETRY_COUNT", "2")),
                "triage_confidence_floor": float(os.getenv("TRIAGE_CONFIDENCE_FLOOR", "0.5")),
                "llm_model": os.getenv("LLM_MODEL", "gpt-4o-mini"),
            },
        )

    # ── /api/chat (SSE) ─────────────────────────────────────────────
    @app.post("/api/chat", tags=["chat"])
    async def chat(req: ChatRequest, request: Request) -> StreamingResponse:
        vertical_name = req.vertical or default_vertical
        try:
            vertical = load_vertical(vertical_name)
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        generator = _run_chat(req, vertical, vertical_name, mode)
        return StreamingResponse(
            generator,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    # ── /api/resume ─────────────────────────────────────────────────
    @app.post("/api/resume", tags=["chat"])
    async def resume(req: ResumeRequest) -> dict:
        if req.session_id not in _PENDING_HUMAN:
            raise HTTPException(status_code=404, detail="Session not pending")
        pending = _PENDING_HUMAN.pop(req.session_id)

        # Reload the vertical the session was using
        v_name = pending.get("vertical_name", default_vertical)
        try:
            vertical = load_vertical(v_name)
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        compile_graph = vertical["build_graph"]
        graph = compile_graph()

        # LangGraph HITL resume pattern:
        #   1. Inject operator decision into the checkpointed state
        #   2. Call ainvoke(None, config) to continue from the interrupt point
        config = {"configurable": {"thread_id": req.session_id}}
        try:
            graph.update_state(config, {"human_decision": req.human_decision})
            final_state = await graph.ainvoke(None, config)
            final_response = final_state.get("final_response") or req.human_decision
        except Exception as exc:  # noqa: BLE001
            logger.warning("Graph resume failed (%s) — using human_decision as final response", exc)
            final_response = req.human_decision

        return {
            "status": "resolved",
            "session_id": req.session_id,
            "final_response": final_response,
        }

    # ── /api/pending-human ──────────────────────────────────────────
    @app.get("/api/pending-human", response_model=PendingHumanResponse, tags=["chat"])
    async def pending() -> PendingHumanResponse:
        items = [
            PendingItem(
                session_id=sid,
                customer_id=p.get("customer_id", "unknown"),
                intent=p.get("intent", "unknown"),
                awaiting_since=p.get("awaiting_since", ""),
                summary=p.get("summary", ""),
            )
            for sid, p in _PENDING_HUMAN.items()
        ]
        return PendingHumanResponse(pending=items, count=len(items))

    # ── /api/eval ───────────────────────────────────────────────────
    @app.post("/api/eval", tags=["evaluation"])
    async def eval_endpoint(req: EvalRequest) -> dict:
        # Security: only datasets shipped under eval/datasets/ may be run.
        # Accepting arbitrary paths here would let a caller point the JSONL
        # parser at any file on disk (and leak its content via the error).
        if req.dataset is not None:
            from eval.run_eval import ROOT as _EVAL_ROOT
            datasets_dir = (_EVAL_ROOT / "eval" / "datasets").resolve()
            candidate = (datasets_dir / Path(req.dataset).name).resolve()
            if candidate.parent != datasets_dir or not candidate.exists():
                raise HTTPException(status_code=400, detail="Unknown dataset")
            dataset_path = str(candidate)
        else:
            dataset_path = None
        try:
            from eval.run_eval import run_evaluation
            metrics = await run_evaluation(
                vertical_name=req.vertical,
                dataset_path=dataset_path,
            )
            return {"status": "ok", "metrics": metrics}
        except Exception as exc:  # noqa: BLE001
            logger.exception("Eval failed")
            raise HTTPException(status_code=500, detail="Eval run failed; see server logs") from exc

    # ── global exception handler ────────────────────────────────────
    @app.exception_handler(Exception)
    async def global_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"detail": f"{type(exc).__name__}: {exc}"},
        )

    logger.info(
        "App created — default_vertical=%s mode=%s version=%s",
        default_vertical, mode, __version__,
    )
    return app


# ─────────────────────────────────────────────────────────────────────
# Chat runner (SSE generator)
# ─────────────────────────────────────────────────────────────────────

async def _run_chat(
    req: ChatRequest,
    vertical: dict,
    vertical_name: str,
    mode: str,
) -> AsyncGenerator[str, None]:
    """Run a single chat request, yielding SSE events."""
    t_start = time.time()

    try:
        # Emit thread event up-front
        yield thread_event(req.session_id)

        # Build initial state
        state = initial_state(
            session_id=req.session_id,
            customer_id=req.customer_id,
            user_message=req.message,
            vertical_name=vertical_name,
            mode=mode,
        )

        # Compile graph (verticals expose `build_graph` callable)
        compile_graph = vertical["build_graph"]
        graph = compile_graph()

        # Thread-scoped config keeps MemorySaver state consistent within a session
        # and is required for interrupt_before / HITL resumption to work correctly.
        graph_config = {"configurable": {"thread_id": req.session_id}}

        # Stream LangGraph events
        token_count = 0
        async for event in graph.astream_events(state, graph_config, version="v2"):
            ev_type = event.get("event", "")

            # Triage classification surfaced
            if ev_type == "on_chain_end" and event.get("name") == "triage":
                output = event.get("data", {}).get("output", {})
                if isinstance(output, dict) and output.get("intent"):
                    yield triage_event(
                        intent=output["intent"],
                        confidence=output.get("confidence", 0.0),
                        urgency=output.get("urgency", "low"),
                    )

            # Resolver tool usage surfaced: one tool_call + tool_result pair per
            # invocation, in call order (the resolver records these on state).
            elif ev_type == "on_chain_end" and event.get("name") == "resolver":
                output = event.get("data", {}).get("output", {})
                if isinstance(output, dict):
                    for inv in output.get("tool_invocations", []) or []:
                        name = inv.get("name", "unknown")
                        yield tool_call_event(name, inv.get("arguments", {}) or {})
                        yield tool_result_event(name, inv.get("result"))

            # Streaming tokens: real mode uses LangChain ChatModel → on_chat_model_stream.
            # Mock mode: emit tokens from supervisor output when it finalises the response.
            elif ev_type == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                content = getattr(chunk, "content", "") if chunk else ""
                if content:
                    yield token_event(content)
                    token_count += 1

            elif ev_type == "on_chain_end" and event.get("name") == "supervisor" and mode == "mock":
                # Mock LLM doesn't emit on_chat_model_stream — simulate streaming from the
                # approved draft so the frontend sees something moving.
                if token_count == 0:
                    output = event.get("data", {}).get("output", {})
                    text = (output or {}).get("final_response") or (output or {}).get("draft_response", "")
                    if text:
                        words = text.split()
                        for i in range(0, len(words), 4):
                            chunk = " ".join(words[i : i + 4])
                            if i + 4 < len(words):
                                chunk += " "
                            yield token_event(chunk)
                            token_count += 1

        # Human escalation: `interrupt_before=["human_escalation"]` pauses the
        # graph *before* that node starts, so no node event ever fires for it.
        # Detect the pause from the checkpoint snapshot instead.
        snapshot = await graph.aget_state(graph_config)
        if snapshot.next and "human_escalation" in snapshot.next:
            values = snapshot.values or {}
            _PENDING_HUMAN[req.session_id] = {
                "customer_id": req.customer_id,
                "vertical_name": vertical_name,
                "intent": values.get("intent", "unknown"),
                "awaiting_since": time.strftime("%Y-%m-%d %H:%M:%S"),
                "summary": req.message[:200],
            }
            yield sse_event("human_escalation", {
                "session_id": req.session_id,
                "reason": "policy_triggered",
                "draft_quality": values.get("quality_score", 0.0),
            })

        latency_ms = int((time.time() - t_start) * 1000)
        yield done_event(latency_ms=latency_ms, tokens=token_count, mode=mode)

    except Exception as exc:  # noqa: BLE001
        logger.exception("Chat stream error")
        yield error_event(str(exc))
        yield done_event(
            latency_ms=int((time.time() - t_start) * 1000),
            tokens=0,
            mode=mode,
        )


__all__ = ["create_app"]
