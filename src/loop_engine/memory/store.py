from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from loop_engine.rag.retriever import RAGConfig


@dataclass
class Lesson:
    failure_mode: str
    lesson: str
    rag_version: int
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class MemoryStore:
    root: Path
    lessons: list[Lesson] = field(default_factory=list)
    rag_versions: list[RAGConfig] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self._path = self.root / "memory.json"
        if self._path.exists():
            self._load()

    def _load(self) -> None:
        data = json.loads(self._path.read_text(encoding="utf-8"))
        self.lessons = [Lesson(**x) for x in data.get("lessons", [])]
        self.rag_versions = [RAGConfig(**x) for x in data.get("rag_versions", [])]

    def save(self) -> None:
        payload = {
            "lessons": [asdict(l) for l in self.lessons],
            "rag_versions": [asdict(c) for c in self.rag_versions],
        }
        self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def add_lesson(self, lesson: Lesson) -> None:
        self.lessons.append(lesson)
        self.save()

    def record_rag_version(self, config: RAGConfig) -> None:
        self.rag_versions.append(config)
        self.save()

    def hints_for_query(self, query: str) -> str:
        q = query.lower()
        relevant = [
            l.lesson
            for l in self.lessons[-10:]
            if any(t in l.lesson.lower() for t in q.split() if len(t) > 4)
        ]
        if not relevant and self.lessons:
            relevant = [self.lessons[-1].lesson]
        return "\n".join(relevant) if relevant else "(no prior lessons)"
