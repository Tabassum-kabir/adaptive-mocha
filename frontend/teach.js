const state = JSON.parse(sessionStorage.getItem("am") || "{}");
if (!state.participant || !state.condition) {
  alert("No session in progress. Returning to console.");
  location.href = "/";
}

const meta = document.getElementById("meta");
const container = document.getElementById("trial-container");
const timerEl = document.getElementById("timer");
const trace = document.getElementById("controller-trace");
const isAdaptive = !!state.is_adaptive;
const showAlignment = !!state.show_alignment_hint;
const blockSeconds = state.block_seconds || 1200;
const endsAt = Date.now() + blockSeconds * 1000;
let currentTrial = null;
let microTLXScheduled = { eight: false, fourteen: false };

meta.textContent = `${state.participant} · ${state.domain_title} · ${state.condition}`;

function tickTimer() {
  const ms = Math.max(0, endsAt - Date.now());
  const s = Math.floor(ms / 1000);
  const mm = String(Math.floor(s / 60)).padStart(2, "0");
  const ss = String(s % 60).padStart(2, "0");
  timerEl.textContent = `${mm}:${ss}`;
  timerEl.classList.toggle("low", s <= 60);
  const elapsedMin = (blockSeconds - s) / 60;
  if (isAdaptive && !microTLXScheduled.eight && elapsedMin >= 8) {
    microTLXScheduled.eight = true;
    runMicroTLX();
  }
  if (isAdaptive && !microTLXScheduled.fourteen && elapsedMin >= 14) {
    microTLXScheduled.fourteen = true;
    runMicroTLX();
  }
  if (ms <= 0) {
    finishBlock();
  } else {
    setTimeout(tickTimer, 250);
  }
}
tickTimer();

async function nextTrial() {
  const q = new URLSearchParams({ participant: state.participant, condition: state.condition });
  const r = await fetch("/api/next?" + q.toString());
  const data = await r.json();
  if (data.done) {
    finishBlock();
    return;
  }
  currentTrial = data;
  renderTrial(data);
}

function renderTrial(t) {
  container.innerHTML = "";
  if (showAlignment && t.rationale) {
    const banner = document.createElement("div");
    banner.className = "alignment";
    banner.innerHTML = `<strong>Compare these examples.</strong> ${escapeHtml(t.rationale)}`;
    container.appendChild(banner);
  }
  const labels = state.labels;
  const responses = t.items.map(() => ({ label: null, rationale: "" }));
  t.items.forEach((it, idx) => {
    const card = document.createElement("div");
    card.className = "trial";
    card.innerHTML = `
      <div class="text">${escapeHtml(it.text)}</div>
      <div class="options"></div>
      <textarea data-i="${idx}" placeholder="(optional) why?" rows="2" style="margin-top:8px"></textarea>
    `;
    const opts = card.querySelector(".options");
    labels.forEach((lbl) => {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = lbl;
      b.addEventListener("click", () => {
        opts.querySelectorAll("button").forEach((x) => x.classList.remove("selected"));
        b.classList.add("selected");
        responses[idx].label = lbl;
        maybeSubmit();
      });
      opts.appendChild(b);
    });
    card.querySelector("textarea").addEventListener("input", (ev) => {
      responses[idx].rationale = ev.target.value;
    });
    container.appendChild(card);
  });

  const submitBtn = document.createElement("button");
  submitBtn.textContent = "Submit & next";
  submitBtn.disabled = true;
  submitBtn.addEventListener("click", async () => {
    submitBtn.disabled = true;
    await submit(responses, t.controller.inter_trial_ms || 600);
  });
  container.appendChild(submitBtn);

  function maybeSubmit() {
    submitBtn.disabled = responses.some((r) => !r.label);
  }

  if (isAdaptive) {
    trace.hidden = false;
    trace.textContent = `controller · band=${t.controller.band} · batch=${t.controller.batch_size} · pause=${t.controller.inter_trial_ms}ms · load=${t.controller.load.toFixed(2)} · axis=${t.contrast_axis}`;
  }
}

async function submit(responses, pauseMs) {
  const r = await fetch("/api/labels", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      participant: state.participant,
      condition: state.condition,
      labels: responses,
    }),
  });
  if (!r.ok) {
    alert("Submit failed: " + (await r.text()));
    return;
  }
  await new Promise((res) => setTimeout(res, pauseMs));
  nextTrial();
}

async function runMicroTLX() {
  const v = window.prompt(
    "Quick check: how hard does this feel right now? Enter a number from 0 (very easy) to 10 (very hard)."
  );
  if (v === null) return;
  const n = parseFloat(v);
  if (Number.isNaN(n)) return;
  await fetch("/api/micro_tlx", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ participant: state.participant, condition: state.condition, value: Math.max(0, Math.min(10, n)) }),
  });
}

async function finishBlock() {
  const q = new URLSearchParams({ participant: state.participant, condition: state.condition });
  await fetch("/api/evaluate?" + q.toString(), { method: "POST" });
  location.href = "/tlx";
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

nextTrial();
