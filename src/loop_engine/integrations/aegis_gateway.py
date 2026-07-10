"""AegisAI governance gateway — authorize git push / PR side effects."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

GIT_PUSH_TOOL = "git.push_branch"
GIT_PR_TOOL = "git.open_pull_request"


@dataclass(frozen=True)
class GatewayAuthz:
    allowed: bool
    requires_approval: bool
    blocked: bool
    decision: str
    reason: str
    case_id: str | None = None
    raw: dict[str, Any] | None = None


def gateway_enabled() -> bool:
    return bool(os.getenv("AEGISAI_API_BASE_URL") and os.getenv("AEGISAI_GATEWAY_ENABLED", "").lower() in {"1", "true", "yes"})


def _env_flag(name: str, default: str = "") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def production_strict() -> bool:
    """Org PRODUCTION_STRICT (ACF ADR-024): fail-closed side effects when true."""
    return _env_flag("PRODUCTION_STRICT")


def _fail_open() -> bool:
    """Fail-open is ignored when PRODUCTION_STRICT is set."""
    if production_strict():
        return False
    return _env_flag("AEGISAI_GATEWAY_FAIL_OPEN", "true")


def authorize_git_side_effect(
    *,
    tool_name: str,
    action_type: str,
    target_system: str,
    run_id: str,
    repo_url: str = "",
    branch: str = "",
) -> GatewayAuthz:
    """Synchronous gateway check for git operations (push, open PR)."""
    if not gateway_enabled():
        if production_strict():
            return GatewayAuthz(
                allowed=False,
                requires_approval=False,
                blocked=True,
                decision="block",
                reason="production_strict_gateway_required",
            )
        return GatewayAuthz(
            allowed=True,
            requires_approval=False,
            blocked=False,
            decision="allow",
            reason="gateway_disabled",
        )

    payload = {
        "tenant_id": os.getenv("AEGISAI_TENANT_ID", "loopforge"),
        "agent_id": os.getenv("AEGISAI_AGENT_ID", "loopforge"),
        "principal_id": os.getenv("AEGISAI_PRINCIPAL_ID", "loopforge-bot"),
        "tool_name": tool_name,
        "action_type": action_type,
        "target_system": target_system,
        "amount_usd": 0.0,
        "data_classification": "internal",
        "reversible": True,
        "customer_impact": False,
        "grounding_score": 0.95,
        "safety_score": 0.95,
        "policy_compliance_score": 0.9,
        "case_id": run_id,
        "proposal_id": run_id,
        "metadata": {"repo_url": repo_url, "branch": branch},
    }
    headers = {"Content-Type": "application/json"}
    bearer = os.getenv("AEGISAI_AUTH_BEARER", "")
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    headers["X-AegisAI-Principal"] = payload["principal_id"]
    headers["X-AegisAI-Tenant"] = payload["tenant_id"]
    headers["X-AegisAI-Roles"] = os.getenv("AEGISAI_ROLES", "editor")

    base = os.getenv("AEGISAI_API_BASE_URL", "").rstrip("/")
    url = f"{base}/api/gateway/tool-request"
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("AegisAI gateway unreachable: %s", exc)
        if _fail_open():
            return GatewayAuthz(
                allowed=True,
                requires_approval=False,
                blocked=False,
                decision="allow",
                reason=f"gateway_error_fail_open:{exc}",
            )
        return GatewayAuthz(
            allowed=False,
            requires_approval=False,
            blocked=True,
            decision="block",
            reason=f"gateway_error:{exc}",
        )

    decision = str(data.get("gateway_decision", "block"))
    token = data.get("execution_token")
    allowed = decision == "allow" and bool(token)
    requires_approval = decision == "approval_required"
    blocked = decision in {"block", "deny", "frozen"}
    return GatewayAuthz(
        allowed=allowed,
        requires_approval=requires_approval,
        blocked=blocked,
        decision=decision,
        reason=str(data.get("business_explanation", decision)),
        case_id=str(data.get("case_id") or run_id),
        raw=data,
    )
