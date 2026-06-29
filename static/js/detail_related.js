async function loadDetailRelated(query, excludeUrl = "") {
  const panel = document.getElementById("relatedPanel");
  const title = document.getElementById("relatedTitle");
  const box = document.getElementById("relatedResults");

  if (!panel || !title || !box) return;

  const q = (query || "").trim();
  if (!q) {
    panel.style.display = "none";
    return;
  }

  const params = new URLSearchParams({ q });
  if (excludeUrl) params.set("exclude_url", excludeUrl);

  try {
    const res = await fetch(`http://127.0.0.1:5083/api/related?${params.toString()}`);
    const records = await res.json();

    if (!records.length) {
      panel.style.display = "none";
      return;
    }

    title.textContent = `Related to “${q}”`;
    box.innerHTML = records.slice(0, 8).map(r => `
      <a class="map-record mine-row" href="${r.url}">
        <strong>${r.title || "Untitled record"}</strong>
        <small>${r.app || "source"} • ${r.type || "record"} • score ${r.score || 0}</small>
        <p>${r.summary || ""}</p>
      </a>
    `).join("");
  } catch (err) {
    panel.style.display = "none";
  }
}
