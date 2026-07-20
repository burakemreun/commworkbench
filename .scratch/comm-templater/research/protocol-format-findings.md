# Binary Communication Protocol JSON Schema Research

**Date:** 2026-07-20  
**Branch:** research/protocol-format

## Executive Summary

Research findings for defining binary communication protocols in JSON for a Python tkinter desktop app. The solution requires:
- General header structure with fields (name, meaning, order, byte size)
- Per-message definitions with field types (int, float, enum, bitfield), sizes, constraints
- Bitfields (1-bit and multi-bit) evaluated individually
- Optional configurable checksum (CRC8/16/32, XOR, sum)
- Configurable byte order (big/little endian)

---

## 1. Python `struct` Module Patterns

### Core Functions

| Function | Purpose |
|----------|---------|
| `struct.pack(format, values...)` | Pack Python values → bytes |
| `struct.unpack(format, bytes)` | Unpack bytes → tuple of values |
| `struct.calcsize(format)` | Get byte size of format string |
| `struct.pack_into(format, buffer, offset, values...)` | Pack into existing buffer |
| `struct.unpack_from(format, buffer, offset)` | Unpack from buffer offset |
| `struct.Struct(format)` | Compile format once for reuse |

### Format Characters

| Char | C Type | Python Type | Size |
|------|--------|-------------|------|
| `b` | signed char | int | 1 |
| `B` | unsigned char | int | 1 |
| `h` | short | int | 2 |
| `H` | unsigned short | int | 2 |
| `i` | int | int | 4 |
| `I` | unsigned int | int | 4 |
| `q` | long long | int | 8 |
| `Q` | unsigned long long | int | 8 |
| `f` | float | float | 4 |
| `d` | double | float | 8 |
| `?` | boolean | bool | 1 |

### Byte Order Prefixes

| Prefix | Meaning |
|--------|---------|
| `@` | Native order, native alignment (default) |
| `=` | Native order, standard sizes, no alignment |
| `<` | Little-endian |
| `>` | Big-endian |
| `!` | Network byte order (big-endian) |

### Key Pattern: Compiled Struct for Reuse

```python
import struct

# Compile once, use many times
SENSOR_FMT = struct.Struct('<H f B I')  # device_id, temp, humidity, timestamp

def encode(data: dict) -> bytes:
    return SENSOR_FMT.pack(
        data['device_id'],
        data['temperature'],
        data['humidity'],
        data['timestamp']
    )

def decode(data: bytes) -> dict:
    fields = SENSOR_FMT.unpack(data)
    return {
        'device_id': fields[0],
        'temperature': fields[1],
        'humidity': fields[2],
        'timestamp': fields[3]
    }
```

