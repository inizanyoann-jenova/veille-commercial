import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


def test_collect_status_unknown_job(client):
    r = client.get("/api/collect/status/nonexistent-id")
    assert r.status_code == 404
    assert r.json()["detail"] == "Job inconnu"


def test_collect_status_known_job(client):
    from main import _COLLECT_JOBS
    _COLLECT_JOBS["test-job-123"] = {
        "status": "done",
        "results": [{"source": "boamp", "status": "ok", "nb_found": 5, "nb_new": 2}],
    }
    r = client.get("/api/collect/status/test-job-123")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "done"
    assert len(data["results"]) == 1
    assert data["results"][0]["nb_new"] == 2
    del _COLLECT_JOBS["test-job-123"]


def test_collect_returns_202_and_job_id(client, monkeypatch):
    """POST /api/collect retourne 202 avec job_id même si aucune source disponible."""
    # Patcher list_sources pour retourner une liste vide (évite les vrais scrapers)
    import main as _main
    monkeypatch.setattr(_main, "list_sources", lambda db: [])

    r = client.post("/api/collect", json={})
    # Le job démarre quand même (retourne 202 immédiatement)
    assert r.status_code == 202
    data = r.json()
    assert "job_id" in data
    assert data["status"] == "running"
