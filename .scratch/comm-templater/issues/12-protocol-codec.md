Status: ready-for-agent
Type: task
Blocked by: 11

# 12 — ProtocolCodec

**What to build:** Protocol encoding and decoding module. Compiles `protocol.json` into `struct.Struct` format strings at load time. Provides `encode(message_id, field_dict) -> bytes` and `decode(message_id, raw_bytes) -> dict`. Handles field types: int, float, enum, bitfield. Bitfield encode/decode uses masking/shifting (dedicated type, not piggybacked on int). Validates min/max/step constraints before encoding. Computes and appends checksums (CRC8/16/32, XOR, sum — config-selected). Supports hierarchical byte order (protocol → message → field). Includes `FieldTypeRegistry` with per-type handlers. Decoder owns full pipeline: frame alignment → message ID extraction from header → schema lookup → unpack.

**Blocked by:** 11 (needs ConfigLoader to read protocol.json).

**Status:** ready-for-agent

- [ ] Compiles protocol.json into per-message `struct.Struct` formats at load time
- [ ] `encode(message_id, field_dict) -> bytes` — validates all inputs before packing, raises on bad values
- [ ] `decode(message_id, raw_bytes) -> dict` — returns `{field_name: value}` with enums mapped to labels, bitfields unpacked into named bits
- [ ] FieldTypeRegistry with dedicated handlers for int, float, enum, bitfield
- [ ] Bitfield encode/decode via masking/shifting (start_bit, length)
- [ ] Constraint validation (min, max, step) on encode
- [ ] Checksum computation and verification (CRC8/16/32, XOR, sum)
- [ ] Hierarchical byte order (protocol → message → field level)
- [ ] Verifiable: encode→decode roundtrip for each field type produces identical dict
