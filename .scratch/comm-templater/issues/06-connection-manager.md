Status: resolved
Type: grilling
Blocked by: none

# 06 — Connection Manager

## Question

Design the connection management layer for TCP and serial communication.

Requirements:
- TCP: connect as client or listen as server (config-selected)
- Serial: configurable port, baud rate, data bits, stop bits, parity
- Connection status visual indicators in UI
- Auto-reconnect option?
- Connection lifecycle: connect, disconnect, reconnect
- Thread-safe: reader thread pushes data to ring buffer, UI thread reads status

Key decisions:
- TCP client vs server mode selection
- Serial port enumeration (list available ports?)
- Connection thread model (dedicated reader thread per connection type?)
- How to signal connection status to UI (callback? queue? event?)
- Error handling strategy (retry? alert? log and continue?)

Ask me one question at a time to resolve this.

## Answer

**TCP mode:** Both client and server available, config-selected. Only one active at a time.

**Serial ports:** Dynamic detection via `serial.tools.list_ports` — dropdown in UI, user selects from available COM ports.

**Connection model:** Single connection at a time, one shared reader thread. `ConnectionManager` class wraps both TCP and serial, exposes same reader-thread interface regardless of type.

**Status signaling:** Connection status (connected/disconnected/error) pushed into the same `queue.Queue` as decoded frames. UI polling loop handles both.

**Auto-reconnect:** Config-driven — on/off toggle + retry interval in config. On disconnect, retry with backoff. Attempts logged to traffic log so user sees "reconnecting..." messages.

**Error handling:** Log the error, update LED to red, trigger auto-reconnect if enabled. No popups — LED and log tell the story.
