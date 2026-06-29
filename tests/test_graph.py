import asyncio
from pathlib import Path

import pytest

from loop_engine.graph.build import run_agent_loop
from loop_engine.graph.routing import route_after_quality
from loop_engine.models.llm import MockLLM


def test_route_pass_when_score_coverage_and_tests_ok():
    state = {
        "review_score": 0.9,
        "test_passed": True,
        "coverage_pct": 85.0,
        "iteration": 1,
        "max_iterations": 5,
        "review_issues": [],
    }
    assert route_after_quality(state) == "pass"


def test_route_escalate_on_security_issue():
    state = {
        "review_score": 0.9,
        "test_passed": True,
        "coverage_pct": 90.0,
        "iteration": 1,
        "max_iterations": 5,
        "review_issues": [{"type": "security", "severity": "high"}],
    }
    assert route_after_quality(state) == "escalate"


def test_route_retry_when_quality_fails():
    state = {
        "review_score": 0.6,
        "test_passed": False,
        "coverage_pct": 40.0,
        "iteration": 1,
        "max_iterations": 5,
        "review_issues": [],
    }
    assert route_after_quality(state) == "retry"


@pytest.mark.asyncio
async def test_agent_loop_passes_with_mock_llm(tmp_path):
    root = Path(__file__).resolve().parents[1]
    result = await run_agent_loop(
        "Write a function that doubles an integer",
        llm=MockLLM(),
        corpus_dir=root / "corpus",
        memory_dir=tmp_path / "agent_memory",
        max_iterations=3,
    )
    assert result["status"] == "passed"
    assert result["review_score"] >= 0.85
    assert result["test_passed"] is True
    assert len(result["trace"]["events"]) >= 5
    phases = {e["phase"] for e in result["trace"]["events"]}
    assert "decide" in phases
    assert "act" in phases
    assert "evaluate" in phases
