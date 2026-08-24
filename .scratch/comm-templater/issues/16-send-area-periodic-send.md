Status: resolved
Type: task
Blocked by: 12, 13, 15

# 16 — Send Area + Periodic Send

**What to build:** Complete send pipeline. Per-message-type forms in the scrollable send area — fields generated from protocol.json message definitions (editable entries for each field). Send button per message: validates inputs, encodes via ProtocolCodec, transmits via ConnectionManager, logs to traffic log. Per-message periodic send: interval input (ms) + Start/Stop button per message. Uses `tkinter.after()` on main thread (no threading). State is ephemeral (in-memory dict, lost on close). Manual send during active periodic: fires once independently, periodic keeps its own schedule.

**Blocked by:** 12 (ProtocolCodec for encoding), 13 (ConnectionManager for transmitting), 15 (UI framework with send area placeholder).

**Status:** resolved — `ui.py` `_build_message_form` / `_send_message` / `_toggle_periodic`

- [x] Per-message send forms in scrollable send area
- [x] Fields generated from protocol.json message definitions (editable entries)
- [x] Send button: validates inputs → encodes via ProtocolCodec → transmits via ConnectionManager → logs to traffic log
- [x] Validation errors shown inline (not popup)
- [x] Per-message periodic send: interval input (ms) + Start/Stop button
- [x] Uses tkinter.after() on main thread
- [x] State ephemeral (in-memory, lost on close)
- [x] Manual send during periodic: fires once independently, doesn't disrupt schedule
- [x] Verifiable: fill fields, send, see in log. Enable periodic, see messages at interval.
