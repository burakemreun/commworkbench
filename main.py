import json
import logging
import queue
from pathlib import Path

from commworkbench.config_loader import CONFIGS_DIR, ConfigLoader
from commworkbench.connection_manager import ConnectionManager
from commworkbench.parser import Parser
from commworkbench.protocol_codec import ProtocolCodec
from commworkbench.traffic_logger import TrafficLogger
from commworkbench.ui import CommWorkbenchUI

log = logging.getLogger(__name__)

APP_STATE_PATH = CONFIGS_DIR / "_app-state.json"


def _load_app_state() -> dict:
    try:
        return json.loads(APP_STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_app_state(state: dict):
    APP_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    APP_STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _load_tx_state(project_dir: Path) -> dict:
    tx_path = project_dir / "tx-state.json"
    try:
        return json.loads(tx_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_tx_state(project_dir: Path, state: dict):
    tx_path = project_dir / "tx-state.json"
    tx_path.write_text(json.dumps(state, indent=2), encoding="utf-8")


class App:
    def __init__(self):
        self._loader = ConfigLoader(CONFIGS_DIR)
        self._frame_queue: queue.Queue = queue.Queue()
        self._projects: list[str] = []
        self._project_name: str = ""
        self._configs: dict[str, dict] = {}
        self._conn_mgr: ConnectionManager | None = None
        self._parser: Parser | None = None
        self._codec: ProtocolCodec | None = None
        self._logger: TrafficLogger | None = None
        self._ui: CommWorkbenchUI | None = None

    def run(self):
        self._projects = self._loader.discover_projects()
        self._pick_initial_project()

        if self._projects:
            self._load_project(self._project_name)
            self._start_ui()
        else:
            self._start_ui_empty()

        self._ui.run()

    def _pick_initial_project(self):
        if not self._projects:
            return
        app_state = _load_app_state()
        last = app_state.get("last_project", "")
        if last in self._projects:
            self._project_name = last
        else:
            self._project_name = self._projects[0]

    def _load_project(self, name: str):
        self._project_name = name
        self._configs = self._loader.load_project(name)
        self._codec = ProtocolCodec(self._configs.get("protocol.json", {}))
        self._parser = Parser(self._configs.get("protocol.json", {}))
        max_entries = self._configs.get("ui.json", {}).get("max_log_entries", 1000)
        self._logger = TrafficLogger(CONFIGS_DIR / name, max_entries)

    def _start_ui(self):
        self._conn_mgr = ConnectionManager(
            self._configs.get("connection.json", {}), self._frame_queue,
        )
        self._ui = CommWorkbenchUI(
            configs=self._configs,
            project_name=self._project_name,
            protocol_config=self._configs.get("protocol.json", {}),
            frame_queue=self._frame_queue,
            parser=self._parser,
            connection_manager=self._conn_mgr,
            close_callback=self._on_close_event,
            traffic_logger=self._logger,
        )
        self._ui.set_protocol_codec(self._codec)
        self._ui.set_project_list(self._projects)
        self._ui._project_var.set(self._project_name)

        tx_state = _load_tx_state(CONFIGS_DIR / self._project_name)
        self._ui.restore_tx_state(tx_state)

        self._conn_mgr.connect()

    def _start_ui_empty(self):
        self._ui = CommWorkbenchUI(
            configs={},
            project_name="_current",
            protocol_config={},
            frame_queue=self._frame_queue,
            close_callback=self._on_close_event,
        )
        self._ui.set_project_list([])
        self._ui.update_status("No projects found \u2014 create a project folder in configs/")

    def _on_close_event(self, event_type: str, *args):
        if event_type == "close":
            self._shutdown()
        elif event_type == "project_switch":
            self._switch_project(args[0])

    def _shutdown(self):
        if self._ui and self._project_name:
            tx_state = self._ui.collect_tx_state()
            _save_tx_state(CONFIGS_DIR / self._project_name, tx_state)
            _save_app_state({"last_project": self._project_name})
        if self._conn_mgr:
            self._conn_mgr.disconnect()

    def _switch_project(self, new_name: str):
        if new_name == self._project_name:
            return
        if new_name not in self._projects:
            return

        if self._ui:
            self._ui.cancel_all_periodic()
            tx_state = self._ui.collect_tx_state()
            _save_tx_state(CONFIGS_DIR / self._project_name, tx_state)

        if self._conn_mgr:
            self._conn_mgr.disconnect()

        self._load_project(new_name)

        if self._ui:
            self._ui._protocol_config = self._configs.get("protocol.json", {})
            self._ui._cfg_path = CONFIGS_DIR / new_name / "ui.json"
            self._ui.apply_ui_config(self._configs.get("ui.json", {}))
            self._ui._protocol_codec = self._codec
            self._ui._parser = self._parser
            self._ui._traffic_logger = self._logger
            self._ui.rebuild_panes()
            self._ui.rebuild_send_area()
            self._ui.clear_display()

            tx_state = _load_tx_state(CONFIGS_DIR / new_name)
            self._ui.restore_tx_state(tx_state)

        self._conn_mgr = ConnectionManager(
            self._configs.get("connection.json", {}), self._frame_queue,
        )
        if self._ui:
            self._ui.set_connection_manager(self._conn_mgr)
        self._conn_mgr.connect()


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    app = App()
    app.run()


if __name__ == "__main__":
    main()
