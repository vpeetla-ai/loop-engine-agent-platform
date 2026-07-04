# ADR-002: API-Key Gate on Repo-Fix Endpoints, Documented Isolation Gap

**Status:** Accepted (partial — sandboxing follow-up outstanding)
**Date:** 2026-07-03
**System:** LoopForge (`loop-engine-agent-platform`)

## Context

`POST /api/repo-fix` and `POST /api/hitl/resume` had zero authentication. `/api/repo-fix`
accepts an arbitrary `repo_url` or `local_path`, clones/copies it into a workspace, and runs
`python -m pytest` directly against it (`WorkspaceManager.run_pytest` →
`subprocess.run(["python", "-m", "pytest", ...])`, no container/chroot/seccomp isolation) before
using the server's own `GITHUB_TOKEN` to push a branch and open a PR. `WorkspaceManager` was
docstring-labeled "Sandboxed," which was inaccurate — the only real protections were a
path-escape check in `_resolve` and an allowlist of command *names* (`python`, `pytest`, `pip`,
`ruff`, `git`), neither of which stops a crafted `conftest.py` or test module in an untrusted
repo from executing arbitrary code with this process's privileges. `local_path` additionally let
a caller point at any local directory the API process can read.

Left as-is, if this API is deployed publicly (it has a live Vercel + Render demo per the
README), anyone could point it at any repo, get the server to execute that repo's code, and
potentially cause the server's GitHub identity to open PRs against unrelated repos.

## Decision

1. Add an `X-API-Key` gate (`_require_api_key` in `backend/app/main.py`) on `/api/repo-fix` and
   `/api/hitl/resume` — the two endpoints that clone/execute/push. Enforced only when
   `LOOPFORGE_API_KEY` is set, so local dev/demo without the env var still works; **production
   deployments must set `LOOPFORGE_API_KEY`**.
2. Reject `local_path` outright whenever `LOOPFORGE_API_KEY` is set — it's a dev/testing-only
   convenience and should never be reachable from a production, internet-facing deployment.
3. Correct `WorkspaceManager`'s docstring — it is not sandboxed in the security sense. Document
   the real protections (path-escape check, command-name allowlist) and their limits.
4. Explicitly defer real isolation (running `run_pytest` inside an ephemeral container, gVisor,
   or similar) as a follow-up — it's a separate infrastructure decision (compute cost, whether
   Render's plan supports spinning containers) rather than a same-pass code fix.

## Consequences

### Positive
- Closes the "wide open to the internet" attack surface with a minimal, standard fix.
- `local_path` can no longer be used to make a production deployment read/execute arbitrary
  local files.
- Docstring now tells the truth, so a future reader doesn't inherit a false sense of security.

### Negative
- Authenticated requests can still trigger unsandboxed code execution against a malicious
  `repo_url` — the API key only restricts *who* can trigger it, not what a crafted repo can do
  once triggered. Only point this at trusted repos until real isolation lands.
- One shared API key, no per-caller scoping or rate limiting yet.

### Follow-ups
- ADR-003 (proposed): run `WorkspaceManager.run_pytest` inside an ephemeral container per run.
- ADR-004 (proposed): per-caller API keys + rate limiting if this is opened to more than one
  trusted operator.

## References
- `backend/app/main.py::_require_api_key`, `_reject_local_path_in_production`
- `src/loop_engine/workspace/manager.py::WorkspaceManager`
- Org-wide protocol stack: [ai-architecture-portfolio ADR-007](https://github.com/vpeetla-ai/ai-architecture-portfolio/blob/main/adr/ADR-007-2026-agent-protocol-stack.md)
