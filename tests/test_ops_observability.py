"""Ops/observability honesty for LoopForge public metrics."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app


def test_ops_metrics_exposes_trace_planes(monkeypatch):
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    monkeypatch.setenv("PRODUCTION_STRICT", "true")
    monkeypatch.delenv("LOOPFORGE_API_KEY", raising=False)
    client = TestClient(app)
    resp = client.get("/api/v1/ops/metrics")
    assert resp.status_code == 200
    extra = resp.json()["extra"]
    assert "odaeu-harness" in extra["graphs"]
    assert extra["langfuse"]["configured"] is False
    assert extra["sandbox"]["required"] is True
    assert extra["sandbox"]["production_strict"] is True
    assert extra["trace_store"] == "in_memory"


def test_observability_status_lists_exporters(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")
    client = TestClient(app)
    resp = client.get("/api/observability/status")
    assert resp.status_code == 200
    body = resp.json()
    assert "LoopForge" in body["source_of_truth"]
    names = {e["name"] for e in body["exporters"]}
    assert names == {"Langfuse", "HarnessTrace"}
    assert body["planes"]["langfuse"]["configured"] is True


def test_health_includes_sandbox_and_langfuse(monkeypatch):
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    monkeypatch.setenv("SANDBOX_REQUIRED", "true")
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["sandbox_required"] is True
    assert body["langfuse_configured"] is False
