# Loop Engineering

Loop engineering is the discipline of designing **closed systems** where agents improve through Observe → Decide → Act → Evaluate → Update cycles.

Unlike prompt engineering (single turn) or context engineering (static retrieval), loop engineering optimizes the **entire runtime**: evaluators, memory, RAG pipelines, and tool boundaries.

## Key concepts

- **State (S)**: current RAG config version, memory lessons, session trace
- **Evaluators (E)**: faithfulness and recall scoring against benchmark or heuristics
- **Memory (M)**: procedural lessons distilled after critique on failure
- **Termination (τ)**: max evolve iterations or eval pass

## Harness role

The harness is the control plane: it schedules inner ReAct loops and outer Evolve loops, enforces budgets, and persists traces for inspection.
