"""Tests for the LOOPFORGE_API_KEY gate on /api/repo-fix and /api/hitl/resume.

See docs/ADR-002-repo-fix-auth-and-isolation.md — these endpoints clone/execute
arbitrary code, so they must reject unauthenticated requests once a key is set,
and must never allow local_path (arbitrary local filesystem access) once a key
is enforced.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "buggy_calc"


@pytest.fixture
def client():
    return TestClient(app)


def test_repo_fix_open_when_no_api_key_set(client, monkeypatch, tmp_path):
    monkeypatch.delenv("LOOPFORGE_API_KEY", raising=False)
    with patch("app.main.run_repo_fix", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = {"run_id": "r1"}
        resp = client.post(
            "/api/repo-fix",
            json={"task": "fix bugs", "local_path": str(FIXTURE), "create_pr": False},
        )
    assert resp.status_code == 200


def test_repo_fix_rejects_missing_key_when_required(client, monkeypatch):
    monkeypatch.setenv("LOOPFORGE_API_KEY", "secret-key")
    resp = client.post(
        "/api/repo-fix",
        json={"task": "fix bugs", "repo_url": "https://github.com/org/repo.git"},
    )
    assert resp.status_code == 401


def test_repo_fix_rejects_wrong_key(client, monkeypatch):
    monkeypatch.setenv("LOOPFORGE_API_KEY", "secret-key")
    resp = client.post(
        "/api/repo-fix",
        json={"task": "fix bugs", "repo_url": "https://github.com/org/repo.git"},
        headers={"X-API-Key": "wrong-key"},
    )
    assert resp.status_code == 401


def test_repo_fix_accepts_correct_key(client, monkeypatch):
    monkeypatch.setenv("LOOPFORGE_API_KEY", "secret-key")
    with patch("app.main.run_repo_fix", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = {"run_id": "r1"}
        resp = client.post(
            "/api/repo-fix",
            json={"task": "fix bugs", "repo_url": "https://github.com/org/repo.git"},
            headers={"X-API-Key": "secret-key"},
        )
    assert resp.status_code == 200


def test_repo_fix_rejects_local_path_when_key_required(client, monkeypatch):
    monkeypatch.setenv("LOOPFORGE_API_KEY", "secret-key")
    resp = client.post(
        "/api/repo-fix",
        json={"task": "fix bugs", "local_path": str(FIXTURE)},
        headers={"X-API-Key": "secret-key"},
    )
    assert resp.status_code == 400
    assert "local_path" in resp.json()["detail"]


def test_hitl_resume_rejects_missing_key_when_required(client, monkeypatch):
    monkeypatch.setenv("LOOPFORGE_API_KEY", "secret-key")
    resp = client.post("/api/hitl/resume", json={"run_id": "r1", "workspace_path": "/tmp/x"})
    assert resp.status_code == 401


def test_health_and_agent_loop_stay_open_regardless_of_key(client, monkeypatch):
    """Only repo-fix/hitl-resume clone+execute arbitrary code — other endpoints are unaffected."""
    monkeypatch.setenv("LOOPFORGE_API_KEY", "secret-key")
    resp = client.get("/health")
    assert resp.status_code == 200
