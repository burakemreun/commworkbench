import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

CONFIGS_DIR = Path("configs")
EXPECTED_FILES = ("connection.json", "protocol.json", "ui.json", "tx-state.json")

DEFAULT_CONNECTION = {
    "mode": "tcp_client",
    "tcp": {"host": "127.0.0.1", "port": 8080, "retry_interval_ms": 3000},
    "serial": {"port": "COM1", "baud_rate": 115200, "data_bits": 8, "stop_bits": 1, "parity": "none"},
}

DEFAULT_UI = {
    "version": 1,
    "geometry": {"width": 1200, "height": 800},
    "log_view": "mixed",
    "panes": {"main_display": 0.5, "send_area": 0.5},
}

DEFAULT_TX_STATE: dict[str, dict] = {}

DEFAULT_PROTOCOL = {"protocol": {"name": "", "version": "0.0", "endianness": "little"}, "messages": {}}

DEFAULTS = {
    "connection.json": DEFAULT_CONNECTION,
    "protocol.json": DEFAULT_PROTOCOL,
    "ui.json": DEFAULT_UI,
    "tx-state.json": DEFAULT_TX_STATE,
}


def _deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def _load_json(path: Path) -> dict | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        log.warning("cannot read %s: %s", path, e)
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        log.error("invalid JSON in %s line %d col %d: %s", path, e.lineno, e.colno, e.msg)
        return None


def _apply_defaults(data: dict | None, filename: str) -> dict:
    defaults = DEFAULTS.get(filename, {})
    if data is None:
        return dict(defaults)
    merged = _deep_merge(defaults, data)
    return merged


class ConfigLoader:
    def __init__(self, configs_dir: Path = CONFIGS_DIR):
        self.configs_dir = configs_dir

    def discover_projects(self) -> list[str]:
        if not self.configs_dir.is_dir():
            return []
        projects = []
        for d in sorted(self.configs_dir.iterdir()):
            if d.is_dir() and not d.name.startswith("_"):
                projects.append(d.name)
        return projects

    def load_project(self, project_name: str) -> dict[str, dict]:
        project_dir = self.configs_dir / project_name
        if not project_dir.is_dir():
            log.warning("project directory not found: %s", project_dir)
            return {f: _apply_defaults(None, f) for f in EXPECTED_FILES}

        result = {}
        for filename in EXPECTED_FILES:
            path = project_dir / filename
            data = _load_json(path)
            result[filename] = _apply_defaults(data, filename)
        return result
