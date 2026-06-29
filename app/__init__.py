from flask import Flask, jsonify, render_template, request
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REGISTRIES = {
    "mines": ROOT / "data/mines/mine_registry.json",
    "companies": ROOT / "data/companies/company_registry.json",
    "counties": ROOT / "data/counties/county_index.json",
    "sources": ROOT / "data/sources/source_index.json",
}


def load_json(path):
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, list) else []
    except Exception:
        return []


def registry_counts():
    return {name: len(load_json(path)) for name, path in REGISTRIES.items()}


def all_records():
    records = []
    for section, path in REGISTRIES.items():
        for item in load_json(path):
            if isinstance(item, dict):
                x = dict(item)
                x["section"] = section
                records.append(x)
    return records


def search_records(q):
    q = (q or "").strip().lower()
    if not q:
        return all_records()

    return [
        item for item in all_records()
        if q in json.dumps(item, ensure_ascii=False).lower()
    ]


def _coord_value(record, keys):
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            try:
                return float(value)
            except Exception:
                pass
    return None


def _extract_coords(record):
    lat = _coord_value(record, ["lat", "latitude", "Latitude"])
    lon = _coord_value(record, ["lon", "lng", "longitude", "Longitude"])

    if lat is not None and lon is not None:
        return lat, lon

    coords = record.get("coordinates") or record.get("coords") or record.get("location")

    if isinstance(coords, dict):
        lat = _coord_value(coords, ["lat", "latitude", "Latitude"])
        lon = _coord_value(coords, ["lon", "lng", "longitude", "Longitude"])
        if lat is not None and lon is not None:
            return lat, lon

    if isinstance(coords, list) and len(coords) >= 2:
        try:
            a = float(coords[0])
            b = float(coords[1])
            if -90 <= a <= 90 and -180 <= b <= 180:
                return a, b
            if -90 <= b <= 90 and -180 <= a <= 180:
                return b, a
        except Exception:
            pass

    return None


def mine_map_points():
    points = []
    for item in load_json(REGISTRIES["mines"]):
        coords = _extract_coords(item)
        if not coords:
            continue

        lat, lon = coords
        points.append({
            "id": item.get("id"),
            "name": item.get("name"),
            "operator": item.get("operator"),
            "company": item.get("company"),
            "county": item.get("county"),
            "state": item.get("state", "Alabama"),
            "mine_type": item.get("mine_type") or item.get("type"),
            "status": item.get("status"),
            "summary": item.get("summary"),
            "lat": lat,
            "lon": lon,
            "source": item.get("source"),
            "source_url": item.get("source_url"),
            "research_status": item.get("research_status"),
        })
    return points


def create_app():
    app = Flask(
        __name__,
        template_folder=str(ROOT / "templates"),
        static_folder=str(ROOT / "static"),
    )

    @app.route("/")
    def index():
        return render_template("index.html", counts=registry_counts())

    @app.route("/mine-map")
    def mine_map_page():
        return render_template("mine_map.html")

    @app.route("/api/status")
    def api_status():
        return jsonify({
            "app": "Alabama Mine Map",
            "status": "mines_only_foundation",
            "port": 5084,
            "scope": "All Alabama mines, past and present. Source-backed mine records only.",
            "counts": registry_counts(),
        })

    @app.route("/api/search")
    def api_search():
        return jsonify(search_records(request.args.get("q", "")))

    @app.route("/api/mine-map-points")
    def api_mine_map_points():
        return jsonify(mine_map_points())

    @app.route("/health")
    def health():
        return jsonify({"status": "ok", "project": "alabama-mine-map"})

    return app
