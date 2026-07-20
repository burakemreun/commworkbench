import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from commworkbench.protocol_codec import ProtocolCodec

PROTO = {
    "protocol": {"name": "Test", "version": "1.0", "endianness": "little"},
    "checksum": {"enabled": True, "algorithm": "crc16", "crc_variant": "modbus", "covers": "payload"},
    "enums": {
        "SensorMode": {
            "values": [{"name": "IDLE", "value": 0}, {"name": "ACTIVE", "value": 1}]
        }
    },
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


def test_roundtrip():
    codec = ProtocolCodec(PROTO)
    values = {"device_id": 42, "temperature": 23.5, "humidity": 65}
    encoded = codec.encode("SensorData", values)
    decoded = codec.decode("SensorData", encoded)
    assert decoded["device_id"] == 42
    assert abs(decoded["temperature"] - 23.5) < 0.01
    assert decoded["humidity"] == 65


def test_bitfield():
    proto = {
        "protocol": {"name": "BF", "version": "1.0", "endianness": "little"},
        "checksum": {"enabled": False},
        "enums": {},
        "messages": {
            "Flags": {
                "id": 10,
                "name": "Flags",
                "fields": [
                    {
                        "name": "flags",
                        "type": "bitfield",
                        "bitfield": {
                            "total_bits": 8,
                            "bits": [
                                {"name": "enable", "width": 1},
                                {"name": "mode", "width": 3},
                                {"name": "count", "width": 4},
                            ],
                        },
                    }
                ],
            }
        },
    }
    codec = ProtocolCodec(proto)
    values = {"flags": {"enable": 1, "mode": 5, "count": 10}}
    encoded = codec.encode("Flags", values)
    decoded = codec.decode("Flags", encoded)
    assert decoded["flags"]["enable"] == 1
    assert decoded["flags"]["mode"] == 5
    assert decoded["flags"]["count"] == 10


def test_checksum_corrupt():
    codec = ProtocolCodec(PROTO)
    values = {"device_id": 1, "temperature": 0.0, "humidity": 0}
    encoded = codec.encode("SensorData", values)
    corrupted = bytearray(encoded)
    corrupted[2] ^= 0xFF
    try:
        codec.decode("SensorData", bytes(corrupted))
        assert False, "should have raised"
    except ValueError as e:
        assert "checksum" in str(e).lower()


def test_constraint_validation():
    proto = {
        "protocol": {"name": "V", "version": "1.0", "endianness": "little"},
        "checksum": {"enabled": False},
        "enums": {},
        "messages": {
            "Constrained": {
                "id": 20,
                "name": "Constrained",
                "fields": [
                    {"name": "val", "type": "uint16", "min": 10, "max": 100},
                ],
            }
        },
    }
    codec = ProtocolCodec(proto)
    errors = codec.validate("Constrained", {"val": 5})
    assert len(errors) == 1
    assert "below minimum" in errors[0]
    errors = codec.validate("Constrained", {"val": 150})
    assert len(errors) == 1
    assert "above maximum" in errors[0]
    errors = codec.validate("Constrained", {"val": 50})
    assert errors == []


def test_enum_mapping():
    proto = {
        "protocol": {"name": "E", "version": "1.0", "endianness": "little"},
        "checksum": {"enabled": False},
        "enums": {"Mode": {"values": [{"name": "OFF", "value": 0}, {"name": "ON", "value": 1}]}},
        "messages": {
            "EnumMsg": {
                "id": 30,
                "name": "EnumMsg",
                "fields": [
                    {"name": "state", "type": "enum", "enum_ref": "Mode", "enum_underlying": "uint8"},
                ],
            }
        },
    }
    codec = ProtocolCodec(proto)
    encoded = codec.encode("EnumMsg", {"state": "ON"})
    decoded = codec.decode("EnumMsg", encoded)
    assert decoded["state"] == "ON"


if __name__ == "__main__":
    test_roundtrip()
    test_bitfield()
    test_checksum_corrupt()
    test_constraint_validation()
    test_enum_mapping()
    print("all tests passed")
