import json

from archai.database import get_db


def test_database_migration_is_applied(app):
    with app.app_context():
        versions = [row["version"] for row in get_db().execute("SELECT version FROM schema_migrations")]
        assert versions == [1]


def test_legacy_project_is_upgraded_to_topology_schema(app, client, brief):
    generated = client.post("/api/v1/layouts/generate", json=brief).get_json()
    legacy_results = generated["results"]
    for result in legacy_results:
        result["layout"].pop("topology", None)

    with app.app_context():
        connection = get_db()
        connection.execute(
            """
            INSERT INTO projects (
                id, name, schema_version, brief_json, results_json,
                active_index, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "legacy-project",
                "Legacy project",
                1,
                json.dumps(generated["brief"]),
                json.dumps(legacy_results),
                0,
                "2026-08-31T00:00:00+00:00",
                "2026-08-31T00:00:00+00:00",
            ),
        )
        connection.commit()

    response = client.get("/api/v1/projects/legacy-project")
    assert response.status_code == 200
    project = response.get_json()["project"]
    assert project["schema_version"] == 3
    assert project["results"][0]["layout"]["topology"]["walls"]
    assert project["results"][0]["layout"]["zones"]["clearances"]
