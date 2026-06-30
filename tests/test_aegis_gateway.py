"""Tests for AegisAI gateway on git push / PR."""

from __future__ import annotations

from unittest.mock import patch

from loop_engine.integrations.aegis_gateway import (
    GatewayAuthz,
    authorize_git_side_effect,
    gateway_enabled,
)


def test_gateway_disabled_by_default():
    with patch.dict("os.environ", {}, clear=True):
        assert gateway_enabled() is False
        authz = authorize_git_side_effect(
            tool_name="git.push_branch",
            action_type="git_push",
            target_system="github",
            run_id="r1",
        )
    assert authz.allowed is True
    assert authz.reason == "gateway_disabled"


@patch("loop_engine.integrations.aegis_gateway.gateway_enabled", return_value=True)
@patch("loop_engine.integrations.aegis_gateway.httpx.Client")
def test_gateway_blocks_push(mock_client, _enabled):
    mock_response = mock_client.return_value.__enter__.return_value.post.return_value
    mock_response.raise_for_status = lambda: None
    mock_response.json.return_value = {
        "gateway_decision": "block",
        "business_explanation": "policy",
    }

    with patch.dict(
        "os.environ",
        {
            "AEGISAI_API_BASE_URL": "https://aegis.example",
            "AEGISAI_GATEWAY_ENABLED": "true",
            "AEGISAI_GATEWAY_FAIL_OPEN": "false",
        },
    ):
        authz = authorize_git_side_effect(
            tool_name="git.push_branch",
            action_type="git_push",
            target_system="github",
            run_id="r2",
        )

    assert authz.blocked is True
    assert authz.allowed is False
