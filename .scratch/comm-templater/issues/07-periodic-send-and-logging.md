Status: resolved
Type: grilling
Blocked by: none

# 07 — Periodic Send & Logging

## Question

Design two related subsystems:

**Periodic Send:**
- Each message type can be toggled for periodic sending
- Per-message configurable interval (ms)
- Start/stop per message independently
- Use tkinter `after()` or threading Timer?

**Logging:**
- All sent/received messages logged (raw hex + parsed)
- Log to separate files (sent.log, received.log? or one combined?)
- Log format (timestamp, direction, message name, raw bytes, parsed fields)
- Log rotation? Max file size?
- Log save location (same as config? user-selected?)

Ask me one question at a time to resolve this.

## Answer

**Periodic Send:**
- Timer: `tkinter.after()` on main thread — simple, no thread-safety concerns
- State: ephemeral (in-memory dict, lost on close, no tx-state.json persistence)
- UI: checkbox + interval entry (ms) per message, next to send button
- Manual send during periodic: fires once independently, periodic keeps its own schedule

**Logging:**
- Single combined log file per project: `configs/<project>/comm.log`
- Block format per event: timestamp, direction, message name, raw hex, parsed fields (separate lines)
- Rotation: configurable in project config — `max_entries: N` or unlimited
- Scope: all traffic — sent, received, decode errors, unrecognized frames
