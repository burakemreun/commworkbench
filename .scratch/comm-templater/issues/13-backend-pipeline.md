Status: ready-for-agent
Type: task
Blocked by: 11, 12

# 13 — Backend Pipeline

**What to build:** Complete backend pipeline from raw connection to decoded frames. ConnectionManager wrapping TCP (client/server, config-selected) and serial (dynamic port enumeration via `serial.tools.list_ports`, configurable baud/data/stop/parity). Single connection at a time, shared reader thread. Parser with 8 KB ring buffer and 5-state machine (SCAN → HEADER → PAYLOAD → CHECKSUM). Sync pattern detection, checksum validation, 5-second partial-frame timeout. ConnectionManager feeds raw bytes to Parser, Parser extracts frames, Decoder (from #12) produces dicts. All output pushed to `queue.Queue` as DecodedFrame objects. Connection status events (connected/disconnected/error) also go through the same queue. Auto-reconnect with configurable retry interval, attempts logged to queue. No popups — LED and log tell the story.

**Blocked by:** 11 (config loader for connection/protocol configs), 12 (ProtocolCodec for decoding frames).

**Status:** ready-for-agent

- [ ] ConnectionManager class wrapping TCP and serial behind one interface
- [ ] TCP: client and server modes, config-selected, only one active at a time
- [ ] Serial: dynamic port enumeration, configurable baud/data/stop/parity
- [ ] Single connection at a time, one shared reader thread
- [ ] Parser with 8 KB ring buffer (RING_BUFFER_SIZE = 8192)
- [ ] 5-state machine: SCAN → HEADER → PAYLOAD → CHECKSUM
- [ ] Sync pattern detection, checksum validation
- [ ] 5s partial-frame timeout (FRAME_TIMEOUT_SECS = 5.0)
- [ ] Invalid checksum → slide 1 byte, retry SCAN
- [ ] DecodedFrame objects pushed to queue.Queue
- [ ] Connection status events (connected/disconnected/error) pushed to same queue
- [ ] Auto-reconnect with configurable retry interval, logged to queue
- [ ] No popups — errors surfaced via queue events only
- [ ] Verifiable: connect to test endpoint, see decoded frames in queue
