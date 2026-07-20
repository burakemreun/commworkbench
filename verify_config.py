import sys
import tempfile
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from commworkbench.config_loader import ConfigLoader

def test_valid_project():
    loader = ConfigLoader(Path(__file__).parent / "configs")
    projects = loader.discover_projects()
    assert "_example" not in projects, "should skip _example"
    print(f"discovered projects: {projects}")

    data = loader.load_project("_example")
    assert data["connection.json"]["mode"] == "tcp_client"
    assert data["protocol.json"]["protocol"]["name"] == "SensorComm"
    assert data["ui.json"]["geometry"]["width"] == 1200
    assert data["tx-state.json"]["SensorData"]["device_id"] == 1
    print("valid project: OK")

def test_missing_project():
    loader = ConfigLoader(Path(__file__).parent / "configs")
    data = loader.load_project("nonexistent")
    assert data["connection.json"]["mode"] == "tcp_client"
    assert data["ui.json"]["geometry"]["width"] == 1200
    print("missing project defaults: OK")

def test_invalid_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "bad"
        p.mkdir()
        (p / "connection.json").write_text("{bad json!!!")
        loader = ConfigLoader(Path(tmpdir))
        data = loader.load_project("bad")
        assert data["connection.json"]["mode"] == "tcp_client"
        print("invalid JSON fallback: OK")

def test_schema_mismatch():
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "partial"
        p.mkdir()
        (p / "ui.json").write_text(json.dumps({"version": 1}))
        loader = ConfigLoader(Path(tmpdir))
        data = loader.load_project("partial")
        assert data["ui.json"]["version"] == 1
        assert data["ui.json"]["geometry"]["width"] == 1200
        assert data["ui.json"]["log_view"] == "mixed"
        print("schema mismatch per-field defaults: OK")

if __name__ == "__main__":
    test_valid_project()
    test_missing_project()
    test_invalid_json()
    test_schema_mismatch()
    print("\nAll tests passed.")
