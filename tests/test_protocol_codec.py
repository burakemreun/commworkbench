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
    # packing is LSB-first and the docs say so: enable on bit 0, mode on 1-3,
    # count on 4-7 -> 1 | (5 << 1) | (10 << 4) = 0xAB. A round-trip alone would
    # pass under any bit order.
    assert encoded == bytes([10, 0xAB]), encoded.hex()
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


def test_endianness_hierarchy():
    # field beats message beats protocol; "inherit" must fall through, never
    # quietly become little-endian
    proto = {
        "protocol": {"name": "T", "version": "1.0", "endianness": "big"},
        "checksum": {"enabled": False},
        "messages": {
            "M": {
                "id": 1,
                "endianness": "little",
                "fields": [
                    {"name": "from_msg", "type": "uint16"},
                    {"name": "inherited", "type": "uint16", "endianness": "inherit"},
                    {"name": "from_field", "type": "uint16", "endianness": "big"},
                ],
            },
            "P": {
                "id": 2,
                "fields": [{"name": "from_proto", "type": "uint16", "endianness": "inherit"}],
            },
        },
    }
    codec = ProtocolCodec(proto)
    enc = codec.encode("M", {"from_msg": 1, "inherited": 1, "from_field": 1})
    assert enc[1:3] == bytes([0x01, 0x00]), enc.hex()   # message says little
    assert enc[3:5] == bytes([0x01, 0x00]), enc.hex()   # inherit -> message
    assert enc[5:7] == bytes([0x00, 0x01]), enc.hex()   # field overrides
    assert codec.decode("M", enc) == {"from_msg": 1, "inherited": 1, "from_field": 1}

    # no message level: inherit reaches the protocol, which is big-endian
    assert codec.encode("P", {"from_proto": 1})[1:3] == bytes([0x00, 0x01])

    try:
        ProtocolCodec({"protocol": {"endianness": "middle"}}).encode("X", {})
    except (ValueError, KeyError):
        pass
    else:
        raise AssertionError("a bogus endianness must not be silently accepted")


def test_bytes_type():
    proto = {
        "protocol": {"name": "T", "version": "1.0", "endianness": "little"},
        "checksum": {"enabled": False},
        "messages": {"M": {"id": 1, "fields": [{"name": "mac", "type": "bytes", "size": 4}]}},
    }
    codec = ProtocolCodec(proto)
    assert codec.decode("M", codec.encode("M", {"mac": b"abcd"}))["mac"] == b"abcd"
    # the send form hands over hex text
    assert codec.encode("M", {"mac": "de ad be ef"})[1:] == bytes.fromhex("deadbeef")
    assert codec.encode("M", {"mac": [1, 2, 3, 4]})[1:] == bytes([1, 2, 3, 4])
    # short pads, long truncates, empty is all zeros (documented behaviour)
    assert codec.encode("M", {"mac": b"ab"})[1:] == bytes([0x61, 0x62, 0, 0])
    assert codec.encode("M", {"mac": b"abcdef"})[1:] == b"abcd"
    assert codec.encode("M", {"mac": None})[1:] == bytes(4)


def test_constant_field():
    # constants carry direction-dependent IDs the user never types
    proto = {
        "protocol": {"name": "T", "version": "1.0", "endianness": "little"},
        "checksum": {"enabled": False},
        "messages": {
            "M": {
                "id": 1,
                "fields": [
                    {"name": "sender_id", "type": "uint8", "constant": 2},
                    {"name": "value", "type": "uint8", "min": 0, "max": 9},
                ],
            }
        },
    }
    codec = ProtocolCodec(proto)
    encoded = codec.encode("M", {"value": 5})
    assert encoded == bytes([1, 2, 5]), encoded.hex()
    # user input for a constant is ignored, not encoded
    assert codec.encode("M", {"sender_id": 99, "value": 5}) == encoded
    assert codec.decode("M", encoded) == {"sender_id": 2, "value": 5}
    # and a constant is never validated as if it were user input
    assert codec.validate("M", {"sender_id": 99, "value": 5}) == []


if __name__ == "__main__":
    test_roundtrip()
    test_bitfield()
    test_checksum_corrupt()
    test_constraint_validation()
    test_enum_mapping()
    test_step_constraint()
    test_id_size()
    test_endianness_hierarchy()
    test_bytes_type()
    test_constant_field()
    print("all tests passed")
