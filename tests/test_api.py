def test_health_endpoint(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"
    assert response.get_json()["version"] == "0.2.0-dev.1"


def test_home_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"ArchAI Design Studio" in response.data


def test_generate_returns_five_ranked_results(client, brief):
    response = client.post("/api/v1/layouts/generate", json=brief)
    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["results"]) == 5
    scores = [result["layout"]["score"] for result in payload["results"]]
    assert scores == sorted(scores, reverse=True)
    assert all(result["layout"]["rooms"] for result in payload["results"])
    assert all(result["layout"]["topology"]["walls"] for result in payload["results"])
    assert all(result["layout"]["topology"]["openings"] for result in payload["results"])
    assert all("disclaimer" in result["compliance"] for result in payload["results"])


def test_generate_rejects_invalid_site(client, brief):
    brief["site_width_m"] = 4
    response = client.post("/api/v1/layouts/generate", json=brief)
    assert response.status_code == 400
    assert "between 10 and 60" in response.get_json()["error"]


def test_edited_overlap_is_detected(client, brief):
    generated = client.post("/api/v1/layouts/generate", json=brief).get_json()
    layout = generated["results"][0]["layout"]
    layout["rooms"][1]["x"] = layout["rooms"][0]["x"]
    layout["rooms"][1]["y"] = layout["rooms"][0]["y"]
    response = client.post("/api/v1/layouts/analyze", json={"brief": brief, "layout": layout})
    assert response.status_code == 200
    payload = response.get_json()
    rules = {issue["rule"] for issue in payload["compliance"]["issues"]}
    assert "ROOM_OVERLAP" in rules
    assert payload["layout"]["metrics"]["adjacency_count"] >= 0


def test_obj_export_contains_geometry(client, brief):
    generated = client.post("/api/v1/layouts/generate", json=brief).get_json()
    layout = generated["results"][0]["layout"]
    response = client.post("/api/v1/exports/obj", json={"layout": layout})
    assert response.status_code == 200
    assert ".obj" in response.headers["Content-Disposition"]
    assert b"\nv " in response.data
    assert b"\nf " in response.data
    assert response.data.index(b"\nv ") < response.data.index(b"\no ")
    assert response.data.count(b"\no ") == len(layout["rooms"])


def test_pdf_export_returns_vector_plan_sheet(client, brief):
    generated = client.post("/api/v1/layouts/generate", json=brief).get_json()
    layout = generated["results"][0]["layout"]
    response = client.post(
        "/api/v1/exports/pdf",
        json={"brief": brief, "layout": layout, "project_name": "Courtyard study"},
    )

    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert response.data.startswith(b"%PDF-")
    assert len(response.data) > 5_000
    assert "concept-plan.pdf" in response.headers["Content-Disposition"]


def test_project_can_be_saved_loaded_updated_and_deleted(client, brief):
    generated = client.post("/api/v1/layouts/generate", json=brief).get_json()
    create_response = client.post(
        "/api/v1/projects",
        json={
            "name": "Courtyard study",
            "brief": generated["brief"],
            "results": generated["results"],
            "active_index": 2,
        },
    )
    assert create_response.status_code == 201
    created = create_response.get_json()["project"]
    assert created["name"] == "Courtyard study"
    assert created["active_index"] == 2
    assert created["schema_version"] == 3
    assert created["results"][0]["layout"]["zones"]["furniture"]
    assert created["results"][0]["layout"]["rooms"][0]["minimum_area"] > 0

    project_id = created["id"]
    index_response = client.get("/api/v1/projects")
    assert index_response.status_code == 200
    assert index_response.get_json()["projects"][0]["layout_count"] == 5

    load_response = client.get(f"/api/v1/projects/{project_id}")
    assert load_response.status_code == 200
    assert load_response.get_json()["project"]["brief"] == generated["brief"]

    created["name"] = "Courtyard study revised"
    created["results"][0]["layout"]["rooms"][0]["width"] += 0.5
    update_response = client.put(f"/api/v1/projects/{project_id}", json=created)
    assert update_response.status_code == 200
    updated = update_response.get_json()["project"]
    assert updated["name"] == "Courtyard study revised"
    assert updated["results"][0]["layout"]["rooms"][0]["width"] == (
        created["results"][0]["layout"]["rooms"][0]["width"]
    )

    assert client.delete(f"/api/v1/projects/{project_id}").status_code == 204
    assert client.get(f"/api/v1/projects/{project_id}").status_code == 404


def test_project_save_rejects_missing_layouts(client, brief):
    response = client.post(
        "/api/v1/projects",
        json={"name": "Incomplete", "brief": brief, "results": [], "active_index": 0},
    )
    assert response.status_code == 400
    assert "between 1 and 10" in response.get_json()["error"]


def test_project_routes_return_not_found_for_unknown_id(client, brief):
    assert client.get("/api/v1/projects/missing").status_code == 404
    assert client.put("/api/v1/projects/missing", json={}).status_code == 404
    assert client.delete("/api/v1/projects/missing").status_code == 404
