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

ID_TYPE_MAP = {1: "B", 2: "H", 4: "I"}

CRC8_VARIANTS = {"ccitt": Crc8.CCITT}
CRC16_VARIANTS = {
    "modbus": Crc16.MODBUS, "xmodem": Crc16.XMODEM,
    "kermit": Crc16.KERMIT, "dnp": Crc16.DNP,
}


def _endian_char(endianness: str) -> str:
    # a typo here would silently swap the byte order on the wire, so it is fatal
    if endianness not in ENDIAN_MAP:
        raise ValueError(f"unknown endianness: {endianness!r}")
    return ENDIAN_MAP[endianness]


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
        proto = protocol_config.get("protocol", {})
        self.endianness = proto.get("endianness", "little")
        self.id_size = proto.get("id_size", 1)
        if self.id_size not in ID_TYPE_MAP:
            raise ValueError(f"protocol.id_size must be 1, 2 or 4, got {self.id_size}")
        self.enums = protocol_config.get("enums", {})
        self.messages = protocol_config.get("messages", {})
        self._checksum_fn, self._checksum_size, self._checksum_covers = (
            _build_checksum(protocol_config.get("checksum", {}))
        )

    @property
    def checksum_size(self) -> int:
        return self._checksum_size

    def pack_id(self, msg_id: int) -> bytes:
        return self._pack(msg_id, ID_TYPE_MAP[self.id_size], self.endianness)

    def unpack_id(self, buf: bytes) -> int:
        return self._unpack(buf[:self.id_size], ID_TYPE_MAP[self.id_size], self.endianness)

    @staticmethod
    def field_size(field_def: dict) -> int:
        if field_def["type"] == "bytes":
            return field_def["size"]
        return _type_info(field_def)[1]

    def _field_endian(self, field_def: dict, msg_def: dict | None = None) -> str:
        """Byte order is hierarchical: field, then message, then protocol."""
        for source in (field_def, msg_def):
            if source:
                endian = source.get("endianness", "inherit")
                if endian != "inherit":
                    return endian
        return self.endianness

    def _pack(self, value: Any, type_char: str, endian: str) -> bytes:
        return struct.pack(f"{_endian_char(endian)}{type_char}", value)

    def _unpack(self, buf: bytes, type_char: str, endian: str) -> Any:
        return struct.unpack(f"{_endian_char(endian)}{type_char}", buf)[0]

    def _encode_field(self, field_def: dict, value: Any, msg_def: dict | None = None) -> bytes:
        ft = field_def["type"]
        endian = self._field_endian(field_def, msg_def)
        if "constant" in field_def:
            value = field_def["constant"]
        if ft == "bytes":
            return self._encode_bytes(field_def, value)
        if ft == "enum":
            mapping = self.enums.get(field_def.get("enum_ref", ""), {})
            int_val = _enum_inv(mapping).get(value, value) if isinstance(value, str) else value
            type_char, _ = _type_info(field_def)
            return self._pack(int_val, type_char, endian)
        if ft == "bitfield":
            return self._encode_bitfield(field_def, value, endian)
        type_char, _ = _type_info(field_def)
        return self._pack(value, type_char, endian)

    def _encode_bytes(self, field_def: dict, value: Any) -> bytes:
        size = field_def["size"]
        if value is None:
            raw = b""
        elif isinstance(value, (bytes, bytearray)):
            raw = bytes(value)
        elif isinstance(value, str):
            # what the send form hands over: "aa bb cc" or "aabbcc"
            raw = bytes.fromhex(value.replace(" ", ""))
        else:
            raw = bytes(value)
        raw = raw[:size]
        return raw + bytes(size - len(raw))

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

    def _decode_field(self, field_def: dict, data: bytes, offset: int,
                      msg_def: dict | None = None) -> tuple[Any, int]:
        ft = field_def["type"]
        endian = self._field_endian(field_def, msg_def)
        if "constant" in field_def:
            return field_def["constant"], offset + self.field_size(field_def)
        if ft == "bytes":
            size = field_def["size"]
            return bytes(data[offset:offset + size]), offset + size
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
        header = self.pack_id(msg_def["id"])
        payload = b""
        for field_def in msg_def["fields"]:
            payload += self._encode_field(field_def, field_values.get(field_def["name"]), msg_def)
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
        msg_id = self.unpack_id(data)
        if msg_id != msg_def["id"]:
            raise ValueError(f"message ID mismatch: expected {msg_def['id']}, got {msg_id}")
        offset = self.id_size
        result = {}
        for field_def in msg_def["fields"]:
            val, offset = self._decode_field(field_def, data, offset, msg_def)
            result[field_def["name"]] = val
        if self._checksum_fn is not None:
            expected = self._unpack(data[offset:], self._checksum_type_char(), self.endianness)
            if self._checksum_covers == "header":
                region = data[0:self.id_size]
            elif self._checksum_covers == "payload":
                region = data[self.id_size:offset]
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
            if "constant" in field_def:
                continue
            val = field_values.get(name)
            if val is None:
                continue
            if "min" in field_def and val < field_def["min"]:
                errors.append(f"{name}: value {val} below minimum {field_def['min']}")
            if "max" in field_def and val > field_def["max"]:
                errors.append(f"{name}: value {val} above maximum {field_def['max']}")
            step = field_def.get("step")
            if step:
                base = field_def.get("min", 0)
                steps = (val - base) / step
                # floats never land exactly on a step, so allow a relative slack
                if abs(steps - round(steps)) > 1e-6:
                    errors.append(f"{name}: value {val} not a multiple of step {step} from {base}")
        return errors
