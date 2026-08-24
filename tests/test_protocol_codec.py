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


def test_step_constraint():
    # step is what keeps a device from being handed an unsupported setpoint
    proto = {
        "protocol": {"name": "T", "version": "1.0", "endianness": "little"},
        "checksum": {"enabled": False},
        "messages": {
            "Setpoint": {
                "id": 1,
                "fields": [
                    {"name": "angle", "type": "uint16", "min": 10, "max": 90, "step": 5},
                    {"name": "gain", "type": "float32", "min": 0.0, "step": 0.1},
                ],
            }
        },
    }
    codec = ProtocolCodec(proto)
    assert codec.validate("Setpoint", {"angle": 25, "gain": 0.3}) == []
    errors = codec.validate("Setpoint", {"angle": 27, "gain": 0.3})
    assert len(errors) == 1 and "step 5" in errors[0], errors
    # steps are counted from min, not from zero
    assert codec.validate("Setpoint", {"angle": 20}) == []
    assert codec.validate("Setpoint", {"angle": 12}) != []
    # float arithmetic must not turn a legal value into an error
    assert codec.validate("Setpoint", {"gain": 0.7}) == []
    assert codec.validate("Setpoint", {"gain": 0.75}) != []


def test_id_size():
    # a protocol with more than 256 messages needs a wider ID; the width must
    # follow protocol endianness and be part of the checksummed frame
    proto = {
        "protocol": {"name": "T", "version": "1.0", "endianness": "big", "id_size": 2},
        "checksum": {"enabled": True, "algorithm": "crc16", "crc_variant": "modbus", "covers": "frame"},
        "messages": {
            "Wide": {"id": 300, "fields": [{"name": "value", "type": "uint8"}]}
        },
    }
    codec = ProtocolCodec(proto)
    assert codec.id_size == 2
    encoded = codec.encode("Wide", {"value": 7})
    assert encoded[0:2] == bytes([0x01, 0x2C]), encoded.hex()
    assert len(encoded) == 2 + 1 + 2
    assert codec.decode("Wide", encoded)["value"] == 7

    try:
        ProtocolCodec({"protocol": {"id_size": 3}})
    except ValueError:
        pass
    else:
        raise AssertionError("id_size 3 must be rejected")


if __name__ == "__main__":
    test_roundtrip()
    test_bitfield()
    test_checksum_corrupt()
    test_constraint_validation()
    test_enum_mapping()
    test_step_constraint()
    test_id_size()
    print("all tests passed")
