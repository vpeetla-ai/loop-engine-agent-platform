from __future__ import annotations

import json
import re
from typing import Any

from loop_engine.graph.nodes import (
    hitl_node,
    memory_retrieve_node,
    memory_write_node,
    orchestrator_node,
    review_agent_node,
    self_improve_node,
)
from loop_engine.graph.routing import append_event
from loop_engine.graph.state import DEFAULT_REPO_CODING_PROMPT, AgentLoopState
from loop_engine.models.llm import LLM
from loop_engine.workspace.manager import WorkspaceManager


def workspace_init_node(
    state: AgentLoopState,
    workspace: WorkspaceManager,
) -> dict[str, Any]:
    files = workspace.list_files("**/*.py")[:30]
    events = append_event(
        state,
        "observe",
        "workspace.ready",
        path=str(workspace.root),
        file_count=len(files),
        files=files[:10],
    )
    return {
        "workspace_path": str(workspace.root),
        "trace_events": events,
    }


def repo_scan_node(state: AgentLoopState, workspace: WorkspaceManager) -> dict[str, Any]:
    """Run project tests to capture baseline failures."""
    passed, coverage, report = workspace.run_pytest()
    failing = report.get("stdout", "") + report.get("stderr", "")
    events = append_event(
        state,
        "observe",
        "repo.scan",
        tests_passed=passed,
        coverage_pct=coverage,
        preview=failing[-500:],
    )
    return {
        "failing_tests": failing[-3000:],
        "test_passed": passed,
        "coverage_pct": coverage,
        "quality_report": report,
        "trace_events": events,
        "status": "passed" if passed and state.get("mode") == "bugfix" else "running",
    }


def _parse_patches(raw: str) -> tuple[list[dict[str, str]], str]:
    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        return [], raw[:200]
    try:
        data = json.loads(match.group())
        patches = list(data.get("patches") or [])
        summary = str(data.get("summary") or "")
        return patches, summary
    except json.JSONDecodeError:
        return [], raw[:200]


def repo_coding_node(state: AgentLoopState, llm: LLM, workspace: WorkspaceManager) -> dict[str, Any]:
    prompt = state.get("active_prompt") or ""
    system = DEFAULT_REPO_CODING_PROMPT if "repo coding agent" not in prompt.lower() else prompt
    py_files = workspace.list_files("**/*.py")
    context_parts: list[str] = []
    for rel in py_files[:12]:
        context_parts.append(f"--- {rel} ---\n{workspace.read_file(rel)[:3000]}")

    user = (
        f"TASK: {state['task']}\n"
        f"MODE: {state.get('mode', 'bugfix')}\n"
        f"PLAN:\n{state.get('plan', '')}\n"
        f"FAILING TESTS:\n{state.get('failing_tests', '')}\n"
        f"REVIEW ISSUES:\n{json.dumps(state.get('review_issues') or [])}\n"
        f"FILES:\n{''.join(context_parts)}\n"
    )

    raw = llm.complete(system, user)
    patches, summary = _parse_patches(raw)

    applied: list[dict[str, str]] = []
    for patch in patches:
        path = patch.get("path", "")
        content = patch.get("content", "")
        if path and content:
            workspace.write_file(path, content)
            applied.append({"path": path, "summary": summary})

    diff = workspace.diff()
    events = append_event(
        state,
        "act",
        "repo.apply_patches",
        patch_count=len(applied),
        paths=[p["path"] for p in applied],
        summary=summary[:300],
    )
    return {
        "patches": applied,
        "code_diff": diff[-4000:],
        "generated_code": diff,
        "trace_events": events,
    }


def repo_quality_node(state: AgentLoopState, workspace: WorkspaceManager) -> dict[str, Any]:
    passed, coverage, report = workspace.run_pytest()
    events = append_event(
        state,
        "evaluate",
        "repo.quality",
        test_passed=passed,
        coverage_pct=coverage,
        report_preview=str(report)[:500],
    )
    return {
        "test_passed": passed,
        "coverage_pct": coverage,
        "quality_report": report,
        "failing_tests": (report.get("stdout", "") + report.get("stderr", ""))[-3000:],
        "trace_events": events,
    }


