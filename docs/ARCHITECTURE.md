# Architecture

## Modern agent stack

```text
┌─────────────────────────────────────────────────────────────┐
│                      AGENT HARNESS                          │
│  budgets · termination · tracing · loop scheduler           │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
   ┌──────────┐        ┌──────────┐        ┌──────────┐
   │  LOOPS   │        │   RAG    │        │  MEMORY  │
   │ ReAct    │◄──────►│ tuner    │◄──────►│ episodic │
   │ Critique │        │ hybrid   │        │ procedural│
   │ Evolve   │        │ rerank   │        │ version  │
   └────┬─────┘        └──────────┘        └──────────┘
        │
        ▼
   ┌──────────┐
   │   MCP    │  filesystem · search · (extensible)
   │  TOOLS   │
   └──────────┘
```

## ODAEU outer loop

| Phase | Component | Output |
|-------|-----------|--------|
| **Observe** | `HarnessContext` | query, RAG config vN, memory hints |
| **Decide** | `AttemptLoop` | plan: retrieve → react → draft answer |
| **Act** | `ReActLoop` + `MCPBridge` | tool observations |
| **Evaluate** | `Evaluator` | scores + failure modes |
| **Update** | `EvolveLoop` + `RAGTuner` + `MemoryStore` | config vN+1, lesson written |

## Package layout

```text
src/loop_engine/
  harness/     # AgentHarness — entry point
  loops/       # react, critique, evolve
  rag/         # HybridRetriever, RAGConfig, RAGTuner
  memory/      # MemoryStore, Lesson, version tree
  mcp/         # MCPBridge + local tool adapters
  eval/        # Evaluator, benchmark suite
  models/      # LLM providers (mock + groq)

backend/app/   # FastAPI — production API
demo/          # Vercel static trace viewer
```

## Data flow (single query)

1. `AgentHarness.run(query)` loads memory hints + current `RAGConfig`.
2. `AttemptLoop` retrieves chunks → `ReActLoop` may call MCP `read_file` / `search_docs`.
3. LLM drafts answer from context + tool output.
4. `Evaluator.evaluate(query, answer, chunks, gold?)` → pass/fail + signals.
5. If fail and budget remains: `EvolveLoop` diagnoses (low recall vs low faithfulness), `RAGTuner` mutates config, `MemoryStore` appends lesson.
6. Retry with new config — trace records all versions.

## Deployment

| Service | Role |
|---------|------|
| Vercel | Static demo UI + optional API proxy |
| Render | FastAPI backend |
| Local JSON | Memory + RAG version tree (v1; Postgres optional v2) |

## Integration with portfolio stack

| Layer | Repo |
|-------|------|
| Orchestration | venkat-ai-platform |
| Governance | aegisai-enterprise-agent-platform |
| Knowledge | enterprise_rag_platform |
| **Self-improvement** | **loop-engine-agent-platform** |
| AgentOps | aegisloop-agentops-workbench |
