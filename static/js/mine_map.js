const map = L.map("mineMap").setView([32.8067, -86.7911], 7);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 18,
  attribution: "&copy; OpenStreetMap contributors"
}).addTo(map);

let allPoints = [];
let bounds = [];

const clusterLayer = L.markerClusterGroup({
  showCoverageOnHover: false,
  spiderfyOnMaxZoom: true,
  maxClusterRadius: 52,
  disableClusteringAtZoom: 14
});

map.addLayer(clusterLayer);

function statusColor(status) {
  const s = (status || "").toLowerCase();
  if (s.includes("active")) return "#2ecc71";
  if (s.includes("nonproducing")) return "#f1c40f";
  if (s.includes("abandoned")) return "#e74c3c";
  return "#95a5a6";
}

function markerIcon(p) {
  const color = statusColor(p.status);
  return L.divIcon({
    className: "mine-marker",
    html: `<span style="background:${color}"></span>`,
    iconSize: [18, 18],
    iconAnchor: [9, 9]
  });
}

function popupHtml(p) {
  return `
    <strong>${p.name || "Mine record"}</strong><br>
    <small>${p.county || "Alabama"} ${p.mine_type ? "• " + p.mine_type : ""}</small>
    <p>${p.summary || ""}</p>
    ${p.operator ? `<p><strong>Operator:</strong> ${p.operator}</p>` : ""}
    ${p.company ? `<p><strong>Company:</strong> ${p.company}</p>` : ""}
    ${p.status ? `<p><strong>Status:</strong> ${p.status}</p>` : ""}
    ${p.id ? `<p><strong>ID:</strong> ${p.id}</p>` : ""}
    ${p.source_url ? `<a href="${p.source_url}">Source</a>` : ""}
  `;
}

function uniqueValues(key) {
  return [...new Set(allPoints.map(p => p[key]).filter(Boolean))].sort();
}

function fillSelect(id, values, label) {
  const el = document.getElementById(id);
  el.innerHTML = `<option value="">${label}</option>` + values.map(v => `<option value="${v}">${v}</option>`).join("");
}

function currentFilteredPoints() {
  const q = document.getElementById("mineSearch").value.trim().toLowerCase();
  const county = document.getElementById("countyFilter").value;
  const status = document.getElementById("statusFilter").value;
  const type = document.getElementById("typeFilter").value;

  return allPoints.filter(p => {
    const text = `${p.name || ""} ${p.operator || ""} ${p.company || ""} ${p.county || ""} ${p.status || ""} ${p.mine_type || ""}`.toLowerCase();
    if (q && !text.includes(q)) return false;
    if (county && p.county !== county) return false;
    if (status && p.status !== status) return false;
    if (type && p.mine_type !== type) return false;
    return true;
  });
}

function renderMap() {
  const points = currentFilteredPoints();

  clusterLayer.clearLayers();
  bounds = [];

  for (const p of points) {
    const marker = L.marker([p.lat, p.lon], {
      icon: markerIcon(p)
    }).bindPopup(popupHtml(p));

    clusterLayer.addLayer(marker);
    bounds.push([p.lat, p.lon]);
  }

  document.getElementById("mineCount").textContent = `${points.length} exact mines plotted`;
  document.getElementById("mineNote").textContent =
    points.length ? "Showing clustered source-backed Alabama mine locations." : "No mines match the current filters.";

  document.getElementById("mineList").innerHTML = points.slice(0, 80).map(p => `
    <button class="map-record mine-row" data-id="${p.id}">
      <strong>${p.name}</strong>
      <small>${p.county || "Alabama"} • ${p.mine_type || "Mine"} • ${p.status || "status unknown"}</small>
    </button>
  `).join("");

  document.querySelectorAll(".mine-row").forEach(row => {
    row.addEventListener("click", () => {
      const p = points.find(x => x.id === row.dataset.id);
      if (!p) return;
      map.setView([p.lat, p.lon], 14);
    });
  });

  if (bounds.length) {
    map.fitBounds(bounds, { padding: [30, 30] });
  }
}

async function loadMineMap() {
  const res = await fetch("/api/mine-map-points");
  allPoints = await res.json();

  fillSelect("countyFilter", uniqueValues("county"), "All counties");
  fillSelect("statusFilter", uniqueValues("status"), "All statuses");
  fillSelect("typeFilter", uniqueValues("mine_type"), "All mine types");

  renderMap();
}

["mineSearch", "countyFilter", "statusFilter", "typeFilter"].forEach(id => {
  document.addEventListener("input", e => {
    if (e.target && e.target.id === id) renderMap();
  });
  document.addEventListener("change", e => {
    if (e.target && e.target.id === id) renderMap();
  });
});

document.getElementById("fitBtn")?.addEventListener("click", () => {
  if (bounds.length) map.fitBounds(bounds, { padding: [30, 30] });
  else map.setView([32.8067, -86.7911], 7);
});

loadMineMap();
