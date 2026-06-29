from __future__ import annotations

import re
from typing import Any

from loop_engine.graph.state import (
    PASS_COVERAGE_THRESHOLD,
    PASS_SCORE_THRESHOLD,
    AgentLoopState,
)


def _event(phase: str, name: str, **payload: Any) -> dict[str, Any]:
    return {"phase": phase, "name": name, "payload": payload}


def append_event(state: AgentLoopState, phase: str, name: str, **payload: Any) -> list[dict[str, Any]]:
    events = list(state.get("trace_events") or [])
    events.append(_event(phase, name, **payload))
    return events


def route_after_quality(state: AgentLoopState) -> str:
    score = float(state.get("review_score") or 0.0)
    passed = bool(state.get("test_passed"))
    coverage = float(state.get("coverage_pct") or 0.0)
    iteration = int(state.get("iteration") or 0)
    max_iterations = int(state.get("max_iterations") or 5)

    issues = state.get("review_issues") or []
    if any(i.get("type") == "security" for i in issues):
        return "escalate"

    if iteration >= max_iterations:
        return "escalate"

    if score >= PASS_SCORE_THRESHOLD and passed and coverage >= PASS_COVERAGE_THRESHOLD:
        return "pass"

    return "retry"


def extract_code_blocks(text: str) -> tuple[str, str]:
    """Parse ```python blocks — first = implementation, second = tests."""
    blocks = re.findall(r"```(?:python)?\s*([\s\S]*?)```", text, flags=re.IGNORECASE)
    code = blocks[0].strip() if blocks else text.strip()
    tests = blocks[1].strip() if len(blocks) > 1 else ""
    return code, tests