**Source:** [Python struct documentation](https://docs.python.org/3/library/struct.html)

---

## 2. Bitfield Patterns in Python

### Basic Bit Manipulation

```python
# Extract a single bit
def get_bit(value: int, bit: int) -> bool:
    return bool(value & (1 << bit))

# Set a single bit
def set_bit(value: int, bit: int) -> int:
    return value | (1 << bit)

# Extract multi-bit field
def get_field(value: int, offset: int, width: int) -> int:
    mask = (1 << width) - 1
    return (value >> offset) & mask

# Set multi-bit field
def set_field(value: int, offset: int, width: int, field_value: int) -> int:
    mask = ((1 << width) - 1) << offset
    return (value & ~mask) | ((field_value << offset) & mask)
```

### Python IntFlag for Type-Safe Bitfields

```python
from enum import IntFlag

class DeviceFlags(IntFlag):
    ENABLED = 1 << 0      # bit 0
    CALIBRATED = 1 << 1   # bit 1
    ERROR = 1 << 2        # bit 2
    HIGH_RANGE = 1 << 3   # bit 3

# Usage
flags = DeviceFlags.ENABLED | DeviceFlags.CALIBRATED
print(flags)  # DeviceFlags.ENABLED|CALIBRATED
print(bool(flags & DeviceFlags.ERROR))  # False
```

**Source:** [Python IntFlag docs](https://docs.python.org/3/library/enum.html#intflag)

### Real-World Pattern: DNS Header Bitfields

```python
# From DNS protocol parsing example
qr = (flags >> 15) & 0x1      # 1-bit field at bit 15
opcode = (flags >> 11) & 0xF   # 4-bit field at bits 11-14
aa = (flags >> 10) & 0x1       # 1-bit field at bit 10
tc = (flags >> 9) & 0x1        # 1-bit field at bit 9
```

**Source:** [Bitwise Operations in Python: Encoding Network Protocol Flags](https://poehlmann.dev/post/python-bitwise-ops/)

---

## 3. Existing Protocol Definition Formats

### 3.1 BinSchema (Recommended Reference)

**Website:** https://binschema.net  
**GitHub:** https://github.com/serialexp/binschema

BinSchema is the most relevant existing solution. It defines binary formats in JSON5 and generates type-safe parsers.

#### Key Features:
- **Bit-level precision**: 1-64 bit fields with configurable MSB/LSB ordering
- **Rich type system**: Primitives, strings, arrays, discriminated unions
- **Computed fields**: Auto-calculate lengths, positions, CRC32 checksums
- **Multi-language output**: TypeScript, Python, Go, Rust, Zig

#### Example Schema (from BinSchema):

```json
{
  "config": {
    "endianness": "big_endian"
  },
  "types": {
    "SensorReading": {
      "sequence": [
        {"name": "device_id", "type": "uint16"},
        {"name": "temperature", "type": "float32"},
        {"name": "humidity", "type": "uint8"},
        {"name": "timestamp", "type": "uint32"}
      ]
    }
  }
}
```

#### Bitfield Example:

```json
{
  "name": "flags",
  "type": "bit",
  "bit_width": 16,
  "bit_order": "msb_first",
  "fields": [
    {"name": "qr", "bit_width": 1},
    {"name": "opcode", "bit_width": 4},
    {"name": "aa", "bit_width": 1},
    {"name": "tc", "bit_width": 1},
    {"name": "rd", "bit_width": 1}
  ]
}
```

#### Computed Checksum Example:

```json
{
  "name": "checksum",
  "type": "uint32",
  "computed": {
    "type": "crc32_of",
    "target": "data"
  }
}
```

### 3.2 Kaitai Struct

**Website:** https://kaitai.io  
**Format:** YAML-based `.ksy` files

Kaitai Struct is a declarative language for binary formats. It generates parsers (read-only) for multiple languages.

#### Example (.ksy format):

```yaml
meta:
  id: tcp_segment
  endian: be
seq:
  - id: src_port
    type: u2
  - id: dst_port
    type: u2
  - id: seq_num
    type: u4
  - id: ack_num
    type: u4
```

**Limitation:** Decode-only, no encoder support.

### 3.3 Protocol Buffers (Protobuf)

**Website:** https://protobuf.dev

Protobuf uses its own binary wire format with field tags. Not suitable when you need full control over byte layout.

#### Example:

```protobuf
message SensorReading {
  int32 device_id = 1;
  float temperature = 2;
  int32 humidity = 3;
}
```

**Trade-off:** Excellent for schema evolution, but doesn't give byte-level control.

### 3.4 Cap'n Proto

**Website:** https://capnproto.org

Zero-copy serialization format. Data layout is platform-independent but designed for efficiency, not custom protocols.

**Trade-off:** Faster than Protobuf, but requires pointer-based layout.

### 3.5 Microsoft Yardl

**GitHub:** https://github.com/microsoft/yardl

Binary encoding format with embedded JSON schema. Supports records, enums, flags, and protocols.

#### Flags Example:

```json
{
  "flags": {
    "name": "TextFormat",
    "values": [
      {"symbol": "regular", "value": 0},
      {"symbol": "bold", "value": 1},
      {"symbol": "italic", "value": 2}
    ]
  }
}
```

---

## 4. Checksum Libraries in Python

### 4.1 `crc` Library (Pure Python)

**PyPI:** https://pypi.org/project/crc/

```python
from crc import Calculator, Crc8, Crc16, Crc32

# CRC8
calc8 = Calculator(Crc8.CCITT)
checksum8 = calc8.checksum(data)

# CRC16
calc16 = Calculator(Crc16.XMODEM)
checksum16 = calc16.checksum(data)

# CRC32
calc32 = Calculator(Crc32.CRC32)
checksum32 = calc32.checksum(data)

# Custom configuration
from crc import Configuration
config = Configuration(
    width=8,
    polynomial=0x07,
    init_value=0x00,
    final_xor_value=0x00,
    reverse_input=False,
    reverse_output=False,
)
calc_custom = Calculator(config)
```

**Available Configurations:**

| CRC8 | CRC16 | CRC32 |
|------|-------|-------|
| CCITT | XMODEM | CRC32 |
| AUTOSAR | GSM | AUTOSAR |
| SAEJ1850 | PROFIBUS | BZIP2 |
| BLUETOOTH | MODBUS | POSIX |
| MAXIM-DOW | KERMIT | |

### 4.2 `fastcrc` Library (Rust-based, Fast)

**PyPI:** https://pypi.org/project/fastcrc/

```python
from fastcrc import crc8, crc16, crc32

data = b"123456789"
print(f"CRC8: {crc8.cdma2000(data)}")
print(f"CRC16: {crc16.xmodem(data)}")
print(f"CRC32: {crc32.aixm(data)}")
```

### 4.3 Built-in Python `zlib.crc32`

```python
import zlib
checksum = zlib.crc32(data) & 0xFFFFFFFF  # Ensure unsigned
```

**Note:** Only CRC-32/ISO-HDLC, not CRC32C.

---

## 5. Proposed JSON Schema for CommWorkbench

Based on research, here's a concrete JSON schema proposal tailored for the requirements:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Binary Protocol Definition",
  "description": "Schema for defining binary communication protocols",
  "type": "object",
  "required": ["protocol", "messages"],
  "properties": {
    "protocol": {
      "type": "object",
      "required": ["name", "version", "endianness"],
      "properties": {
        "name": {"type": "string"},
        "version": {"type": "string"},
        "endianness": {
          "type": "string",
          "enum": ["little", "big"],
          "default": "little"
        }
      }
    },
    "messages": {
      "type": "object",
      "additionalProperties": {"$ref": "#/definitions/message"}
    },
    "checksum": {
      "type": "object",
      "properties": {
        "enabled": {"type": "boolean", "default": false},
        "algorithm": {
          "type": "string",
          "enum": ["crc8", "crc16", "crc32", "crc32c", "xor", "sum"],
          "default": "crc16"
        },
        "crc_variant": {
          "type": "string",
          "description": "CRC variant name (e.g., 'ccitt', 'modbus', 'xmodem')"
        },
        "size": {
          "type": "integer",
          "enum": [1, 2, 4],
          "description": "Checksum field size in bytes (1 for CRC8, 2 for CRC16, 4 for CRC32)"
        },
        "covers": {
          "type": "string",
          "enum": ["header", "payload", "header_and_payload"],
          "default": "header_and_payload"
        },
        "offset": {
          "type": "integer",
          "description": "Byte offset where checksum starts (null = last field)"
        }
      }
    },
    "enums": {
      "type": "object",
      "additionalProperties": {"$ref": "#/definitions/enum_def"}
    }
  },
  "definitions": {
    "message": {
      "type": "object",
      "required": ["id", "name", "fields"],
      "properties": {
        "id": {
          "type": "integer",
          "minimum": 0,
          "maximum": 255,
          "description": "Message type identifier"
        },
        "name": {"type": "string"},
        "description": {"type": "string"},
        "fields": {
          "type": "array",
          "items": {"$ref": "#/definitions/field"}
        }
      }
    },
    "field": {
      "type": "object",
      "required": ["name", "type"],
      "properties": {
        "name": {"type": "string"},
        "description": {"type": "string"},
        "type": {
          "type": "string",
          "enum": ["int8", "uint8", "int16", "uint16", "int32", "uint32", 
                   "int64", "uint64", "float32", "float64", 
                   "enum", "bitfield", "bytes", "string"]
        },
        "size": {
          "type": "integer",
          "description": "Byte size (for string/bytes), null for fixed types"
        },
        "endianness": {
          "type": "string",
          "enum": ["little", "big", "inherit"],
          "default": "inherit"
        },
        "min": {"type": "number"},
        "max": {"type": "number"},
        "default": {},
        "enum_ref": {
          "type": "string",
          "description": "Reference to enum definition"
        },
        "bitfield": {"$ref": "#/definitions/bitfield_def"}
      }
    },
    "bitfield_def": {
      "type": "object",
      "required": ["bits"],
      "properties": {
        "total_bits": {
          "type": "integer",
          "enum": [8, 16, 32],
          "description": "Total bits for the bitfield container"
        },
        "bit_order": {
          "type": "string",
          "enum": ["msb", "lsb"],
          "default": "msb"
        },
        "bits": {
          "type": "array",
          "items": {"$ref": "#/definitions/bitfield_entry"}
        }
      }
    },
    "bitfield_entry": {
      "type": "object",
      "required": ["name", "width"],
      "properties": {
        "name": {"type": "string"},
        "width": {
          "type": "integer",
          "minimum": 1,
          "maximum": 64
        },
        "offset": {
          "type": "integer",
          "description": "Auto-calculated if not provided"
        },
        "description": {"type": "string"},
        "enum_ref": {
          "type": "string",
          "description": "Optional enum for named values"
        }
      }
    },
    "enum_def": {
      "type": "object",
      "required": ["values"],
      "properties": {
        "description": {"type": "string"},
        "values": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["name", "value"],
            "properties": {
              "name": {"type": "string"},
              "value": {"type": "integer"},
              "description": {"type": "string"}
            }
          }
        }
      }
    }
  }
}
```

### Example Protocol Definition

```json
{
  "protocol": {
    "name": "SensorComm",
    "version": "1.0",
    "endianness": "little"
  },
  "checksum": {
    "enabled": true,
    "algorithm": "crc16",
    "crc_variant": "modbus",
    "covers": "payload",
    "offset": null
  },
  "enums": {
    "SensorMode": {
      "values": [
        {"name": "IDLE", "value": 0},
        {"name": "ACTIVE", "value": 1},
        {"name": "CALIBRATING", "value": 2}
      ]
    },
    "ErrorCode": {
      "values": [
        {"name": "NONE", "value": 0},
        {"name": "OVERFLOW", "value": 1},
        {"name": "TIMEOUT", "value": 2}
      ]
    }
  },
  "messages": {
    "SensorData": {
      "id": 0x01,
      "name": "Sensor Data",
      "description": "Primary sensor reading message",
      "fields": [
        {
          "name": "device_id",
          "type": "uint16",
          "min": 0,
          "max": 65535
        },
        {
          "name": "status",
          "type": "bitfield",
          "bitfield": {
            "total_bits": 8,
            "bit_order": "msb",
            "bits": [
              {"name": "enabled", "width": 1, "description": "Device enabled"},
              {"name": "calibrated", "width": 1, "description": "Calibration status"},
              {"name": "mode", "width": 2, "enum_ref": "SensorMode"},
              {"name": "error", "width": 2, "enum_ref": "ErrorCode"},
              {"name": "reserved", "width": 2}
            ]
          }
        },
        {
          "name": "temperature",
          "type": "float32",
          "min": -40.0,
          "max": 85.0
        },
        {
          "name": "humidity",
          "type": "uint8",
          "min": 0,
          "max": 100
        },
        {
          "name": "timestamp",
          "type": "uint32",
          "description": "Unix timestamp in seconds"
        }
      ]
    }
  }
}
```

---

## 6. Recommended Python Implementation Approach

### Architecture

```
┌─────────────────┐
│   JSON Schema   │  (protocol definition)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Schema Loader  │  (validate + parse JSON)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Encoder/       │  (build struct format, pack data)
│  Decoder        │  (unpack bytes, validate)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Checksum       │  (CRC/XOR/sum calculation)
│  Calculator     │
└─────────────────┘
```

### Core Implementation Pattern

```python
import struct
from dataclasses import dataclass
from typing import Any
from crc import Calculator, Crc16, Crc8, Crc32