def repo_review_node(state: AgentLoopState, llm: LLM) -> dict[str, Any]:
    """Review uses diff instead of generated code blocks."""
    state_copy = dict(state)
    state_copy["generated_code"] = state.get("code_diff") or state.get("generated_code") or ""
    state_copy["generated_tests"] = state.get("failing_tests") or ""
    return review_agent_node(state_copy, llm)  # type: ignore[arg-type]


def git_branch_node(state: AgentLoopState, workspace: WorkspaceManager) -> dict[str, Any]:
    run_id = state.get("run_id") or "run"
    result = workspace.create_fix_branch(run_id)
    events = append_event(state, "act", "git.branch", **result)
    return {
        "pr_branch": result.get("branch", ""),
        "trace_events": events,
        "status": "branch_ready" if result.get("status") == "created" else state.get("status", "running"),
    }


def git_commit_node(state: AgentLoopState, workspace: WorkspaceManager) -> dict[str, Any]:
    summary = (state.get("patches") or [{}])[0]
    msg = f"fix(loopforge): {summary.get('summary', state['task'])[:72]}"
    try:
        sha = workspace.commit(msg)
    except RuntimeError as exc:
        events = append_event(state, "act", "git.commit_failed", error=str(exc))
        return {"trace_events": events, "status": "failed", "git_commit_sha": ""}

    events = append_event(state, "act", "git.commit", sha=sha, message=msg)
    return {"git_commit_sha": sha, "trace_events": events, "status": "committed"}


def git_pr_node(
    state: AgentLoopState,
    workspace: WorkspaceManager,
    token: str | None,
) -> dict[str, Any]:
    create_pr = state.get("create_pr", state.get("auto_push", False))
    fix_branch = state.get("pr_branch") or f"loopforge/fix-{state.get('run_id', 'run')[:12]}"

    if not create_pr:
        events = append_event(state, "act", "git.pr_skipped", reason="create_pr_disabled")
        return {
            "push_status": {"status": "skipped", "reason": "create_pr_disabled"},
            "trace_events": events,
            "status": "committed",
        }

    if not token:
        events = append_event(state, "act", "git.pr_skipped", reason="no_github_token")
        return {
            "push_status": {"status": "skipped", "reason": "no_github_token"},
            "trace_events": events,
            "status": "committed",
        }

    push_result = workspace.push_branch(fix_branch, token=token)
    if push_result.get("status") != "pushed":
        events = append_event(state, "act", "git.push_branch", **push_result)
        return {"push_status": push_result, "trace_events": events, "status": "push_failed"}

    summary = (state.get("patches") or [{}])[0].get("summary", state["task"])
    title = f"fix(loopforge): {summary[:60]}"
    body = (
        f"## LoopForge automated fix\n\n"
        f"**Task:** {state['task']}\n\n"
        f"**Run ID:** `{state.get('run_id')}`\n\n"
        f"**Review score:** {state.get('review_score')}\n\n"
        f"**Tests:** {'PASS' if state.get('test_passed') else 'FAIL'}\n\n"
        f"---\n_Auto-generated by [LoopForge](https://github.com/vpeetla-ai/loop-engine-agent-platform)_"
    )
    pr_result = workspace.open_pull_request(
        token=token,
        fix_branch=fix_branch,
        title=title,
        body=body,
    )
    events = append_event(state, "act", "git.pull_request", **push_result, **pr_result)
    status = "pr_created" if pr_result.get("status") == "created" else "pushed"
    return {
        "push_status": push_result,
        "pr_url": pr_result.get("pr_url", ""),
        "pr_number": pr_result.get("pr_number", 0),
        "pr_branch": fix_branch,
        "trace_events": events,
        "status": status,
    }


# Backward compat alias
git_push_node = git_pr_node
