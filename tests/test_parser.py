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
    assert len(frames) == 2, frames
    assert frames[0]["type"] == "unknown" and frames[0]["raw_hex"] == "01ff", frames[0]
    assert frames[1]["fields"]["value"] == 1234
    assert frames[1]["msg_id"] == 300


def test_unknown_id_reported():
    # unexpected traffic must be visible in the log, not silently dropped
    codec = ProtocolCodec(PROTO)
    parser = Parser(PROTO)
    parser.feed(bytes([0x07, 0x99, 0xAB]))
    out = parser.get_frames()
    assert len(out) == 1, out
    assert out[0]["type"] == "unknown", out[0]
    assert out[0]["raw_hex"] == "0799ab", out[0]

    # and a good frame right after still parses, reported after the garbage
    parser.feed(bytes([0x42]) + codec.encode("SensorData", {"device_id": 7, "temperature": 1.0, "humidity": 2}))
    out = parser.get_frames()
    assert [f["type"] for f in out] == ["unknown", "frame"], out
    assert out[0]["raw_hex"] == "42", out[0]
    assert out[1]["fields"]["device_id"] == 7


def test_bytes_and_constant_framing():
    # the frame sizer must know about bytes fields, or the state machine stalls
    proto = {
        "protocol": {"name": "T", "version": "1.0", "endianness": "little"},
        "checksum": {"enabled": True, "algorithm": "xor", "covers": "payload"},
        "messages": {
            "Blob": {
                "id": 5, "direction": "rx",
                "fields": [
                    {"name": "sender_id", "type": "uint8", "constant": 2},
                    {"name": "raw", "type": "bytes", "size": 3},
                ],
            }
        },
    }
    codec = ProtocolCodec(proto)
    parser = Parser(proto)
    parser.feed(codec.encode("Blob", {"raw": "aabbcc"}))
    frames = parser.get_frames()
    assert len(frames) == 1, frames
    assert frames[0]["fields"] == {"sender_id": 2, "raw": bytes.fromhex("aabbcc")}, frames[0]


if __name__ == "__main__":
    test_parse_valid_frame()
    test_parse_bad_checksum()
    test_parse_multiple_frames()
    test_partial_frame_no_hang()
    test_wide_id_framing()
    test_unknown_id_reported()
    test_bytes_and_constant_framing()
    print("all tests passed")
