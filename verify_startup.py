import json
import tempfile
from pathlib import Path

from commworkbench.config_loader import ConfigLoader, EXPECTED_FILES
from commworkbench.protocol_codec import ProtocolCodec
from commworkbench.parser import Parser
from commworkbench.connection_manager import ConnectionManager
from commworkbench.traffic_logger import TrafficLogger


def test_discover_projects():
    loader = ConfigLoader(Path("configs"))
    projects = loader.discover_projects()
    assert isinstance(projects, list), "discover_projects must return list"
    for p in projects:
        assert not p.startswith("_"), f"underscore-prefixed dir leaked: {p}"
    print(f"  discover_projects: OK ({len(projects)} projects: {projects})")


def test_app_state_roundtrip():
    from main import _load_app_state, _save_app_state, APP_STATE_PATH

    original = _load_app_state()
    try:
        _save_app_state({"last_project": "test-proj"})
        loaded = _load_app_state()
        assert loaded == {"last_project": "test-proj"}, f"roundtrip failed: {loaded}"

        _save_app_state({})
        loaded = _load_app_state()
        assert loaded == {}, f"clear failed: {loaded}"
        print("  app-state roundtrip: OK")
    finally:
        if original:
            _save_app_state(original)
        elif APP_STATE_PATH.exists():
            APP_STATE_PATH.unlink()


def test_tx_state_roundtrip():
    from main import _load_tx_state, _save_tx_state

    with tempfile.TemporaryDirectory() as td:
        project_dir = Path(td)
        _save_tx_state(project_dir, {"MsgA": {"field1": "42", "field2": "hello"}})
        loaded = _load_tx_state(project_dir)
        assert loaded == {"MsgA": {"field1": "42", "field2": "hello"}}, f"roundtrip failed: {loaded}"

        _save_tx_state(project_dir, {})
        loaded = _load_tx_state(project_dir)
        assert loaded == {}, f"clear failed: {loaded}"
        print("  tx-state roundtrip: OK")


def test_load_project():
    loader = ConfigLoader(Path("configs"))
    projects = loader.discover_projects()
    if not projects:
        print("  load_project: SKIP (no projects)")
        return
    configs = loader.load_project(projects[0])
    assert isinstance(configs, dict), "load_project must return dict"
    for f in EXPECTED_FILES:
        assert f in configs, f"missing key: {f}"
    print(f"  load_project({projects[0]}): OK (keys: {list(configs.keys())})")


def test_protocol_codec_from_config():
    loader = ConfigLoader(Path("configs"))
    projects = loader.discover_projects()
    if not projects:
        print("  protocol_codec: SKIP (no projects)")
        return
    configs = loader.load_project(projects[0])
    proto = configs.get("protocol.json", {})
    codec = ProtocolCodec(proto)
    msgs = proto.get("messages", {})
    if msgs:
        msg_name = next(iter(msgs))
        values = {}
        for f in msgs[msg_name].get("fields", []):
            if f["type"] in ("float32", "float64"):
                values[f["name"]] = 1.0
            elif "int" in f["type"]:
                values[f["name"]] = 1
            else:
                values[f["name"]] = "test"
        encoded = codec.encode(msg_name, values)
        assert isinstance(encoded, bytes), "encode must return bytes"
        print(f"  protocol_codec encode({msg_name}): OK ({len(encoded)} bytes)")
    else:
        print("  protocol_codec: OK (no messages to encode)")


def test_parser_from_config():
    loader = ConfigLoader(Path("configs"))
    projects = loader.discover_projects()
    if not projects:
        print("  parser: SKIP (no projects)")
        return
    configs = loader.load_project(projects[0])
    proto = configs.get("protocol.json", {})
    parser = Parser(proto)
    assert parser is not None
    print("  parser creation: OK")


def test_connection_manager_from_config():
    loader = ConfigLoader(Path("configs"))
    projects = loader.discover_projects()
    if not projects:
        print("  connection_manager: SKIP (no projects)")
        return
    configs = loader.load_project(projects[0])
    import queue
    q = queue.Queue()
    conn = ConnectionManager(configs.get("connection.json", {}), q)
    assert conn.status_text, "status_text should be non-empty"
    assert not conn.is_connected()
    print(f"  connection_manager: OK (status: {conn.status_text})")


def test_traffic_logger():
    with tempfile.TemporaryDirectory() as td:
        logger = TrafficLogger(Path(td))
        logger.log_event("tx", "TestMsg", {"field": "val"}, "aabb")
        logger.log_error("bad frame", "dead")
        logger.log_status("connected")
        log_path = Path(td) / "comm.log"
        assert log_path.exists(), "comm.log not created"
        content = log_path.read_text()
        assert "TestMsg" in content
        assert "bad frame" in content
        print("  traffic_logger: OK")


def main():
    print("Verifying startup components...\n")
    test_discover_projects()
    test_app_state_roundtrip()
    test_tx_state_roundtrip()
    test_load_project()
    test_protocol_codec_from_config()
    test_parser_from_config()
    test_connection_manager_from_config()
    test_traffic_logger()
    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
