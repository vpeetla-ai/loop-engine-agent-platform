# LOOPS — LoopForge overnight agent protocol

**Who this serves:** Platform engineers and AI leads who want agents to improve RAG configs or fix repos without babysitting every turn.

**Job-to-be-done:** Wake up to a measurable improvement (higher eval score, passing tests, open PR) with a full trace of what was tried.

## Metric (one number per harness mode)

| Mode | Optimize | Better when |
|------|----------|-------------|
| ODAEU harness | eval pass + recall/faithfulness | Higher pass, higher recall |
| Repo fix | `pytest` pass | `test_passed=true` |
| RAG evolve | golden query hit rate | Recall ↑ without faithfulness ↓ |

## Mutable surface (agent MAY change)

- `RAGConfig` fields: `top_k`, `hybrid_alpha`, `rerank_threshold`
- Repo files via `repo_coding_node` patches (bugfix mode)
- **Not:** `prepare.py` equivalents — `workspace.run_pytest()`, eval harness, gateway integration

## Locked (agent MUST NOT change)

- `integrations/aegis_gateway.py` — git push authorization
- Pytest fixtures and golden query files
- CI workflows, `main` branch (PR-only ship path)

## Time budget

| Loop | Budget |
|------|--------|
| ODAEU iteration | bounded by `max_evolve_iterations` (default 3) |
| Repo fix graph | `max_iterations` + quality gate |
| Live Groq codegen | Render cold start ~30–60s — factor into demos |

## Loop protocol

```text
Observe (RAG retrieve / repo scan)
  → Decide (orchestrator / ReAct plan)
  → Act (MCP tools or patches)
  → Evaluate (evaluator / pytest / review score)
  → Update (evolve RAG config + memory lesson OR git branch)
  → repeat until pass or budget exhausted
```

## Stop conditions

- Eval passed
- `max_iterations` reached → HITL escalate (`interrupt_before`)
- Gateway `approval_required` or `block` on git push
- Cost/token budget (set on API)

## Learnings log

- Procedural memory: `data/memory/` JSON lessons
- Trace: `trace_events` + optional Langfuse export
- Repo fix: commit message + PR body with run_id

## Karpathy mapping

| autoresearch | LoopForge |
|--------------|-----------|
| `program.md` | this file + `loops/*.yaml` |
| `train.py` | patches / RAG config |
| `prepare.py` | pytest + evaluator |
| git keep/discard | `loopforge/fix-*` branch + PR |

See org skill **`agents-that-run-for-days`** in [vpeetla-ai-skills](https://github.com/vpeetla-ai/vpeetla-ai-skills).
