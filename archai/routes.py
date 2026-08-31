"""Web and JSON API routes."""

from __future__ import annotations

from io import BytesIO

from flask import Blueprint, jsonify, render_template, request, send_file

from archai.models import DesignBrief, Layout
from archai.services.compliance import analyze_compliance
from archai.services.cost_estimator import estimate_cost
from archai.services.exporter import layout_to_obj
from archai.services.layout_generator import generate_layouts

pages = Blueprint("pages", __name__)
api = Blueprint("api", __name__)


@pages.get("/")
def index():
    return render_template("index.html")


@api.get("/health")
def health():
    return jsonify({"status": "ok", "service": "archai", "version": "0.1.0"})


@api.post("/layouts/generate")
def generate():
    try:
        brief = DesignBrief.from_dict(request.get_json(silent=True) or {})
        layouts = generate_layouts(brief)
        results = []
        for layout in layouts:
            compliance = analyze_compliance(layout, brief)
            cost = estimate_cost(layout, brief)
            layout.score = layout.score * 0.75 + compliance["score"] * 0.25
            results.append({"layout": layout.to_dict(), "compliance": compliance, "cost": cost})
        results.sort(key=lambda item: item["layout"]["score"], reverse=True)
        return jsonify({"brief": brief.to_dict(), "results": results})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@api.post("/layouts/analyze")
def analyze():
    payload = request.get_json(silent=True) or {}
    try:
        layout = Layout.from_dict(payload.get("layout", {}))
        brief = DesignBrief.from_dict(payload.get("brief", {}))
        return jsonify(
            {"compliance": analyze_compliance(layout, brief), "cost": estimate_cost(layout, brief)}
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@api.post("/exports/obj")
def export_obj():
    payload = request.get_json(silent=True) or {}
    try:
        layout = Layout.from_dict(payload.get("layout", {}))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    stream = BytesIO(layout_to_obj(layout).encode("utf-8"))
    return send_file(
        stream,
        mimetype="text/plain",
        as_attachment=True,
        download_name=f"{layout.id}.obj",
    )
