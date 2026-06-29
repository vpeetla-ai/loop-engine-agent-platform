# Architecture

## Live production URLs

| Surface | URL |
|---------|-----|
| **Demo UI** | [demo-omega-taupe.vercel.app](https://demo-omega-taupe.vercel.app) |
| **API** | [loopforge-api.onrender.com](https://loopforge-api.onrender.com) |
| **Source** | [github.com/vpeetla-ai/loop-engine-agent-platform](https://github.com/vpeetla-ai/loop-engine-agent-platform) |
| **Portfolio** | [venkat-ai.com/work](https://venkat-ai.com/work) |
| **Architecture hub** | [ai-architecture-portfolio](https://github.com/vpeetla-ai/ai-architecture-portfolio) |

---

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
   ┌──────────┐        ┌──────────┐
   │   MCP    │        │ LangGraph│
   │  TOOLS   │        │  graphs  │
   └──────────┘        └──────────┘
```

## Three LangGraph / harness loops

### 1. ODAEU harness (RAG tuning)

| Phase | Component | Output |
|-------|-----------|--------|
| **Observe** | `HarnessContext` | query, RAG config vN, memory hints |
| **Decide** | `AttemptLoop` | plan: retrieve → react → draft answer |
| **Act** | `ReActLoop` + `MCPBridge` | tool observations |
| **Evaluate** | `Evaluator` | scores + failure modes |
| **Update** | `EvolveLoop` + `RAGTuner` + `MemoryStore` | config vN+1, lesson written |

`POST /api/run` · `src/loop_engine/harness/`

### 2. Coding agent loop (Orchestrator · Coding · Review · Quality)

```text
orchestrate → memory_retrieve → code → review → quality
  → route_after_quality (retry | HITL | pass)
  → memory_write → self_improve → END
```

`POST /api/agent-loop` · `src/loop_engine/graph/build.py`

### 3. Repo fix loop (real GitHub → PR)

```text
clone → pytest scan → orchestrate → patch files → review → quality
  → branch loopforge/fix-{run_id} → commit → push branch → GitHub PR
```

**Never pushes to `main`.** All fixes land on a branch + pull request.

| Agent | Role |
|-------|------|
| **Orchestrator** | Plans task, rewrites coding prompt on retry |
| **Coding** | Reads repo files, applies JSON patches |
| **Review** | Scores diff across correctness · security · complexity · style |
| **Quality** | Runs project pytest in cloned workspace |
| **Memory** | Retrieves lessons, writes on pass |
| **Self-improve** | Promotes prompt version on outer loop tick |

`POST /api/repo-fix` · `src/loop_engine/graph/repo_build.py` · `src/loop_engine/workspace/`

---

## Package layout

```text
src/loop_engine/
  harness/     # AgentHarness — ODAEU entry
  graph/       # LangGraph: build, repo_build, nodes, routing, state
  workspace/   # clone, pytest, git branch, GitHub PR API
  loops/       # react, evolve
  rag/         # HybridRetriever, RAGConfig, RAGTuner
  memory/      # MemoryStore, Lesson, version tree
  mcp/         # MCPBridge + local tool adapters
  eval/        # Evaluator, benchmark suite
  models/      # LLM providers (mock + groq)

backend/app/   # FastAPI — production API
demo/          # Vercel static UI (wired to Render API)
```

## Deployment

| Service | Role |
|---------|------|
| [Vercel](https://demo-omega-taupe.vercel.app) | Static demo UI |
| [Render](https://loopforge-api.onrender.com) | FastAPI + Docker (git, pytest) |
| GitHub API | PR creation via `GITHUB_TOKEN` |

See [DEPLOY.md](DEPLOY.md) for env vars and token scopes.

## Integration with portfolio stack ([vpeetla-ai](https://github.com/vpeetla-ai))

| Question | System |
|----------|--------|
| What should agents do? | [venkat-ai-platform](https://github.com/vpeetla-ai/venkat-ai-platform) |
| What are agents allowed? | [aegisai-enterprise-agent-platform](https://github.com/vpeetla-ai/aegisai-enterprise-agent-platform) |
| What knowledge can they use? | [enterprise_rag_platform](https://github.com/vpeetla-ai/enterprise_rag_platform) |
| How do we operate fleets? | [aegisloop-agentops-workbench](https://github.com/vpeetla-ai/aegisloop-agentops-workbench) |
| What do they produce? | [ai-content-factory](https://github.com/vpeetla-ai/ai-content-factory) |
| **How do agents improve?** | **loop-engine-agent-platform (this repo)** |
