# Requirements

## Functional

| ID | Requirement | Priority |
|----|-------------|----------|
| F1 | Agent harness schedules bounded ODAEU loops | P0 |
| F2 | RAG retrieval with tunable hybrid config | P0 |
| F3 | Evaluator scores answers (benchmark + heuristics) | P0 |
| F4 | Evolve loop updates RAG config on eval failure | P0 |
| F5 | Episodic + procedural memory persistence | P0 |
| F6 | MCP tool bridge (filesystem read, local search) | P0 |
| F7 | REST API: `/run`, `/benchmark`, `/trace/{id}` | P0 |
| F8 | Static trace demo UI (Vercel) | P0 |
| F9 | Loop spec declarable in YAML (LSS-inspired) | P1 |
| F10 | Groq/OpenAI LLM provider via env | P1 |

## Non-functional

| ID | Requirement |
|----|-------------|
| NF1 | Runs on free tier (Render + Vercel + Groq) |
| NF2 | No API keys required for demo mode (deterministic mock LLM) |
| NF3 | MIT license, forkable |
| NF4 | pytest coverage on harness + eval + RAG tuner |
| NF5 | JSON traces exportable for portfolio embed |

## Acceptance (v1 release)

- [ ] `pytest` passes
- [ ] `POST /api/run` returns trace with ≥1 evolve iteration on hard benchmark item
- [ ] Demo UI animates ODAEU phases
- [ ] README shows before/after RAG metrics on benchmark
- [ ] Wired on venkat-ai.com/work as live platform #6
