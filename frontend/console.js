document.getElementById("start").addEventListener("submit", async (e) => {
  e.preventDefault();
  const data = new FormData(e.target);
  const body = {
    participant: data.get("participant").trim(),
    domain: data.get("domain"),
    condition: data.get("condition"),
  };
  const r = await fetch("/api/session/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    alert("Failed to start session: " + (await r.text()));
    return;
  }
  const info = await r.json();
  sessionStorage.setItem("am", JSON.stringify({ ...body, ...info }));
  location.href = "/teach";
});
