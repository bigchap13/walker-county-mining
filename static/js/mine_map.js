async function loadMineMapStatus() {
  const res = await fetch("/api/mine-map-points");
  const points = await res.json();

  document.getElementById("mineCount").textContent = `${points.length} exact mines plotted`;

  if (!points.length) {
    document.getElementById("mineNote").textContent =
      "No exact mine-location records are loaded yet. This is correct until mine names and coordinates are sourced.";
    document.getElementById("mineList").innerHTML = "";
    return;
  }

  document.getElementById("mineList").innerHTML = points.map(p => `
    <div class="map-record">
      <strong>${p.name}</strong>
      <small>${p.lat.toFixed(5)}, ${p.lon.toFixed(5)}</small>
    </div>
  `).join("");
}

loadMineMapStatus();
