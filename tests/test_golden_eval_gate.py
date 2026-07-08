"""Golden eval registry gates — harness_qa + repo_fix suites."""

from __future__ import annotations

import os
import shutil
import unittest
from pathlib import Path

import pytest

from loop_engine.graph.repo_build import run_repo_fix
from loop_engine.harness.agent_harness import AgentHarness
from loop_engine.models.llm import MockLLM

try:
    from golden_eval_registry.runner import score_suite
    from golden_eval_registry.schema import parse_manifest
    from golden_eval_registry.validate import load_jsonl

    GOLDEN_EVAL_REGISTRY_AVAILABLE = True
except ImportError:
    GOLDEN_EVAL_REGISTRY_AVAILABLE = False

REGISTRY_PATH = Path(os.getenv("GOLDEN_EVAL_REGISTRY_PATH", "../golden-eval-registry")).resolve()
BENCHMARK_SUITE = REGISTRY_PATH / "suites" / "loopforge_benchmark_v1"
REPO_FIX_SUITE = REGISTRY_PATH / "suites" / "loopforge_repo_fix_v1"

pytestmark = pytest.mark.skipif(
    not GOLDEN_EVAL_REGISTRY_AVAILABLE,
    reason="golden-eval-registry not installed",
)


@pytest.mark.skipif(not BENCHMARK_SUITE.exists(), reason="benchmark suite missing")
def test_loopforge_benchmark_v1_suite_passes(tmp_path: Path) -> None:
    manifest = parse_manifest(BENCHMARK_SUITE / "manifest.json")
    cases = load_jsonl(manifest.cases_path)
    corpus_dir = BENCHMARK_SUITE / "corpus"

    harness = AgentHarness(
        llm=MockLLM(),
        corpus_dir=corpus_dir,
        memory_dir=tmp_path / "memory",
        max_evolve_iterations=3,
    )

    actual_by_id: dict[str, dict] = {}
    for case in cases:
        payload = case["input"]
        result = harness.run(payload["query"], gold_keywords=payload.get("gold_keywords"))
        actual_by_id[str(case["id"])] = {
            "answer": result.answer,
            "passed": result.passed,
            "recall": result.eval.get("recall", 0),
            "faithfulness": result.eval.get("faithfulness", 0),
        }

    suite_result = score_suite(manifest, cases, actual_by_id)
    failures = "\n".join(f"{f.case_id}: {f.detail}" for f in suite_result.failures)
    assert suite_result.passed, f"golden eval regressions:\n{failures}"


@pytest.mark.asyncio
@pytest.mark.skipif(not REPO_FIX_SUITE.exists(), reason="repo_fix suite missing")
async def test_loopforge_repo_fix_v1_suite_passes(tmp_path: Path) -> None:
    manifest = parse_manifest(REPO_FIX_SUITE / "manifest.json")
    cases = load_jsonl(manifest.cases_path)

    actual_by_id: dict[str, dict] = {}
    for case in cases:
        fixture_src = REPO_FIX_SUITE / case["fixture_ref"]
        fixture_copy = tmp_path / case["id"] / "repo"
        shutil.copytree(fixture_src, fixture_copy)

        result = await run_repo_fix(
            case["input"]["task"],
            local_path=fixture_copy,
            mode=case["input"].get("mode", "bugfix"),
            create_pr=False,
            llm=MockLLM(),
            memory_dir=tmp_path / case["id"] / "memory",
            work_root=tmp_path / case["id"] / "work",
            max_iterations=3,
        )
        actual_by_id[str(case["id"])] = {
            "pytest_passed": result.get("test_passed", False),
            "branch": result.get("pr_branch") or f"loopforge/fix-{result.get('run_id', 'run')[:12]}",
            "patches": result.get("patches") or [],
            "coverage_pct": result.get("coverage_pct", 0),
        }

    suite_result = score_suite(manifest, cases, actual_by_id)
    failures = "\n".join(f"{f.case_id}: {f.detail}" for f in suite_result.failures)
    assert suite_result.passed, f"golden eval regressions:\n{failures}"
