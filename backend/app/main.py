from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from loop_engine.eval.evaluator import BENCHMARK_SUITE
from loop_engine.graph.build import run_agent_loop
from loop_engine.graph.repo_build import resume_repo_fix, run_repo_fix
from loop_engine.harness.agent_harness import AgentHarness
from loop_engine.models.llm import GroqLLM, MockLLM

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "corpus"
MEMORY = ROOT / "data" / "memory"
WORKSPACES = ROOT / "data" / "workspaces"

app = FastAPI(title="LoopForge API", version="0.4.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_TRACES: dict[str, dict] = {}


def _llm():
    key = os.getenv("GROQ_API_KEY")
    if key:
        return GroqLLM(api_key=key)
    return MockLLM()


def _require_api_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    """Gate expensive/code-executing endpoints behind LOOPFORGE_API_KEY.

    /api/repo-fix clones an arbitrary repo_url and runs `python -m pytest`
    against it with no sandboxing — left open with no auth at all, anyone
    could point it at any repo (or, via local_path, any local directory) and
    get the server to execute that code. Unset in dev for demo convenience;
    MUST be set in production (see docs/DEPLOY.md).
    """
    expected = os.getenv("LOOPFORGE_API_KEY")
    if not expected:
        return
    if not x_api_key or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(401, "Invalid or missing X-API-Key")


def _reject_local_path_in_production(local_path: str | None) -> None:
    """local_path lets a caller point at an arbitrary local directory — only
    safe for local dev/testing, never once LOOPFORGE_API_KEY is enforced."""
    if local_path and os.getenv("LOOPFORGE_API_KEY"):
        raise HTTPException(400, "local_path is disabled when LOOPFORGE_API_KEY is set")


def _harness() -> AgentHarness:
    return AgentHarness(llm=_llm(), corpus_dir=CORPUS, memory_dir=MEMORY)


class RunRequest(BaseModel):
    query: str = Field(..., min_length=3)
    gold_keywords: list[str] | None = None


class AgentLoopRequest(BaseModel):
    task: str = Field(..., min_length=3)
    max_iterations: int = Field(default=5, ge=1, le=10)


class RepoFixRequest(BaseModel):
    task: str = Field(..., min_length=3, description="e.g. 'find and fix bugs' or a feature requirement")
    repo_url: str | None = Field(default=None, description="GitHub HTTPS clone URL")
    local_path: str | None = Field(default=None, description="Local path for dev/testing")
    branch: str = Field(default="main")
    mode: Literal["bugfix", "feature"] = "bugfix"
    create_pr: bool = Field(default=True, description="Push fix branch and open a GitHub PR (never pushes to main)")
    auto_push: bool | None = Field(default=None, description="Deprecated alias for create_pr")
    max_iterations: int = Field(default=5, ge=1, le=10)


class HitlResumeRequest(BaseModel):
    run_id: str
    approve_push: bool = False
    workspace_path: str | None = None


@app.get("/health")
def health():
    return {
        "status": "ok",
        "demo_mode": os.getenv("GROQ_API_KEY") is None,
        "github_configured": bool(os.getenv("GITHUB_TOKEN")),
        "graphs": ["odaeu-harness", "langgraph-agent-loop", "repo-fix"],
    }


@app.post("/api/run")
def run_query(body: RunRequest):
    result = _harness().run(body.query, body.gold_keywords)
    payload = result.to_dict()
    _TRACES[result.run_id] = payload
    return payload


@app.post("/api/agent-loop")
async def run_langgraph_loop(body: AgentLoopRequest):
    """LangGraph loop: Orchestrator → Memory → Code → Review → Quality → (retry|HITL|pass)."""
    result = await run_agent_loop(
        body.task,
        llm=_llm(),
        corpus_dir=CORPUS,
        memory_dir=MEMORY,
        max_iterations=body.max_iterations,
    )
    _TRACES[result["run_id"]] = result
    return result


@app.post("/api/repo-fix", dependencies=[Depends(_require_api_key)])
async def run_repo_fix_job(body: RepoFixRequest):
    """Clone repo → scan → fix → review → quality → branch → commit → PR."""
    if not body.repo_url and not body.local_path:
        raise HTTPException(400, "repo_url or local_path required")

    _reject_local_path_in_production(body.local_path)
    local = Path(body.local_path).resolve() if body.local_path else None
    if local and not local.exists():
        raise HTTPException(400, f"local_path not found: {local}")

    create_pr = body.create_pr if body.auto_push is None else (body.create_pr or body.auto_push)

    WORKSPACES.mkdir(parents=True, exist_ok=True)
    result = await run_repo_fix(
        body.task,
        repo_url=body.repo_url,
        local_path=local,
        branch=body.branch,
        mode=body.mode,
        create_pr=create_pr,
        auto_push=body.auto_push,
        llm=_llm(),
        memory_dir=MEMORY,
        work_root=WORKSPACES,
        max_iterations=body.max_iterations,
    )
    _TRACES[result["run_id"]] = result
    return result


@app.post("/api/hitl/resume", dependencies=[Depends(_require_api_key)])
async def hitl_resume(body: HitlResumeRequest):
    trace = _TRACES.get(body.run_id)
    workspace_path = body.workspace_path or (trace or {}).get("workspace_path")
    if not workspace_path:
        raise HTTPException(400, "workspace_path required")

    result = await resume_repo_fix(
        body.run_id,
        approve_push=body.approve_push,
        workspace_path=workspace_path,
        llm=_llm(),
        memory_dir=MEMORY,
    )
    if body.run_id in _TRACES:
        _TRACES[body.run_id].update(result)
    return result


@app.get("/api/trace/{run_id}")
def get_trace(run_id: str):
    if run_id not in _TRACES:
        return {"error": "not_found"}
    return _TRACES[run_id]


@app.post("/api/benchmark")
def run_benchmark():
    harness = _harness()
    results = []
    for item in BENCHMARK_SUITE:
        r = harness.run(item.query, item.gold_keywords)
        results.append(
            {
                "query": item.query,
                "passed": r.passed,
                "iterations": r.iterations,
                "rag_version": r.final_rag_version,
                "eval": r.eval,
            }
        )
    passed = sum(1 for x in results if x["passed"])
    return {"total": len(results), "passed": passed, "results": results}


@app.get("/api/loop-spec")
def loop_spec():
    spec_path = ROOT / "loops" / "support-intelligence.yaml"
    if spec_path.exists():
        return {"spec": spec_path.read_text(encoding="utf-8")}
    return {"spec": None}
