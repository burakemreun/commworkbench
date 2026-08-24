# How to Write a protocol.json

This document defines the JSON format used to describe binary communication protocols for CommWorkbench. An AI given a struct definition and this guide should be able to produce a valid `protocol.json`.

---

## Overview

A `protocol.json` describes:
1. **Protocol metadata** — name, version, byte order
2. **Enums** — named integer constants (optional)
3. **Messages** — frame definitions with ordered fields
4. **Checksum** — frame integrity check (optional)

```
Wire format: [1-byte msg ID] [payload fields...] [checksum bytes]
```

---

## JSON Schema

```json
{
  "protocol": { /* required */ },
  "enums": { /* optional */ },
  "messages": { /* required */ },
  "checksum": { /* optional */ }
}
```

---

## Section: `protocol` (required)

```json
{
  "protocol": {
    "name": "MyProtocol",
    "version": "1.0",
    "endianness": "little"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Protocol identifier |
| `version` | string | yes | Version string |
| `endianness` | `"little"` or `"big"` | yes | Global byte order. Overridable per-field. |
| `id_size` | `1`, `2` or `4` | no | Message ID width in bytes (default `1`, i.e. max 256 messages). Written in the global byte order. |

---

## Section: `enums` (optional)

Named integer value mappings. Used by fields with `type: "enum"` or `enum_ref`.

```json
{
  "enums": {
    "DeviceState": {
      "values": [
        {"name": "IDLE", "value": 0},
        {"name": "RUNNING", "value": 1},
        {"name": "ERROR", "value": 2}
      ]
    }
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `values` | array | yes | Array of `{name, value}` objects |
| `values[].name` | string | yes | Enum constant name |
| `values[].value` | integer | yes | Integer value |

---

## Section: `messages` (required)

Keyed by a PascalCase identifier (used as internal key). Each message defines one frame type.

```json
{
  "messages": {
    "SendCommand": {
      "id": 1,
      "name": "Send Command",
      "direction": "tx",
      "fields": [
        {"name": "command_id", "type": "uint8"},
        {"name": "payload", "type": "uint16"}
      ]
    }
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | integer 0-255 | yes | 1-byte message type ID in the wire header |
| `name` | string | yes | Human-readable display name |
| `direction` | `"tx"` or `"rx"` | no | `tx` = sent by app, `rx` = received from device |
| `description` | string | no | Optional description |
| `fields` | array | yes | Ordered field definitions (see below) |

---

## Field Types

Each entry in `fields[]` has:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Field name (snake_case) |
| `type` | string | yes | One of the types below |
| `endianness` | `"little"`, `"big"`, or `"inherit"` | no | Override global endianness (default: inherit) |
| `constant` | integer | no | Fixed value. Encode always writes this, decode returns this. Ignores user input. |
| `min` | number | no | Minimum valid value |
| `max` | number | no | Maximum valid value |
| `step` | number | no | Value must be `min + k * step` (`min` defaults to 0). Rejected before encoding. |
| `enum_ref` | string | no | Reference to an enum name (required if type is `"enum"`) |
| `description` | string | no | Optional description |

### Primitive Types

| Type | Bytes | Python struct | Description |
|------|-------|---------------|-------------|
| `int8` | 1 | `b` | Signed 8-bit |
| `uint8` | 1 | `B` | Unsigned 8-bit |
| `int16` | 2 | `h` | Signed 16-bit |
| `uint16` | 2 | `H` | Unsigned 16-bit |
| `int32` | 4 | `i` | Signed 32-bit |
| `uint32` | 4 | `I` | Unsigned 32-bit |
| `int64` | 8 | `q` | Signed 64-bit |
| `uint64` | 8 | `Q` | Unsigned 64-bit |
| `float32` | 4 | `f` | IEEE 754 single |
| `float64` | 8 | `d` | IEEE 754 double |
| `bytes` | `size` | raw | Fixed-size byte array (requires `size` field) |

### Enum Type

For fields that map to named integer constants:

```json
{"name": "mode", "type": "enum", "enum_ref": "DeviceState"}
```

The underlying wire type defaults to `uint16` (2 bytes). Use `enum_underlying` to override:

```json
{"name": "mode", "type": "enum", "enum_ref": "DeviceState", "enum_underlying": "uint8"}
```

### Constant Fields

For fields that always carry a fixed value (e.g. sender/receiver IDs that depend on direction):

```json
{"name": "sender_id", "type": "uint8", "constant": 2}
```

- **Encode:** always writes the constant value, ignoring any user-provided value.
- **Decode:** skips the bytes and returns the constant value.
- The field still occupies its normal byte size in the wire format.

Example — TX message with direction-dependent IDs:

```json
{
  "name": "gonderen_id",
  "type": "uint8",
  "constant": 2,
  "description": "Sender is always 2 for TX messages"
}
```

### Bytes Type

Fixed-size byte array. Requires `"size"` to specify the byte count.

```json
{"name": "raw_data", "type": "bytes", "size": 8}
```

- **Encode:** accepts `bytes`, `bytearray`, or `list[int]`. Pads with `\x00` if shorter, truncates if longer.
- **Decode:** returns a `bytes` object of exactly `size` length.

```json
{"name": "mac_address", "type": "bytes", "size": 6}
{"name": "uuid", "type": "bytes", "size": 16}
```

### Bitfield Type

Packs multiple small values into a single integer container.

```json
{
  "name": "flags",
  "type": "bitfield",
  "bitfield": {
    "total_bits": 8,
    "bit_order": "msb",
    "bits": [
      {"name": "enabled", "width": 1},
      {"name": "mode", "width": 2, "enum_ref": "DeviceState"},
      {"name": "error", "width": 3},
      {"name": "reserved", "width": 2}
    ]
  }
}
```

| Bitfield Property | Type | Required | Description |
|-------------------|------|----------|-------------|
| `total_bits` | `8`, `16`, or `32` | no | Container size. Default: auto-calculate from bits sum. |
| `bit_order` | `"msb"` or `"lsb"` | no | Bit packing order. Default: `"msb"`. |
| `bits` | array | yes | Array of bit entries |

Each bit entry:

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | string | yes | Bit field name |
| `width` | integer 1-64 | yes | Number of bits |
| `enum_ref` | string | no | Optional enum for named values |
| `description` | string | no | Optional description |

Bits are packed sequentially. Offsets auto-calculate from order.

---

## Section: `checksum` (optional)

Adds a checksum to each frame for integrity verification.

```json
{
  "checksum": {
    "enabled": true,
    "algorithm": "crc16",
    "crc_variant": "modbus",
    "covers": "payload"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `enabled` | boolean | yes | Enable/disable checksum |
| `algorithm` | string | yes | `"crc8"`, `"crc16"`, `"crc32"`, `"xor"`, `"sum"` |
| `crc_variant` | string | no | CRC variant (e.g. `"modbus"`, `"ccitt"`, `"xmodem"`, `"dnp"`) |
| `covers` | string | no | What the checksum covers: `"header"`, `"payload"`, `"header_and_payload"` |
| `offset` | integer | no | Byte offset where checksum starts (null = appended at end) |

CRC variants by algorithm:

| Algorithm | Variants |
|-----------|----------|
| `crc8` | `ccitt` |
| `crc16` | `modbus`, `xmodem`, `kermit`, `dnp` |
| `crc32` | (standard) |

---

## Examples

### Example 1: Minimal Protocol (TX + RX)

A simple query-response protocol:

```json
{
  "protocol": {
    "name": "SensorComm",
    "version": "1.0",
    "endianness": "little"
  },
  "messages": {
    "QuerySensor": {
      "id": 1,
      "name": "Query Sensor",
      "direction": "tx",
      "fields": [
        {"name": "device_id", "type": "uint16"}
      ]
    },
    "SensorResponse": {
      "id": 2,
      "name": "Sensor Response",
      "direction": "rx",
      "fields": [
        {"name": "device_id", "type": "uint16"},
        {"name": "temperature", "type": "float32"},
        {"name": "humidity", "type": "uint8"}
      ]
    }
  }
}
```

**Wire bytes (SensorResponse, device_id=1, temp=23.5, humidity=65):**
```
[02] [01 00] [00 00 BC 41] [41]
 │     │         │           │
 │     │         │           └─ humidity (uint8): 65
 │     │         └─ temperature (float32 LE): 23.5
 │     └─ device_id (uint16 LE): 1
 └─ message ID: 2
```

### Example 2: With Enums and Checksum

```json
{
  "protocol": {
    "name": "MotorCtrl",
    "version": "2.1",
    "endianness": "little"
  },
  "checksum": {
    "enabled": true,
    "algorithm": "crc16",
    "crc_variant": "modbus",
    "covers": "payload"
  },
  "enums": {
    "MotorState": {
      "values": [
        {"name": "STOPPED", "value": 0},
        {"name": "RUNNING", "value": 1},
        {"name": "BRAKING", "value": 2}
      ]
    },
    "Direction": {
      "values": [
        {"name": "CW", "value": 0},
        {"name": "CCW", "value": 1}
      ]
    }
  },
  "messages": {
    "SetSpeed": {
      "id": 10,
      "name": "Set Motor Speed",
      "direction": "tx",
      "fields": [
        {"name": "motor_id", "type": "uint8", "min": 0, "max": 3},
        {"name": "speed_rpm", "type": "uint16", "min": 0, "max": 3000},
        {"name": "direction", "type": "enum", "enum_ref": "Direction"}
      ]
    },
    "MotorStatus": {
      "id": 11,
      "name": "Motor Status",
      "direction": "rx",
      "fields": [
        {"name": "motor_id", "type": "uint8"},
        {"name": "state", "type": "enum", "enum_ref": "MotorState"},
        {"name": "current_rpm", "type": "uint16"},
        {"name": "temperature_c", "type": "int8"},
        {"name": "error_code", "type": "uint32"}
      ]
    }
  }
}
```

### Example 3: With Bitfields

```json
{
  "protocol": {
    "name": "PowerMeter",
    "version": "1.0",
    "endianness": "little"
  },
  "enums": {
    "ErrorFlag": {
      "values": [
        {"name": "NONE", "value": 0},
        {"name": "OVERCURRENT", "value": 1},
        {"name": "OVERVOLTAGE", "value": 2},
        {"name": "OVERTEMP", "value": 3}
      ]
    }
  },
  "messages": {
    "PowerData": {
      "id": 20,
      "name": "Power Data",
      "direction": "rx",
      "fields": [
        {"name": "voltage", "type": "float32"},
        {"name": "current", "type": "float32"},
        {"name": "status", "type": "bitfield", "bitfield": {
          "total_bits": 16,
          "bit_order": "msb",
          "bits": [
            {"name": "online", "width": 1},
            {"name": "error_flag", "width": 4, "enum_ref": "ErrorFlag"},
            {"name": "phase_count", "width": 3},
            {"name": "reserved", "width": 8}
          ]
        }},
        {"name": "power_factor", "type": "float32"}
      ]
    }
  }
}
```

---

## Rules for AI Generation

When converting a struct definition to `protocol.json`:

1. **Map struct fields to message fields** in the order they appear in the struct.
2. **Choose the smallest type that fits** — if a field is 0-255 use `uint8`, not `uint16`.
3. **Assign unique message IDs** — each message needs a unique integer 0-255.
4. **Define enums first** — any named constant set becomes an `enums` entry.
5. **Use `bitfield` for packed flags** — multiple small values in one byte/word.
6. **Use `constant` for fixed values** — if a field always carries the same value per direction (e.g. sender ID = 2 for TX, 1 for RX), use `"constant"` instead of making the user pass it every time.
7. **Set `endianness`** — ask the user or default to `"little"` (most common).
8. **Add checksum only if specified** — default to no checksum if not mentioned.
9. **Use snake_case** for field names, **PascalCase** for message keys and enum names.

### Type Mapping Heuristics

| C / Struct Type | JSON Type |
|----------------|-----------|
| `char` / `int8_t` | `int8` |
| `unsigned char` / `uint8_t` | `uint8` |
| `short` / `int16_t` | `int16` |
| `unsigned short` / `uint16_t` | `uint16` |
| `int` / `int32_t` | `int32` |
| `unsigned int` / `uint32_t` | `uint32` |
| `long long` / `int64_t` | `int64` |
| `unsigned long long` / `uint64_t` | `uint64` |
| `float` | `float32` |
| `double` | `float64` |
| `enum { ... }` | `enum` + `enums` definition |
| Bitfield `: N` | `bitfield` with `total_bits` matching container |
| `uint8_t[N]` / raw buffer | `bytes` with `size: N` |

### Field Order Rule

Fields in `fields[]` MUST match the byte layout of the struct. The first field is packed first, the second next, etc. No implicit padding — the codec packs fields consecutively.

### Validation Constraints

Use `min` and `max` to enforce value ranges:

```json
{"name": "temperature", "type": "float32", "min": -40.0, "max": 85.0}
```

These are enforced during encode. Values outside range raise errors.

---

## Quick Reference: Full Minimal Template

```json
{
  "protocol": {
    "name": "MY_PROTOCOL",
    "version": "1.0",
    "endianness": "little"
  },
  "enums": {},
  "messages": {
    "MessageName": {
      "id": 1,
      "name": "Display Name",
      "direction": "tx",
      "fields": [
        {"name": "field_name", "type": "uint8"}
      ]
    }
  }
}
```
