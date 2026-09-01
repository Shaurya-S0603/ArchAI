"""Validated local project persistence for the Phase 1 editor."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from archai.database import get_db, transaction
from archai.models import DesignBrief, Layout
from archai.services.compliance import analyze_compliance
from archai.services.cost_estimator import estimate_cost
from archai.services.layout_generator import calculate_layout_metrics, calculate_layout_score
from archai.services.topology import build_topology
from archai.services.zoning import build_zones

PROJECT_SCHEMA_VERSION = 3
MAX_PROJECTS_RETURNED = 100


def _timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _validated_name(value: Any) -> str:
    name = str(value or "").strip()
    if not 1 <= len(name) <= 80:
        raise ValueError("Project name must contain between 1 and 80 characters.")
    return name


def _validated_state(payload: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], int]:
    if not isinstance(payload, dict):
        raise ValueError("Project data must be a JSON object.")
    brief = DesignBrief.from_dict(payload.get("brief", {}))
    raw_results = payload.get("results")
    if not isinstance(raw_results, list) or not 1 <= len(raw_results) <= 10:
        raise ValueError("A project must contain between 1 and 10 layout results.")

    results: list[dict[str, Any]] = []
    for raw_result in raw_results:
        if not isinstance(raw_result, dict):
            raise ValueError("Each project result must be a JSON object.")
        layout = Layout.from_dict(raw_result.get("layout", {}))
        if (
            abs(layout.site_width_m - brief.site_width_m) > 0.01
            or abs(layout.site_depth_m - brief.site_depth_m) > 0.01
        ):
            raise ValueError("Every saved layout must use the design brief site dimensions.")
        layout.topology = build_topology(layout, accessibility=brief.accessibility)
        layout.zones = build_zones(layout, accessibility=brief.accessibility)
        layout.metrics = calculate_layout_metrics(layout)
        compliance = analyze_compliance(layout, brief)
        layout.score = calculate_layout_score(layout) * 0.75 + compliance["score"] * 0.25
        results.append(
            {
                "layout": layout.to_dict(),
                "compliance": compliance,
                "cost": estimate_cost(layout, brief),
            }
        )

    try:
        active_index = int(payload.get("active_index", 0))
    except (TypeError, ValueError) as exc:
        raise ValueError("active_index must be a whole number.") from exc
    if not 0 <= active_index < len(results):
        raise ValueError("active_index must identify one of the saved layouts.")
    return brief.to_dict(), results, active_index


def _row_to_project(row: Any) -> dict[str, Any]:
    project = {
        "id": row["id"],
        "name": row["name"],
        "schema_version": row["schema_version"],
        "brief": json.loads(row["brief_json"]),
        "results": json.loads(row["results_json"]),
        "active_index": row["active_index"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
    if project["schema_version"] < PROJECT_SCHEMA_VERSION:
        brief, results, active_index = _validated_state(project)
        project.update(
            {
                "schema_version": PROJECT_SCHEMA_VERSION,
                "brief": brief,
                "results": results,
                "active_index": active_index,
            }
        )
    return project


def list_projects() -> list[dict[str, Any]]:
    rows = get_db().execute(
        """
        SELECT id, name, active_index, created_at, updated_at, results_json
        FROM projects
        ORDER BY updated_at DESC, name ASC
        LIMIT ?
        """,
        (MAX_PROJECTS_RETURNED,),
    )
    projects = []
    for row in rows:
        project = dict(row)
        project["layout_count"] = len(json.loads(project.pop("results_json")))
        projects.append(project)
    return projects


def get_project(project_id: str) -> dict[str, Any] | None:
    row = get_db().execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    return _row_to_project(row) if row else None


def create_project(payload: dict[str, Any]) -> dict[str, Any]:
    name = _validated_name(payload.get("name"))
    brief, results, active_index = _validated_state(payload)
    project_id = uuid4().hex
    now = _timestamp()
    with transaction() as connection:
        connection.execute(
            """
            INSERT INTO projects (
                id, name, schema_version, brief_json, results_json,
                active_index, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                name,
                PROJECT_SCHEMA_VERSION,
                json.dumps(brief, separators=(",", ":")),
                json.dumps(results, separators=(",", ":")),
                active_index,
                now,
                now,
            ),
        )
    return get_project(project_id)  # type: ignore[return-value]


def update_project(project_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    if get_project(project_id) is None:
        return None
    name = _validated_name(payload.get("name"))
    brief, results, active_index = _validated_state(payload)
    with transaction() as connection:
        connection.execute(
            """
            UPDATE projects
            SET name = ?, schema_version = ?, brief_json = ?, results_json = ?,
                active_index = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                name,
                PROJECT_SCHEMA_VERSION,
                json.dumps(brief, separators=(",", ":")),
                json.dumps(results, separators=(",", ":")),
                active_index,
                _timestamp(),
                project_id,
            ),
        )
    return get_project(project_id)


def delete_project(project_id: str) -> bool:
    with transaction() as connection:
        cursor = connection.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    return cursor.rowcount > 0
