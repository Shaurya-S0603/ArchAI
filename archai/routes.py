"""Web and JSON API routes."""

from __future__ import annotations

from io import BytesIO

from flask import Blueprint, jsonify, render_template, request, send_file

from archai.models import DesignBrief, Layout
from archai.services.compliance import analyze_compliance
from archai.services.cost_estimator import estimate_cost
from archai.services.exporter import layout_to_obj
from archai.services.layout_generator import (
    calculate_layout_metrics,
    calculate_layout_score,
    generate_layouts,
)
from archai.services.plan_exporter import layout_to_pdf
from archai.services.project_store import (
    create_project,
    delete_project,
    get_project,
    list_projects,
    update_project,
)
from archai.services.topology import build_topology
from archai.services.zoning import build_zones
from archai.version import VERSION

pages = Blueprint("pages", __name__)
api = Blueprint("api", __name__)


@pages.get("/")
def index():
    return render_template("index.html")


@api.get("/health")
def health():
    return jsonify({"status": "ok", "service": "archai", "version": VERSION})


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
        layout.topology = build_topology(layout, accessibility=brief.accessibility)
        layout.zones = build_zones(layout, accessibility=brief.accessibility)
        layout.metrics = calculate_layout_metrics(layout)
        compliance = analyze_compliance(layout, brief)
        layout.score = calculate_layout_score(layout) * 0.75 + compliance["score"] * 0.25
        return jsonify(
            {
                "layout": layout.to_dict(),
                "compliance": compliance,
                "cost": estimate_cost(layout, brief),
            }
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


@api.post("/exports/pdf")
def export_pdf():
    payload = request.get_json(silent=True) or {}
    try:
        layout = Layout.from_dict(payload.get("layout", {}))
        brief = DesignBrief.from_dict(payload.get("brief", {}))
        layout.topology = build_topology(layout, accessibility=brief.accessibility)
        layout.zones = build_zones(layout, accessibility=brief.accessibility)
        compliance = analyze_compliance(layout, brief)
        project_name = str(payload.get("project_name", "ArchAI project")).strip()[:80]
        stream = BytesIO(layout_to_pdf(layout, brief, project_name, compliance))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return send_file(
        stream,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"{layout.id}-concept-plan.pdf",
    )


@api.get("/projects")
def projects_index():
    return jsonify({"projects": list_projects()})


@api.post("/projects")
def projects_create():
    try:
        project = create_project(request.get_json(silent=True) or {})
        return jsonify({"project": project}), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@api.get("/projects/<project_id>")
def projects_show(project_id: str):
    project = get_project(project_id)
    if project is None:
        return jsonify({"error": "Project not found."}), 404
    return jsonify({"project": project})


@api.put("/projects/<project_id>")
def projects_update(project_id: str):
    try:
        project = update_project(project_id, request.get_json(silent=True) or {})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if project is None:
        return jsonify({"error": "Project not found."}), 404
    return jsonify({"project": project})


@api.delete("/projects/<project_id>")
def projects_delete(project_id: str):
    if not delete_project(project_id):
        return jsonify({"error": "Project not found."}), 404
    return "", 204
