from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path

from loop_engine.eval.evaluator import Evaluator
from loop_engine.loops.evolve_loop import EvolveLoop
from loop_engine.loops.react_loop import ReActLoop
from loop_engine.memory.store import MemoryStore
from loop_engine.mcp.bridge import MCPBridge
from loop_engine.models.llm import LLM
from loop_engine.rag.retriever import Corpus, HybridRetriever, RAGConfig
from loop_engine.tracing import Trace


@dataclass
class HarnessResult:
    run_id: str
    query: str
    answer: str
    passed: bool
    iterations: int
    final_rag_version: int
    trace: Trace
    eval: dict

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "query": self.query,
            "answer": self.answer,
            "passed": self.passed,
            "iterations": self.iterations,
            "final_rag_version": self.final_rag_version,
            "eval": self.eval,
            "trace": self.trace.to_dict(),
        }


@dataclass
class AgentHarness:
  llm: LLM
  corpus_dir: Path
  memory_dir: Path
  max_evolve_iterations: int = 3
  _retriever: HybridRetriever = field(init=False)
  _mcp: MCPBridge = field(init=False)
  _memory: MemoryStore = field(init=False)
  _evaluator: Evaluator = field(init=False)

  def __post_init__(self) -> None:
      self._retriever = HybridRetriever(Corpus.from_directory(self.corpus_dir))
      self._mcp = MCPBridge.from_corpus_dir(self.corpus_dir)
      self._memory = MemoryStore(self.memory_dir)
      self._evaluator = Evaluator()

  def run(
      self,
      query: str,
      gold_keywords: list[str] | None = None,
  ) -> HarnessResult:
      run_id = uuid.uuid4().hex[:12]
      trace = Trace(run_id=run_id)
      config = RAGConfig()
      react = ReActLoop(llm=self.llm, mcp=self._mcp)
      evolve = EvolveLoop(llm=self.llm, memory=self._memory)

      answer = ""
      eval_result = None

      for iteration in range(1, self.max_evolve_iterations + 1):
          trace.add("observe", "iteration.start", iteration=iteration, rag_version=config.version)
          hints = self._memory.hints_for_query(query)
          chunks = self._retriever.retrieve(query, config)
          trace.add(
              "observe",
              "rag.retrieve",
              iteration=iteration,
              top_k=config.top_k,
              hybrid_alpha=config.hybrid_alpha,
              chunk_ids=[c.doc_id for c in chunks],
              scores=[c.score for c in chunks],
          )

          context = "MEMORY HINTS:\n" + hints + "\n\nRETRIEVED:\n"
          context += "\n---\n".join(c.text[:400] for c in chunks) if chunks else "(empty)"

          trace.add("decide", "attempt.plan", iteration=iteration, strategy="react_then_answer")
          draft, _ = react.run(query, context, trace)

          system = "Write a concise support answer using only the context."
          answer = self.llm.complete(system, f"Query: {query}\n\nContext:\n{context}\n\nDraft:\n{draft}")
          trace.add("act", "answer.draft", iteration=iteration, answer=answer[:500])

          eval_result = self._evaluator.evaluate(query, answer, chunks, gold_keywords)
          trace.add(
              "evaluate",
              "eval.score",
              iteration=iteration,
              passed=eval_result.passed,
              recall=eval_result.recall,
              faithfulness=eval_result.faithfulness,
              failure_mode=eval_result.failure_mode,
          )

          if eval_result.passed:
              trace.add("evaluate", "run.passed", iteration=iteration)
              break

          if iteration < self.max_evolve_iterations and eval_result.failure_mode:
              config = evolve.run(query, eval_result.failure_mode, config, trace)
          else:
              trace.add("evaluate", "run.exhausted", iteration=iteration)

      assert eval_result is not None
      return HarnessResult(
          run_id=run_id,
          query=query,
          answer=answer,
          passed=eval_result.passed,
          iterations=iteration,
          final_rag_version=config.version,
          trace=trace,
          eval={
              "passed": eval_result.passed,
              "recall": eval_result.recall,
              "faithfulness": eval_result.faithfulness,
              "failure_mode": eval_result.failure_mode,
          },
      )
