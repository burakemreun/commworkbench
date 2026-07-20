import struct
from typing import Any

from crc import Calculator, Crc8, Crc16, Crc32


TYPE_MAP = {
    "int8": "b", "uint8": "B",
    "int16": "h", "uint16": "H",
    "int32": "i", "uint32": "I",
    "int64": "q", "uint64": "Q",
    "float32": "f", "float64": "d",
}

ENDIAN_MAP = {"little": "<", "big": ">"}

CRC8_VARIANTS = {"ccitt": Crc8.CCITT}
CRC16_VARIANTS = {
    "modbus": Crc16.MODBUS, "xmodem": Crc16.XMODEM,
    "kermit": Crc16.KERMIT, "dnp": Crc16.DNP,
}


def _endian_char(endianness: str) -> str:
    return ENDIAN_MAP.get(endianness, "<")


def _enum_fwd(enum_def: dict) -> dict[int, str]:
    return {v["value"]: v["name"] for v in enum_def.get("values", [])}


def _enum_inv(enum_def: dict) -> dict[str, int]:
    return {v["name"]: v["value"] for v in enum_def.get("values", [])}


def _type_info(field_def: dict) -> tuple[str, int]:
    ft = field_def["type"]
    if ft in TYPE_MAP:
        c = TYPE_MAP[ft]
        return c, struct.calcsize(c)
    if ft == "enum":
        underlying = field_def.get("enum_underlying", "uint16")
        c = TYPE_MAP.get(underlying, "H")
        return c, struct.calcsize(c)
    if ft == "bitfield":
        bits = field_def["bitfield"]["total_bits"]
        if bits <= 8:
            return "B", 1
        if bits <= 16:
            return "H", 2
        return "I", 4
    raise ValueError(f"unknown type: {ft}")


def _build_checksum(cfg: dict):
    if not cfg or not cfg.get("enabled"):
        return None, 0, None
    algo = cfg["algorithm"]
    covers = cfg.get("covers", "payload")

    if algo == "crc8":
        variant = cfg.get("crc_variant", "")
        crc_cls = CRC8_VARIANTS.get(variant, Crc8.CCITT)
        calc = Calculator(crc_cls)
        return lambda data: calc.checksum(data) & 0xFF, 1, covers
    if algo == "crc16":
        variant = cfg.get("crc_variant", "")
        crc_cls = CRC16_VARIANTS.get(variant, Crc16.MODBUS)
        calc = Calculator(crc_cls)
        return lambda data: calc.checksum(data) & 0xFFFF, 2, covers
    if algo == "crc32":
        calc = Calculator(Crc32.AUTO)
        return lambda data: calc.checksum(data), 4, covers
    if algo == "xor":
        def xor_cs(data: bytes) -> int:
            r = 0
            for b in data:
                r ^= b
            return r
        return xor_cs, 1, covers
    if algo == "sum":
        return lambda data: sum(data) & 0xFFFF, 2, covers
    raise ValueError(f"unknown checksum algorithm: {algo}")


