"""Optional Langfuse export for harness and repo-fix traces."""

from __future__ import annotations

import logging
import os
from typing import Any

from loop_engine.tracing import Trace

logger = logging.getLogger(__name__)


def langfuse_configured() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))


def export_trace(trace: Trace, *, name: str = "loopforge.harness", metadata: dict[str, Any] | None = None) -> None:
    """Export in-process Trace to Langfuse when keys are set."""
    if not langfuse_configured():
        return
    try:
        from langfuse import Langfuse
    except ImportError:
        logger.debug("langfuse package not installed — skipping export")
        return

    try:
        client = Langfuse(
            public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
            secret_key=os.environ["LANGFUSE_SECRET_KEY"],
            host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        )
        root = client.trace(id=trace.run_id, name=name, metadata=metadata or {})
        for event in trace.events:
            root.span(
                name=f"{event.phase}.{event.name}",
                metadata=event.payload,
            )
        client.flush()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Langfuse export failed: %s", exc)


def export_trace_events(
    run_id: str,
    events: list[dict[str, Any]],
    *,
    name: str = "loopforge.repo_fix",
) -> None:
    """Export repo-fix trace_events list to Langfuse."""
    if not langfuse_configured() or not events:
        return
    trace = Trace(run_id=run_id)
    for ev in events:
        trace.add(ev.get("phase", "act"), ev.get("name", "event"), **(ev.get("payload") or {}))
    export_trace(trace, name=name)
