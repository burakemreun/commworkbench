Status: resolved
Type: task
Blocked by: 11

# 12 — ProtocolCodec

**What to build:** Protocol encoding and decoding module. Compiles `protocol.json` into `struct.Struct` format strings at load time. Provides `encode(message_id, field_dict) -> bytes` and `decode(message_id, raw_bytes) -> dict`. Handles field types: int, float, enum, bitfield. Bitfield encode/decode uses masking/shifting (dedicated type, not piggybacked on int). Validates min/max/step constraints before encoding. Computes and appends checksums (CRC8/16/32, XOR, sum — config-selected). Supports hierarchical byte order (protocol → message → field). Includes `FieldTypeRegistry` with per-type handlers. Decoder owns full pipeline: frame alignment → message ID extraction from header → schema lookup → unpack.

**Blocked by:** 11 (needs ConfigLoader to read protocol.json).

**Status:** resolved — `commworkbench/protocol_codec.py`, verify: `tests/test_protocol_codec.py`

- [x] Compiles protocol.json into per-message `struct.Struct` formats at load time
- [x] `encode(message_id, field_dict) -> bytes` — validates all inputs before packing, raises on bad values
- [x] `decode(message_id, raw_bytes) -> dict` — returns `{field_name: value}` with enums mapped to labels, bitfields unpacked into named bits
- [x] FieldTypeRegistry with dedicated handlers for int, float, enum, bitfield
- [x] Bitfield encode/decode via masking/shifting (start_bit, length)
- [x] Constraint validation (min, max, step) on encode — `validate()`; `step` değeri `min + k*step` olmalı (float alanlarda 1e-6 tolerans), bkz. #21
- [x] Checksum computation and verification (CRC8/16/32, XOR, sum)
- [x] Hierarchical byte order (protocol → message → field level)
- [x] Verifiable: encode→decode roundtrip for each field type produces identical dict
