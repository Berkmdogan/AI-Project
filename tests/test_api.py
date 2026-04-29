"""FastAPI endpoint testleri (mock'larla)."""
import os

import pytest
from unittest.mock import MagicMock, patch

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("FAISS_INDEX_PATH", str(tmp_path / "test.index"))
    monkeypatch.setenv("EVENTS_METADATA_PATH", str(tmp_path / "meta.json"))
    monkeypatch.setenv("FRAMES_DIR", str(tmp_path / "frames"))
    monkeypatch.setenv("EVENTS_DIR", str(tmp_path / "events"))

    from api.main import app
    return TestClient(app)


def test_health(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_stats(client):
    resp = client.get("/api/v1/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_events" in data


def test_list_events_empty(client):
    resp = client.get("/api/v1/events")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_query_no_events(client, monkeypatch):
    """Olay yokken sorgu yaptığında anlamlı yanıt döner."""
    resp = client.post("/api/v1/query", json={"question": "kırmızı araç geldi mi?"})
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
