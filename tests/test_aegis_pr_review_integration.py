"""aegis-pr-review CLI integration for repo_review_node."""

from __future__ import annotations

from unittest.mock import patch

from loop_engine.integrations.aegis_pr_review import report_to_review_fields
from loop_engine.graph.repo_nodes import repo_review_node
from loop_engine.models.llm import MockLLM
from loop_engine.workspace.manager import WorkspaceManager


def test_report_to_review_fields_critical_lowers_score():
    fields = report_to_review_fields(
        {
            "findings": [
                {
                    "severity": "critical",
                    "path": "api.py",
                    "line": 3,
                    "title": "Open route",
                    "why": "no auth",
                    "fix_hint": "add Depends",
                    "rule_id": "open-mutating-route",
                }
            ],
            "summary": "1 critical",
            "llm_mode": "stub",
        }
    )
    assert fields["review_score"] < 0.5
    assert fields["review_issues"][0]["type"] == "security"


def test_repo_review_uses_aegis_when_available(tmp_path):
    fixture = tmp_path / "repo"
    fixture.mkdir()
    (fixture / "x.py").write_text("x = 1\n", encoding="utf-8")
    ws = WorkspaceManager(root=fixture)

    fake = {
        "findings": [],
        "summary": "clean",
        "llm_mode": "stub",
    }
    with patch(
        "loop_engine.integrations.aegis_pr_review.run_aegis_pr_review",
        return_value=fake,
    ):
        out = repo_review_node({"task": "t", "trace_events": []}, MockLLM(), ws)
    assert out["review_score"] == 0.88
    assert out["aegis_pr_review"]["finding_count"] == 0
