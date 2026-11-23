/**
 * Griductive Web Frontend Controller.
 * Talks exclusively to the local Python JSON API (PublicState only).
 */
(function () {
  const DIFFICULTY_LEVELS = { Easy: 2, Normal: 4, Medium: 5, Hard: 6, Stress: 7 };
  const SPEEDS = [
    { label: "1×", ms: 420 },
    { label: "2×", ms: 200 },
    { label: "4×", ms: 85 },
  ];

  const $ = (id) => document.getElementById(id);

  const state = {
    cases: [],
    data: null,
    puzzleKey: null,
    focus: null,
    highlights: new Set(),
    hintTarget: null,
    callingCell: null,
    markMode: false,
    marks: {},            // cell_id -> "INNOCENT" | "CRIMINAL"
    autoRunning: false,
    autoTimer: null,
    speedIdx: 0,
    elapsedSec: 0,
    timerPaused: false,
    timerInterval: null,
    victoryShown: false,
    genSize: { rows: 5, cols: 4 },
  };

  // ── API Helper ─────────────────────────────────────────────────────────────
  async function api(path, body = null) {
    const opts = body === null
      ? { method: "GET" }
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        };
    const res = await fetch(path, opts);
    const payload = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(payload.error || `Request failed (${res.status})`);
    }
    return payload;
  }

  // ── Toast & Feedback ───────────────────────────────────────────────────────
  function toast(message, tone = "info") {
    const host = $("toastHost");
    const el = document.createElement("div");
    el.className = `toast ${tone}`;
    el.textContent = message;
    host.appendChild(el);
    setTimeout(() => {
      el.style.opacity = "0";
      el.style.transform = "translateY(8px)";
      el.style.transition = "all 0.22s ease";
      setTimeout(() => el.remove(), 230);
    }, 3000);
  }

  function setFeedback(text, tone = "neutral") {
    const el = $("feedbackBanner");
    el.textContent = text;
    el.dataset.tone = tone;
  }

  function escapeHTML(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function formatClueHTML(text) {
    return escapeHTML(text).replace(/\b([A-Z]\d+)\b/g, '<span class="cell-ref-chip">$1</span>');
  }

  // ── Theme Switcher (Dark Noir ↔ Warm Paper) ────────────────────────────────
  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("griductive_theme", theme);
    const isNoir = theme === "noir";
    $("themeLabel").textContent = isNoir ? "Paper" : "Noir";
    $("themeIcon").innerHTML = isNoir
      ? '<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/>'
      : '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>';
  }

  // ── Puzzle Timer ───────────────────────────────────────────────────────────
  function resetTimer() {
    state.elapsedSec = 0;
    state.timerPaused = false;
    renderTimer();
    updateTimerIcon();
    if (state.timerInterval) clearInterval(state.timerInterval);
    state.timerInterval = setInterval(() => {
      if (!state.timerPaused && state.data && !state.data.solved) {
        state.elapsedSec += 1;
        renderTimer();
      }
    }, 1000);
  }

  function renderTimer() {
    const m = String(Math.floor(state.elapsedSec / 60)).padStart(2, "0");
    const s = String(state.elapsedSec % 60).padStart(2, "0");
    $("timerDisplay").textContent = `${m}:${s}`;
  }

  function updateTimerIcon() {
    $("timerIcon").innerHTML = state.timerPaused
      ? '<polygon points="6,4 20,12 6,20"/>'
      : '<rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/>';
  }

  // ── Responsive Card Dimensions ─────────────────────────────────────────────
  function computeCardMetrics(rows, cols) {
    const stage = $("boardStage");
    const rect = stage.getBoundingClientRect();
    const availW = Math.max(420, rect.width - 36);
    const availH = Math.max(420, rect.height - 84);
    const gap = rows >= 5 || cols >= 5 ? 8 : 11;

    const maxW = (availW - (cols - 1) * gap) / cols;
    const maxH = (availH - (rows - 1) * gap) / rows;

    const cardH = Math.max(106, Math.min(148, maxH));
    const cardW = Math.max(106, Math.min(146, maxW, cardH * 1.03));
    const finalH = Math.max(106, Math.min(cardH, cardW * 1.1));

    const root = document.documentElement.style;
    root.setProperty("--cols", cols);
    root.setProperty("--rows", rows);
    root.setProperty("--card-w", `${Math.floor(cardW)}px`);
    root.setProperty("--card-h", `${Math.floor(finalH)}px`);
    root.setProperty("--card-gap", `${gap}px`);
  }

  // ── Build Grid DOM Once per Loaded Puzzle (Enables Smooth 3D Flips!) ───────
  function colLabel(col) {
    let label = "";
    let n = col;
    while (n > 0) {
      const rem = (n - 1) % 26;
      label = String.fromCharCode(65 + rem) + label;
      n = Math.floor((n - 1) / 26);
    }
    return label;
  }

  function buildGridDOM(data) {
    const { num_rows: rows, num_cols: cols } = data.puzzle;
    computeCardMetrics(rows, cols);

    // Column & row headers
    const colHead = $("colHeaders");
    colHead.innerHTML = "";
    for (let c = 1; c <= cols; c++) {
      const el = document.createElement("div");
      el.className = "col-header";
      el.textContent = colLabel(c);
      colHead.appendChild(el);
    }

    const rowHead = $("rowHeaders");
    rowHead.innerHTML = "";
    for (let r = 1; r <= rows; r++) {
      const el = document.createElement("div");
      el.className = "row-header";
      el.textContent = String(r);
      rowHead.appendChild(el);
    }

    // Cards
    const grid = $("suspectGrid");
    grid.innerHTML = "";
    for (const person of data.people) {
      const scene = document.createElement("div");
      scene.className = "card-scene";
      scene.dataset.cell = person.cell_id;

      const isInitiallyKnown = Boolean(data.known[person.cell_id]);
      if (isInitiallyKnown) {
        scene.classList.add("is-revealed");
      }

      scene.innerHTML = `
        <div class="card-inner">
          <div class="card-face card-front">
            <span class="card-coord">${escapeHTML(person.cell_id)}</span>
            <span class="mark-badge hidden"></span>
            <div class="avatar-wrap">${window.renderAvatarSVG(person, false)}</div>
            <div class="card-identity">
              <div class="card-name">${escapeHTML(person.name)}</div>
              <div class="card-prof">${escapeHTML(person.profession)}</div>
            </div>
          </div>
          <div class="card-face card-back">
            <span class="card-coord">${escapeHTML(person.cell_id)}</span>
            <span class="status-pip"></span>
            <div class="revealed-top">
              ${window.renderAvatarSVG(person, true)}
              <div class="revealed-meta">
                <div class="revealed-name">${escapeHTML(person.name)}</div>
                <div class="revealed-prof">${escapeHTML(person.profession)}</div>
              </div>
            </div>
            <div class="clue-body"></div>
          </div>
        </div>
      `;

      scene.addEventListener("click", (e) => {
        e.stopPropagation();
        onCardClick(person.cell_id);
      });
      scene.addEventListener("contextmenu", (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (!state.data.known[person.cell_id]) {
          cycleMark(person.cell_id);
        }
      });

      grid.appendChild(scene);
    }
  }

  // ── Incremental Sync of Cards, Evidence, Stats & Trace ────────────────────
  function syncCards() {
    if (!state.data) return;
    const { known, clues, people } = state.data;
    const peopleById = Object.fromEntries(people.map((p) => [p.cell_id, p]));
    const hasSpotlight = Boolean(state.focus || state.highlights.size > 0);

    document.querySelectorAll(".card-scene").forEach((scene) => {
      const cid = scene.dataset.cell;
      const status = known[cid];
      const clue = clues[cid];
      const isFocused = state.focus === cid;
      const isReferenced = state.highlights.has(cid);
      const isHinted = state.hintTarget === cid;
      const isCalling = state.callingCell === cid && !status;

      scene.classList.toggle("is-revealed", Boolean(status));
      scene.classList.toggle("is-focused", isFocused);
      scene.classList.toggle("is-referenced", isReferenced && !isFocused);
      scene.classList.toggle("is-hinted", isHinted);
      scene.classList.toggle("is-calling", isCalling);
      scene.classList.toggle(
        "is-dimmed",
        hasSpotlight && !isFocused && !isReferenced && !isHinted && !isCalling
      );

      // Update back face when revealed
      if (status && clue) {
        const back = scene.querySelector(".card-back");
        back.classList.remove("status-CRIMINAL", "status-INNOCENT");
        back.classList.add(`status-${status}`);
        const clueBody = back.querySelector(".clue-body");
        if (clueBody.textContent !== clue.text) {
          clueBody.textContent = clue.text;
          clueBody.style.fontSize = clue.text.length > 62 ? "10px" : "11px";
        }
      }

      // Pencil mark badge on front face
      const badge = scene.querySelector(".mark-badge");
      const mark = !status ? state.marks[cid] : null;
      if (mark) {
        badge.className = `mark-badge ${mark === "INNOCENT" ? "inno" : "crim"}`;
        badge.textContent = mark === "INNOCENT" ? "I?" : "C?";
      } else {
        badge.className = "mark-badge hidden";
        badge.textContent = "";
      }

      // Inline Verdict Call Overlay
      const front = scene.querySelector(".card-front");
      const existingOverlay = front.querySelector(".call-overlay");
      if (isCalling && !existingOverlay) {
        const person = peopleById[cid];
        const ov = document.createElement("div");
        ov.className = "call-overlay";
        ov.innerHTML = `
          <div class="call-head">
            <div class="call-person">
              ${window.renderAvatarSVG(person, true)}
              <span class="call-person-name">${escapeHTML(person.name)}</span>
            </div>
            <button class="call-close" title="Cancel (Esc)">✕</button>
          </div>
          <div class="call-actions">
            <button class="verdict-btn inno" data-status="INNOCENT">Innocent</button>
            <button class="verdict-btn crim" data-status="CRIMINAL">Criminal</button>
          </div>
        `;
        ov.addEventListener("click", (e) => e.stopPropagation());
        ov.querySelector(".call-close").addEventListener("click", () => {
          state.callingCell = null;
          syncCards();
        });
        ov.querySelectorAll(".verdict-btn").forEach((btn) => {
          btn.addEventListener("click", () => submitVerdict(cid, btn.dataset.status));
        });
        front.appendChild(ov);
      } else if (!isCalling && existingOverlay) {
        existingOverlay.remove();
      }
    });
  }

  function renderEvidence(badgeText, lines) {
    $("evidenceBadge").textContent = badgeText || "";
    const html = lines
      .map((line) => formatClueHTML(line))
      .join("<br />");
    $("evidenceText").innerHTML = html || "Select a revealed card to inspect its clue.";
  }

  function renderMetaAndStats(data) {
    const { puzzle, stats, trace, open_count, total_count } = data;

    // Header progress & stepper
    $("progressText").textContent = `${open_count} / ${total_count}`;
    document.querySelectorAll(".step-dot").forEach((btn) => {
      const idx = Number(btn.dataset.idx);
      btn.classList.toggle("active", puzzle.case_index === idx);
    });

    // Left hero metadata
    const caseTag = puzzle.case_index !== null
      ? `CASE ${String(puzzle.case_index + 1).padStart(2, "0")}`
      : "CUSTOM";
    $("caseMetaBadge").textContent = `${puzzle.num_rows}×${puzzle.num_cols} · ${caseTag}`;
    $("caseSubtitle").textContent = `${puzzle.title} · ${puzzle.difficulty}`;

    // Difficulty dots (1..7)
    const filled = DIFFICULTY_LEVELS[puzzle.difficulty] || 4;
    const dotsEl = $("levelDots");
    dotsEl.innerHTML = "";
    for (let i = 0; i < 7; i++) {
      const d = document.createElement("span");
      d.className = `level-dot ${i < filled ? "filled" : ""}`;
      dotsEl.appendChild(d);
    }

    // Sync select dropdown
    const sel = $("caseSelect");
    if (puzzle.case_index !== null) {
      sel.value = String(puzzle.case_index);
    } else {
      sel.value = "__custom__";
    }

    // Solver stats
    const isDpll = String(stats.mode).toUpperCase() === "DPLL";
    const modeBadge = $("statMode");
    modeBadge.textContent = stats.mode;
    modeBadge.classList.toggle("dpll", isDpll);
    $("solverMiniDot").classList.toggle("dpll", isDpll);

    $("statPrimary").textContent = stats.primary_vars;
    $("statAux").textContent = stats.aux_vars;
    $("statClauses").textContent = stats.cnf_clauses;
    $("statSatCalls").textContent = stats.sat_calls;
    $("statDecisions").textContent = stats.decisions;
    $("statPropagations").textContent = stats.propagations;
    $("statBacktracks").textContent = stats.backtracks;
    $("statRuntime").textContent = Number(stats.runtime_ms).toFixed(2);

    // Deduction trace
    $("traceTabBtn").textContent = `Trace (${trace.length})`;
    const traceEl = $("traceList");
    if (trace.length === 0) {
      traceEl.innerHTML = '<div class="trace-empty">No deduction steps recorded yet.</div>';
    } else {
      traceEl.innerHTML = trace
        .map((entry, idx) => {
          const match = entry.match(/^([A-Z]\d+)/);
          const cid = match ? match[1] : "";
          return `<div class="trace-item" data-cell="${cid}"><span class="trace-num">#${idx + 1}</span><span>${formatClueHTML(entry)}</span></div>`;
        })
        .join("");
      traceEl.querySelectorAll(".trace-item").forEach((item) => {
        item.addEventListener("click", () => {
          const cid = item.dataset.cell;
          if (cid && state.data.clues[cid]) {
            inspectRevealedCell(cid);
          }
        });
      });
      traceEl.scrollTop = traceEl.scrollHeight;
    }
  }

  function applyState(newData, { isFreshPuzzle = false } = {}) {
    const key = `${newData.puzzle.puzzle_id}:${newData.puzzle.num_rows}x${newData.puzzle.num_cols}:${newData.open_count === Object.keys(newData.known).length && isFreshPuzzle ? Date.now() : ""}`;
    state.data = newData;

    if (isFreshPuzzle || !state.puzzleKey) {
      state.puzzleKey = key;
      state.callingCell = null;
      state.hintTarget = null;
      state.marks = {};
      state.victoryShown = false;
      $("uniqueResult").textContent = "";
      buildGridDOM(newData);
      resetTimer();

      const first = newData.initial_focus;
      if (first && newData.clues[first]) {
        const clue = newData.clues[first];
        state.focus = first;
        state.highlights = new Set(clue.references);
        renderEvidence(first, [`${first}: ${clue.text}`]);
      } else {
        state.focus = null;
        state.highlights.clear();
        renderEvidence("", []);
      }
      setFeedback("Tap a suspect to call Innocent or Criminal, or tap a revealed card to highlight its clues.", "neutral");
    }

    renderMetaAndStats(newData);
    syncCards();

    if (newData.solved && !state.victoryShown) {
      state.victoryShown = true;
      stopAutoSolve();
      setFeedback("Case closed! Every verdict was logically proved with zero guesses.", "success");
      setTimeout(() => openVictoryModal(newData), 420);
    }
  }

  // ── Interactions ───────────────────────────────────────────────────────────
  function inspectRevealedCell(cid) {
    const clue = state.data.clues[cid];
    if (!clue) return;
    state.callingCell = null;
    state.hintTarget = null;
    state.focus = cid;
    state.highlights = new Set(clue.references);
    renderEvidence(cid, [`${cid}: ${clue.text}`]);
    syncCards();
  }

  function cycleMark(cid) {
    const cur = state.marks[cid];
    if (!cur) state.marks[cid] = "INNOCENT";
    else if (cur === "INNOCENT") state.marks[cid] = "CRIMINAL";
    else delete state.marks[cid];
    syncCards();
  }

  function toggleMarkMode() {
    state.markMode = !state.markMode;
    $("markBtn").classList.toggle("active-toggle", state.markMode);
    if (state.markMode) {
      state.callingCell = null;
      setFeedback("Mark mode ON — click any face-down suspect to cycle pencil notes (I? / C?).", "hint");
    } else {
      setFeedback("Mark mode OFF — click any suspect to submit a verdict.", "neutral");
    }
    syncCards();
  }

  function onCardClick(cid) {
    stopAutoSolve();
    const isKnown = Boolean(state.data.known[cid]);
    if (isKnown) {
      inspectRevealedCell(cid);
      return;
    }
    if (state.markMode) {
      cycleMark(cid);
      return;
    }
    state.callingCell = state.callingCell === cid ? null : cid;
    syncCards();
  }

  function shakeCard(cid) {
    const el = document.querySelector(`.card-scene[data-cell="${cid}"]`);
    if (!el) return;
    el.classList.remove("is-shaking");
    void el.offsetWidth;
    el.classList.add("is-shaking");
    setTimeout(() => el.classList.remove("is-shaking"), 460);
  }

  async function submitVerdict(cid, status) {
    try {
      const res = await api("/api/submit", { cell_id: cid, status });
      state.callingCell = null;
      state.hintTarget = null;

      if (res.verdict === "ACCEPTED") {
        delete state.marks[cid];
        const clue = res.state.clues[cid];
        state.focus = cid;
        state.highlights = new Set(clue ? clue.references : []);
        if (clue) renderEvidence(cid, [`${cid}: ${clue.text}`]);
        setFeedback(`ACCEPTED · ${cid} is ${status}. New clue revealed!`, "success");
        applyState(res.state);
      } else {
        shakeCard(cid);
        const msg = res.verdict === "NOT_PROVABLE"
          ? `NOT_PROVABLE: Not enough logical evidence to prove ${cid} yet. Do not guess!`
          : `CONTRADICTED: Calling ${cid} as ${status} contradicts the current public clues!`;
        setFeedback(msg, "error");
        toast(msg, "error");
        applyState(res.state);
      }
    } catch (err) {
      toast(err.message, "error");
    }
  }

  async function requestHint() {
    stopAutoSolve();
    state.callingCell = null;
    try {
      const res = await api("/api/hint", {});
      if (res.hint) {
        const { cell_id, related } = res.hint;
        state.focus = null;
        state.hintTarget = cell_id;
        state.highlights = new Set(related);
        const lines = related
          .map((owner) => res.state.clues[owner])
          .filter(Boolean)
          .map((c) => `${c.owner_cell}: ${c.text}`);
        renderEvidence(`HINT → ${cell_id}`, lines.length ? lines : [`${cell_id} can be deduced from current clues.`]);
        setFeedback(`Hint · ${cell_id} is logically forced. Inspect the highlighted clues!`, "hint");
      } else {
        setFeedback("No more provable cells remain.", "neutral");
      }
      applyState(res.state);
    } catch (err) {
      toast(err.message, "error");
    }
  }

  async function runStep() {
    state.callingCell = null;
    state.hintTarget = null;
    try {
      const res = await api("/api/step", {});
      if (res.revealed) {
        const cid = res.revealed;
        delete state.marks[cid];
        const clue = res.state.clues[cid];
        state.focus = cid;
        state.highlights = new Set(clue ? clue.references : []);
        if (clue) renderEvidence(cid, [`${cid}: ${clue.text}`]);
        setFeedback(`ACCEPTED · Agent proved ${cid} (${res.state.known[cid]}).`, "success");
        applyState(res.state);
        return true;
      }
      applyState(res.state);
      return false;
    } catch (err) {
      stopAutoSolve();
      toast(err.message, "error");
      return false;
    }
  }

  function stopAutoSolve() {
    state.autoRunning = false;
    if (state.autoTimer !== null) {
      clearTimeout(state.autoTimer);
      state.autoTimer = null;
    }
    const btn = $("autoBtn");
    btn.classList.remove("is-running");
    $("autoLabel").textContent = "Auto Solve";
    $("autoIcon").innerHTML = '<polygon points="4,5 13,12 4,19"/><polygon points="12,5 21,12 12,19"/>';
  }

  function toggleAutoSolve() {
    if (state.autoRunning) {
      stopAutoSolve();
      return;
    }
    state.autoRunning = true;
    const btn = $("autoBtn");
    btn.classList.add("is-running");
    $("autoLabel").textContent = "Pause";
    $("autoIcon").innerHTML = '<rect x="6" y="5" width="4" height="14" rx="1"/><rect x="14" y="5" width="4" height="14" rx="1"/>';

    const tick = async () => {
      if (!state.autoRunning) return;
      const moved = await runStep();
      if (moved && state.autoRunning && state.data && !state.data.solved) {
        state.autoTimer = setTimeout(tick, SPEEDS[state.speedIdx].ms);
      } else {
        stopAutoSolve();
      }
    };
    tick();
  }

  async function loadCase(index) {
    stopAutoSolve();
    try {
      const data = await api("/api/case", { index });
      applyState(data, { isFreshPuzzle: true });
    } catch (err) {
      toast(err.message, "error");
    }
  }

  async function restartCase() {
    stopAutoSolve();
    try {
      const data = await api("/api/restart", {});
      applyState(data, { isFreshPuzzle: true });
    } catch (err) {
      toast(err.message, "error");
    }
  }

  async function checkUniqueness() {
    const out = $("uniqueResult");
    out.textContent = "Checking...";
    out.style.color = "var(--muted)";
    try {
      const res = await api("/api/check_uniqueness", {});
      out.textContent = res.unique ? "Unique solution ✓" : "Multiple / No solution ✕";
      out.style.color = res.unique ? "var(--success)" : "var(--danger)";
    } catch (err) {
      out.textContent = "Error";
      out.style.color = "var(--danger)";
      toast(err.message, "error");
    }
  }

  // ── Victory Modal ──────────────────────────────────────────────────────────
  function openVictoryModal(data) {
    const { stats, puzzle, trace } = data;
    $("victoryTitle").textContent = puzzle.title;
    $("victorySub").textContent = `Solved in ${$("timerDisplay").textContent} using ${stats.mode} backend.`;
    $("victoryStats").innerHTML = `
      <div class="v-stat"><span class="v-stat-val">${$("timerDisplay").textContent}</span><span class="v-stat-lbl">Time</span></div>
      <div class="v-stat"><span class="v-stat-val">${trace.length}</span><span class="v-stat-lbl">Deductions</span></div>
      <div class="v-stat"><span class="v-stat-val">${stats.mode}</span><span class="v-stat-lbl">Solver Mode</span></div>
      <div class="v-stat"><span class="v-stat-val">${stats.sat_calls}</span><span class="v-stat-lbl">SAT Calls</span></div>
      <div class="v-stat"><span class="v-stat-val">${stats.decisions}</span><span class="v-stat-lbl">Decisions</span></div>
      <div class="v-stat"><span class="v-stat-val">${Number(stats.runtime_ms).toFixed(1)} ms</span><span class="v-stat-lbl">Inference</span></div>
    `;
    $("victoryModal").classList.remove("hidden");
  }

  // ── Initialization ─────────────────────────────────────────────────────────
  function buildCaseSelectors(cases) {
    const stepper = $("caseStepper");
    const select = $("caseSelect");
    stepper.innerHTML = "";
    select.innerHTML = "";

    for (const c of cases) {
      const dot = document.createElement("button");
      dot.className = "step-dot";
      dot.dataset.idx = String(c.index);
      dot.textContent = String(c.index + 1);
      dot.title = `${c.rows}×${c.cols} · ${c.title} (${c.difficulty})`;
      dot.addEventListener("click", () => loadCase(c.index));
      stepper.appendChild(dot);

      const opt = document.createElement("option");
      opt.value = String(c.index);
      opt.textContent = `0${c.index + 1} · ${c.rows}×${c.cols}  ${c.title} (${c.difficulty})`;
      select.appendChild(opt);
    }

    const customOpt = document.createElement("option");
    customOpt.value = "__custom__";
    customOpt.textContent = "Custom / Generated Case";
    customOpt.disabled = true;
    select.appendChild(customOpt);
  }

  function wireEvents() {
    // Theme toggle
    const savedTheme = localStorage.getItem("griductive_theme") || "noir";
    applyTheme(savedTheme);
    $("themeToggleBtn").addEventListener("click", () => {
      const cur = document.documentElement.getAttribute("data-theme");
      applyTheme(cur === "noir" ? "paper" : "noir");
    });

    // Timer pause
    $("timerToggleBtn").addEventListener("click", () => {
      state.timerPaused = !state.timerPaused;
      updateTimerIcon();
    });

    // Case dropdown & brand click
    $("caseSelect").addEventListener("change", (e) => {
      const idx = Number(e.target.value);
      if (!Number.isNaN(idx)) loadCase(idx);
    });
    $("brandReset").addEventListener("click", restartCase);

    // Tabs
    document.querySelectorAll(".seg-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".seg-btn").forEach((b) => b.classList.remove("active"));
        document.querySelectorAll(".tab-pane").forEach((p) => p.classList.remove("active"));
        btn.classList.add("active");
        $(`tab-${btn.dataset.tab}`).classList.add("active");
      });
    });

    // Toolbar buttons
    $("markBtn").addEventListener("click", toggleMarkMode);
    $("hintBtn").addEventListener("click", requestHint);
    $("stepBtn").addEventListener("click", () => { stopAutoSolve(); runStep(); });
    $("autoBtn").addEventListener("click", toggleAutoSolve);
    $("speedBtn").addEventListener("click", () => {
      state.speedIdx = (state.speedIdx + 1) % SPEEDS.length;
      $("speedBtn").textContent = SPEEDS[state.speedIdx].label;
    });
    $("restartBtn").addEventListener("click", restartCase);
    $("checkUniqueBtn").addEventListener("click", checkUniqueness);
    $("exportBtn").addEventListener("click", () => {
      window.location.href = "/api/export";
      toast("Downloading current case JSON...", "info");
    });

    // Load JSON file upload
    $("loadJsonBtn").addEventListener("click", () => $("jsonFileInput").click());
    $("jsonFileInput").addEventListener("change", async (e) => {
      const file = e.target.files[0];
      e.target.value = "";
      if (!file) return;
      try {
        const parsed = JSON.parse(await file.text());
        stopAutoSolve();
        const data = await api("/api/load_json", { puzzle: parsed });
        applyState(data, { isFreshPuzzle: true });
        toast(`Loaded "${data.puzzle.title}"`, "success");
      } catch (err) {
        toast(`Failed to load JSON: ${err.message}`, "error");
      }
    });

    // Generate Modal
    const openGen = () => $("genModal").classList.remove("hidden");
    const closeGen = () => $("genModal").classList.add("hidden");
    $("genModalBtn").addEventListener("click", openGen);
    $("closeGenModal").addEventListener("click", closeGen);
    $("cancelGenBtn").addEventListener("click", closeGen);
    $("genModal").addEventListener("click", (e) => { if (e.target === $("genModal")) closeGen(); });

    document.querySelectorAll("#sizeChips .chip-btn").forEach((chip) => {
      chip.addEventListener("click", () => {
        document.querySelectorAll("#sizeChips .chip-btn").forEach((c) => c.classList.remove("active"));
        chip.classList.add("active");
        state.genSize = { rows: Number(chip.dataset.r), cols: Number(chip.dataset.c) };
      });
    });

    $("confirmGenBtn").addEventListener("click", async () => {
      closeGen();
      stopAutoSolve();
      try {
        const seedRaw = $("seedInput").value.trim();
        const data = await api("/api/generate", {
          rows: state.genSize.rows,
          cols: state.genSize.cols,
          extensions: $("extToggle").checked,
          seed: seedRaw === "" ? null : Number(seedRaw),
        });
        applyState(data, { isFreshPuzzle: true });
        toast(`Generated ${data.puzzle.num_rows}×${data.puzzle.num_cols} verified puzzle`, "success");
      } catch (err) {
        toast(err.message, "error");
      }
    });

    // Victory Modal
    $("victoryInspectBtn").addEventListener("click", () => $("victoryModal").classList.add("hidden"));
    $("victoryNextBtn").addEventListener("click", () => {
      $("victoryModal").classList.add("hidden");
      const curIdx = state.data.puzzle.case_index;
      const nextIdx = curIdx !== null ? (curIdx + 1) % state.cases.length : 0;
      loadCase(nextIdx);
    });
    $("victoryModal").addEventListener("click", (e) => {
      if (e.target === $("victoryModal")) $("victoryModal").classList.add("hidden");
    });

    // Click empty area clears overlay & spotlight
    $("boardStage").addEventListener("click", () => {
      if (state.callingCell || state.focus || state.highlights.size || state.hintTarget) {
        state.callingCell = null;
        state.focus = null;
        state.hintTarget = null;
        state.highlights.clear();
        syncCards();
      }
    });

    // Keyboard shortcuts
    window.addEventListener("keydown", (e) => {
      if (["INPUT", "SELECT", "TEXTAREA"].includes(e.target.tagName)) return;
      if (e.key === "Escape") {
        state.callingCell = null;
        $("genModal").classList.add("hidden");
        $("victoryModal").classList.add("hidden");
        if (state.markMode) toggleMarkMode();
        syncCards();
      } else if (e.key === "m" || e.key === "M") {
        toggleMarkMode();
      } else if (e.key === "h" || e.key === "H") {
        requestHint();
      } else if (e.key === "r" || e.key === "R") {
        restartCase();
      } else if (e.key === "t" || e.key === "T") {
        const cur = document.documentElement.getAttribute("data-theme");
        applyTheme(cur === "noir" ? "paper" : "noir");
      } else if (e.code === "Space") {
        e.preventDefault();
        stopAutoSolve();
        runStep();
      }
    });

    // Recompute card dimensions cleanly on resize
    window.addEventListener("resize", () => {
      if (state.data) {
        computeCardMetrics(state.data.puzzle.num_rows, state.data.puzzle.num_cols);
      }
    });
  }

  async function bootstrap() {
    wireEvents();
    try {
      const [{ cases }, initialState] = await Promise.all([
        api("/api/cases"),
        api("/api/state"),
      ]);
      state.cases = cases;
      buildCaseSelectors(cases);
      applyState(initialState, { isFreshPuzzle: true });
    } catch (err) {
      toast(`Failed to connect to Python backend: ${err.message}`, "error");
    }
  }

  bootstrap();
})();
