Status: ready-for-agent
Type: task
Blocked by: 12, 13, 15

# 16 — Send Area + Periodic Send

**What to build:** Complete send pipeline. Per-message-type forms in the scrollable send area — fields generated from protocol.json message definitions (editable entries for each field). Send button per message: validates inputs, encodes via ProtocolCodec, transmits via ConnectionManager, logs to traffic log. Per-message periodic send: interval input (ms) + Start/Stop button per message. Uses `tkinter.after()` on main thread (no threading). State is ephemeral (in-memory dict, lost on close). Manual send during active periodic: fires once independently, periodic keeps its own schedule.

**Blocked by:** 12 (ProtocolCodec for encoding), 13 (ConnectionManager for transmitting), 15 (UI framework with send area placeholder).

**Status:** ready-for-agent

- [ ] Per-message send forms in scrollable send area
- [ ] Fields generated from protocol.json message definitions (editable entries)
- [ ] Send button: validates inputs → encodes via ProtocolCodec → transmits via ConnectionManager → logs to traffic log
- [ ] Validation errors shown inline (not popup)
- [ ] Per-message periodic send: interval input (ms) + Start/Stop button
- [ ] Uses tkinter.after() on main thread
- [ ] State ephemeral (in-memory, lost on close)
- [ ] Manual send during periodic: fires once independently, doesn't disrupt schedule
- [ ] Verifiable: fill fields, send, see in log. Enable periodic, see messages at interval.
