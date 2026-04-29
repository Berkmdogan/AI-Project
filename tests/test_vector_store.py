"""VectorStore temel testleri."""
import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_store(tmp_path, monkeypatch):
    """Geçici dizinde sıfır kayıtlı bir VectorStore döndürür."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("FAISS_INDEX_PATH", str(tmp_path / "test.index"))
    monkeypatch.setenv("EVENTS_METADATA_PATH", str(tmp_path / "meta.json"))

    from rag_engine.vector_store import VectorStore
    return VectorStore()


def test_add_and_search(temp_store):
    vs = temp_store
    vs.add_event("09:15 - kırmızı araç tespit", {"timestamp": 1000, "frame_path": "a.jpg"})
    vs.add_event("10:30 - mavi kamyon tespit", {"timestamp": 2000, "frame_path": "b.jpg"})

    results = vs.search("kırmızı araç", top_k=5, min_score=0.0)
    assert len(results) >= 1
    assert any("kırmızı" in r["text"] for r in results)


def test_empty_search(temp_store):
    results = temp_store.search("herhangi bir şey", top_k=5, min_score=0.0)
    assert results == []


def test_reset(temp_store):
    vs = temp_store
    vs.add_event("test olay", {"timestamp": 1})
    assert vs.total_events == 1
    vs.reset()
    assert vs.total_events == 0


def test_batch_add(temp_store):
    vs = temp_store
    texts = ["olay 1", "olay 2", "olay 3"]
    metas = [{"timestamp": i} for i in range(3)]
    indices = vs.add_events_batch(texts, metas)
    assert len(indices) == 3
    assert vs.total_events == 3
