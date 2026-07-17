"""Checkpointer selection for the support graph.

Durable human-in-the-loop needs a checkpointer that survives process
restarts: an interrupted (escalated) thread must be resumable even if the
serving instance that paused it is gone. `MemorySaver` cannot promise that
— it is per-process and dies with the worker.

Policy:
    CHECKPOINT_DATABASE_URL set   → Postgres-backed saver (durable HITL)
    unset                          → MemorySaver (demo / tests / MOCK_MODE)

The Postgres path degrades gracefully: any import or connection failure
logs a warning and falls back to MemorySaver rather than taking the
service down — a dead checkpointer must not become a dead API.

Requires (only for the Postgres path):
    pip install langgraph-checkpoint-postgres "psycopg[binary,pool]"
"""
from __future__ import annotations

import logging
import os
from typing import Any

from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)

_ENV_VAR = "CHECKPOINT_DATABASE_URL"


def build_checkpointer() -> Any:
    """Return the configured checkpointer (Postgres if available, else memory)."""
    url = os.getenv(_ENV_VAR, "").strip()
    if not url:
        logger.info("Checkpointer: MemorySaver (set %s for durable HITL)", _ENV_VAR)
        return MemorySaver()

    try:
        from psycopg_pool import ConnectionPool
        from langgraph.checkpoint.postgres import PostgresSaver

        pool = ConnectionPool(
            conninfo=url,
            max_size=int(os.getenv("CHECKPOINT_POOL_MAX", "5")),
            kwargs={"autocommit": True, "prepare_threshold": 0},
        )
        saver = PostgresSaver(pool)
        saver.setup()  # idempotent: creates checkpoint tables if missing
        logger.info("Checkpointer: PostgresSaver (durable HITL enabled)")
        return saver
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Checkpointer: Postgres unavailable (%s: %s) — falling back to "
            "MemorySaver. Paused threads will NOT survive a restart.",
            type(exc).__name__,
            exc,
        )
        return MemorySaver()


__all__ = ["build_checkpointer"]