@dataclass
class BitfieldDef:
    name: str
    width: int
    offset: int
    enum_ref: str | None = None

@dataclass
class FieldDef:
    name: str
    type: str
    size: int | None = None
    endianness: str = 'inherit'
    min: float | None = None
    max: float | None = None
    enum_ref: str | None = None
    bitfield: list[BitfieldDef] | None = None

class ProtocolCodec:
    def __init__(self, schema: dict):
        self.schema = schema
        self.endianness = schema['protocol']['endianness']
        self.messages = schema['messages']
        self.enums = schema.get('enums', {})
        self.checksum_config = schema.get('checksum', {})
        self._compiled_formats: dict[str, struct.Struct] = {}
        self._compile_formats()
    
    def _get_endian_char(self, field_endian: str | None) -> str:
        if field_endian == 'inherit':
            return '<' if self.endianness == 'little' else '>'
        return '<' if field_endian == 'little' else '>'
    
    def _compile_formats(self):
        for msg_name, msg_def in self.messages.items():
            format_parts = []
            for field in msg_def['fields']:
                endian = self._get_endian_char(field.get('endianness', 'inherit'))
                fmt_char = self._type_to_format(field['type'])
                format_parts.append(f"{endian}{fmt_char}")
            self._compiled_formats[msg_name] = struct.Struct(''.join(format_parts))
    
    def _type_to_format(self, field_type: str) -> str:
        type_map = {
            'int8': 'b', 'uint8': 'B',
            'int16': 'h', 'uint16': 'H',
            'int32': 'i', 'uint32': 'I',
            'int64': 'q', 'uint64': 'Q',
            'float32': 'f', 'float64': 'd'
        }
        return type_map.get(field_type, 'B')
    
    def encode(self, msg_name: str, data: dict) -> bytes:
        fmt = self._compiled_formats[msg_name]
        msg_def = self.messages[msg_name]
        values = []
        
        for field in msg_def['fields']:
            value = data[field['name']]
            
            if field['type'] == 'bitfield':
                value = self._encode_bitfield(field['bitfield'], data)
            
            if field.get('min') is not None and value < field['min']:
                raise ValueError(f"{field['name']} below minimum")
            if field.get('max') is not None and value > field['max']:
                raise ValueError(f"{field['name']} above maximum")
            
            values.append(value)
        
        packed = fmt.pack(*values)
        
        if self.checksum_config.get('enabled'):
            checksum = self._calculate_checksum(packed)
            packed += self._pack_checksum(checksum)
        
        return packed
    
    def _encode_bitfield(self, bitfield_def: dict, data: dict) -> int:
        result = 0
        offset = 0
        
        for bit in bitfield_def['bits']:
            value = data.get(bit['name'], 0)
            mask = (1 << bit['width']) - 1
            result |= (value & mask) << offset
            offset += bit['width']
        
        return result
    
    def _calculate_checksum(self, data: bytes) -> int:
        algo = self.checksum_config.get('algorithm', 'crc16')
        variant = self.checksum_config.get('crc_variant', 'modbus')
        
        if algo == 'crc8':
            config = getattr(Crc8, variant.upper(), Crc8.CCITT)
            calc = Calculator(config)
            return calc.checksum(data)
        elif algo == 'crc16':
            config = getattr(Crc16, variant.upper(), Crc16.MODBUS)
            calc = Calculator(config)
            return calc.checksum(data)
        elif algo == 'crc32':
            config = getattr(Crc32, variant.upper(), Crc32.CRC32)
            calc = Calculator(config)
            return calc.checksum(data)
        elif algo == 'xor':
            result = 0
            for byte in data:
                result ^= byte
            return result
        elif algo == 'sum':
            return sum(data) & 0xFFFF
        
        return 0
    
    def _pack_checksum(self, checksum: int) -> bytes:
        size = self.checksum_config.get('size', 2)
        endian = '<' if self.endianness == 'little' else '>'
        
        if size == 1:
            return struct.pack(f'{endian}B', checksum & 0xFF)
        elif size == 2:
            return struct.pack(f'{endian}H', checksum & 0xFFFF)
        elif size == 4:
            return struct.pack(f'{endian}I', checksum & 0xFFFFFFFF)
        
        return b''
    
    def decode(self, msg_name: str, data: bytes) -> dict:
        fmt = self._compiled_formats[msg_name]
        msg_def = self.messages[msg_name]
        
        if self.checksum_config.get('enabled'):
            checksum_size = self.checksum_config.get('size', 2)
            received_checksum = int.from_bytes(data[-checksum_size:], 'little')
            data_to_verify = data[:-checksum_size]
            
            if not self._verify_checksum(data_to_verify, received_checksum):
                raise ValueError("Checksum verification failed")
        
        values = fmt.unpack(data[:fmt.size])
        result = {}
        
        for i, field in enumerate(msg_def['fields']):
            if field['type'] == 'bitfield':
                result[field['name']] = self._decode_bitfield(
                    field['bitfield'], values[i]
                )
            else:
                result[field['name']] = values[i]
        
        return result
    
    def _decode_bitfield(self, bitfield_def: dict, value: int) -> dict:
        result = {}
        offset = 0
        
        for bit in bitfield_def['bits']:
            mask = (1 << bit['width']) - 1
            field_value = (value >> offset) & mask
            result[bit['name']] = field_value
            offset += bit['width']
        
        return result
