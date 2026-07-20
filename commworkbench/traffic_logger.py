import threading
import time
from datetime import datetime
from pathlib import Path


class TrafficLogger:
    def __init__(self, project_dir: Path, max_entries: int = 1000):
        self._log_path = project_dir / "comm.log"
        self._max_entries = max_entries
        self._lock = threading.Lock()

    def log_event(self, direction: str, msg_name: str, fields: dict, raw_hex: str):
        lines = [f"{direction} {msg_name}"]
        for k, v in fields.items():
            lines.append(f"  {k}={v}")
        lines.append(f"  hex: {raw_hex}")
        self._write_block(lines)

    def log_error(self, message: str, raw_hex: str):
        lines = [f"RX ERROR", f"  message={message}", f"  hex: {raw_hex}"]
        self._write_block(lines)

    def log_status(self, message: str):
        lines = [f"STATUS", f"  {message}"]
        self._write_block(lines)

    def _write_block(self, lines: list[str]):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        block = f"---\n{now} {'  '.join([lines[0]] + lines[1:])}\n"
        # SHORTCUT: rewrite entire file for rotation. Upgrade: append-only with periodic compaction.
        with self._lock:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
            existing = self._read_all_blocks() if self._log_path.exists() else []
            existing.append(block)
            if len(existing) > self._max_entries:
                existing = existing[-self._max_entries:]
            self._log_path.write_text("".join(existing), encoding="utf-8")

    def _read_all_blocks(self) -> list[str]:
        content = self._log_path.read_text(encoding="utf-8")
        blocks = []
        current = ""
        for line in content.splitlines(keepends=True):
            if line.startswith("---") and current:
                blocks.append(current)
                current = line
            else:
                current += line
        if current:
            blocks.append(current)
        return blocks
