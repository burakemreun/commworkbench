"""Live session checks: layout/tx-state restore across restarts, project switch.

Part A drives the real app on configs/Test1: resize, move the sash, type into a
send field, close, reopen -- ui.json and tx-state.json must come back.
Part B creates a throwaway second project, switches to it mid-session through
the project combobox, and verifies every per-project object (codec, parser,
logger, ui config) was swapped -- and that closing does not clobber the new
project's ui.json with the old project's settings.

Run from the repo root: python verify_session.py
"""

import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, ".")

from commworkbench.config_loader import CONFIGS_DIR  # noqa: E402
from main import App  # noqa: E402

PROJECT = "Test1"
PROJ_DIR = CONFIGS_DIR / PROJECT
TOUCHED = ("ui.json", "tx-state.json", "comm.log")
OTHER = "ZZTemp"
OTHER_DIR = CONFIGS_DIR / OTHER

OTHER_PROTOCOL = {
    "protocol": {"name": "OtherComm", "version": "2.0", "endianness": "big"},
    "checksum": {"enabled": False},
    "messages": {
        "PingDevice": {
            "id": 9, "name": "Ping", "direction": "tx",
            "fields": [{"name": "seq", "type": "uint8"}],
        },
        "PongDevice": {
            "id": 10, "name": "Pong", "direction": "rx",
            "fields": [{"name": "seq", "type": "uint8"}],
        },
    },
}
OTHER_UI = {
    "version": 1,
    "geometry": {"width": 900, "height": 600},
    "log_view": "mixed",
    "panes": {"main_display": 0.7},
    "max_log_entries": 42,
}
OTHER_CONNECTION = {"mode": "tcp_client",
                    "tcp": {"host": "127.0.0.1", "port": 8099, "retry_interval_ms": 60000}}


def pump(root, seconds: float):
    end = time.time() + seconds
    while time.time() < end:
        root.update()
        time.sleep(0.01)


def build_app(project: str) -> App:
    app = App()
    app._projects = app._loader.discover_projects()
    app._load_project(project)
    app._start_ui()
    pump(app._ui.root, 0.4)
    return app


def close_app(app: App):
    app._ui._on_close()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def part_a():
    print("Part A -- layout + tx-state restore across restart")
    app = build_app(PROJECT)
    ui = app._ui
    root = ui.root

    root.geometry("980x640")
    pump(root, 0.5)
    pw = ui._paned.winfo_width()
    ui._paned.sash_place(0, int(pw * 0.3), 0)
    ui._record_sash_ratio()
    pump(root, 0.3)

    entry = ui._send_entries["QuerySensor"]["device_id"]
    entry.delete(0, "end")
    entry.insert(0, "42")
    close_app(app)

    saved_ui = read_json(PROJ_DIR / "ui.json")
    assert abs(saved_ui["geometry"]["width"] - 980) <= 4, saved_ui["geometry"]
    assert abs(saved_ui["geometry"]["height"] - 640) <= 4, saved_ui["geometry"]
    ratio = saved_ui["panes"]["main_display"]
    assert abs(ratio - 0.3) < 0.05, f"sash ratio not saved: {ratio}"
    assert saved_ui["log_view"] == "mixed", saved_ui
    print(f"  ui.json saved on close: OK (geometry={saved_ui['geometry']}, ratio={ratio:.3f})")

    saved_tx = read_json(PROJ_DIR / "tx-state.json")
    assert saved_tx == {"QuerySensor": {"device_id": "42"}}, saved_tx
    print("  tx-state.json saved on close: OK")

    app2 = build_app(PROJECT)
    ui2 = app2._ui
    pump(ui2.root, 0.5)
    assert abs(ui2.root.winfo_width() - 980) <= 4, ui2.root.winfo_width()
    assert abs(ui2.root.winfo_height() - 640) <= 4, ui2.root.winfo_height()
    pw2 = ui2._paned.winfo_width()
    ratio2 = ui2._paned.sash_coord(0)[0] / pw2
    assert abs(ratio2 - ratio) < 0.05, f"sash not restored: {ratio2} vs {ratio}"
    assert ui2._send_entries["QuerySensor"]["device_id"].get() == "42", "tx field not restored"
    print(f"  restored on reopen: OK (geometry={ui2.root.winfo_width()}x{ui2.root.winfo_height()}, ratio={ratio2:.3f}, device_id=42)")
    close_app(app2)


