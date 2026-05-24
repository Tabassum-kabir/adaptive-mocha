const ITEMS = [
  ["mental", "Mental Demand", "Very Low", "Very High"],
  ["physical", "Physical Demand", "Very Low", "Very High"],
  ["temporal", "Temporal Demand", "Very Low", "Very High"],
  ["performance", "Performance", "Perfect", "Failure"],
  ["effort", "Effort", "Very Low", "Very High"],
  ["frustration", "Frustration", "Very Low", "Very High"],
];

const state = JSON.parse(sessionStorage.getItem("am") || "{}");
if (!state.participant) { alert("No active session"); location.href = "/"; }

const table = document.getElementById("tlx-table");
for (const [id, label, lo, hi] of ITEMS) {
  const tr = document.createElement("tr");
  tr.innerHTML = `
    <td class="label">${label}</td>
    <td class="scale">
      <input type="range" min="0" max="20" value="10" id="${id}" />
      <div style="display:flex;justify-content:space-between;font-size:.8rem;color:#777">
        <span>${lo}</span><span>${hi}</span>
      </div>
    </td>
    <td class="val"><span id="${id}-val">10</span></td>
  `;
  table.appendChild(tr);
  const slider = tr.querySelector(`#${id}`);
  const out = tr.querySelector(`#${id}-val`);
  slider.addEventListener("input", () => out.textContent = slider.value);
}

document.getElementById("tlx-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = { participant: state.participant, condition: state.condition };
  for (const [id] of ITEMS) {
    body[id] = parseInt(document.getElementById(id).value, 10);
  }
  const r = await fetch("/api/tlx", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) { alert("TLX submit failed"); return; }
  location.href = "/quiz";
});
