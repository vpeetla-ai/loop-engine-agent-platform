# Research Foundation — Loop Engineering & Self-Improving Agents

This platform synthesizes 2025–2026 research into a **production harness**, not a paper reproduction.

## Thesis

> **Agent → Harness → Loops → Memory** is the modern agent stack.  
> Prompt engineering optimizes a single turn. **Loop engineering** optimizes the closed system: Observe → Decide → Act → Evaluate → Update.

## Papers & frameworks mapped to this repo

| Source | Insight | Implementation here |
|--------|---------|---------------------|
| [Loop Engineering (KanakMalpani)](https://github.com/KanakMalpani/Loop-Engineering) | L = (S, A, O, T, E, M, τ) — state, actions, observations, transitions, **evaluators**, **memory**, termination | `LoopSpec` YAML + `EvolveLoop` |
| [Agent Harness Engineering](https://medium.com/@adnanmasood/agent-harness-engineering-the-rise-of-the-ai-control-plane-938ead884b1d) | Harness = loop + tools + memory + guardrails + tracing | `AgentHarness` |
| [MemPro (2026)](https://arxiv.org/html/2606.00619) | Memory construction–retrieval as **evolvable program**; version tree of pipeline configs | `RAGTuner` + `MemoryStore` version tree |
| [MUSE (ACL 2026)](https://aclanthology.org/2026.findings-acl.1522/) | Post-execution critique → structured procedural/strategic memory | `CritiqueLoop` → episodic memory |
| [SemaClaw (2026)](https://arxiv.org/html/2604.11548v1) | Working + external memory; permission before risky ops | Session scratchpad + JSON memory bank |
| **MCP** | Standard agent↔tool boundary | `mcp/` bridge (filesystem, search, fetch) |

## Problem we solve

**Self-Improving Support Intelligence** — technical Q&A where:

1. First-pass RAG often misses the right chunk or uses wrong hybrid weights.
2. Static RAG configs do not adapt to failure modes.
3. Agents need **real tools** (MCP) and **durable lessons** (memory), not bigger prompts.

**Goal:** Demonstrate measurable improvement in retrieval recall and answer faithfulness across loop iterations on a fixed benchmark — inspectable via trace UI and API.

## Loop taxonomy (this repo)

| Loop | Level | Role |
|------|-------|------|
| **ReAct** | Inner | Tool use within one attempt |
| **Critique** | Inner | Post-answer failure analysis |
| **Evolve** | Outer | RAG config + memory update after eval failure |
| **Harness** | System | Schedules loops, enforces budgets, persists state |

## References

- KanakMalpani/Loop-Engineering — D-D-M-I-S framework, LSS loop declarations
- Anthropic / OpenAI applied eng blogs — harness as control plane
- Model Context Protocol — tool standardization
