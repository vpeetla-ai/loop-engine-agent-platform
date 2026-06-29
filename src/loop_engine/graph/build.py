from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from loop_engine.graph.nodes import (
    coding_agent_node,
    hitl_node,
    memory_retrieve_node,
    memory_write_node,
    orchestrator_node,
    quality_agent_node,
    review_agent_node,
    self_improve_node,
)
from loop_engine.graph.routing import route_after_quality
from loop_engine.graph.state import MAX_ITERATIONS_DEFAULT, AgentLoopState
from loop_engine.memory.store import MemoryStore
from loop_engine.mcp.bridge import MCPBridge
from loop_engine.models.llm import LLM, MockLLM


def build_agent_loop_graph(
    llm: LLM | None = None,
    corpus_dir: Path | None = None,
    memory_dir: Path | None = None,
):
    root = Path(__file__).resolve().parents[3]
    corpus = corpus_dir or root / "corpus"
    memory_path = memory_dir or root / "data" / "memory"
    model = llm or MockLLM()
    memory = MemoryStore(memory_path)
    mcp = MCPBridge.from_corpus_dir(corpus)

    def _memory_hints(task: str) -> tuple[str, list[str]]:
        hints = memory.hints_for_query(task)
        anti = [l.lesson for l in memory.lessons if l.failure_mode != "success"][-5:]
        return hints, anti

    async def n_orchestrate(state: AgentLoopState) -> dict[str, Any]:
        return orchestrator_node(state, model)

    async def n_memory_retrieve(state: AgentLoopState) -> dict[str, Any]:
        hints, anti = _memory_hints(state["task"])
        return memory_retrieve_node(state, hints, anti)

    async def n_code(state: AgentLoopState) -> dict[str, Any]:
        return coding_agent_node(state, model, lambda q: mcp.call("search_docs", q))

    async def n_review(state: AgentLoopState) -> dict[str, Any]:
        return review_agent_node(state, model)

    async def n_quality(state: AgentLoopState) -> dict[str, Any]:
        return quality_agent_node(state, model)

    async def n_memory_write(state: AgentLoopState) -> dict[str, Any]:
        return memory_write_node(state, memory)

    async def n_self_improve(state: AgentLoopState) -> dict[str, Any]:
        return self_improve_node(state, model, memory)

    async def n_hitl(state: AgentLoopState) -> dict[str, Any]:
        return hitl_node(state)

    builder = StateGraph(AgentLoopState)
    builder.add_node("orchestrate", n_orchestrate)
    builder.add_node("memory_retrieve", n_memory_retrieve)
    builder.add_node("code", n_code)
    builder.add_node("review", n_review)
    builder.add_node("quality", n_quality)
    builder.add_node("memory_write", n_memory_write)
    builder.add_node("self_improve", n_self_improve)
    builder.add_node("hitl", n_hitl)

    builder.add_edge(START, "orchestrate")
    builder.add_edge("orchestrate", "memory_retrieve")
    builder.add_edge("memory_retrieve", "code")
    builder.add_edge("code", "review")
    builder.add_edge("review", "quality")
    builder.add_conditional_edges(
        "quality",
        route_after_quality,
        {
            "retry": "orchestrate",
            "escalate": "hitl",
            "pass": "memory_write",
        },
    )
    builder.add_edge("memory_write", "self_improve")
    builder.add_edge("self_improve", END)
    builder.add_edge("hitl", END)

    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer, interrupt_before=["hitl"])


async def run_agent_loop(
    task: str,
    *,
    llm: LLM | None = None,
    corpus_dir: Path | None = None,
    memory_dir: Path | None = None,
    max_iterations: int = MAX_ITERATIONS_DEFAULT,
    thread_id: str | None = None,
) -> dict[str, Any]:
    graph = build_agent_loop_graph(llm=llm, corpus_dir=corpus_dir, memory_dir=memory_dir)
    run_id = thread_id or uuid.uuid4().hex[:12]
    config = {"configurable": {"thread_id": run_id}}

    initial: AgentLoopState = {
        "task": task,
        "spec": {},
        "run_id": run_id,
        "iteration": 0,
        "max_iterations": max_iterations,
        "active_prompt": "",
        "trace_events": [],
        "prompt_version": 1,
        "status": "running",
    }

    final = await graph.ainvoke(initial, config=config)
    return {
        "run_id": run_id,
        "task": task,
        "status": final.get("status", "running"),
        "iteration": final.get("iteration"),
        "review_score": final.get("review_score"),
        "test_passed": final.get("test_passed"),
        "coverage_pct": final.get("coverage_pct"),
        "generated_code": final.get("generated_code"),
        "generated_tests": final.get("generated_tests"),
        "plan": final.get("plan"),
        "trace": {"run_id": run_id, "events": final.get("trace_events") or []},
    }
