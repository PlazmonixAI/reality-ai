from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["service"] == "reality-asm"


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


def test_simulate_differentiate():
    r = client.post("/simulate", json={
        "domain": "mathematics", "name": "differentiate",
        "args": {"expression": "x**3", "variable": "x"},
    })
    assert r.status_code == 200
    assert r.json()["result"] == "3*x**2"


def test_simulate_bad_args_422():
    r = client.post("/simulate", json={
        "domain": "mathematics", "name": "determinant", "args": {"matrix": [[1, 2, 3]]},
    })
    assert r.status_code == 422


def test_simulate_unsafe_expression_422():
    r = client.post("/simulate", json={
        "domain": "mathematics", "name": "solve_equation",
        "args": {"equation": "().__class__"},
    })
    assert r.status_code == 422
