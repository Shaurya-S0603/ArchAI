def test_health_endpoint(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


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
    rules = {issue["rule"] for issue in response.get_json()["compliance"]["issues"]}
    assert "ROOM_OVERLAP" in rules


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
