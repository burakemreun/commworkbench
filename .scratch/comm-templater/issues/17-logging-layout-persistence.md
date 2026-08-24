Status: resolved
Type: task
Blocked by: 13, 15

# 17 — Logging + Layout Persistence

**What to build:** Persistent storage for traffic and UI state. Single combined log file per project: `configs/<project>/comm.log`. Block format per event: timestamp, direction, message name, raw hex, parsed fields (separate lines). All traffic logged: sent, received, decode errors, unrecognized frames. Configurable rotation (max_entries). Atomic layout save on exit to `ui.json`: version, geometry, log_view, panes ratio. Already implemented in #14 — this ticket adds the logging half and ensures both work end-to-end.

**Blocked by:** 13 (backend pipeline delivering frames to log), 15 (UI displaying traffic that gets logged).

**Status:** resolved — `traffic_logger.py` + `ui.py` `_save_layout`

- [x] Single combined log file per project: configs/<project>/comm.log
- [x] Block format: timestamp, direction, message name, raw hex, parsed fields
- [x] All traffic logged: sent, received, decode errors, unrecognized frames
- [x] Configurable rotation — `ui.json` → `max_log_entries` (varsayılan 1000); hem `comm.log` hem UI Treeview limiti aynı anahtardan
- [x] Layout persistence verified end-to-end (save on exit, restore on launch)
- [x] Verifiable: check log file after traffic. Resize window, restart, see same layout.
