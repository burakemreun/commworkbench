Status: resolved
Type: research
Blocked by: none

# 01 — Binary Protocol Definition Format

## Question

How should the binary protocol be defined in JSON? The protocol has:
- A general header structure with fields (name, meaning, order, byte size)
- Per-message definitions with field types (int, float, enum, bitfield), sizes, constraints (min/max), enum values
- Bitfields that can be 1-bit or multi-bit, each evaluated individually
- Optional checksum (configurable: presence, size, calculation method)
- Configurable byte order (big/little endian)

Research Python `struct` module patterns, existing protocol definition formats (like protobuf schemas, Cap'n Proto, or custom JSON-based protocol defs), and propose a JSON schema that covers all these requirements. Focus on:
1. How to express header vs payload fields
2. How to define bitfields within larger fields
3. How to express checksum algorithm (CRC8, CRC16, CRC32, XOR, sum, etc.)
4. How to handle variable-length messages
5. How to express enum mappings (value → label)
6. How to express numeric constraints (min, max, step)

Return a concrete JSON schema example and recommended Python approach.

## Answer

Research complete. Findings saved to `.scratch/comm-templater/research/protocol-format-findings.md`.

**Key decisions:**
- Custom JSON schema (not protobuf/kaitai — need runtime loading for tkinter)
- `struct.Struct` for compiled format strings, bitfield masking/shifting for bits
- Flat bitfield array with auto-calculated offsets
- Checksum: configurable algorithm (CRC8/16/32, XOR, sum) with variant selection
- Byte order: hierarchical (protocol → message → field) with inheritance
- `crc` library for CRC calculations

**Schema structure:** `protocol` (name, version, endianness), `messages` (id, name, fields[]), `enums` (value mappings), `checksum` (algorithm, variant, covers, offset). Fields support: int/float types, bitfield with sub-entries, enum references, min/max constraints.

**Python approach:** `ProtocolCodec` class that compiles JSON schema into `struct.Struct` formats, handles bitfield encode/decode via masking, validates constraints, computes/appends checksums.
