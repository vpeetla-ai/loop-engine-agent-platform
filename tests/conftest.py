collect_ignore = ["fixtures"]

import pytest


@pytest.fixture(autouse=True)
def _default_host_sandbox_for_unit_tests(monkeypatch):
    """Repo-fix / workspace unit tests use host pytest unless a test overrides.

    Explicit sandbox-wrapper tests set LOOPFORGE_SANDBOX_MODE / PRODUCTION_STRICT
    via patch.dict for the duration of their assertions.
    """
    monkeypatch.setenv("LOOPFORGE_SANDBOX_MODE", "host")
    monkeypatch.delenv("PRODUCTION_STRICT", raising=False)
    monkeypatch.delenv("SANDBOX_REQUIRED", raising=False)
