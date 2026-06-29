from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Awaitable

ToolFn = Callable[[str], str]


@dataclass
class MCPTool:
    name: str
    description: str
    invoke: ToolFn


@dataclass
class MCPBridge:
    """MCP-style tool boundary — local adapters; extensible to stdio MCP servers."""

    tools: dict[str, MCPTool] = field(default_factory=dict)

    @classmethod
    def from_corpus_dir(cls, corpus_dir: Path) -> MCPBridge:
        def read_file(path: str) -> str:
            target = corpus_dir / path
            if not target.exists() or not target.is_file():
                return f"Error: file not found: {path}"
            return target.read_text(encoding="utf-8")[:4000]

        def search_docs(query: str) -> str:
            hits: list[str] = []
            q = query.lower()
            for md in sorted(corpus_dir.glob("**/*.md")):
                text = md.read_text(encoding="utf-8")
                if any(t in text.lower() for t in q.split() if len(t) > 3):
                    hits.append(f"[{md.name}] {text[:400]}...")
            return "\n---\n".join(hits[:5]) if hits else "No matches."

        return cls(
            tools={
                "read_file": MCPTool(
                    name="read_file",
                    description="Read a file from the knowledge corpus by relative path",
                    invoke=read_file,
                ),
                "search_docs": MCPTool(
                    name="search_docs",
                    description="Full-text search across markdown knowledge corpus",
                    invoke=search_docs,
                ),
            }
        )

    def list_tools(self) -> list[str]:
        return list(self.tools.keys())

    def call(self, name: str, argument: str) -> str:
        if name not in self.tools:
            return f"Error: unknown tool {name}"
        return self.tools[name].invoke(argument)
