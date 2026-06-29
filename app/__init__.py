from flask import Flask, jsonify, render_template, request
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REGISTRIES = {
    "mines": ROOT / "data/mines/mine_registry.json",
    "companies": ROOT / "data/companies/company_registry.json",
    "counties": ROOT / "data/counties/county_index.json",
    "sources": ROOT / "data/sources/source_index.json",
    "coal_camps": ROOT / "data/registries/coal_camps.json",
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


def _valid_alabama_coord(lat, lon):
    # Rough Alabama bounding box. Prevents bad MSHA values like latitude 0.x or 38.x from plotting.
    return 30.0 <= lat <= 35.2 and -88.6 <= lon <= -84.7


def find_mine_record(mine_id):
    for item in load_json(REGISTRIES["mines"]):
        if item.get("id") == mine_id:
            return item
    return None


def county_slug(name):
    return str(name or "").strip().lower().replace(" ", "-")


def county_mines(county):
    wanted = county_slug(county)
    return [
        item for item in load_json(REGISTRIES["mines"])
        if county_slug(item.get("county")) == wanted
    ]


def county_stats(records):
    statuses = {}
    types = {}
    operators = {}

    for r in records:
        statuses[r.get("status") or "Unknown"] = statuses.get(r.get("status") or "Unknown", 0) + 1
        types[r.get("mine_type") or r.get("type") or "Unknown"] = types.get(r.get("mine_type") or r.get("type") or "Unknown", 0) + 1
        operators[r.get("operator") or "Unknown"] = operators.get(r.get("operator") or "Unknown", 0) + 1

    return {
        "total": len(records),
        "statuses": sorted(statuses.items(), key=lambda x: (-x[1], x[0])),
        "types": sorted(types.items(), key=lambda x: (-x[1], x[0])),
        "operators": sorted(operators.items(), key=lambda x: (-x[1], x[0]))[:12],
    }


def county_index():
    names = sorted(set(r.get("county") for r in load_json(REGISTRIES["mines"]) if r.get("county")))
    return [
        {
            "name": name,
            "slug": county_slug(name),
            "count": len(county_mines(name)),
        }
        for name in names
    ]


def clean_company_name(name):
    return " ".join(str(name or "").replace(";", "; ").split())


def company_slug(name):
    cleaned = clean_company_name(name)
    return cleaned.lower().replace("&", "and").replace(".", "").replace(",", "").replace(";", "").replace(" ", "-")


def company_mines(company):
    wanted = company_slug(company)
    return [
        item for item in load_json(REGISTRIES["mines"])
        if company_slug(item.get("operator")) == wanted
        or company_slug(item.get("controller")) == wanted
    ]


def company_index():
    companies = {}

    for r in load_json(REGISTRIES["mines"]):
        for name in [r.get("operator"), r.get("controller")]:
            if not name:
                continue

            slug = company_slug(name)
            if not slug:
                continue

            if slug not in companies:
                companies[slug] = {
                    "name": clean_company_name(name),
                    "slug": slug,
                    "count": 0,
                    "aliases": set(),
                }

            companies[slug]["count"] += 1
            companies[slug]["aliases"].add(name)

    out = []
    for item in companies.values():
        aliases = sorted(item["aliases"])
        out.append({
            "name": clean_company_name(item["name"]),
            "slug": item["slug"],
            "count": item["count"],
            "aliases": aliases,
            "alias_count": len(aliases),
        })

    return sorted(out, key=lambda x: (-x["count"], x["name"]))


def coal_camp_slug(name):
    return str(name or "").strip().lower().replace("&", "and").replace(".", "").replace(",", "").replace(" ", "-")


def coal_camp_index():
    camps = load_json(REGISTRIES["coal_camps"])
    return sorted(camps, key=lambda x: x.get("name", ""))


def find_coal_camp(camp_id):
    for camp in load_json(REGISTRIES["coal_camps"]):
        if camp.get("id") == camp_id or coal_camp_slug(camp.get("name")) == camp_id:
            return camp
    return None


def global_search(query):
    q = str(query or "").strip().lower()
    if not q:
        return []

    results = []

    for m in load_json(REGISTRIES["mines"]):
        text = " ".join([
            str(m.get("name","")),
            str(m.get("nearest_town","")),
            str(m.get("county","")),
            str(m.get("operator","")),
            str(m.get("controller",""))
        ]).lower()

        if q in text:
            results.append({
                "type":"Mine",
                "title":m.get("name"),
                "subtitle":m.get("county"),
                "url":f"/mine/{m.get('id')}"
            })

    for c in company_index():
        if q in c["name"].lower():
            results.append({
                "type":"Company",
                "title":c["name"],
                "subtitle":f'{c["count"]} mine records',
                "url":f'/company/{c["slug"]}'
            })

    for camp in load_json(REGISTRIES["coal_camps"]):
        text = " ".join([
            str(camp.get("name","")),
            str(camp.get("county","")),
            str(camp.get("company",""))
        ]).lower()

        if q in text:
            results.append({
                "type":"Coal Camp",
                "title":camp.get("name"),
                "subtitle":camp.get("county"),
                "url":f'/coal-camp/{camp.get("id")}'
            })

    return results[:200]

def company_stats(records):
    counties = {}
    statuses = {}
    types = {}

    for r in records:
        counties[r.get("county") or "Unknown"] = counties.get(r.get("county") or "Unknown", 0) + 1
        statuses[r.get("status") or "Unknown"] = statuses.get(r.get("status") or "Unknown", 0) + 1
        types[r.get("mine_type") or r.get("type") or "Unknown"] = types.get(r.get("mine_type") or r.get("type") or "Unknown", 0) + 1

    return {
        "total": len(records),
        "counties": sorted(counties.items(), key=lambda x: (-x[1], x[0])),
        "statuses": sorted(statuses.items(), key=lambda x: (-x[1], x[0])),
        "types": sorted(types.items(), key=lambda x: (-x[1], x[0])),
    }


def mine_map_points():
    points = []
    for item in load_json(REGISTRIES["mines"]):
        coords = _extract_coords(item)
        if not coords:
            continue

        lat, lon = coords
        if not _valid_alabama_coord(lat, lon):
            continue
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

    @app.route("/coal-camps")
    def coal_camps_page():
        return render_template("coal_camps.html")

    @app.route("/api/coal-camps")
    def api_coal_camps():
        return jsonify(coal_camp_index())

    @app.route("/coal-camp/<camp_id>")
    def coal_camp_page(camp_id):
        camp = find_coal_camp(camp_id)
        if not camp:
            return render_template("coal_camp.html", camp=None), 404
        return render_template("coal_camp.html", camp=camp)

    @app.route("/api/coal-camp/<camp_id>")
    def api_coal_camp(camp_id):
        camp = find_coal_camp(camp_id)
        if not camp:
            return jsonify({"error": "coal camp not found"}), 404
        return jsonify(camp)

    @app.route("/companies")
    def companies_page():
        return render_template("companies.html")

    @app.route("/api/companies")
    def api_companies():
        return jsonify(company_index())

    @app.route("/company/<company>")
    def company_page(company):
        records = company_mines(company)
        if not records:
            return render_template("company.html", company=company.title(), records=[], stats=company_stats([])), 404

        label = None
        wanted = company_slug(company)
        for r in records:
            if company_slug(r.get("operator")) == wanted:
                label = r.get("operator")
                break
            if company_slug(r.get("controller")) == wanted:
                label = r.get("controller")
                break

        return render_template("company.html", company=label or company.title(), records=records, stats=company_stats(records))

    @app.route("/api/company/<company>")
    def api_company(company):
        records = company_mines(company)
        return jsonify({
            "company": company,
            "count": len(records),
            "stats": company_stats(records),
            "mines": records,
        })

    @app.route("/counties")
    def counties_page():
        counties = county_index()
        return render_template("counties.html", counties=counties)

    @app.route("/county/<county>")
    def county_page(county):
        records = county_mines(county)
        if not records:
            return render_template("county.html", county=county.title(), records=[], stats=county_stats([])), 404
        label = records[0].get("county") or county.title()
        return render_template("county.html", county=label, records=records, stats=county_stats(records))

    @app.route("/api/county/<county>")
    def api_county(county):
        records = county_mines(county)
        return jsonify({
            "county": county,
            "count": len(records),
            "stats": county_stats(records),
            "mines": records,
        })

    @app.route("/mine/<mine_id>")
    def mine_detail_page(mine_id):
        mine = find_mine_record(mine_id)
        if not mine:
            return render_template("mine_detail.html", mine=None), 404
        return render_template("mine_detail.html", mine=mine)

    @app.route("/api/mine/<mine_id>")
    def api_mine_detail(mine_id):
        mine = find_mine_record(mine_id)
        if not mine:
            return jsonify({"error": "mine not found"}), 404
        return jsonify(mine)

    @app.route("/api/county-coverage")
    def api_county_coverage():
        mines = load_json(REGISTRIES["mines"])
        all_counties = sorted({
            r.get("county")
            for r in mines
            if r.get("county")
        })

        mapped_points = mine_map_points()
        mapped_counties = sorted({
            r.get("county")
            for r in mapped_points
            if r.get("county")
        })

        unmapped_counties = sorted(set(all_counties) - set(mapped_counties))

        return jsonify({
            "all_registry_counties": len(all_counties),
            "mapped_counties": len(mapped_counties),
            "unmapped_counties": len(unmapped_counties),
            "unmapped_county_names": unmapped_counties,
            "mapped_county_names": mapped_counties,
        })

    @app.route("/api/status")
    def api_status():
        mines = load_json(REGISTRIES["mines"])

        counties = {
            r.get("county")
            for r in mines
            if r.get("county")
        }

        companies = set()
        for r in mines:
            if r.get("operator"):
                companies.add(company_slug(r["operator"]))
            if r.get("controller"):
                companies.add(company_slug(r["controller"]))

        return jsonify({
            "app": "Alabama Mining Encyclopedia",
            "status": "mines_only_foundation",
            "scope": "All Alabama mines, past and present. Source-backed mine records only.",
            "port": 5084,
            "counts": {
                "mines": len(mines),
                "counties": len(counties),
                "companies": len(companies),
                "sources": len(load_json(REGISTRIES["sources"]))
            }
        })

    @app.route("/api/search")
    def api_search():
        return jsonify(search_records(request.args.get("q", "")))

    @app.route("/api/mine-map-points")
    def api_mine_map_points():
        return jsonify(mine_map_points())

    @app.route("/health")
    def health():
        return jsonify({"status": "ok", "project": "alabama-mining-encyclopedia"})

    return app
