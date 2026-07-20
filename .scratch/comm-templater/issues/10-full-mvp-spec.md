Status: ready-for-agent
Type: spec
Blocked by: 01, 02, 03, 04, 05, 06, 07, 08, 09

# 10 — Full MVP Spec

## Problem Statement

CommWorkbench needs a working minimum viable product that lets a user define a binary protocol in JSON, connect to a device over TCP or serial, send/receive structured messages, and see decoded traffic — all through a tkinter GUI. No code exists yet; all 9 architecture decisions are resolved.

## Solution

A single-file or few-file Python application (tkinter GUI) that:
- Loads project configs from `configs/<project>/` on startup
- Connects to a device via TCP (client/server) or serial (config-selected)
- Parses incoming binary data through a ring buffer + state machine
- Decodes frames into readable dicts via a protocol codec
- Displays latest decoded message per type in tabbed main panel
- Shows all traffic (raw hex + decoded) in a Treeview log
- Provides per-message-type send forms with editable fields
- Supports per-message periodic sending
- Logs all traffic to `configs/<project>/comm.log`
- Saves/restores UI layout automatically
- Packages as single PyInstaller exe

## User Stories

1. As a protocol engineer, I want to define my protocol in a JSON file so that I don't need to write code to communicate with my device
2. As a protocol engineer, I want to define header and payload fields with types (int, float, enum, bitfield) so that the tool understands my message structure
3. As a protocol engineer, I want to define bitfields with individual named bits so that I can inspect flag fields meaningfully
4. As a protocol engineer, I want configurable byte order (big/little endian) at protocol, message, and field level so that I can match my device's wire format
5. As a protocol engineer, I want configurable checksums (CRC8/16/32, XOR, sum) so that the tool validates frames correctly
6. As a protocol engineer, I want to define enum mappings (value → label) so that decoded numeric fields show human-readable names
7. As a protocol engineer, I want to define min/max/step constraints on numeric fields so that invalid values are caught before encoding
8. As a protocol engineer, I want separate config files (connection, protocol, ui, tx-state) so that each concern is isolated
9. As a protocol engineer, I want to switch between projects via a UI dropdown so that I can work with multiple devices without restarting
10. As a protocol engineer, I want the tool to auto-discover project folders in `configs/` so that adding a project is just dropping a folder
11. As a user, I want to connect to a device over TCP as a client so that I can communicate with TCP-enabled devices
12. As a user, I want to connect to a device over TCP as a server so that the tool can listen for incoming connections
13. As a user, I want to connect via serial port with configurable baud rate, data bits, stop bits, parity so that I can talk to serial devices
14. As a user, I want a dropdown of available serial ports so that I don't have to manually type COM port names
15. As a user, I want a visual LED indicator (green=connected, red=disconnected) so that I can see connection status at a glance
16. As a user, I want the LED to show connection details (IP:port or COM@baud) so that I know which device I'm connected to
17. As a user, I want auto-reconnect with configurable retry interval so that temporary disconnects don't require manual intervention
18. As a user, I want reconnect attempts logged to the traffic log so that I can see what's happening without popups
19. As a user, I want incoming binary data parsed through a ring buffer so that sync patterns are found reliably even in noisy streams
20. As a user, I want a 5-state parser (SCAN → HEADER → PAYLOAD → CHECKSUM) so that frames are extracted correctly
21. As a user, I want a 5-second partial-frame timeout so that stalled parses don't hang forever
22. As a user, I want the latest decoded message for each type shown in a tabbed main panel so that I can see the most recent state of each message
23. As a user, I want all traffic logged in a Treeview with Time, Direction, Message, Raw Hex columns so that I can review the full conversation
24. As a user, I want the log view to support "mixed" (chronological) and "split" (TX/RX separate) modes so that I can organize traffic how I prefer
25. As a user, I want a scrollable send area with one form per message type so that I can send any message without switching views
26. As a user, I want each send form to have editable fields generated from the protocol schema so that I fill in values and hit Send
27. As a user, I want each send form to have a Send button that validates then encodes then transmits so that invalid data is never sent
28. As a user, I want per-message periodic send with configurable interval (ms) and Start/Stop button so that I can poll a device automatically
29. As a user, I want periodic send state to be ephemeral (lost on close) so that I don't accidentally restart polling on next launch
30. As a user, I want a manual send during an active periodic send to fire once independently without disrupting the schedule
31. As a user, I want all traffic logged to `configs/<project>/comm.log` in block format so that I have a persistent record
32. As a user, I want log rotation configurable by max entries so that log files don't grow unbounded
33. As a user, I want decode errors and unrecognized frames logged so that I can diagnose protocol mismatches
34. As a user, I want unknown message IDs to show as raw hex in the log so that unexpected traffic is visible, not silently dropped
35. As a user, I want the UI layout (window size, pane positions, log view mode) auto-saved on exit so that my workspace is restored next launch
36. As a user, I want pane positions saved as ratios so that they survive window resizing
37. As a user, I want the layout save to be atomic (write temp, rename) so that a crash mid-save doesn't corrupt the config
38. As a user, I want sensible defaults on first launch (1200x800, mixed log, 50/50 panes) so that the tool works immediately
39. As a user, I want last-used TX field values restored on launch so that I don't re-enter the same data every session
40. As a user, I want the last-used project remembered across launches so that I don't have to reselect it every time
41. As a user, I want config load failures logged with file path and line number so that I can fix issues in a text editor
42. As a user, I want schema mismatches handled per-field (missing field → default + warning) so that one bad field doesn't discard the whole config
43. As a user, I want the first-launch experience to be an empty shell with a hint to create a project so that I'm not blocked by missing configs
44. As a user, I want invalid JSON in config files to be skipped with defaults used and error logged so that the app doesn't crash on bad config
45. As a user, I want the app to be packageable as a single PyInstaller exe so that deployment is a single file transfer

