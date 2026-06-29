from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def _run(cmd: list[str], cwd: Path, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    )


def parse_github_repo(remote_url: str) -> tuple[str, str] | None:
    """Extract owner/repo from HTTPS or SSH GitHub remote."""
    url = remote_url.strip().rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    # git@github.com:owner/repo
    ssh = re.match(r"git@github\.com:(?P<owner>[^/]+)/(?P<repo>[^/]+)$", url)
    if ssh:
        return ssh.group("owner"), ssh.group("repo")
    parsed = urlparse(url if "://" in url else f"https://{url}")
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) >= 2 and "github.com" in (parsed.netloc or url):
        return parts[0], parts[1].replace(".git", "")
    return None


def clone_repo(repo_url: str, dest: Path, branch: str = "main") -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        shutil.rmtree(dest)
    proc = _run(
        ["git", "clone", "--depth", "1", "--branch", branch, repo_url, str(dest)],
        cwd=dest.parent,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git clone failed: {proc.stderr.strip() or proc.stdout}")


def copy_local_repo(source: Path, dest: Path, remote_url: str | None = None) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(source, dest, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"))
    _run(["git", "init"], cwd=dest)
    if remote_url:
        _run(["git", "remote", "add", "origin", remote_url], cwd=dest)
    _run(["git", "add", "-A"], cwd=dest)
    _run(["git", "commit", "-m", "initial"], cwd=dest)


def git_create_branch(cwd: Path, branch: str) -> dict[str, str]:
    proc = _run(["git", "checkout", "-b", branch], cwd=cwd)
    if proc.returncode != 0:
        return {"status": "failed", "error": proc.stderr.strip() or proc.stdout}
    return {"status": "created", "branch": branch}


def git_diff(cwd: Path) -> str:
    proc = _run(["git", "diff", "HEAD"], cwd=cwd)
    staged = _run(["git", "diff", "--cached"], cwd=cwd)
    return (proc.stdout or "") + (staged.stdout or "")


def git_status(cwd: Path) -> str:
    proc = _run(["git", "status", "--short"], cwd=cwd)
    return proc.stdout.strip()


def git_commit(cwd: Path, message: str) -> str:
    _run(["git", "add", "-A"], cwd=cwd)
    proc = _run(["git", "commit", "-m", message], cwd=cwd)
    if proc.returncode != 0 and "nothing to commit" in (proc.stdout + proc.stderr):
        return "no_changes"
    if proc.returncode != 0:
        raise RuntimeError(f"git commit failed: {proc.stderr.strip()}")
    sha_proc = _run(["git", "rev-parse", "HEAD"], cwd=cwd)
    return sha_proc.stdout.strip()


def _with_auth_remote(cwd: Path, token: str | None):
    remote_proc = _run(["git", "remote", "get-url", "origin"], cwd=cwd)
    remote = remote_proc.stdout.strip()
    if not token or not remote.startswith("https://"):
        return remote, None
    authed = remote.replace("https://", f"https://x-access-token:{token}@")
    _run(["git", "remote", "set-url", "origin", authed], cwd=cwd)
    return remote, authed


def _restore_remote(cwd: Path, original: str, authed: str | None) -> None:
    if authed:
        _run(["git", "remote", "set-url", "origin", original], cwd=cwd)


def git_push_branch(cwd: Path, branch: str, token: str | None = None) -> dict[str, str]:
    remote_proc = _run(["git", "remote", "get-url", "origin"], cwd=cwd)
    remote = remote_proc.stdout.strip()
    if not remote:
        return {"status": "skipped", "reason": "no_remote"}

    original, authed = _with_auth_remote(cwd, token)
    push_cmd = ["git", "push", "-u", "origin", branch]
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    try:
        proc = subprocess.run(push_cmd, cwd=cwd, capture_output=True, text=True, timeout=180, env=env)
    finally:
        _restore_remote(cwd, original, authed)

    if proc.returncode != 0:
        return {"status": "failed", "error": (proc.stderr or proc.stdout)[-500:]}
    return {"status": "pushed", "branch": branch}


def create_pull_request(
    token: str,
    owner: str,
    repo: str,
    *,
    head: str,
    base: str,
    title: str,
    body: str,
) -> dict[str, Any]:
    import httpx

    resp = httpx.post(
        f"https://api.github.com/repos/{owner}/{repo}/pulls",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json={"title": title, "body": body, "head": head, "base": base},
        timeout=60.0,
    )
    if resp.status_code >= 400:
        return {"status": "failed", "error": resp.text[-500:], "http_status": resp.status_code}
    data = resp.json()
    return {
        "status": "created",
        "pr_number": data.get("number"),
        "pr_url": data.get("html_url"),
        "branch": head,
    }


# Backward compat — direct push to branch (avoid for main)
def git_push(cwd: Path, branch: str, token: str | None = None) -> dict[str, str]:
    return git_push_branch(cwd, branch, token=token)
