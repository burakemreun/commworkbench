Status: resolved
Type: grilling
Blocked by: 01

# 05 — Message Encoding/Decoding Pipeline

## Question

Design how messages are encoded (for sending) and decoded (for receiving) based on the protocol definition.

Requirements:
- Read field definitions from protocol config
- Encode: take user-entered values from the form, pack into binary according to field types, sizes, byte order
- Decode: take raw binary frame, unpack into readable field values
- Handle enums (numeric value ↔ label mapping)
- Handle bitfields (extract individual bits from a byte/word)
- Handle numeric constraints (validate min/max before encoding)
- Handle variable-length fields if applicable

Key decisions:
- Use Python `struct` module or manual byte manipulation?
- How to handle bitfield extraction/insertion?
- How to validate input before encoding?
- How to present decoded values (display format: hex, decimal, binary)?

## Answer

**Architecture:**
- Separate `Encoder` and `Decoder` classes, no shared base
- Standalone `FieldTypeRegistry` composed into both — holds encode/decode functions per field type (int, float, enum, bitfield)
- Encoder validates all inputs before packing (raises on bad values)
- Decoder owns the full pipeline: frame alignment → message ID extraction from header → schema lookup → unpack

**Field types:**
- `int`, `float`, `enum` — each registered with dedicated encode/decode functions
- `bitfield` — dedicated type with its own encode/decode (masking/shifting), not piggybacked on int, to handle multi-bit fields cleanly

**Output format:**
- Decoder returns a structured dict `{field_name: value}` — enums mapped to labels, bitfields unpacked into individual named bits
- Self-describing, no positional mapping needed downstream

**Variable-length:**
- Not needed — each message ID maps to its own fixed schema with known field sizes
- `struct.Struct` compiles a separate format string per message type