## Implementation Decisions

### Architecture: Queue Seam

The primary architectural seam is `queue.Queue` between backend and frontend:
- **Backend thread** runs ConnectionManager + Parser + Decoder, pushes `DecodedFrame` objects into the queue
- **Frontend** (main tkinter thread) polls the queue on `root.after(50ms)` and processes frames
- Connection status events (connected/disconnected/error) also go through the same queue

### Modules (in dependency order)

1. **ConfigLoader** — reads/validates all JSON from `configs/<project>/`. Returns typed dicts or defaults. Never touches filesystem from other modules.
2. **ProtocolCodec** — compiles `protocol.json` into `struct.Struct` formats. `encode(message_id, field_dict) -> bytes`, `decode(message_id, raw_bytes) -> dict`. Includes `FieldTypeRegistry` with per-type handlers for int, float, enum, bitfield. Bitfield encode/decode uses masking/shifting, not piggybacked on int type.
3. **ConnectionManager** — wraps TCP + serial behind one interface. Config-selected mode. Dynamic serial port enumeration via `serial.tools.list_ports`. Pushes raw bytes into a reader thread that feeds the parser. Status events go into the shared queue.
4. **Parser** — 8 KB ring buffer (`RING_BUFFER_SIZE = 8192`). 5-state machine: SCAN → HEADER → PAYLOAD → CHECKSUM. `FRAME_TIMEOUT_SECS = 5.0`. Delivers valid frames to queue. Invalid checksum → slide 1 byte, retry SCAN.
5. **UI** — tkinter. Status bar top, `PanedWindow` horizontal split (tabbed main display | Treeview log), scrollable send area bottom. LED = `tk.Canvas` oval + text label. Main display: one tab per message type showing latest decoded dict. Log: `tk.Treeview` with Time, Direction, Message, Raw Hex columns. View mode: mixed (chronological) or split (TX/RX separate panes).
6. **PeriodicSend** — `tkinter.after()` on main thread. Per-message interval entry + Start/Stop button. State in-memory dict, ephemeral. Manual send during periodic: fires once independently.
7. **Logger** — single combined log per project: `configs/<project>/comm.log`. Block format per event. Configurable max entries rotation. Logs all traffic: sent, received, decode errors, unrecognized frames.
8. **LayoutPersistence** — saves `ui.json` on exit: version, geometry, log_view, panes (ratio). Atomic save via temp+rename. Restores on launch. Defaults: 1200x800 centered, mixed, 50/50.
9. **Startup** — loading order: protocol → connection → ui → tx-state. Missing configs → defaults + log. Invalid JSON → skip + log with line. Schema mismatch → per-field defaults + warnings. Unknown message IDs → raw hex in log. First launch → empty shell with "Create Project" hint. Last project in `app-state.json`.