def part_b():
    print("\nPart B -- mid-session project switch")
    OTHER_DIR.mkdir(parents=True, exist_ok=True)
    (OTHER_DIR / "protocol.json").write_text(json.dumps(OTHER_PROTOCOL, indent=2), encoding="utf-8")
    (OTHER_DIR / "ui.json").write_text(json.dumps(OTHER_UI, indent=2), encoding="utf-8")
    (OTHER_DIR / "connection.json").write_text(json.dumps(OTHER_CONNECTION, indent=2), encoding="utf-8")
    (OTHER_DIR / "tx-state.json").write_text(json.dumps({"PingDevice": {"seq": "5"}}, indent=2), encoding="utf-8")

    app = build_app(PROJECT)
    ui = app._ui
    root = ui.root
    ui.set_project_list(app._projects)
    ui._project_var.set(PROJECT)
    assert OTHER in app._projects, f"{OTHER} not discovered: {app._projects}"

    entry = ui._send_entries["QuerySensor"]["device_id"]
    entry.delete(0, "end")
    entry.insert(0, "77")
    old_codec, old_parser, old_logger = ui._protocol_codec, ui._parser, ui._traffic_logger

    ui._project_var.set(OTHER)
    ui._project_combo.event_generate("<<ComboboxSelected>>")
    pump(root, 0.6)

    assert app._project_name == OTHER, app._project_name
    assert ui._protocol_codec is not old_codec, "codec not swapped"
    assert ui._parser is not old_parser, "parser not swapped"
    assert ui._traffic_logger is not old_logger, "logger not swapped"
    assert ui._traffic_logger._log_path == OTHER_DIR / "comm.log", ui._traffic_logger._log_path
    assert ui._cfg_path == OTHER_DIR / "ui.json", ui._cfg_path
    assert set(ui._send_entries) == {"PingDevice"}, set(ui._send_entries)
    assert set(ui._field_labels) == {"PongDevice"}, set(ui._field_labels)
    assert ui._send_entries["PingDevice"]["seq"].get() == "5", "new project tx-state not restored"
    assert ui._max_log_entries == 42, ui._max_log_entries
    print("  codec/parser/logger/send-area/tx-state swapped: OK")

    assert read_json(PROJ_DIR / "tx-state.json") == {"QuerySensor": {"device_id": "77"}}, "old tx-state not saved"
    print("  old project tx-state saved on switch: OK")

    assert ui.ui_cfg.get("max_log_entries") == 42, f"ui_cfg still the old project's: {ui.ui_cfg}"
    assert abs(ui._ratios.get("main_display", 0) - 0.7) < 0.05, f"ratios not swapped: {ui._ratios}"
    pump(root, 0.4)
    assert abs(root.winfo_width() - 900) <= 4, f"geometry not applied: {root.winfo_width()}"
    print("  ui config swapped (ui_cfg/ratios/geometry): OK")

    codec = ui._protocol_codec
    frame = codec.encode("PingDevice", {"seq": 3})
    assert frame[0] == 9, f"encoded with the wrong protocol: {frame.hex()}"
    print(f"  new protocol encodes: OK ({frame.hex(' ')})")

    close_app(app)
    saved = read_json(OTHER_DIR / "ui.json")
    assert saved["max_log_entries"] == 42, f"new project's ui.json clobbered: {saved}"
    assert abs(saved["geometry"]["width"] - 900) <= 4, saved["geometry"]
    assert abs(saved["panes"]["main_display"] - 0.7) < 0.05, saved["panes"]
    print("  new project's ui.json intact after close: OK")

    saved_old = read_json(PROJ_DIR / "ui.json")
    assert saved_old["max_log_entries"] == read_json(PROJ_DIR / "ui.json")["max_log_entries"]
    print("  old project's ui.json untouched by the switch: OK")


def main():
    backup = {f: (PROJ_DIR / f).read_bytes() for f in TOUCHED if (PROJ_DIR / f).exists()}
    try:
        part_a()
        part_b()
        print("\nSession checks OK.")
    finally:
        for f, data in backup.items():
            (PROJ_DIR / f).write_bytes(data)
        for f in TOUCHED:
            if f not in backup and (PROJ_DIR / f).exists():
                (PROJ_DIR / f).unlink()
        shutil.rmtree(OTHER_DIR, ignore_errors=True)


if __name__ == "__main__":
    main()
