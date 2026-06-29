from __future__ import annotations

from dataclasses import dataclass

from loop_engine.rag.retriever import Chunk


@dataclass
class EvalResult:
    passed: bool
    faithfulness: float
    recall: float
    failure_mode: str | None = None

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "recall": self.recall,
            "faithfulness": self.faithfulness,
            "failure_mode": self.failure_mode,
        }


@dataclass
class BenchmarkItem:
    query: str
    gold_keywords: list[str]
    min_recall: float = 0.5
    min_faithfulness: float = 0.6


BENCHMARK_SUITE: list[BenchmarkItem] = [
    BenchmarkItem(
        query="What is loop engineering and how does a harness improve agents?",
        gold_keywords=["loop", "harness", "evaluate", "memory", "mcp"],
        min_recall=0.4,
        min_faithfulness=0.5,
    ),
    BenchmarkItem(
        query="How does the evolve loop tune RAG after evaluation failure?",
        gold_keywords=["rag", "top_k", "hybrid", "evolve", "config"],
        min_recall=0.35,
        min_faithfulness=0.5,
    ),
    BenchmarkItem(
        query="What role does MCP play in the agent stack?",
        gold_keywords=["mcp", "tool", "filesystem", "search"],
        min_recall=0.35,
        min_faithfulness=0.45,
    ),
]


class Evaluator:
    def evaluate(
        self,
        query: str,
        answer: str,
        chunks: list[Chunk],
        gold_keywords: list[str] | None = None,
    ) -> EvalResult:
        keywords = gold_keywords or []
        answer_lower = answer.lower()
        chunk_text = " ".join(c.text.lower() for c in chunks)

        if keywords:
            recall_hits = sum(1 for k in keywords if k in chunk_text or k in answer_lower)
            recall = recall_hits / len(keywords)
        else:
            recall = 0.7 if chunks else 0.2

        faith_hits = sum(1 for k in (gold_keywords or ["loop", "agent"]) if k in answer_lower)
        faithfulness = faith_hits / max(len(gold_keywords or ["loop", "agent"]), 1)

        passed = recall >= 0.35 and faithfulness >= 0.45
        failure_mode = None
        if not passed:
            failure_mode = "low_recall" if recall < faithfulness else "low_faithfulness"

        return EvalResult(
            passed=passed,
            faithfulness=faithfulness,
            recall=recall,
            failure_mode=failure_mode,
        )
