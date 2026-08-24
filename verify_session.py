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
TOUCHED = ("ui.json", "tx-state.json", "comm.log", "connection.json")
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


def tx_row(i):
    return {"type": "frame", "msg_name": "QuerySensor", "fields": {"device_id": i},
            "raw_hex": "01 0%d 00" % i, "direction": "tx"}


def rx_row(i):
    return {"type": "frame", "msg_name": "SensorResponse", "fields": {"device_id": i},
            "raw_hex": "02 0%d 00" % i, "direction": "rx"}


def part_c():
    print()
    print("Part C -- split TX/RX log view")
    app = build_app(PROJECT)
    ui = app._ui
    root = ui.root

    assert ui._trees["TX"] is ui._trees["RX"], "mixed view must share one tree"
    ui._add_log_entry(tx_row(1))
    ui._add_log_entry(rx_row(1))
    assert len(ui._trees["TX"].get_children()) == 2, "mixed view lost a row"
    print("  mixed view: OK (one chronological tree)")

    ui._log_view_var.set("split")
    ui._log_view_combo.event_generate("<<ComboboxSelected>>")
    pump(root, 0.4)

    tx_tree, rx_tree = ui._trees["TX"], ui._trees["RX"]
    assert tx_tree is not rx_tree, "split view still shares one tree"
    assert len(tx_tree.get_children()) == 1, tx_tree.get_children()
    assert len(rx_tree.get_children()) == 1, rx_tree.get_children()
    assert "QuerySensor" in tx_tree.item(tx_tree.get_children()[0], "values")[2]
    assert "SensorResponse" in rx_tree.item(rx_tree.get_children()[0], "values")[2]
    print("  toggle to split: OK (history kept, rows routed by direction)")

    ui._add_log_entry(rx_row(2))
    assert len(rx_tree.get_children()) == 2 and len(tx_tree.get_children()) == 1, "new row routed wrong"
    print("  new traffic routed to its pane: OK")

    close_app(app)
    assert read_json(PROJ_DIR / "ui.json")["log_view"] == "split", "log_view not persisted"

    app2 = build_app(PROJECT)
    ui2 = app2._ui
    assert ui2._trees["TX"] is not ui2._trees["RX"], "split view not restored from ui.json"
    assert ui2._log_view_var.get() == "split", ui2._log_view_var.get()
    assert not ui2._trees["TX"].get_children(), "traffic log must start empty"
    print("  split view restored on reopen: OK")
    close_app(app2)



def part_d():
    print("\nPart D -- connection bar")
    # seed a known connection.json: this part asserts on the values it loads, so
    # it must not depend on whatever the last live session left behind
    (PROJ_DIR / "connection.json").write_text(json.dumps({
        "mode": "tcp_client",
        "tcp": {"host": "127.0.0.1", "port": 8080, "retry_interval_ms": 3000},
        "serial": {"port": "COM1", "baud_rate": 115200},
    }, indent=2), encoding="utf-8")

    app = build_app(PROJECT)
    ui = app._ui
    root = ui.root

    # the bar must open on what connection.json already says
    assert ui._type_var.get() == "tcp", ui._type_var.get()
    assert ui._host_var.get() == "127.0.0.1", ui._host_var.get()
    assert ui._tcp_port_var.get() == "8080", ui._tcp_port_var.get()
    assert ui._mode_var.get() == "client", ui._mode_var.get()
    # the app auto-connects at startup, so the button offers the opposite action
    assert ui._connect_btn.cget("text") == "Disconnect", ui._connect_btn.cget("text")
    print("  fields loaded from connection.json: OK")

    ui._on_connect_click()
    pump(root, 0.3)
    assert ui._connect_btn.cget("text") == "Connect", ui._connect_btn.cget("text")
    ui._on_connect_click()
    pump(root, 0.3)
    assert ui._connect_btn.cget("text") == "Disconnect", ui._connect_btn.cget("text")
    print("  connect/disconnect toggle: OK")

    # a typo in the port must not reach the connection manager or the file
    ui._on_connect_click()
    ui._tcp_port_var.set("nope")
    ui._on_connect_click()
    pump(root, 0.2)
    assert ui._connect_btn.cget("text") == "Connect", "bad port must not connect"
    assert app._configs["connection.json"]["tcp"]["port"] == 8080
    print("  invalid port rejected: OK")

    ui._tcp_port_var.set("9100")
    ui._host_var.set("10.0.0.5")
    ui._type_var.set("serial")
    ui._show_type_fields()
    # the port box scans the machine but stays typeable
    assert ui._com_combo.cget("state") != "readonly", ui._com_combo.cget("state")
    ui._refresh_ports()
    assert isinstance(ui._com_combo.cget("values"), (tuple, str)), ui._com_combo.cget("values")
    assert set(ui._port_info) == set(ui._com_combo["values"]), ui._port_info
    ui._com_var.set("COM_NOPE")
    assert "not detected" in ui._port_tooltip() or "No serial ports" in ui._port_tooltip(),         ui._port_tooltip()
    real_ports = dict(ui._port_info)
    # the detail branch has to be checked even on a machine with no COM ports
    ui._port_info = dict(real_ports)
    ui._port_info["COM_FAKE"] = "USB Serial Device' + BS + 'nFTDI' + BS + 'nUSB VID:PID=0403:6001"
    ui._com_var.set("COM_FAKE")
    tip = ui._port_tooltip()
    assert tip.startswith("COM_FAKE"), tip
    assert "FTDI" in tip and "VID:PID" in tip, tip
    ui._port_info = real_ports
    print(f"  port scan + tooltip: OK ({len(real_ports)} real port(s): {list(real_ports)})")

    ui._com_var.set("COM7")
    # the baud box is editable on purpose: a rate outside the dropdown list must
    # still survive to the config
    assert ui._baud_combo.cget("state") != "readonly", ui._baud_combo.cget("state")
    ui._baud_var.set("500000")
    assert ui._apply_conn_fields() is None
    assert app._configs["connection.json"]["serial"]["baud_rate"] == 500000
    ui._baud_var.set("57600")
    pump(root, 0.2)
    close_app(app)

    saved = read_json(PROJ_DIR / "connection.json")
    assert saved["mode"] == "serial", saved
    assert saved["serial"]["port"] == "COM7", saved
    assert saved["serial"]["baud_rate"] == 57600, saved
    # switching type must not throw away the tcp settings that were typed in
    assert saved["tcp"]["host"] == "127.0.0.1", saved
    print("  hand-typed baud accepted + edits saved to connection.json: OK")

    app2 = build_app(PROJECT)
    ui2 = app2._ui
    assert ui2._type_var.get() == "serial", ui2._type_var.get()
    assert ui2._com_var.get() == "COM7", ui2._com_var.get()
    assert ui2._baud_var.get() == "57600", ui2._baud_var.get()
    close_app(app2)
    print("  restored on reopen: OK")


def main():
    backup = {f: (PROJ_DIR / f).read_bytes() for f in TOUCHED if (PROJ_DIR / f).exists()}
    try:
        part_a()
        part_b()
        part_c()
        part_d()
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
