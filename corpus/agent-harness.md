# Agent Harness

An **agent harness** wraps an LLM with deterministic scaffolding:

- Loop scheduler (ReAct, Critique, Evolve)
- MCP tool bridge (filesystem, search)
- Memory store (episodic + procedural)
- Evaluators with backpressure

## Plan-Execute-Verify

Production harnesses use eval gates before accepting an answer. On failure, the **evolve loop** tunes RAG parameters:

- `top_k` — retrieve more chunks when recall is low
- `hybrid_alpha` — balance lexical vs semantic weighting
- `rerank_threshold` — filter noise vs signal

Each config version is recorded in a version tree (MemPro-inspired).
