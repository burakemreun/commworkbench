import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from commworkbench.parser import Parser
from commworkbench.protocol_codec import ProtocolCodec

PROTO = {
    "protocol": {"name": "Test", "version": "1.0", "endianness": "little"},
    "checksum": {"enabled": True, "algorithm": "crc16", "crc_variant": "modbus", "covers": "payload"},
    "enums": {},
    "messages": {
        "SensorData": {
            "id": 1,
            "name": "Sensor Data",
            "fields": [
                {"name": "device_id", "type": "uint16"},
                {"name": "temperature", "type": "float32"},
                {"name": "humidity", "type": "uint8"},
            ],
        }
    },
}


def test_parse_valid_frame():
    codec = ProtocolCodec(PROTO)
    parser = Parser(PROTO)
    values = {"device_id": 42, "temperature": 23.5, "humidity": 65}
    encoded = codec.encode("SensorData", values)
    parser.feed(encoded)
    frames = parser.get_frames()
    assert len(frames) == 1
    f = frames[0]
    assert f["type"] == "frame"
    assert f["msg_name"] == "SensorData"
    assert f["msg_id"] == 1
    assert f["fields"]["device_id"] == 42
    assert abs(f["fields"]["temperature"] - 23.5) < 0.01
    assert f["fields"]["humidity"] == 65
    assert f["direction"] == "rx"
    assert isinstance(f["raw_hex"], str)


def test_parse_bad_checksum():
    codec = ProtocolCodec(PROTO)
    parser = Parser(PROTO)
    encoded = codec.encode("SensorData", {"device_id": 1, "temperature": 0.0, "humidity": 0})
    corrupted = bytearray(encoded)
    corrupted[2] ^= 0xFF
    parser.feed(bytes(corrupted))
    frames = parser.get_frames()
    assert len(frames) == 1
    f = frames[0]
    assert f["type"] == "error"
    assert "checksum" in f["message"].lower()


def test_parse_multiple_frames():
    codec = ProtocolCodec(PROTO)
    parser = Parser(PROTO)
    enc1 = codec.encode("SensorData", {"device_id": 1, "temperature": 10.0, "humidity": 30})
    enc2 = codec.encode("SensorData", {"device_id": 2, "temperature": 20.0, "humidity": 40})
    parser.feed(enc1 + enc2)
    frames = parser.get_frames()
    assert len(frames) == 2
    assert frames[0]["fields"]["device_id"] == 1
    assert frames[1]["fields"]["device_id"] == 2


def test_partial_frame_no_hang():
    parser = Parser(PROTO)
    parser.feed(bytes([1, 0x01, 0x02]))
    frames = parser.get_frames()
    assert len(frames) == 0


def test_wide_id_framing():
    # with a 2-byte ID the scanner must match on the pair, not on a single byte,
    # and must still resync past leading garbage
    proto = {
        "protocol": {"name": "T", "version": "1.0", "endianness": "big", "id_size": 2},
        "checksum": {"enabled": True, "algorithm": "crc16", "crc_variant": "modbus", "covers": "payload"},
        "messages": {
            "Wide": {"id": 300, "direction": "rx", "fields": [{"name": "value", "type": "uint16"}]}
        },
    }
    codec = ProtocolCodec(proto)
    parser = Parser(proto)
    encoded = codec.encode("Wide", {"value": 1234})
    parser.feed(bytes([0x01, 0xFF]) + encoded)
    frames = parser.get_frames()
    assert len(frames) == 1, frames
    assert frames[0]["fields"]["value"] == 1234
    assert frames[0]["msg_id"] == 300


if __name__ == "__main__":
    test_parse_valid_frame()
    test_parse_bad_checksum()
    test_parse_multiple_frames()
    test_partial_frame_no_hang()
    test_wide_id_framing()
    print("all tests passed")
