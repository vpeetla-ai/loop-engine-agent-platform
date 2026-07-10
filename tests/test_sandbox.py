"""Tests for ephemeral container sandbox wrapper (ADR-003)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from loop_engine.workspace.sandbox import (
    SandboxUnavailableError,
    run_pytest_sandboxed,
    sandbox_required,
)


def _fake_proc(*, returncode: int = 0, stdout: str = "ok", stderr: str = "") -> MagicMock:
    proc = MagicMock()
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


def test_sandbox_required_when_production_strict():
    with patch.dict("os.environ", {"PRODUCTION_STRICT": "true"}, clear=False):
        assert sandbox_required() is True


def test_docker_mode_runs_docker_when_available(tmp_path: Path):
    with patch.dict(
        "os.environ",
        {"LOOPFORGE_SANDBOX_MODE": "docker", "PRODUCTION_STRICT": "", "SANDBOX_REQUIRED": ""},
        clear=False,
    ):
        with patch("loop_engine.workspace.sandbox.docker_available", return_value=True):
            with patch(
                "loop_engine.workspace.sandbox.subprocess.run",
                return_value=_fake_proc(returncode=0),
            ) as mock_run:
                passed, coverage, report = run_pytest_sandboxed(tmp_path)

    assert passed is True
    assert coverage >= 80
    assert report["sandbox"] == "docker"
    cmd = mock_run.call_args.args[0]
    assert cmd[0] == "docker"
    assert "run" in cmd
    assert "--network" in cmd
    assert "none" in cmd


def test_docker_required_fails_closed_when_unavailable(tmp_path: Path):
    with patch.dict(
        "os.environ",
        {"LOOPFORGE_SANDBOX_MODE": "auto", "PRODUCTION_STRICT": "true"},
        clear=False,
    ):
        with patch("loop_engine.workspace.sandbox.docker_available", return_value=False):
            with pytest.raises(SandboxUnavailableError, match="PRODUCTION_STRICT"):
                run_pytest_sandboxed(tmp_path)


def test_sandbox_required_fails_closed_without_docker(tmp_path: Path):
    with patch.dict(
        "os.environ",
        {"LOOPFORGE_SANDBOX_MODE": "auto", "SANDBOX_REQUIRED": "true", "PRODUCTION_STRICT": ""},
        clear=False,
    ):
        with patch("loop_engine.workspace.sandbox.docker_available", return_value=False):
            with pytest.raises(SandboxUnavailableError):
                run_pytest_sandboxed(tmp_path)


def test_auto_falls_back_to_host_when_docker_missing(tmp_path: Path):
    with patch.dict(
        "os.environ",
        {"LOOPFORGE_SANDBOX_MODE": "auto", "PRODUCTION_STRICT": "", "SANDBOX_REQUIRED": ""},
        clear=False,
    ):
        with patch("loop_engine.workspace.sandbox.docker_available", return_value=False):
            with patch(
                "loop_engine.workspace.sandbox.subprocess.run",
                return_value=_fake_proc(returncode=1, stdout="fail"),
            ) as mock_run:
                passed, coverage, report = run_pytest_sandboxed(tmp_path)

    assert passed is False
    assert coverage < 80
    assert report["sandbox"] == "host_fallback"
    assert mock_run.call_args.args[0][0] == "python"


def test_host_mode_blocked_when_sandbox_required(tmp_path: Path):
    with patch.dict(
        "os.environ",
        {"LOOPFORGE_SANDBOX_MODE": "host", "SANDBOX_REQUIRED": "true"},
        clear=False,
    ):
        with pytest.raises(SandboxUnavailableError, match="host sandbox forbidden"):
            run_pytest_sandboxed(tmp_path)
