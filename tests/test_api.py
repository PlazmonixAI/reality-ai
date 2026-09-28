from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_tools_listing():
    r = client.get("/tools")
    assert "mathematics" in r.json()


def test_simulate_solve_equation():
    r = client.post("/simulate", json={
        "domain": "mathematics", "name": "solve_equation",
        "args": {"equation": "x**2 - 4 = 0", "variable": "x"},
    })
    assert r.status_code == 200
    assert sorted(r.json()["result"]) == ["-2", "2"]


def test_unknown_tool():
    r = client.post("/simulate", json={"domain": "physics", "name": "nope"})
    assert r.status_code == 404