class ProtocolCodec:
    def __init__(self, protocol_config: dict):
        self.endianness = protocol_config.get("protocol", {}).get("endianness", "little")
        self.enums = protocol_config.get("enums", {})
        self.messages = protocol_config.get("messages", {})
        self._checksum_fn, self._checksum_size, self._checksum_covers = (
            _build_checksum(protocol_config.get("checksum", {}))
        )

    @property
    def checksum_size(self) -> int:
        return self._checksum_size

    def _field_endian(self, field_def: dict) -> str:
        return field_def.get("endianness", self.endianness)

    def _pack(self, value: Any, type_char: str, endian: str) -> bytes:
        return struct.pack(f"{_endian_char(endian)}{type_char}", value)

    def _unpack(self, buf: bytes, type_char: str, endian: str) -> Any:
        return struct.unpack(f"{_endian_char(endian)}{type_char}", buf)[0]

    def _encode_field(self, field_def: dict, value: Any) -> bytes:
        ft = field_def["type"]
        endian = self._field_endian(field_def)
        if ft == "enum":
            mapping = self.enums.get(field_def.get("enum_ref", ""), {})
            int_val = _enum_inv(mapping).get(value, value) if isinstance(value, str) else value
            type_char, _ = _type_info(field_def)
            return self._pack(int_val, type_char, endian)
        if ft == "bitfield":
            return self._encode_bitfield(field_def, value, endian)
        type_char, _ = _type_info(field_def)
        return self._pack(value, type_char, endian)

    def _encode_bitfield(self, field_def: dict, values: dict, endian: str) -> bytes:
        bf = field_def["bitfield"]
        type_char, _ = _type_info(field_def)
        word = 0
        offset = 0
        for bit_def in bf["bits"]:
            width = bit_def["width"]
            val = values.get(bit_def["name"], 0)
            if "enum_ref" in bit_def:
                mapping = self.enums.get(bit_def["enum_ref"], {})
                val = _enum_inv(mapping).get(val, val) if isinstance(val, str) else val
            word |= (val & ((1 << width) - 1)) << offset
            offset += width
        return self._pack(word, type_char, endian)

    def _decode_bitfield(self, field_def: dict, buf: bytes, endian: str) -> dict:
        bf = field_def["bitfield"]
        type_char, _ = _type_info(field_def)
        word = self._unpack(buf, type_char, endian)
        result = {}
        offset = 0
        for bit_def in bf["bits"]:
            width = bit_def["width"]
            raw = (word >> offset) & ((1 << width) - 1)
            if "enum_ref" in bit_def:
                mapping = self.enums.get(bit_def["enum_ref"], {})
                result[bit_def["name"]] = _enum_fwd(mapping).get(raw, raw)
            else:
                result[bit_def["name"]] = raw
            offset += width
        return result

    def _decode_field(self, field_def: dict, data: bytes, offset: int) -> tuple[Any, int]:
        ft = field_def["type"]
        endian = self._field_endian(field_def)
        if ft == "enum":
            type_char, size = _type_info(field_def)
            int_val = self._unpack(data[offset:offset + size], type_char, endian)
            mapping = self.enums.get(field_def.get("enum_ref", ""), {})
            return _enum_fwd(mapping).get(int_val, int_val), offset + size
        if ft == "bitfield":
            type_char, size = _type_info(field_def)
            return self._decode_bitfield(field_def, data[offset:offset + size], endian), offset + size
        type_char, size = _type_info(field_def)
        return self._unpack(data[offset:offset + size], type_char, endian), offset + size

    def _checksum_type_char(self) -> str:
        if self._checksum_size == 1:
            return "B"
        if self._checksum_size == 2:
            return "H"
        return "I"

    def encode(self, msg_name: str, field_values: dict) -> bytes:
        msg_def = self.messages[msg_name]
        # SHORTCUT: 1-byte msg ID, max 256 messages. Upgrade: add configurable header_size to protocol config.
        header = struct.pack("B", msg_def["id"])
        payload = b""
        for field_def in msg_def["fields"]:
            payload += self._encode_field(field_def, field_values.get(field_def["name"]))
        body = header + payload
        if self._checksum_fn is None:
            return body
        if self._checksum_covers == "header":
            cs_data = header
        elif self._checksum_covers == "payload":
            cs_data = payload
        else:
            cs_data = body
        cs_bytes = self._pack(self._checksum_fn(cs_data), self._checksum_type_char(), self.endianness)
        return body + cs_bytes

    def decode(self, msg_name: str, data: bytes) -> dict:
        msg_def = self.messages[msg_name]
        msg_id = struct.unpack("B", data[0:1])[0]
        if msg_id != msg_def["id"]:
            raise ValueError(f"message ID mismatch: expected {msg_def['id']}, got {msg_id}")
        offset = 1
        result = {}
        for field_def in msg_def["fields"]:
            val, offset = self._decode_field(field_def, data, offset)
            result[field_def["name"]] = val
        if self._checksum_fn is not None:
            expected = self._unpack(data[offset:], self._checksum_type_char(), self.endianness)
            if self._checksum_covers == "header":
                region = data[0:1]
            elif self._checksum_covers == "payload":
                region = data[1:offset]
            else:
                region = data[0:offset]
            actual = self._checksum_fn(region)
            if actual != expected:
                raise ValueError(f"checksum mismatch: expected {expected}, got {actual}")
        return result

    def validate(self, msg_name: str, field_values: dict) -> list[str]:
        errors = []
        msg_def = self.messages.get(msg_name)
        if not msg_def:
            return [f"unknown message: {msg_name}"]
        for field_def in msg_def["fields"]:
            name = field_def["name"]
            val = field_values.get(name)
            if val is None:
                continue
            if "min" in field_def and val < field_def["min"]:
                errors.append(f"{name}: value {val} below minimum {field_def['min']}")
            if "max" in field_def and val > field_def["max"]:
                errors.append(f"{name}: value {val} above maximum {field_def['max']}")
        return errors
