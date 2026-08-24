"""Live end-to-end check: simulator.py + full app wiring over TCP.

Starts the device simulator on configs/Test1, builds the real App (real
ConnectionManager, Parser, ProtocolCodec, TrafficLogger, tkinter UI), sends a
message from the UI, and verifies the RX answer reaches display, traffic log
and comm.log. Also exercises periodic send start/stop.

Run from the repo root: python verify_e2e.py
"""

import socket
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, ".")

from commworkbench.config_loader import CONFIGS_DIR  # noqa: E402
from main import App  # noqa: E402

PROJECT = "Test1"
PROJ_DIR = CONFIGS_DIR / PROJECT
TOUCHED = ("ui.json", "tx-state.json", "comm.log")
TX_MSG = "QuerySensor"
RX_MSG = "SensorResponse"
DEVICE_ID = "7"


def pump(root, seconds: float):
    end = time.time() + seconds
    while time.time() < end:
        root.update()
        time.sleep(0.01)


def pump_until(root, predicate, timeout: float) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        root.update()
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


def wait_port(host: str, port: int, timeout: float) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        try:
            with socket.create_connection((host, port), 0.5):
                return True
        except OSError:
            time.sleep(0.05)
    return False


def rows(ui, direction: str) -> list[tuple]:
    out = []
    for iid in ui._tree.get_children():
        vals = ui._tree.item(iid, "values")
        if vals[1] == direction:
            out.append(vals)
    return out


def send_button(ui, msg_name):
    for frame in ui._send_inner.winfo_children():
        if frame.cget("text") != ui._protocol_config["messages"][msg_name].get("name", msg_name):
            continue
        for child in frame.winfo_children():
            if child.winfo_class() == "Button" and child.cget("text") == "Send":
                return child
    raise AssertionError(f"Send button not found for {msg_name}")


def main():
    backup = {f: (PROJ_DIR / f).read_bytes() for f in TOUCHED if (PROJ_DIR / f).exists()}
    log_path = PROJ_DIR / "comm.log"
    if log_path.exists():
        log_path.unlink()

    sim = subprocess.Popen(
        [sys.executable, "simulator.py", str(PROJ_DIR)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    app = None
    try:
        assert wait_port("127.0.0.1", 8080, 10), "simulator did not start listening"
        print("  simulator listening: OK")

        app = App()
        app._projects = app._loader.discover_projects()
        assert PROJECT in app._projects, f"{PROJECT} not discovered"
        app._load_project(PROJECT)
        app._start_ui()
        ui = app._ui
        root = ui.root

        assert pump_until(root, app._conn_mgr.is_connected, 10), "app did not connect"
        pump(root, 0.3)
        assert ui._status_label.cget("text") == "127.0.0.1:8080", ui._status_label.cget("text")
        print("  connected + status bar: OK")

        entry = ui._send_entries[TX_MSG]["device_id"]
        entry.delete(0, "end")
        entry.insert(0, DEVICE_ID)
        send_button(ui, TX_MSG).invoke()

        assert pump_until(root, lambda: rows(ui, "RX"), 5), "no RX row after send"
        pump(root, 0.3)

        assert ui._send_errors[TX_MSG].cget("text") == "", ui._send_errors[TX_MSG].cget("text")
        tx = rows(ui, "TX")
        rx = rows(ui, "RX")
        assert len(tx) == 1, f"expected 1 TX row, got {len(tx)}: {tx}"
        assert len(rx) == 1, f"expected 1 RX row, got {len(rx)}: {rx}"
        assert TX_MSG in tx[0][2] and "device_id=7" in tx[0][2], tx[0]
        assert tx[0][3].replace(" ", "").startswith("010700"), tx[0]
        assert RX_MSG in rx[0][2] and "temperature=" in rx[0][2], rx[0]
        assert rx[0][3], "RX row has no raw hex"
        print(f"  traffic log TX+RX rows: OK ({tx[0][2]} | {rx[0][2]})")

        labels = ui._field_labels[RX_MSG]
        assert labels["device_id"].cget("text") == DEVICE_ID, labels["device_id"].cget("text")
        assert labels["temperature"].cget("text") not in ("", "—"), "temperature not decoded"
        assert labels["mode"].cget("text") in ("IDLE", "ACTIVE"), labels["mode"].cget("text")
        print("  tab decode (device_id/temperature/mode): OK")

        content = log_path.read_text(encoding="utf-8")
        assert f"tx {TX_MSG}" in content, "TX block missing in comm.log"
        assert f"rx {RX_MSG}" in content, "RX block missing in comm.log"
        assert content.count("---") >= 3, "expected status + tx + rx blocks"
        print(f"  comm.log blocks: OK ({content.count(chr(10) + '---') + 1} blocks)")

        info = ui._periodic[TX_MSG]
        info["interval_entry"].delete(0, "end")
        info["interval_entry"].insert(0, "200")
        before = len(rows(ui, "TX"))
        info["btn"].invoke()
        assert info["btn"].cget("text") == "Stop"
        pump(root, 1.3)
        during = len(rows(ui, "TX"))
        assert during - before >= 4, f"periodic sent {during - before} frames in 1.3s @200ms"
        info["btn"].invoke()
        assert info["btn"].cget("text") == "Start"
        pump(root, 0.7)
        after = len(rows(ui, "TX"))
        assert after == during, f"periodic kept sending after stop: {during} -> {after}"
        rx_total = len(rows(ui, "RX"))
        assert rx_total >= during - 1, f"only {rx_total} RX for {during} TX"
        print(f"  periodic send start/stop: OK ({during - before} frames, {rx_total} RX total)")

        ui._on_close()
        app = None
        print("\nE2E OK.")
    finally:
        if app is not None and app._ui is not None:
            try:
                app._ui.root.destroy()
            except Exception:
                pass
            if app._conn_mgr:
                app._conn_mgr.disconnect()
        sim.terminate()
        try:
            sim.wait(timeout=5)
        except subprocess.TimeoutExpired:
            sim.kill()
        for f, data in backup.items():
            (PROJ_DIR / f).write_bytes(data)


if __name__ == "__main__":
    main()
