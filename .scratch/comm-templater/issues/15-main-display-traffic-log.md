Status: ready-for-agent
Type: task
Blocked by: 13, 14

# 15 — Main Display + Traffic Log

**What to build:** Decode the queue and display everything. Tabbed main display with one tab per message type from protocol.json — each tab shows the latest decoded dict for that message type. Treeview traffic log with columns: Time, Direction, Message, Raw Hex. View mode configurable: "mixed" (single chronological list, default) or "split" (TX and RX in separate panes). Queue polling on `root.after(50ms)` (UI_POLL_INTERVAL_MS = 50). Unknown message IDs show as raw hex in log (e.g. `[UNKNOWN] 0x07 | 4A 3B 2C ...`). Decode errors logged, not popped up. Connection status events update LED.

**Blocked by:** 13 (backend pipeline delivering DecodedFrames to queue), 14 (UI skeleton with PanedWindow and placeholders).

**Status:** ready-for-agent

- [ ] Tabbed main display: one tab per message type from protocol.json
- [ ] Each tab shows latest decoded dict for that message type
- [ ] Treeview traffic log: Time, Direction, Message, Raw Hex columns
- [ ] Mixed view mode: single chronological list (default)
- [ ] Split view mode: TX and RX in separate panes
- [ ] View mode toggle in UI (or config-driven)
- [ ] Queue polling on root.after(50ms)
- [ ] Unknown message IDs show as raw hex in log: `[UNKNOWN] 0xXX | ...`
- [ ] Decode errors logged to traffic log, no popups
- [ ] Connection status events update LED indicator
- [ ] Verifiable: connect to device, see decoded messages in tabs and traffic in log
