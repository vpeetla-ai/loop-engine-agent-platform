# Product — LoopForge Self-Improving Support Intelligence

## One-liner

**Agents that get better at answering — because the harness loops on eval failure and tunes RAG + memory, not just the prompt.**

## User personas

| Persona | Need |
|---------|------|
| **AI lab recruiter** | Inspectable proof of loop engineering, MCP, eval discipline |
| **Applied AI engineer** | Forkable harness + RAG tuner reference |
| **Platform architect** | ADR-backed split: agent / harness / loops / memory |

## Core user journey

1. Submit a support question (or run benchmark suite).
2. Harness runs **AttemptLoop** (RAG retrieve → ReAct with MCP tools → answer).
3. **Evaluator** scores faithfulness + retrieval recall vs gold (benchmark) or heuristics.
4. On failure: **EvolveLoop** adjusts RAG params (`top_k`, `hybrid_alpha`, `rerank_threshold`) and writes a **procedural memory** entry.
5. Re-run — next attempt uses tuned config + memory hints.
6. Inspect full trace: every loop phase, MCP call, memory write, RAG version.

## Success metrics

| Metric | Target (benchmark) |
|--------|-------------------|
| Retrieval recall@k | Improves ≥1 step by iteration 3 |
| Answer faithfulness | ≥0.85 on held-out suite after evolve |
| Loop transparency | 100% steps in JSON trace |
| MCP tool success | Filesystem + search tools wired |

## Non-goals (v1)

- Training custom embedding models
- Full OPA / enterprise gateway (pairs with AegisAI in portfolio stack)
- Multi-tenant SaaS billing

## Portfolio position

Sixth layer of the governed AI reference stack:

**How do agents improve over time?** → LoopForge (`loop-engine-agent-platform`)

Pairs with VAP (orchestration), Enterprise RAG (knowledge), AegisAI (governance).
