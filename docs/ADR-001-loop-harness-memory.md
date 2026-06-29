# ADR-001: Loop Harness Instead of Monolithic Self-Prompting Agent

**Status:** Accepted  
**Date:** 2026-06  
**System:** LoopForge (`loop-engine-agent-platform`)

## Context

Self-improving agents are often implemented as "reflect and rewrite your system prompt" — which conflates reasoning, retrieval config, tool use, and memory into one opaque string. Production systems need separable concerns and measurable improvement.

Research (MemPro, MUSE, Loop Engineering taxonomy) points to **system-level evolution**: evaluators + memory + tunable pipelines — not larger prompts.

## Decision

Implement **Agent → Harness → Loops → Memory**:

1. **Harness** — schedules ODAEU, enforces iteration budget, exports traces
2. **Inner loops** — ReAct with MCP tools
3. **Outer loop** — Evolve on eval failure; tune RAG config; write procedural memory
4. **MCP bridge** — standardized tool boundary

Do **not** merge orchestration, governance, and evolution into one LLM call chain.

## Consequences

**Positive**

- Inspectable improvement (RAG version tree, lesson log)
- Recruiters and applied AI teams can fork harness without rewriting agent
- Pairs with AegisAI gateway at tool side-effect boundaries (portfolio integration)

**Negative**

- More moving parts than a single ReAct script
- v1 uses local MCP adapters; stdio MCP servers are follow-up

## References

- MemPro — evolvable memory programs
- MUSE — hierarchical memory from execution critique
- KanakMalpani/Loop-Engineering — LSS loop declarations
