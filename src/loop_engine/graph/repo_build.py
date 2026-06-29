from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any, Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from loop_engine.graph.nodes import hitl_node, memory_retrieve_node, memory_write_node, orchestrator_node, self_improve_node
from loop_engine.graph.repo_nodes import (
    git_branch_node,
    git_commit_node,
    git_pr_node,
    repo_coding_node,
    repo_quality_node,
    repo_review_node,
    repo_scan_node,
    workspace_init_node,
)
from loop_engine.graph.routing import route_after_quality
from loop_engine.graph.state import MAX_ITERATIONS_DEFAULT, AgentLoopState, DEFAULT_REPO_CODING_PROMPT
from loop_engine.memory.store import MemoryStore
from loop_engine.models.llm import LLM, MockLLM
from loop_engine.workspace.manager import WorkspaceManager

def build_repo_fix_graph(
    workspace: WorkspaceManager,
    llm: LLM | None = None,
    memory_dir: Path | None = None,
):
    root = Path(__file__).resolve().parents[3]
    memory_path = memory_dir or root / "data" / "memory"
    model = llm or MockLLM()
    memory = MemoryStore(memory_path)
    github_token = os.getenv("GITHUB_TOKEN")

    def _memory_hints(task: str) -> tuple[str, list[str]]:
        hints = memory.hints_for_query(task)
        anti = [l.lesson for l in memory.lessons if l.failure_mode != "success"][-5:]
        return hints, anti

    async def n_workspace(state: AgentLoopState) -> dict[str, Any]:
        return workspace_init_node(state, workspace)

    async def n_scan(state: AgentLoopState) -> dict[str, Any]:
        return repo_scan_node(state, workspace)

    async def n_orchestrate(state: AgentLoopState) -> dict[str, Any]:
        return orchestrator_node(state, model)

    async def n_memory_retrieve(state: AgentLoopState) -> dict[str, Any]:
        hints, anti = _memory_hints(state["task"])
        return memory_retrieve_node(state, hints, anti)

    async def n_code(state: AgentLoopState) -> dict[str, Any]:
        return repo_coding_node(state, model, workspace)

    async def n_review(state: AgentLoopState) -> dict[str, Any]:
        return repo_review_node(state, model)

    async def n_quality(state: AgentLoopState) -> dict[str, Any]:
        return repo_quality_node(state, workspace)

    async def n_branch(state: AgentLoopState) -> dict[str, Any]:
        return git_branch_node(state, workspace)

    async def n_commit(state: AgentLoopState) -> dict[str, Any]:
        return git_commit_node(state, workspace)

    async def n_pr(state: AgentLoopState) -> dict[str, Any]:
        return git_pr_node(state, workspace, github_token)

    async def n_memory_write(state: AgentLoopState) -> dict[str, Any]:
        return memory_write_node(state, memory)

    async def n_self_improve(state: AgentLoopState) -> dict[str, Any]:
        return self_improve_node(state, model, memory)

    async def n_hitl(state: AgentLoopState) -> dict[str, Any]:
        return hitl_node(state)

    builder = StateGraph(AgentLoopState)
    builder.add_node("workspace", n_workspace)
    builder.add_node("scan", n_scan)
    builder.add_node("orchestrate", n_orchestrate)
    builder.add_node("memory_retrieve", n_memory_retrieve)
    builder.add_node("code", n_code)
    builder.add_node("review", n_review)
    builder.add_node("quality", n_quality)
    builder.add_node("git_branch", n_branch)
    builder.add_node("git_commit", n_commit)
    builder.add_node("git_pr", n_pr)
    builder.add_node("memory_write", n_memory_write)
    builder.add_node("self_improve", n_self_improve)
    builder.add_node("hitl", n_hitl)

    builder.add_edge(START, "workspace")
    builder.add_edge("workspace", "scan")

    def route_after_scan(state: AgentLoopState) -> str:
        if state.get("mode") == "bugfix" and state.get("test_passed"):
            return "already_fixed"
        return "fix"

    builder.add_conditional_edges(
        "scan",
        route_after_scan,
        {"already_fixed": "git_branch", "fix": "orchestrate"},
    )

    builder.add_edge("orchestrate", "memory_retrieve")
    builder.add_edge("memory_retrieve", "code")
    builder.add_edge("code", "review")
    builder.add_edge("review", "quality")
    builder.add_conditional_edges(
        "quality",
        route_after_quality,
        {"retry": "orchestrate", "escalate": "hitl", "pass": "git_branch"},
    )
    builder.add_edge("git_branch", "git_commit")
    builder.add_edge("git_commit", "git_pr")
    builder.add_edge("git_pr", "memory_write")
    builder.add_edge("memory_write", "self_improve")
    builder.add_edge("self_improve", END)
    builder.add_edge("hitl", END)

    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer, interrupt_before=["hitl"])


