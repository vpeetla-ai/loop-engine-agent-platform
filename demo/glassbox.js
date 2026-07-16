/**
 * LoopForge glass-box harness UX — ODAEU phase replay from POST /api/run trace events.
 * Replay (not SSE): highlights diagram nodes as events play back.
 */
(function (global) {
  const PHASE_ORDER = ["observe", "decide", "act", "evaluate", "update"];
  const PHASE_LABELS = {
    observe: "Observe",
    decide: "Decide",
    act: "Act",
    evaluate: "Evaluate",
    update: "Update",
  };
  const PHASE_COLORS = {
    observe: "var(--gb-observe)",
    decide: "var(--gb-decide)",
    act: "var(--gb-act)",
    evaluate: "var(--gb-evaluate)",
    update: "var(--gb-update)",
  };

  const DEMO_HARNESS = {
    run_id: "demo-local",
    query: "What is loop engineering?",
    answer: "[demo] Loop engineering closes ODAEU cycles: observe retrieval, decide strategy, act, evaluate, update RAG config and lessons.",
    passed: true,
    iterations: 1,
    final_rag_version: 1,
    runtime_ms: 420,
    eval: { passed: true, recall: 0.72, faithfulness: 0.81, failure_mode: null },
    trace: {
      events: [
        { phase: "observe", name: "iteration.start", payload: { iteration: 1, rag_version: 1 } },
        { phase: "observe", name: "memory.hints", payload: { hint_count: 1, preview: "(no prior lessons)" } },
        { phase: "observe", name: "rag.retrieve", payload: { top_k: 5, chunk_ids: ["doc-1"] } },
        { phase: "decide", name: "attempt.plan", payload: { strategy: "react_then_answer" } },
        { phase: "act", name: "answer.draft", payload: { answer: "[demo draft]" } },
        { phase: "evaluate", name: "eval.score", payload: { passed: true, recall: 0.72, faithfulness: 0.81 } },
        { phase: "evaluate", name: "run.passed", payload: { iteration: 1 } },
        { phase: "update", name: "run.complete", payload: { rag_version: 1, lesson_written: false } },
      ],
    },
  };

  function $(id) {
    return document.getElementById(id);
  }

  function resetDiagram() {
    document.querySelectorAll(".gb-node").forEach((n) => {
      n.classList.remove("gb-active", "gb-done");
    });
    PHASE_ORDER.forEach((p) => {
      const pill = $("gb-pill-" + p);
      if (pill) pill.classList.remove("gb-active", "gb-done");
    });
  }

  function markPhase(phase, state) {
    const node = $("gb-node-" + phase);
    if (node) {
      node.classList.remove("gb-active", "gb-done");
      if (state) node.classList.add(state);
    }
    const pill = $("gb-pill-" + phase);
    if (pill) {
      pill.classList.remove("gb-active", "gb-done");
      if (state) pill.classList.add(state);
    }
  }

  function renderPills() {
    const wrap = $("gbPills");
    if (!wrap) return;
    wrap.innerHTML = PHASE_ORDER.map(
      (p) =>
        `<span class="gb-pill" id="gb-pill-${p}" style="--pill-color:${PHASE_COLORS[p]}">${PHASE_LABELS[p]}</span>`
    ).join('<span class="gb-pill-arrow">→</span>');
  }

  function setGate(text) {
    const el = $("gbGate");
    if (el) el.textContent = text;
  }

  function setMemory(lessons, ragLine) {
    const l = $("gbLessons");
    const r = $("gbRag");
    if (l) l.textContent = lessons;
    if (r) r.textContent = ragLine;
  }

  function setOps(data) {
    const el = $("gbOps");
    if (!el) return;
    el.innerHTML = [
      `<span><strong>run</strong> ${data.run_id || "—"}</span>`,
      `<span><strong>iter</strong> ${data.iterations ?? "—"}</span>`,
      `<span><strong>passed</strong> ${data.passed ? "yes" : "no"}</span>`,
      `<span><strong>rag v</strong> ${data.final_rag_version ?? "—"}</span>`,
      `<span><strong>latency</strong> ${data.runtime_ms != null ? data.runtime_ms + " ms" : "n/a"}</span>`,
    ].join("");
  }

  function setEval(evalObj) {
    const el = $("gbEval");
    if (!el || !evalObj) return;
    const badge = evalObj.passed ? "PASS" : "FAIL";
    el.innerHTML = `<span class="gb-eval-badge ${evalObj.passed ? "pass" : "fail"}">${badge}</span>
      recall ${(evalObj.recall ?? 0).toFixed(2)} · faithfulness ${(evalObj.faithfulness ?? 0).toFixed(2)}
      ${evalObj.failure_mode ? " · " + evalObj.failure_mode : ""}`;
  }

  function setAnswer(text) {
    const el = $("gbAnswer");
    if (el) el.textContent = text || "";
  }

  function appendEvent(ev, live) {
    const log = $("gbEventLog");
    if (!log) return;
    const row = document.createElement("div");
    row.className = "gb-event" + (live ? " gb-event-live" : "");
    const color = PHASE_COLORS[ev.phase] || "var(--muted)";
    row.innerHTML = `<span class="gb-event-phase" style="color:${color}">[${ev.phase}]</span>
      <strong>${ev.name}</strong>
      <pre>${JSON.stringify(ev.payload || {}, null, 0)}</pre>`;
    log.appendChild(row);
    log.scrollTop = log.scrollHeight;
  }

  function extractMemoryFromEvents(events, finalRagVersion) {
    let lessons = "—";
    let rag = `final v${finalRagVersion ?? "—"}`;
    for (const ev of events) {
      if (ev.name === "memory.hints") {
        lessons = ev.payload?.preview || `(hints: ${ev.payload?.hint_count ?? 0})`;
      }
      if (ev.name === "evolve.rag") {
        rag = `v${ev.payload?.from_version} → v${ev.payload?.to_version}`;
        if (ev.payload?.lesson) lessons = String(ev.payload.lesson).slice(0, 200);
      }
      if (ev.name === "run.complete") {
        rag = `v${ev.payload?.rag_version ?? finalRagVersion}`;
      }
    }
    return { lessons, rag };
  }

  function gateFromEvents(events) {
    const retrieve = [...events].reverse().find((e) => e.name === "rag.retrieve");
    const hints = [...events].reverse().find((e) => e.name === "memory.hints");
    if (!retrieve && !hints) return "no turns yet — run a harness query";
    const chunks = retrieve?.payload?.chunk_ids?.length ?? 0;
    const hintsN = hints?.payload?.hint_count ?? 0;
    return `retrieve ${chunks} chunk(s) · procedural hints ${hintsN} · replay (not live SSE)`;
  }

  async function playReplay(data, stepMs) {
    const events = data.trace?.events || [];
    resetDiagram();
    const log = $("gbEventLog");
    if (log) log.innerHTML = "";

    setGate(gateFromEvents(events));
    const mem = extractMemoryFromEvents(events, data.final_rag_version);
    setMemory(mem.lessons, mem.rag);
    setOps(data);
    setEval(data.eval);
    setAnswer(data.answer);

    const donePhases = new Set();
    for (let i = 0; i < events.length; i++) {
      const ev = events[i];
      markPhase(ev.phase, "gb-active");
      if (ev.name === "rag.retrieve" || ev.name === "memory.hints") {
        setGate(gateFromEvents(events.slice(0, i + 1)));
      }
      appendEvent(ev, true);
      await new Promise((r) => setTimeout(r, stepMs));
      donePhases.add(ev.phase);
      markPhase(ev.phase, "gb-done");
      document.querySelectorAll(".gb-event.gb-event-live").forEach((el) => el.classList.remove("gb-event-live"));
    }
    PHASE_ORDER.forEach((p) => {
      if (donePhases.has(p)) markPhase(p, "gb-done");
    });
  }

  async function runHarness(apiBase, query) {
    const status = $("gbStatus");
    const btn = $("gbRunBtn");
    if (btn) btn.disabled = true;
    if (status) status.textContent = "Running harness…";
    resetDiagram();
    setAnswer("");
    setEval(null);
    if ($("gbEventLog")) $("gbEventLog").innerHTML = "";

    let data;
    const started = performance.now();
    try {
      if (!apiBase) {
        await new Promise((r) => setTimeout(r, 400));
        data = { ...DEMO_HARNESS, query };
        if (status) status.textContent = "demo_fallback — set LOOPFORGE_API for live trace";
      } else {
        const res = await fetch(apiBase.replace(/\/$/, "") + "/api/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query, gold_keywords: [] }),
        });
        data = await res.json();
        if (!res.ok) throw new Error(data.detail || res.statusText);
        if (data.runtime_ms == null) {
          data.runtime_ms = Math.round(performance.now() - started);
        }
        if (status) status.textContent = `live · run ${data.run_id}`;
      }
      await playReplay(data, 380);
    } catch (err) {
      if (status) status.textContent = "API error — replaying demo_fallback";
      data = { ...DEMO_HARNESS, query };
      await playReplay(data, 320);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  function init() {
    renderPills();
    const btn = $("gbRunBtn");
    const input = $("gbQuery");
    if (btn) {
      btn.onclick = () => {
        const q = (input?.value || "").trim();
        if (!q) return;
        const api = global.LOOPFORGE_API || "";
        runHarness(api, q);
      };
    }
    if (input) {
      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") btn?.click();
      });
    }
  }

  global.LoopForgeGlassBox = { init, playReplay, runHarness, DEMO_HARNESS };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window);
