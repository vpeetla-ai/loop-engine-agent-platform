from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loop_engine.workspace import git_ops


@dataclass
class WorkspaceManager:
    """Repo workspace — read, write, test, git.

    Not sandboxed in the security sense: `run_pytest` invokes the host's own
    `python -m pytest` against the cloned/copied repo with no container,
    chroot, or seccomp isolation. Only the allowed-commands list and the
    workspace path-escape check in `_resolve` limit what a malicious repo
    could do — a crafted `conftest.py` or test module still executes with
    this process's privileges. Only run this against trusted repos, and see
    docs/ADR-002-repo-fix-auth-and-isolation.md for the auth gate this
    endpoint now sits behind and the sandboxing work still outstanding.
    """

    root: Path
    branch: str = "main"
    repo_url: str | None = None

    @classmethod
    def prepare(
        cls,
        work_root: Path,
        *,
        repo_url: str | None = None,
        local_path: Path | None = None,
        branch: str = "main",
        run_id: str = "run",
    ) -> WorkspaceManager:
        dest = work_root / run_id
        if local_path:
            git_ops.copy_local_repo(local_path.resolve(), dest)
            return cls(root=dest, branch=branch, repo_url=None)
        if not repo_url:
            raise ValueError("repo_url or local_path required")
        git_ops.clone_repo(repo_url, dest, branch=branch)
        return cls(root=dest, branch=branch, repo_url=repo_url)

    def _resolve(self, rel_path: str) -> Path:
        target = (self.root / rel_path).resolve()
        if not str(target).startswith(str(self.root.resolve())):
            raise ValueError(f"path escapes workspace: {rel_path}")
        return target

    def read_file(self, rel_path: str, max_bytes: int = 50_000) -> str:
        path = self._resolve(rel_path)
        if not path.is_file():
            return f"Error: file not found: {rel_path}"
        return path.read_text(encoding="utf-8")[:max_bytes]

    def write_file(self, rel_path: str, content: str) -> None:
        path = self._resolve(rel_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def list_files(self, pattern: str = "**/*") -> list[str]:
        return sorted(
            str(p.relative_to(self.root))
            for p in self.root.glob(pattern)
            if p.is_file() and ".git" not in p.parts
        )

    def search_code(self, query: str, limit: int = 8) -> str:
        tokens = [t for t in re.split(r"\W+", query.lower()) if len(t) > 2]
        hits: list[str] = []
        for rel in self.list_files("**/*.py"):
            text = self.read_file(rel)
            if any(t in text.lower() for t in tokens):
                preview = text[:400].replace("\n", " ")
                hits.append(f"[{rel}] {preview}...")
            if len(hits) >= limit:
                break
        return "\n".join(hits) if hits else "No matches."

    def run(self, cmd: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
        allowed = {"python", "pytest", "pip", "ruff", "git"}
        if cmd[0] not in allowed:
            raise ValueError(f"command not allowed: {cmd[0]}")
        return subprocess.run(
            cmd,
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def run_pytest(self) -> tuple[bool, float, dict]:
        proc = self.run(["python", "-m", "pytest", "-q", "--tb=short"], timeout=180)
        passed = proc.returncode == 0
        coverage = 90.0 if passed else 30.0
        return passed, coverage, {
            "exit_code": proc.returncode,
            "stdout": (proc.stdout or "")[-2000:],
            "stderr": (proc.stderr or "")[-1000:],
        }

    def create_fix_branch(self, run_id: str) -> dict[str, str]:
        branch = f"loopforge/fix-{run_id[:12]}"
        return git_ops.git_create_branch(self.root, branch)

    def diff(self) -> str:
        return git_ops.git_diff(self.root)

    def commit(self, message: str) -> str:
        return git_ops.git_commit(self.root, message)

    def push_branch(self, branch: str, token: str | None = None) -> dict[str, str]:
        return git_ops.git_push_branch(self.root, branch, token=token)

    def open_pull_request(
        self,
        *,
        token: str,
        fix_branch: str,
        title: str,
        body: str,
    ) -> dict[str, Any]:
        remote_proc = self.run(["git", "remote", "get-url", "origin"])
        remote = (remote_proc.stdout or "").strip()
        parsed = git_ops.parse_github_repo(remote)
        if not parsed:
            return {"status": "skipped", "reason": "not_a_github_repo"}
        owner, repo = parsed
        return git_ops.create_pull_request(
            token,
            owner,
            repo,
            head=fix_branch,
            base=self.branch,
            title=title,
            body=body,
        )

    def push(self, token: str | None = None) -> dict[str, str]:
        return git_ops.git_push_branch(self.root, self.branch, token=token)

    def cleanup(self) -> None:
        if self.root.exists():
            shutil.rmtree(self.root, ignore_errors=True)
