from flask import Flask, jsonify, render_template, request
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ATLAS_ROOT = Path.home() / "walker-county-atlas"

REGISTRIES = {
    "mines": ROOT / "data/mines/mine_registry.json",
    "companies": ROOT / "data/companies/company_registry.json",
    "coal_camps": ROOT / "data/coal_camps/coal_camp_registry.json",
    "railroads": ROOT / "data/railroads/railroad_registry.json",
    "disasters": ROOT / "data/disasters/disaster_registry.json",
    "maps": ROOT / "data/maps/mine_map_source_index.json",
    "sources": ROOT / "data/sources/source_index.json",
}


def load_json(path):
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text())
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

    results = []
    for item in all_records():
        text = json.dumps(item, ensure_ascii=False).lower()
        if q in text:
            results.append(item)
    return results


def _find_atlas_record(atlas_id):
    if not atlas_id:
        return None

    registry = ATLAS_ROOT / "data" / "registry"
    if not registry.exists():
        return None

    for p in registry.rglob("*.json"):
        if "_before_" in p.name:
            continue
        try:
            data = json.loads(p.read_text())
        except Exception:
            continue

        records = data if isinstance(data, list) else [data]
        for rec in records:
            if isinstance(rec, dict) and rec.get("id") == atlas_id:
                return rec

    return None


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
    if not isinstance(record, dict):
        return None

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


def true_mine_map_points():
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
            "type": item.get("type"),
            "summary": item.get("summary"),
            "lat": lat,
            "lon": lon,
            "source": item.get("source"),
            "research_status": item.get("research_status"),
        })
    return points


def mining_map_points():
    points = []

    for item in load_json(REGISTRIES["coal_camps"]):
        atlas_id = item.get("atlas_place_id")
        atlas_record = _find_atlas_record(atlas_id)
        coords = _extract_coords(atlas_record or {})

        if not coords:
            continue

        lat, lon = coords
        points.append({
            "id": item.get("id"),
            "name": item.get("name"),
            "type": item.get("type"),
            "summary": item.get("summary"),
            "lat": lat,
            "lon": lon,
            "atlas_place_id": atlas_id,
            "atlas_url": item.get("atlas_url"),
            "almanac_url": item.get("almanac_url"),
            "research_status": item.get("research_status"),
            "source": "Walker County Atlas coordinates + Walker County Almanac mining-linked record",
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

    @app.route("/map")
    def map_page():
        return render_template("map.html")

    @app.route("/mine-map")
    def mine_map_page():
        return render_template("mine_map.html")

    @app.route("/api/status")
    def api_status():
        return jsonify({
            "app": "Walker County Mining",
            "status": "foundation",
            "port": 5084,
            "counts": registry_counts()
        })

    @app.route("/api/search")
    def api_search():
        return jsonify(search_records(request.args.get("q", "")))

    @app.route("/api/map-points")
    def api_map_points():
        return jsonify(mining_map_points())

    @app.route("/api/mine-map-points")
    def api_mine_map_points():
        return jsonify(true_mine_map_points())

    @app.route("/health")
    def health():
        return jsonify({"status": "ok", "project": "walker-county-mining"})

    return app
