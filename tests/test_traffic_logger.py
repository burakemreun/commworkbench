import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from commworkbench.traffic_logger import TrafficLogger


def test_log_event_format():
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = TrafficLogger(Path(tmpdir), max_entries=100)
        logger.log_event("TX", "SensorData", {"device_id": 42, "temperature": 23.5}, "01002a41")
        content = (Path(tmpdir) / "comm.log").read_text()
        assert "---" in content
        assert "TX SensorData" in content
        assert "device_id=42" in content
        assert "temperature=23.5" in content
        assert "hex: 01002a41" in content


def test_rotation():
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = TrafficLogger(Path(tmpdir), max_entries=3)
        for i in range(5):
            logger.log_event("TX", "Msg", {"i": i}, "00")
        content = (Path(tmpdir) / "comm.log").read_text()
        blocks = [b for b in content.split("---") if b.strip()]
        assert len(blocks) == 3
        assert "i=2" in blocks[0]
        assert "i=3" in blocks[1]
        assert "i=4" in blocks[2]


def test_log_error():
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = TrafficLogger(Path(tmpdir), max_entries=100)
        logger.log_error("bad checksum", "ff00ff")
        content = (Path(tmpdir) / "comm.log").read_text()
        assert "RX ERROR" in content
        assert "message=bad checksum" in content
        assert "hex: ff00ff" in content


def test_log_status():
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = TrafficLogger(Path(tmpdir), max_entries=100)
        logger.log_status("Connected to COM3")
        content = (Path(tmpdir) / "comm.log").read_text()
        assert "STATUS" in content
        assert "Connected to COM3" in content


if __name__ == "__main__":
    test_log_event_format()
    test_rotation()
    test_log_error()
    test_log_status()
    print("all tests passed")
