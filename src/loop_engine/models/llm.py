from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Protocol

DEFAULT_CODING_PROMPT = """You are a production coding agent.
- Write minimal, correct Python with type hints
- Always include pytest tests in the same response
- Use clear function names and handle edge cases
- Output format: first ```python code block, then ```python tests block"""


class LLM(Protocol):
    def complete(self, system: str, user: str) -> str: ...


@dataclass
class MockLLM:
    """Deterministic LLM for demo mode — no API keys required."""

    def complete(self, system: str, user: str) -> str:
        sys_lower = system.lower()
        user_lower = user.lower()

        # LangGraph coding loop agents
        if "orchestrator" in sys_lower:
            return (
                "1. Define a minimal Python function for the task\n"
                "2. Add pytest coverage for happy path and edge cases\n"
                "3. Keep implementation under 20 lines"
            )
        if "production coding agent" in sys_lower or "rewrite the coding agent" in sys_lower:
            if "rewrite" in sys_lower:
                return DEFAULT_CODING_PROMPT + "\n- Address all review suggestions before resubmitting."
            return (
                "```python\n"
                "def solve(x: int) -> int:\n"
                "    \"\"\"Double the input.\"\"\"\n"
                "    return x * 2\n"
                "```\n"
                "```python\n"
                "from solution import solve\n\n"
                "def test_solve():\n"
                "    assert solve(3) == 6\n"
                "    assert solve(0) == 0\n"
                "```"
            )
        if "review agent" in sys_lower:
            diff = user
            if "code_diff" in user_lower or "+++ " in user or "def add" in user:
                return json.dumps(
                    {
                        "score": 0.88,
                        "dimensions": {
                            "correctness": 0.9,
                            "security": 0.85,
                            "complexity": 0.88,
                            "style": 0.86,
                        },
                        "issues": [],
                    }
                )
            return json.dumps(
                {
                    "score": 0.88,
                    "dimensions": {
                        "correctness": 0.9,
                        "security": 0.85,
                        "complexity": 0.88,
                        "style": 0.86,
                    },
                    "issues": [],
                }
            )
        if "repo coding agent" in sys_lower:
            fixed_calc = (
                '"""Simple calculator module."""\n\n\n'
                "def add(a: int, b: int) -> int:\n"
                '    """Return sum of two integers."""\n'
                "    return a + b\n"
            )
            if "calc.py" in user and ("+ 1" in user or "FAIL" in user or "assert" in user):
                return json.dumps(
                    {
                        "patches": [{"path": "calc.py", "content": fixed_calc}],
                        "summary": "Remove off-by-one bug in add()",
                    }
                )
            return json.dumps({"patches": [], "summary": "No patches generated"})

        if "THOUGHT" in system or "ReAct" in system:
            if "hybrid_alpha" in user_lower or "rag config" in user_lower:
                return "THOUGHT: I should search docs for RAG tuning guidance.\nACTION: search_docs\nINPUT: hybrid retrieval alpha"
            if "loop engineering" in user_lower or "harness" in user_lower:
                return (
                    "THOUGHT: The corpus covers loop engineering and harness design.\n"
                    "ACTION: FINISH\n"
                    "INPUT: Loop engineering treats agents as closed systems: Observe, Decide, Act, "
                    "Evaluate, Update. The harness schedules loops, MCP connects real tools, and "
                    "memory stores lessons so RAG config improves on the next attempt."
                )
            return "THOUGHT: Search the knowledge base.\nACTION: search_docs\nINPUT: agent harness memory"
        if "critique" in system.lower() or "failure" in system.lower():
            return (
                "FAILURE_MODE: low_recall\n"
                "LESSON: Increase top_k and hybrid_alpha for harness terminology queries."
            )
        if "final answer" in system.lower() or "support" in system.lower():
            return (
                "Loop engineering is the discipline of designing self-improving agent systems. "
                "A harness wraps the LLM with loops, evaluators, MCP tools, and memory — "
                "so RAG config and behavior improve after each failed evaluation."
            )
        return "Loop engineering improves agents via eval-driven RAG config tuning and procedural memory."


@dataclass
class GroqLLM:
    api_key: str
    model: str = "llama-3.3-70b-versatile"

    def complete(self, system: str, user: str) -> str:
        import httpx

        resp = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.2,
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
