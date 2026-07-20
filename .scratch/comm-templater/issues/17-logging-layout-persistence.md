Status: ready-for-agent
Type: task
Blocked by: 13, 15

# 17 — Logging + Layout Persistence

**What to build:** Persistent storage for traffic and UI state. Single combined log file per project: `configs/<project>/comm.log`. Block format per event: timestamp, direction, message name, raw hex, parsed fields (separate lines). All traffic logged: sent, received, decode errors, unrecognized frames. Configurable rotation (max_entries). Atomic layout save on exit to `ui.json`: version, geometry, log_view, panes ratio. Already implemented in #14 — this ticket adds the logging half and ensures both work end-to-end.

**Blocked by:** 13 (backend pipeline delivering frames to log), 15 (UI displaying traffic that gets logged).

**Status:** ready-for-agent

- [ ] Single combined log file per project: configs/<project>/comm.log
- [ ] Block format: timestamp, direction, message name, raw hex, parsed fields
- [ ] All traffic logged: sent, received, decode errors, unrecognized frames
- [ ] Configurable rotation (max_entries in config)
- [ ] Layout persistence verified end-to-end (save on exit, restore on launch)
- [ ] Verifiable: check log file after traffic. Resize window, restart, see same layout.
