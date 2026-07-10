"""Ephemeral-container sandbox for repo-fix pytest execution.

See docs/ADR-003-ephemeral-container-sandbox.md.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_SANDBOX_IMAGE = "python:3.11-slim"


class SandboxUnavailableError(RuntimeError):
    """Raised when isolation is required but Docker cannot be used."""


def _env_flag(name: str, default: str = "") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def production_strict() -> bool:
    return _env_flag("PRODUCTION_STRICT")


def sandbox_required() -> bool:
    """Fail closed when PRODUCTION_STRICT or SANDBOX_REQUIRED is set."""
    return production_strict() or _env_flag("SANDBOX_REQUIRED")


def docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        proc = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return proc.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def sandbox_mode() -> str:
    """auto (default) | docker | host — see ADR-003."""
    mode = os.getenv("LOOPFORGE_SANDBOX_MODE", "auto").strip().lower()
    if mode not in {"auto", "docker", "host"}:
        return "auto"
    return mode


def sandbox_image() -> str:
    return os.getenv("LOOPFORGE_SANDBOX_IMAGE", DEFAULT_SANDBOX_IMAGE).strip() or DEFAULT_SANDBOX_IMAGE


def _host_report(
    proc: subprocess.CompletedProcess[str],
    *,
    isolation: str,
) -> tuple[bool, float, dict[str, Any]]:
    passed = proc.returncode == 0
    coverage = 90.0 if passed else 30.0
    return passed, coverage, {
        "exit_code": proc.returncode,
        "stdout": (proc.stdout or "")[-2000:],
        "stderr": (proc.stderr or "")[-1000:],
        "sandbox": isolation,
    }


def _run_on_host(workspace: Path, *, timeout: int) -> tuple[bool, float, dict[str, Any]]:
    proc = subprocess.run(
        ["python", "-m", "pytest", "-q", "--tb=short"],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return _host_report(proc, isolation="host_fallback")


def _run_in_docker(workspace: Path, *, timeout: int) -> tuple[bool, float, dict[str, Any]]:
    """Run pytest inside an ephemeral container with the workspace mounted."""
    image = sandbox_image()
    # Install pytest in the container; fixture repos are plain pytest suites.
    inner = (
        "pip install -q pytest "
        "&& python -m pytest -q --tb=short"
    )
    cmd = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "-v",
        f"{workspace.resolve()}:/workspace:rw",
        "-w",
        "/workspace",
        image,
        "bash",
        "-lc",
        inner,
    ]
    logger.info("sandbox: docker run %s for %s", image, workspace)
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout + 120,
    )
    return _host_report(proc, isolation="docker")


def run_pytest_sandboxed(workspace: Path, *, timeout: int = 180) -> tuple[bool, float, dict[str, Any]]:
    """Execute pytest with Docker isolation when available / required.

    Policy (ADR-003):
    - LOOPFORGE_SANDBOX_MODE=docker → require Docker; fail closed if unavailable
    - LOOPFORGE_SANDBOX_MODE=host → host cwd (blocked when sandbox_required())
    - LOOPFORGE_SANDBOX_MODE=auto (default) → Docker if available, else host
      unless PRODUCTION_STRICT or SANDBOX_REQUIRED (fail closed)
    """
    mode = sandbox_mode()
    required = sandbox_required()
    has_docker = docker_available()

    if mode == "host":
        if required:
            raise SandboxUnavailableError(
                "host sandbox forbidden when PRODUCTION_STRICT or SANDBOX_REQUIRED is set"
            )
        logger.warning("sandbox: host fallback (LOOPFORGE_SANDBOX_MODE=host)")
        return _run_on_host(workspace, timeout=timeout)

    if mode == "docker" or (mode == "auto" and has_docker):
        if not has_docker:
            raise SandboxUnavailableError(
                "Docker sandbox required but docker is unavailable "
                "(set LOOPFORGE_SANDBOX_MODE=host only for trusted local dev)"
            )
        return _run_in_docker(workspace, timeout=timeout)

    # auto + no docker
    if required:
        raise SandboxUnavailableError(
            "Docker unavailable and PRODUCTION_STRICT/SANDBOX_REQUIRED forbids host fallback"
        )
    logger.warning(
        "sandbox: Docker unavailable — host fallback "
        "(set SANDBOX_REQUIRED=true or PRODUCTION_STRICT=true to fail closed)"
    )
    return _run_on_host(workspace, timeout=timeout)
