import pytest
from pathlib import Path
from unittest.mock import patch

from loop_engine.graph.repo_build import run_repo_fix
from loop_engine.models.llm import MockLLM
from loop_engine.workspace import git_ops
from loop_engine.workspace.manager import WorkspaceManager


@pytest.mark.asyncio
async def test_repo_fix_fixes_buggy_calc(tmp_path):
    fixture = Path(__file__).resolve().parent / "fixtures" / "buggy_calc"
    result = await run_repo_fix(
        "Find and fix bugs in this repo",
        local_path=fixture,
        mode="bugfix",
        create_pr=False,
        llm=MockLLM(),
        memory_dir=tmp_path / "memory",
        work_root=tmp_path / "workspaces",
        max_iterations=3,
    )
    assert result["test_passed"] is True
    assert result["git_commit_sha"]
    assert result["git_commit_sha"] != "no_changes"
    assert result["pr_branch"].startswith("loopforge/fix-")
    assert any(p.get("path") == "calc.py" for p in (result.get("patches") or []))


def test_workspace_pytest_detects_bug(tmp_path):
    fixture = Path(__file__).resolve().parent / "fixtures" / "buggy_calc"
    ws = WorkspaceManager.prepare(tmp_path / "ws", local_path=fixture, run_id="t1")
    passed, _, _ = ws.run_pytest()
    assert passed is False
    ws.cleanup()


def test_workspace_write_and_test_pass(tmp_path):
    fixture = Path(__file__).resolve().parent / "fixtures" / "buggy_calc"
    ws = WorkspaceManager.prepare(tmp_path / "ws", local_path=fixture, run_id="t2")
    ws.write_file(
        "calc.py",
        '"""Simple calculator module."""\n\n\ndef add(a: int, b: int) -> int:\n    return a + b\n',
    )
    passed, coverage, _ = ws.run_pytest()
    assert passed is True
    assert coverage >= 80
    ws.cleanup()


def test_parse_github_repo():
    assert git_ops.parse_github_repo("https://github.com/org/repo.git") == ("org", "repo")
    assert git_ops.parse_github_repo("git@github.com:org/repo.git") == ("org", "repo")


def test_create_fix_branch(tmp_path):
    fixture = Path(__file__).resolve().parent / "fixtures" / "buggy_calc"
    ws = WorkspaceManager.prepare(tmp_path / "ws", local_path=fixture, run_id="t3")
    result = ws.create_fix_branch("abc123")
    assert result["status"] == "created"
    assert result["branch"] == "loopforge/fix-abc123"
    ws.cleanup()


@patch("loop_engine.workspace.git_ops.create_pull_request")
def test_open_pull_request(mock_pr, tmp_path):
    mock_pr.return_value = {"status": "created", "pr_url": "https://github.com/o/r/pull/1", "pr_number": 1}
    fixture = Path(__file__).resolve().parent / "fixtures" / "buggy_calc"
    dest = tmp_path / "remote"
    git_ops.copy_local_repo(fixture, dest, remote_url="https://github.com/org/repo.git")
    ws = WorkspaceManager(root=dest, branch="main")
    pr = ws.open_pull_request(
        token="test-token",
        fix_branch="loopforge/fix-x",
        title="fix: test",
        body="body",
    )
    assert pr["status"] == "created"
    assert pr["pr_url"].endswith("/pull/1")
    mock_pr.assert_called_once()
