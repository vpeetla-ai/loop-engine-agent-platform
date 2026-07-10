# ADR-003: Ephemeral Container Sandbox for Repo-Fix Pytest

**Status:** Accepted
**Date:** 2026-07-09
**System:** LoopForge (`loop-engine-agent-platform`)

## Context

[ADR-002](ADR-002-repo-fix-auth-and-isolation.md) authenticated `/api/repo-fix` but deferred real
isolation: `WorkspaceManager.run_pytest` still invoked the host's `python -m pytest` against a
cloned repo. A crafted `conftest.py` could execute with the API process identity.

Real isolation is the infrastructure follow-up named in ADR-002.

## Decision

1. Route all repo-fix / workspace `run_pytest` calls through
   `loop_engine.workspace.sandbox.run_pytest_sandboxed`.
2. Prefer an **ephemeral Docker container** per run:
   - `docker run --rm --network none -v <workspace>:/workspace -w /workspace <image>`
   - Default image: `python:3.11-slim` (override with `LOOPFORGE_SANDBOX_IMAGE`)
3. Env gates:
   - `LOOPFORGE_SANDBOX_MODE=auto|docker|host` (default `auto`)
   - `SANDBOX_REQUIRED=true` or `PRODUCTION_STRICT=true` → **fail closed** if Docker cannot be used
   - Without those flags, document a **host fallback** for local/dev when Docker is missing
4. Do not change the API surface — only the execution path of `WorkspaceManager.run_pytest`.

## Consequences

### Positive
- Untrusted repo test code no longer shares the API process namespace when Docker is present.
- Production can enforce isolation via `PRODUCTION_STRICT` / `SANDBOX_REQUIRED` without a deploy
  code fork.
- Tests mock `docker` so CI does not need a nested Docker daemon for unit coverage of the wrapper.

### Negative
- Host fallback remains available in non-strict mode — honest README status is **Partial** until
  production Always-On Docker is the only supported path.
- First container run pays `pip install pytest` cost inside the ephemeral image.
- Render free-tier may not expose a Docker socket; deploy docs must set
  `PRODUCTION_STRICT`/`SANDBOX_REQUIRED` only where Docker is available, or refuse repo-fix.

### Follow-ups
- Read-only mounts + separate writable pytest cache volume
- gVisor / Firecracker if Docker-on-Docker is unavailable in the target host
- Extend the same wrapper to in-graph `_run_pytest_in_sandbox` (coding-loop temp tests)

## References
- `src/loop_engine/workspace/sandbox.py`
- `src/loop_engine/workspace/manager.py::WorkspaceManager.run_pytest`
- Org `PRODUCTION_STRICT` pattern (ACF ADR-024)
