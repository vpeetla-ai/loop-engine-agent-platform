from __future__ import annotations

from dataclasses import dataclass

from loop_engine.memory.store import Lesson, MemoryStore
from loop_engine.models.llm import LLM
from loop_engine.rag.retriever import RAGConfig
from loop_engine.tracing import Trace


@dataclass
class EvolveLoop:
    llm: LLM
    memory: MemoryStore

    def run(
        self,
        query: str,
        failure_mode: str,
        config: RAGConfig,
        trace: Trace,
    ) -> RAGConfig:
        critique = self.llm.complete(
            "Analyze the failure and output FAILURE_MODE and LESSON lines.",
            f"Query: {query}\nFailure: {failure_mode}\nRAG config: top_k={config.top_k}, "
            f"hybrid_alpha={config.hybrid_alpha}, rerank_threshold={config.rerank_threshold}",
        )
        trace.add("update", "critique.raw", text=critique)

        lesson_text = critique
        for line in critique.splitlines():
            if line.upper().startswith("LESSON:"):
                lesson_text = line.split(":", 1)[1].strip()

        if failure_mode == "low_recall":
            new_config = config.mutate_for_recall()
        else:
            new_config = config.mutate_for_faithfulness()

        lesson = Lesson(
            failure_mode=failure_mode,
            lesson=lesson_text,
            rag_version=new_config.version,
        )
        self.memory.add_lesson(lesson)
        self.memory.record_rag_version(new_config)
        trace.add(
            "update",
            "evolve.rag",
            from_version=config.version,
            to_version=new_config.version,
            config={
                "top_k": new_config.top_k,
                "hybrid_alpha": new_config.hybrid_alpha,
                "rerank_threshold": new_config.rerank_threshold,
            },
            lesson=lesson_text,
        )
        return new_config
