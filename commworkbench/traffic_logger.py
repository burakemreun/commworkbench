import threading
from datetime import datetime
from pathlib import Path

# blocks the file may run past max_entries before it is worth a rewrite
COMPACT_SLACK = 100


class TrafficLogger:
    def __init__(self, project_dir: Path, max_entries: int = 1000):
        self._log_path = project_dir / "comm.log"
        self._max_entries = max_entries
        self._lock = threading.Lock()
        self._block_count: int | None = None

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
        with self._lock:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
            if self._block_count is None:
                self._block_count = len(self._read_all_blocks()) if self._log_path.exists() else 0

            with self._log_path.open("a", encoding="utf-8") as f:
                f.write(block)
            self._block_count += 1

            # writes are appends; the file is only rewritten once it has drifted
            # a whole slack past the cap, so rotation costs O(1) per message
            if self._block_count > self._max_entries + COMPACT_SLACK:
                kept = self._read_all_blocks()[-self._max_entries:]
                self._log_path.write_text("".join(kept), encoding="utf-8")
                self._block_count = len(kept)

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
