"""The simulator UI is served by the API app and every catalogued simulation module exists."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
SIM_INDEX = (FRONTEND / "js" / "sims" / "index.js").read_text()


def test_index_served_at_root():
    r = client.get("/")
    assert r.status_code == 200
    assert "Reality ASM" in r.text


def test_api_routes_still_win():
    assert client.get("/health").json()["status"] == "ok"


def test_every_sim_module_exists_and_is_served():
    modules = re.findall(r'import\("\./([\w.]+\.js)"\)', SIM_INDEX)
    assert len(modules) >= 12
    for m in modules:
        assert (FRONTEND / "js" / "sims" / m).is_file(), m
        assert client.get(f"/js/sims/{m}").status_code == 200


def test_sims_only_call_registered_tools():
    tools = {(d, t["name"]) for d, ts in client.get("/tools").json().items() for t in ts}
    for f in (FRONTEND / "js").rglob("*.js"):
        for domain, name in re.findall(r'simulate\("(\w+)", "(\w+)"', f.read_text()):
            assert (domain, name) in tools, f"{f.name} calls unknown tool {domain}.{name}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_javascript_syntax():
    for f in FRONTEND.rglob("*.js"):
        r = subprocess.run(["node", "--check", "--input-type=module"], input=f.read_text(),
                           capture_output=True, text=True)
        assert r.returncode == 0, f"{f}: {r.stderr}"
