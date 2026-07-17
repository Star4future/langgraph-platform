"""Checkpointer selection: durable when configured, safe when not."""
import logging

from langgraph.checkpoint.memory import MemorySaver

from core.checkpointing import build_checkpointer


def test_defaults_to_memory_saver(monkeypatch):
    monkeypatch.delenv("CHECKPOINT_DATABASE_URL", raising=False)
    assert isinstance(build_checkpointer(), MemorySaver)


def test_blank_url_defaults_to_memory_saver(monkeypatch):
    monkeypatch.setenv("CHECKPOINT_DATABASE_URL", "   ")
    assert isinstance(build_checkpointer(), MemorySaver)


def test_unreachable_postgres_falls_back_not_crashes(monkeypatch, caplog):
    # A dead checkpointer must not become a dead API: bad URL → warn + memory.
    monkeypatch.setenv(
        "CHECKPOINT_DATABASE_URL",
        "postgresql://user:pw@127.0.0.1:1/nope?connect_timeout=1",
    )
    with caplog.at_level(logging.WARNING):
        saver = build_checkpointer()
    assert isinstance(saver, MemorySaver)
    assert any("falling back" in r.message for r in caplog.records)
