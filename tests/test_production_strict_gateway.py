"""PRODUCTION_STRICT fail-closed gateway (ACF ADR-024 pattern)."""

from __future__ import annotations

from unittest.mock import patch

from loop_engine.integrations.aegis_gateway import authorize_git_side_effect


def test_production_strict_blocks_when_gateway_disabled():
    with patch.dict(
        "os.environ",
        {
            "PRODUCTION_STRICT": "true",
            "AEGISAI_API_BASE_URL": "",
            "AEGISAI_GATEWAY_ENABLED": "",
            "AEGISAI_GATEWAY_FAIL_OPEN": "true",
        },
        clear=True,
    ):
        authz = authorize_git_side_effect(
            tool_name="git.push_branch",
            action_type="git_push",
            target_system="github",
            run_id="strict-1",
        )
    assert authz.allowed is False
    assert authz.blocked is True
    assert authz.reason == "production_strict_gateway_required"


@patch("loop_engine.integrations.aegis_gateway.gateway_enabled", return_value=True)
@patch("loop_engine.integrations.aegis_gateway.httpx.Client")
def test_production_strict_ignores_fail_open_on_gateway_error(mock_client, _enabled):
    mock_client.return_value.__enter__.return_value.post.side_effect = RuntimeError("down")

    with patch.dict(
        "os.environ",
        {
            "PRODUCTION_STRICT": "true",
            "AEGISAI_API_BASE_URL": "https://aegis.example",
            "AEGISAI_GATEWAY_ENABLED": "true",
            "AEGISAI_GATEWAY_FAIL_OPEN": "true",
        },
        clear=True,
    ):
        authz = authorize_git_side_effect(
            tool_name="git.push_branch",
            action_type="git_push",
            target_system="github",
            run_id="strict-2",
        )

    assert authz.allowed is False
    assert authz.blocked is True
    assert authz.reason.startswith("gateway_error:")


def test_without_production_strict_gateway_disabled_still_allows():
    with patch.dict(
        "os.environ",
        {
            "PRODUCTION_STRICT": "false",
            "AEGISAI_API_BASE_URL": "",
            "AEGISAI_GATEWAY_ENABLED": "",
        },
        clear=True,
    ):
        authz = authorize_git_side_effect(
            tool_name="git.push_branch",
            action_type="git_push",
            target_system="github",
            run_id="dev-1",
        )
    assert authz.allowed is True
    assert authz.reason == "gateway_disabled"
