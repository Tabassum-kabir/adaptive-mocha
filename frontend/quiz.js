const state = JSON.parse(sessionStorage.getItem("am") || "{}");
if (!state.participant) { alert("No active session"); location.href = "/"; }

const itemsEl = document.getElementById("quiz-items");
const answers = {};

async function load() {
  const q = new URLSearchParams({ participant: state.participant, condition: state.condition });
  const r = await fetch("/api/quiz_items?" + q.toString());
  const data = await r.json();
  for (const it of data.items) {
    const div = document.createElement("div");
    div.className = "quiz-item";
    div.innerHTML = `
      <div class="text">${escapeHtml(it.text)}</div>
      <div class="options" data-id="${it.id}"></div>
    `;
    const opts = div.querySelector(".options");
    it.options.forEach((opt) => {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = opt;
      b.addEventListener("click", () => {
        opts.querySelectorAll("button").forEach((x) => x.classList.remove("selected"));
        b.classList.add("selected");
        answers[it.id] = opt;
      });
      opts.appendChild(b);
    });
    itemsEl.appendChild(div);
  }
}

document.getElementById("quiz-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const r = await fetch("/api/quiz", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      participant: state.participant,
      condition: state.condition,
      answers,
    }),
  });
  const data = await r.json();
  const out = document.getElementById("result");
  out.textContent = `You scored ${data.score} / ${data.total} on the concept check. Tell the researcher you are finished with this block.`;
  out.hidden = false;
  await fetch("/api/session/end?" + new URLSearchParams({
    participant: state.participant,
    condition: state.condition,
  }), { method: "POST" });
});

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

load();
