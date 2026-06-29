from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TraceEvent:
    phase: str
    name: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class Trace:
    run_id: str
    events: list[TraceEvent] = field(default_factory=list)

    def add(self, phase: str, name: str, **payload: Any) -> None:
        self.events.append(TraceEvent(phase=phase, name=name, payload=payload))

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "events": [
                {"phase": e.phase, "name": e.name, "payload": e.payload} for e in self.events
            ],
        }