### Protocol Schema

The `protocol.json` schema (from issue #01 research):
- Top level: `protocol` (name, version, endianness), `messages` (id, name, fields[]), `enums` (value mappings), `checksum` (algorithm, variant, covers, offset)
- Fields: `type` (int/float/enum/bitfield), `size`, `endian`, `min`, `max`, `step`, `enum_ref`
- Bitfields: `type: "bitfield"` with `bits` array, each bit has `name`, `start_bit`, `length`
- Checksum algorithms: CRC8, CRC16, CRC32, XOR, sum — selected by string name in config
- `struct.Struct` compiled per message type at load time

### Config File Layout

```
configs/
  project-name/
    connection.json    — TCP/serial settings
    protocol.json      — message definitions + field-level display prefs
    ui.json            — layout state (saved on exit)
    tx-state.json      — last-used TX field values per message type
    comm.log           — combined traffic log
```

### Constants

All in one place (`constants.py`):
- `RING_BUFFER_SIZE = 8192`
- `FRAME_TIMEOUT_SECS = 5.0`
- `UI_POLL_INTERVAL_MS = 50`

### Dependencies

- `pyserial` — serial port communication
- `crc` — CRC calculations (preferred over fastcrc for simplicity)
- `tkinter` — stdlib, no install needed
- `struct` — stdlib, binary packing
- `pyinstaller` — packaging only, not runtime

## Testing Decisions

### What makes a good test

Tests verify external behavior, not implementation details. A good test: "given this binary frame, the decoder produces this dict." Not: "the state machine was in STATE_PAYLOAD."

### Modules to test

1. **ProtocolCodec** — encode/decode roundtrips for each field type (int, float, enum, bitfield). Checksum computation. Constraint validation (min/max). Byte order handling. This is the most testable module (pure functions, no I/O).
2. **Parser** — ring buffer state machine transitions. Sync pattern detection. Partial frame timeout. Checksum validation failure → slide 1 byte.
3. **ConfigLoader** — missing file → defaults. Invalid JSON → skip + defaults. Schema mismatch → per-field defaults. Valid config → correct typed dict.
4. **ConnectionManager** — harder to unit test (real I/O). Integration test with a mock server/loopback is possible but lower priority for MVP.

### Prior art

No existing tests in the codebase (greenfield). First tests to write:
- ProtocolCodec roundtrip tests (the foundation everything else depends on)
- Parser state machine tests with synthetic byte streams
- ConfigLoader error handling tests with temp files

### Test approach

Per engineering guidelines: `assert`-based self-checks or small `test_*.py` files. No test frameworks unless asked. One runnable check per non-trivial logic path.

## Out of Scope

- Multiple simultaneous connections
- Plugin/extension system
- Message scripting or automation beyond periodic send
- Export/import of protocol definitions
- Multi-monitor or advanced window management
- Network discovery or mDNS
- Encrypted connections (TLS/SSL)
- Unit conversion or custom display formatters beyond hex/dec/bin
- Undo/redo in send forms
- Message favorites or presets
- Search/filter in traffic log
- Sound or notification on message receipt
- Custom themes or appearance settings

## Further Notes

- This is a greenfield project. No code exists. Start from `pyproject.toml` / `requirements.txt`.
- The research doc at `.scratch/comm-templater/research/protocol-format-findings.md` (907 lines) contains concrete code samples and a full proposed JSON schema — reference it when implementing the ProtocolCodec.
- Engineering guidelines require `SHORTCUT:` markers for any deliberate simplification with ceiling and upgrade path.
- Token budget: ~4,000 tokens per task. This MVP should be decomposed into budget-sized subtasks.
- Natural implementation order: ConfigLoader → ProtocolCodec → Parser → ConnectionManager → UI (skeleton) → Send area → PeriodicSend → Logger → LayoutPersistence → Startup wiring.
