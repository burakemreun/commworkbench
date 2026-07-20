Status: resolved
Type: grilling
Blocked by: none

# 03 — Ring Buffer Parser Architecture

## Question

Design the ring buffer and parser state machine for processing incoming binary data.

Requirements:
- Collect incoming bytes in a ring buffer
- Scan byte-by-byte looking for header sync pattern
- Once header found, read header fields to determine message length
- Extract payload based on length
- Validate checksum
- If checksum fails, slide 1 byte and retry scanning
- Deliver valid frames to message decoder

Key decisions:
- Ring buffer size (fixed? config-defined?)
- State machine states (IDLE, HEADER, PAYLOAD, CHECKSUM?)
- How to handle partial messages (connection drops mid-frame?)
- Thread safety (serial/TCP reader thread vs UI thread)
- How to signal valid frames to the UI layer

## Answer

**Buffer:** Fixed size, 8 KB default. `RING_BUFFER_SIZE = 8192` as a module-level constant, configurable at startup if needed later.

**State machine:** Explicit states — `SCAN` (sliding byte-by-byte for sync pattern), `IDLE` (connected, no active parse), `HEADER` (reading header fields), `PAYLOAD` (reading N payload bytes), `CHECKSUM` (reading/validating checksum). Transitions: IDLE → SCAN on connect; SCAN → HEADER on sync match; HEADER → PAYLOAD when length known; PAYLOAD → CHECKSUM when payload complete; CHECKSUM valid → deliver + back to SCAN; CHECKSUM invalid → back to SCAN (slide 1 byte). IDLE entered on disconnect; SCAN entered on reconnect or after timeout.

**Partial message timeout:** `FRAME_TIMEOUT_SECS = 5.0` as a configurable constant. If no new bytes arrive within the timeout window during HEADER, PAYLOAD, or CHECKSUM states, discard the partial frame and return to SCAN.

**Thread model:** Dedicated reader thread pushes raw bytes into the ring buffer. A separate parser thread (or the same reader thread) pulls from the buffer, runs the state machine, and decodes frames.

**Frame delivery:** Parser pushes `DecodedFrame` objects into a `queue.Queue`. UI polls the queue on a `root.after()` timer (e.g. every 50 ms) and processes any available frames.

**Configurable constants (all in one place, e.g. `constants.py`):**
- `RING_BUFFER_SIZE = 8192`
- `FRAME_TIMEOUT_SECS = 5.0`
- `UI_POLL_INTERVAL_MS = 50`
