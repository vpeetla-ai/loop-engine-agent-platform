from __future__ import annotations

from typing import Any, Literal, TypedDict


class ReviewIssue(TypedDict, total=False):
    line: int
    type: str
    severity: str
    suggestion: str


class AgentLoopState(TypedDict, total=False):
    # Input
    task: str
    spec: dict[str, Any]
    run_id: str

    # Orchestrator
    plan: str
    active_prompt: str
    iteration: int
    max_iterations: int
    route_decision: str

    # Memory
    memory_context: str
    anti_patterns: list[str]

    # Coding agent
    generated_code: str
    generated_tests: str
    code_diff: str
    workspace_path: str

    # Review agent
    review_score: float
    review_issues: list[ReviewIssue]
    review_dimensions: dict[str, float]

    # Quality agent
    test_passed: bool
    coverage_pct: float
    quality_report: dict[str, Any]

    # Control
    should_escalate: bool
    hitl_approved: bool
    status: Literal["running", "passed", "retry", "escalated", "failed"]
    trace_events: list[dict[str, Any]]

    # Self-improve
    prompt_version: int
    rag_config_version: int

    # Repo workflow
    repo_url: str
    branch: str
    mode: Literal["bugfix", "feature"]
    auto_push: bool  # deprecated: use create_pr
    create_pr: bool
    patches: list[dict[str, str]]
    failing_tests: str
    git_commit_sha: str
    push_status: dict[str, str]
    pr_branch: str
    pr_url: str
    pr_number: int


DEFAULT_CODING_PROMPT = """You are a production coding agent.
- Write minimal, correct Python with type hints
- Always include pytest tests in the same response
- Use clear function names and handle edge cases
- Output format: first ```python code block, then ```python tests block"""


PASS_SCORE_THRESHOLD = 0.85
PASS_COVERAGE_THRESHOLD = 80.0
MAX_ITERATIONS_DEFAULT = 5

DEFAULT_REPO_CODING_PROMPT = """You are a repo coding agent working on a real codebase.
Analyze failing tests and source files, then return JSON only:
{"patches":[{"path":"relative/file.py","content":"full file content"}],"summary":"what you fixed"}
Rules:
- Fix root cause, minimal diff
- Preserve existing style and imports
- Do not delete unrelated code
"""
