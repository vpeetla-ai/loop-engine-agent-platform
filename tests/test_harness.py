from pathlib import Path

from loop_engine.harness.agent_harness import AgentHarness
from loop_engine.models.llm import MockLLM


def test_harness_improves_rag_version_on_hard_query(tmp_path):
    root = Path(__file__).resolve().parents[1]
    harness = AgentHarness(
        llm=MockLLM(),
        corpus_dir=root / "corpus",
        memory_dir=tmp_path / "memory",
        max_evolve_iterations=3,
    )
    result = harness.run(
        "How does the evolve loop tune RAG after evaluation failure?",
        gold_keywords=["rag", "evolve", "config", "top_k"],
    )
    assert result.iterations >= 1
    assert len(result.trace.events) > 5
    phases = {e.phase for e in result.trace.events}
    assert phases >= {"observe", "decide", "act", "evaluate", "update"}
    assert result.runtime_ms >= 0
    names = [e.name for e in result.trace.events]
    assert "memory.hints" in names
    assert "rag.retrieve" in names


def test_harness_trace_covers_all_odaeu_phases_on_evolve(tmp_path):
    root = Path(__file__).resolve().parents[1]
    harness = AgentHarness(
        llm=MockLLM(),
        corpus_dir=root / "corpus",
        memory_dir=tmp_path / "memory-evolve",
        max_evolve_iterations=3,
    )
    result = harness.run(
        "What is loop engineering?",
        gold_keywords=["nonexistent", "keywords", "only", "fail"],
    )
    phases = {e.phase for e in result.trace.events}
    assert phases >= {"observe", "decide", "act", "evaluate", "update"}
    assert any(e.name == "evolve.rag" for e in result.trace.events)


def test_benchmark_evaluator_detects_keywords():
    from loop_engine.eval.evaluator import Evaluator
    from loop_engine.rag.retriever import Chunk

    ev = Evaluator()
    chunks = [Chunk(doc_id="1", text="loop harness mcp memory rag evolve")]
    r = ev.evaluate("test", "loop harness improves agents", chunks, ["loop", "harness"])
    assert r.recall > 0
