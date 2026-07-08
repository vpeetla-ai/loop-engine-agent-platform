window.ARCHITECT_CONFIG = {
  tagline:
    "Self-improving agent harness: ODAEU loop, LangGraph agent loop, and repo-fix graph with golden eval gates — improvement is a system, not a prompt tweak.",
  metricsUrl: (window.LOOPFORGE_API || "https://loopforge-api.onrender.com") + "/api/v1/ops/metrics",
  metricsPath: "/api/v1/ops/metrics",
  metricLabels: { runs: "Harness traces", entities: "Unique run IDs", latency: "P95 runtime" },
  layers: [
    { tier: "L1", name: "Harness UI", role: "Loop visibility", components: ["ODAEU diagram", "Benchmark tab", "Repo-fix flow"] },
    { tier: "L2", name: "Graphs", role: "Three loop types", components: ["ODAEU harness", "LangGraph loop", "Repo-fix + HITL"] },
    { tier: "L3", name: "Eval", role: "Prove improvement", components: ["Golden benchmark", "repo_fix CI", "Mock/Groq LLM"] },
    { tier: "L4", name: "Ops", role: "Trace store", components: ["In-memory traces", "/api/v1/ops/metrics", "Security scan CI"] },
  ],
  tradeoffs: [
    { decision: "Separate harness from production orchestrator", gain: "Tune loops without risking prod graphs", trade: "Two codepaths to keep aligned" },
    { decision: "API key gate on repo-fix", gain: "Blocks arbitrary code execution abuse", trade: "Extra secret for live fix demos" },
    { decision: "In-memory trace store", gain: "Simple portfolio deploy", trade: "Metrics reset on API restart" },
    { decision: "Mock LLM default", gain: "CI + demo without spend", trade: "Fix quality ≠ prod model quality" },
  ],
};