```

---

## 7. Key Design Decisions and Trade-offs

### Decision 1: JSON vs YAML vs Custom DSL

| Format | Pros | Cons |
|--------|------|------|
| **JSON** | Universal support, easy validation, schema available | Verbose, no comments |
| **YAML** | More readable, supports comments | Parsing quirks, no standard schema |
| **Custom DSL** | Most expressive | Requires parser, steeper learning curve |

**Recommendation:** JSON with JSON Schema validation. It's universally supported in Python, easy to validate in tkinter UIs, and can be version-controlled easily.

### Decision 2: Schema-Driven vs Code-Generated

| Approach | Pros | Cons |
|----------|------|------|
| **Runtime parsing** | Flexible, no compilation step | Slower, more complex runtime |
| **Code generation** | Type-safe, optimized | Requires build step |

**Recommendation:** Runtime parsing. For a tkinter desktop app, the flexibility of loading protocol definitions at runtime outweighs the performance cost. The `struct.Struct` class compiles formats for reuse.

### Decision 3: Bitfield Representation

| Approach | Pros | Cons |
|----------|------|------|
| **Flat array of bits** | Simple, explicit | Requires manual offset calculation |
| **Nested structure** | Hierarchical, natural | More complex parser |

**Recommendation:** Flat array with auto-calculated offsets. This matches hardware conventions and is simpler to implement.

### Decision 4: Checksum Position

| Approach | Pros | Cons |
|----------|------|------|
| **Always last** | Simple, predictable | Inflexible |
| **Configurable offset** | Matches real protocols | More complex |
| **Separate from schema** | Cleaner schema | Requires extra config |

**Recommendation:** Configurable offset with default to last field. Most protocols put checksum last, but some (like MAVLink) put it before payload.

### Decision 5: Endianness Scope

| Approach | Pros | Cons |
|----------|------|------|
| **Global only** | Simple | Inflexible for mixed protocols |
| **Per-field** | Maximum flexibility | Complex, error-prone |
| **Hierarchical** | Balanced | Moderate complexity |

**Recommendation:** Hierarchical (protocol → message → field) with inheritance.

---

## 8. Comparison with Existing Tools

### For This Use Case

| Feature | BinSchema | Kaitai | Protobuf | Custom JSON |
|---------|-----------|--------|----------|-------------|
| Encode + Decode | ✓ | ✗ | ✓ | ✓ |
| Bitfield support | ✓ | ✓ | ✗ | ✓ |
| Configurable CRC | ✓ | ✗ | ✗ | ✓ |
| Runtime loading | ✗ (codegen) | ✗ (codegen) | ✗ (codegen) | ✓ |
| JSON schema | ✓ | ✗ | ✗ | ✓ |
| Python tkinter friendly | Medium | Medium | Hard | **Easy** |

**Conclusion:** For a tkinter desktop app requiring runtime protocol loading, a custom JSON-based approach with the proposed schema is the most suitable solution.

---

## 9. References

1. [Python struct documentation](https://docs.python.org/3/library/struct.html)
2. [BinSchema - Binary Protocol Schema Generator](https://binschema.net)
3. [Kaitai Struct](https://kaitai.io)
4. [Protocol Buffers](https://protobuf.dev)
5. [Cap'n Proto](https://capnproto.org)
6. [crc library (PyPI)](https://pypi.org/project/crc/)
7. [fastcrc library (PyPI)](https://pypi.org/project/fastcrc/)
8. [Bitwise Operations in Python - Encoding Network Protocol Flags](https://poehlmann.dev/post/python-bitwise-ops/)
9. [JSON Schema Specification](https://json-schema.org/specification)
10. [MAVLink Serialization Format](https://mavlink.io/ko/guide/serialization.html)

---

## 10. Next Steps

1. Create a JSON Schema file for protocol definitions
2. Implement a basic ProtocolCodec class in Python
3. Build a tkinter UI for protocol definition and visualization
4. Add support for protocol versioning
5. Implement real-time protocol preview in the UI
