# LoopForge — Self-Improving Agent Harness



<!-- vpeetla-tech-stack:start -->
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square)]() [![LangGraph](https://img.shields.io/badge/LangGraph-9333EA?style=flat-square)]() [![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square)]() [![Langfuse](https://img.shields.io/badge/Langfuse-6366F1?style=flat-square)]() [![MCP](https://img.shields.io/badge/MCP-374151?style=flat-square)]() [![Groq](https://img.shields.io/badge/Groq-F55036?style=flat-square)]() [![GitHub API](https://img.shields.io/badge/GitHub-API-181717?style=flat-square)]() [![Vercel](https://img.shields.io/badge/Vercel-000000?style=flat-square)]() [![Render](https://img.shields.io/badge/Render-46E3B7?style=flat-square)]()
<!-- vpeetla-tech-stack:end -->
## Agent skills (Cursor + Codex)

Org skills: [vpeetla-ai-skills](https://github.com/vpeetla-ai/vpeetla-ai-skills). This repo includes `.cursor/skills/`, `AGENTS.md`, and `CONTEXT.md`.

```bash
git clone https://github.com/vpeetla-ai/vpeetla-ai-skills.git
./vpeetla-ai-skills/scripts/install.sh --cursor --codex --project .
```

---

### Agent → Harness → Loops → Memory — loop engineering with RAG tuning & MCP tools

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Portfolio](https://img.shields.io/badge/🌐_venkat--ai.com-Portfolio-5eead4?style=flat-square)](https://venkat-ai.com/work)
[![Live Demo](https://img.shields.io/badge/▶_Live_Demo-LoopForge_UI-8b5cf6?style=flat-square)](https://demo-omega-taupe.vercel.app)
[![API](https://img.shields.io/badge/API-Render-46E3B7?style=flat-square)](https://loopforge-api.onrender.com/health)

> **The problem:** Static RAG configs and one-shot prompts do not improve. Production agents need **closed loops** that evaluate, tune retrieval, and store lessons.
>
> **The goal:** Demonstrate measurable improvement across ODAEU iterations — with MCP tools, procedural memory, and inspectable traces.

**Portfolio:** [Case study](https://github.com/vpeetla-ai/ai-architecture-portfolio/blob/main/case-studies/loopforge-self-improving-harness.md) · [Architecture](docs/ARCHITECTURE.md) · [Tradeoffs / LOOPS](docs/LOOPS.md) · [Deploy](docs/LIVE_DEMO.md)
[Portfolio](https://venkat-ai.com/work) · [Architecture ADRs](https://github.com/vpeetla-ai/ai-architecture-portfolio) · [GitHub org](https://github.com/vpeetla-ai)

---

## Why this exists

| Era | Optimized | Ceiling |
|-----|-----------|---------|
| 2020–23 | Prompt engineering | Single turn |
| 2023–24 | Context engineering | Static retrieval |
| 2024–25 | Agent engineering | Autonomous actors, no system improvement |
| **2025+** | **Loop engineering** | **Self-improving harnesses** |

This repo implements the **modern agent stack**:

```text
AGENT  →  reasoning inside bounded loops
HARNESS →  scheduler, budgets, tracing, eval gates
LOOPS  →  ReAct (inner) · Critique · Evolve (outer)
MEMORY →  procedural lessons + RAG version tree
MCP    →  filesystem + search tools on real corpus
OBS    →  trace-linked evals → Langfuse (LANGFUSE_*)
```

```mermaid
flowchart TB
    subgraph Harness["Agent harness"]
        RUN["POST /api/run · /api/repo-fix"]
        REC["TraceRecorder"]
        EVAL["eval scores"]
    end
    subgraph Loops["LangGraph loops"]
        ODAEU["ODAEU harness"]
        CODE["coding loop"]
        FIX["repo fix → PR"]
    end
    subgraph Obs["LLMOps export"]
        LF["Langfuse Cloud<br/>system · trace · node"]
    end
    RUN --> REC --> Loops
    Loops --> EVAL
    REC -.-> LF
```

Research foundation: [docs/RESEARCH.md](docs/RESEARCH.md) · [docs/LOOPS.md](docs/LOOPS.md) (overnight agent protocol).

---

## Live demo

| Surface | URL |
|---------|-----|
| **Demo UI** | [demo-omega-taupe.vercel.app](https://demo-omega-taupe.vercel.app) |
| **API** | [loopforge-api.onrender.com](https://loopforge-api.onrender.com) |
| **Health** | [`/health`](https://loopforge-api.onrender.com/health) |

Paste a GitHub repo URL → **Fix Repo & Open PR**. Or run the codegen LangGraph loop. ODAEU RAG tuning available via API (`POST /api/run`).

---

## Implementation status

| Component | Status | Notes |
|-----------|--------|-------|
| ODAEU harness + RAG evolve | ✅ | `POST /api/run` |
| LangGraph coding loop | ✅ | Orchestrator · Review · Quality |
| Repo fix → GitHub PR | ✅ | `loopforge/fix-*` branch, never `main` |
| MCP tool bridge | ✅ | `read_file`, `search_docs` |
| Procedural memory | ✅ | JSON lesson store |
| Graph HITL escalate | ✅ | `interrupt_before` on quality fail |
| AegisAI gateway on git push | ✅ | `integrations/aegis_gateway.py` — push + PR |
| Langfuse / OTel export | ✅ | `vpeetla_observability` + `langfuse_export.py` — set `LANGFUSE_*` |
| Live Groq codegen | 🟡 | Requires `GROQ_API_KEY` on Render |

---

## Architecture (60 seconds)

Two complementary loops ship in this repo:

### 1. ODAEU harness (RAG tuning)
```text
Query → Harness → ReAct + MCP → Eval → Evolve RAG config → Memory
```

### 2. LangGraph agent loop (Coding · Review · Quality)
```text
orchestrate → memory_retrieve → code → review → quality
  → route_after_quality (retry | escalate HITL | pass)
  → memory_write → self_improve → END
```

| Agent | Role |
|-------|------|
| **Orchestrator** | Plans task, rewrites coding prompt on retry |
| **Coding** | Generates code + tests via MCP corpus search |
| **Review** | Scores correctness · security · complexity · style |
| **Quality** | Runs pytest sandbox gate (coverage ≥ 80%) |
| **Memory** | Retrieves lessons, writes on pass |
| **Self-improve** | Promotes prompt version on outer loop tick |

### 3. Repo fix loop (real GitHub repos → PR)
```text
clone → pytest scan → orchestrate → patch files → review → quality
  → branch loopforge/fix-{id} → commit → push branch → open GitHub PR
```

**Never pushes to `main`.** All fixes land on a branch + pull request for review.

| Step | What happens |
|------|----------------|
| UI | Paste repo URL + task ("find and fix bugs") |
| API | `POST /api/repo-fix` with `create_pr: true` |
| Output | `pr_url`, `pr_branch`, `code_diff`, full trace |

Production guide: [docs/DEPLOY.md](docs/DEPLOY.md)

API: `POST /api/repo-fix` · Graph: `src/loop_engine/graph/repo_build.py`

Full spec: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · Loop declaration: [loops/support-intelligence.yaml](loops/support-intelligence.yaml)

---

## Quick start

```bash
git clone https://github.com/vpeetla-ai/loop-engine-agent-platform.git
cd loop-engine-agent-platform
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Tests (no API keys — MockLLM)
pytest -q

# API
uvicorn app.main:app --app-dir backend --reload
# POST http://localhost:8000/api/run  {"query": "What is loop engineering?"}
# POST http://localhost:8000/api/benchmark
```

Optional env vars:
```bash
export GROQ_API_KEY=...    # live LLM on real repos
export GITHUB_TOKEN=...    # PR workflow (branch push + create pull request)
```

```bash
# Fix a repo and open a PR
curl -X POST http://localhost:8000/api/repo-fix \
  -H "Content-Type: application/json" \
  -d '{"repo_url":"https://github.com/org/repo.git","task":"Find and fix failing tests","create_pr":true}'
```

---

## What gets tuned (RAG evolve loop)

Inspired by **MemPro** — treat retrieval pipeline as evolvable config, not frozen hyperparameters:

| Signal | Action |
|--------|--------|
| `low_recall` | ↑ `top_k`, ↑ `hybrid_alpha`, ↓ `rerank_threshold` |
| `low_faithfulness` | ↑ `rerank_threshold`, ↓ `hybrid_alpha` |

Each version persisted in memory version tree. Lessons written in MUSE-style critique.

---

## MCP tools

| Tool | Purpose |
|------|---------|
| `read_file` | Read corpus markdown by path |
| `search_docs` | Full-text search across knowledge base |

Extensible to stdio MCP servers — agent logic stays behind the bridge.

---

## Portfolio stack position

| Question | System |
|----------|--------|
| What should agents do? | [VAP](https://github.com/vpeetla-ai/venkat-ai-platform) |
| What are agents allowed? | [AegisAI](https://github.com/vpeetla-ai/aegisai-enterprise-agent-platform) |
| What knowledge can they use? | [Enterprise RAG](https://github.com/vpeetla-ai/enterprise_rag_platform) |
| How do we operate fleets? | [AegisLoop](https://github.com/vpeetla-ai/aegisloop-agentops-workbench) |
| **How do agents improve?** | **LoopForge (this repo)** |

---

## Docs

- [Product](docs/PRODUCT.md) · [Requirements](docs/REQUIREMENTS.md)
- [Architecture](docs/ARCHITECTURE.md) · [Research](docs/RESEARCH.md)
- [ADR-001: Loop harness over monolithic agent](docs/ADR-001-loop-harness-memory.md)

---

## License

MIT — fork for your own self-improving agent harness.
