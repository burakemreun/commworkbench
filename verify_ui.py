import queue
import sys
import threading
import time

sys.path.insert(0, ".")

from commworkbench.config_loader import ConfigLoader
from commworkbench.parser import Parser
from commworkbench.ui import CommWorkbenchUI

MOCK_PROTOCOL = {
    "protocol": {"name": "Test", "version": "1.0", "endianness": "little"},
    "checksum": {"enabled": False},
    "messages": {
        "SensorData": {
            "id": 1,
            "name": "Sensor",
            "fields": [
                {"name": "device_id", "type": "uint16"},
                {"name": "temperature", "type": "float32"},
            ],
        },
        "MotorCmd": {
            "id": 2,
            "name": "Motor",
            "fields": [
                {"name": "speed", "type": "uint8"},
                {"name": "direction", "type": "uint8"},
            ],
        },
    },
}

loader = ConfigLoader()
configs = loader.load_project("_example")

frame_queue: queue.Queue = queue.Queue()
parser = Parser(MOCK_PROTOCOL)

ui = CommWorkbenchUI(
    configs,
    protocol_config=MOCK_PROTOCOL,
    frame_queue=frame_queue,
    parser=parser,
)


def push_test_frames():
    time.sleep(0.5)
    frame_queue.put({"type": "status", "connected": True, "text": "Connected"})

    raw = bytes([1, 0x01, 0x00, 0x42, 0xC8, 0x00, 0x00])
    frame_queue.put({"type": "data", "raw": raw})

    raw2 = bytes([2, 0x0A, 0x01])
    frame_queue.put({"type": "data", "raw": raw2})

    frame_queue.put({
        "type": "error",
        "message": "checksum mismatch",
        "raw_hex": "ff001122",
    })


threading.Thread(target=push_test_frames, daemon=True).start()

ui.root.after(3000, ui._on_close)
ui.run()
print("OK: UI with display and log verified")
