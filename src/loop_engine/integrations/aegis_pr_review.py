"""Shell out to aegis-pr-review CLI (shared PR-review brain)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def run_aegis_pr_review(
    repo: Path,
    *,
    base: str | None = None,
    head: str = "HEAD",
    repo_name: str | None = None,
) -> dict[str, Any] | None:
    """Run `aegis-pr-review review` on a working tree.

    Returns parsed report dict, or None if the CLI is unavailable / fails hard.
    Disabled when AEGIS_PR_REVIEW=0.
    """
    if os.getenv("AEGIS_PR_REVIEW", "1").strip() in {"0", "false", "off"}:
        return None

    base = base or os.getenv("AEGIS_PR_REVIEW_BASE", "HEAD~1")
    cmd = [
        sys.executable,
        "-m",
        "aegis_pr_review",
        "review",
        "--repo",
        str(repo),
        "--base",
        base,
        "--head",
        head,
    ]
    if repo_name:
        cmd.extend(["--repo-name", repo_name])

    env = os.environ.copy()
    env.setdefault("AEGIS_PR_REVIEW_LLM_MODE", "stub")

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            env=env,
            timeout=float(os.getenv("AEGIS_PR_REVIEW_TIMEOUT", "120")),
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    stdout = (proc.stdout or "").strip()
    if not stdout.startswith("{"):
        # Module missing or git diff failed
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


def report_to_review_fields(report: dict[str, Any]) -> dict[str, Any]:
    """Map Aegis findings into LoopForge review_score / review_issues."""
    findings = list(report.get("findings") or [])
    crit = sum(1 for f in findings if str(f.get("severity", "")).lower() == "critical")
    high = sum(1 for f in findings if str(f.get("severity", "")).lower() == "high")

    if crit:
        score = 0.35
    elif high:
        score = 0.55
    elif findings:
        score = 0.72
    else:
        score = 0.88

    issues: list[dict[str, Any]] = []
    for f in findings:
        sev = str(f.get("severity") or "medium").lower()
        issue_type = "security" if sev == "critical" else "correctness"
        if str(f.get("rule_id") or "").startswith("access") or "policy" in str(f.get("pass_id") or ""):
            issue_type = "security"
        issues.append(
            {
                "line": f.get("line") or 1,
                "type": issue_type,
                "severity": sev,
                "suggestion": f"{f.get('title', '')}: {f.get('fix_hint') or f.get('why') or ''}".strip(),
                "rule_id": f.get("rule_id"),
                "path": f.get("path"),
            }
        )

    dimensions = {
        "correctness": score,
        "security": 0.3 if crit else (0.6 if high else score),
        "complexity": 0.8,
        "style": 0.8,
        "source": "aegis-pr-review",
    }
    return {
        "review_score": score,
        "review_dimensions": dimensions,
        "review_issues": issues,
        "aegis_pr_review": {
            "summary": report.get("summary"),
            "finding_count": len(findings),
            "critical": crit,
            "high": high,
            "llm_mode": report.get("llm_mode"),
        },
    }
