# MCP and Memory

## Model Context Protocol (MCP)

MCP separates **agent logic** from **tool implementations**. This platform exposes:

- `read_file` — read corpus documents
- `search_docs` — full-text search across knowledge base

Tools are invoked inside the ReAct loop; traces record every MCP call.

## Memory layers

| Layer | Scope | Purpose |
|-------|-------|---------|
| Working | Single attempt | Retrieved chunks + tool output |
| Procedural | Cross-session | Lessons after eval failure |
| RAG versions | Cross-session | Config version tree |

MUSE-style critique distills failure modes into reusable lessons so the next attempt starts smarter — not with a longer prompt.