async def run_repo_fix(
    task: str,
    *,
    repo_url: str | None = None,
    local_path: Path | None = None,
    branch: str = "main",
    mode: Literal["bugfix", "feature"] = "bugfix",
    create_pr: bool = True,
    auto_push: bool | None = None,
    llm: LLM | None = None,
    memory_dir: Path | None = None,
    work_root: Path | None = None,
    max_iterations: int = MAX_ITERATIONS_DEFAULT,
    thread_id: str | None = None,
) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[3]
    runs_dir = work_root or root / "data" / "workspaces"
    runs_dir.mkdir(parents=True, exist_ok=True)
    run_id = thread_id or uuid.uuid4().hex[:12]

    workspace = WorkspaceManager.prepare(
        runs_dir,
        repo_url=repo_url,
        local_path=local_path,
        branch=branch,
        run_id=run_id,
    )

    graph = build_repo_fix_graph(workspace, llm=llm, memory_dir=memory_dir)
    config = {"configurable": {"thread_id": run_id}}

    submit_pr = create_pr if auto_push is None else (create_pr or auto_push)

    initial: AgentLoopState = {
        "task": task,
        "spec": {},
        "run_id": run_id,
        "iteration": 0,
        "max_iterations": max_iterations,
        "active_prompt": DEFAULT_REPO_CODING_PROMPT,
        "trace_events": [],
        "prompt_version": 1,
        "status": "running",
        "repo_url": repo_url or str(local_path or ""),
        "branch": branch,
        "mode": mode,
        "create_pr": submit_pr,
        "auto_push": submit_pr,
        "patches": [],
    }

    try:
        final = await graph.ainvoke(initial, config=config)
    except Exception:
        workspace.cleanup()
        raise

    return {
        "run_id": run_id,
        "task": task,
        "repo_url": repo_url,
        "branch": branch,
        "mode": mode,
        "status": final.get("status", "running"),
        "iteration": final.get("iteration"),
        "review_score": final.get("review_score"),
        "test_passed": final.get("test_passed"),
        "coverage_pct": final.get("coverage_pct"),
        "workspace_path": final.get("workspace_path"),
        "code_diff": final.get("code_diff"),
        "patches": final.get("patches"),
        "git_commit_sha": final.get("git_commit_sha"),
        "push_status": final.get("push_status"),
        "pr_branch": final.get("pr_branch"),
        "pr_url": final.get("pr_url"),
        "pr_number": final.get("pr_number"),
        "plan": final.get("plan"),
        "trace": {"run_id": run_id, "events": final.get("trace_events") or []},
    }


async def resume_repo_fix(
    run_id: str,
    *,
    approve_push: bool = False,
    workspace_path: str | None = None,
    llm: LLM | None = None,
    memory_dir: Path | None = None,
) -> dict[str, Any]:
    """Resume after HITL or before git_push when auto_push requires approval."""
    if not workspace_path:
        raise ValueError("workspace_path required to resume")
    workspace = WorkspaceManager(root=Path(workspace_path))
    graph = build_repo_fix_graph(workspace, llm=llm, memory_dir=memory_dir)
    config = {"configurable": {"thread_id": run_id}}

    update: AgentLoopState = {
        "create_pr": approve_push,
        "auto_push": approve_push,
        "hitl_approved": approve_push,
    }
    final = await graph.ainvoke(update, config=config)
    return {
        "run_id": run_id,
        "status": final.get("status"),
        "push_status": final.get("push_status"),
        "git_commit_sha": final.get("git_commit_sha"),
        "trace": {"run_id": run_id, "events": final.get("trace_events") or []},
    }
