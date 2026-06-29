from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RAGConfig:
    top_k: int = 3
    hybrid_alpha: float = 0.5
    rerank_threshold: float = 0.35
    version: int = 1

    def mutate_for_recall(self) -> RAGConfig:
        return RAGConfig(
            top_k=min(self.top_k + 2, 10),
            hybrid_alpha=min(self.hybrid_alpha + 0.15, 0.95),
            rerank_threshold=max(self.rerank_threshold - 0.1, 0.1),
            version=self.version + 1,
        )

    def mutate_for_faithfulness(self) -> RAGConfig:
        return RAGConfig(
            top_k=self.top_k,
            hybrid_alpha=max(self.hybrid_alpha - 0.1, 0.2),
            rerank_threshold=min(self.rerank_threshold + 0.1, 0.9),
            version=self.version + 1,
        )


@dataclass
class Chunk:
    doc_id: str
    text: str
    score: float = 0.0


@dataclass
class Corpus:
    chunks: list[Chunk] = field(default_factory=list)

    @classmethod
    def from_directory(cls, root: Path) -> Corpus:
        chunks: list[Chunk] = []
        for path in sorted(root.glob("**/*.md")):
            text = path.read_text(encoding="utf-8")
            for i, para in enumerate(p for p in text.split("\n\n") if p.strip()):
                chunks.append(Chunk(doc_id=f"{path.stem}#{i}", text=para.strip()))
        return cls(chunks=chunks)


class HybridRetriever:
    def __init__(self, corpus: Corpus) -> None:
        self.corpus = corpus

    def retrieve(self, query: str, config: RAGConfig) -> list[Chunk]:
        q = query.lower()
        tokens = [t for t in q.split() if len(t) > 2]
        scored: list[Chunk] = []
        for chunk in self.corpus.chunks:
            text_lower = chunk.text.lower()
            lexical = sum(1 for t in tokens if t in text_lower) / max(len(tokens), 1)
            semantic = 1.0 if any(k in text_lower for k in ("loop", "harness", "mcp", "memory", "rag")) else 0.0
            if any(k in q for k in ("harness", "mcp")):
                semantic += 0.3 if "harness" in text_lower or "mcp" in text_lower else 0
            score = config.hybrid_alpha * semantic + (1 - config.hybrid_alpha) * lexical
            if score >= config.rerank_threshold:
                scored.append(Chunk(doc_id=chunk.doc_id, text=chunk.text, score=score))
        scored.sort(key=lambda c: c.score, reverse=True)
        return scored[: config.top_k]
