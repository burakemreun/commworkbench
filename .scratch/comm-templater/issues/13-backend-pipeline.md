Status: resolved
Type: task
Blocked by: 11, 12

# 13 — Backend Pipeline

**What to build:** Complete backend pipeline from raw connection to decoded frames. ConnectionManager wrapping TCP (client/server, config-selected) and serial (dynamic port enumeration via `serial.tools.list_ports`, configurable baud/data/stop/parity). Single connection at a time, shared reader thread. Parser with 8 KB ring buffer and 5-state machine (SCAN → HEADER → PAYLOAD → CHECKSUM). Sync pattern detection, checksum validation, 5-second partial-frame timeout. ConnectionManager feeds raw bytes to Parser, Parser extracts frames, Decoder (from #12) produces dicts. All output pushed to `queue.Queue` as DecodedFrame objects. Connection status events (connected/disconnected/error) also go through the same queue. Auto-reconnect with configurable retry interval, attempts logged to queue. No popups — LED and log tell the story.

**Blocked by:** 11 (config loader for connection/protocol configs), 12 (ProtocolCodec for decoding frames).

**Status:** resolved — `connection_manager.py` + `parser.py`, verify: `tests/test_parser.py`, `simulator.py`

- [x] ConnectionManager class wrapping TCP and serial behind one interface
- [x] TCP: client and server modes, config-selected, only one active at a time
- [x] Serial: dynamic port enumeration, configurable baud/data/stop/parity
- [x] Single connection at a time, one shared reader thread
- [x] Parser with 8 KB ring buffer (RING_BUFFER_SIZE = 8192)
- [x] 5-state machine: SCAN → HEADER → PAYLOAD → CHECKSUM
- [x] Checksum validation. Sync pattern yok: #01 kararı 1-byte msg ID ile başlıyor, SCAN bilinen ID'leri arıyor
- [x] 5s partial-frame timeout (FRAME_TIMEOUT_SECS = 5.0)
- [x] Invalid checksum → slide 1 byte, retry SCAN
- [x] DecodedFrame objects pushed to queue.Queue
- [x] Connection status events (connected/disconnected/error) pushed to same queue
- [x] Auto-reconnect with configurable retry interval, logged to queue
- [x] No popups — errors surfaced via queue events only
- [x] Verifiable: connect to test endpoint, see decoded frames in queue
