Status: resolved
Type: task
Blocked by: 13, 14

# 15 — Main Display + Traffic Log

**What to build:** Decode the queue and display everything. Tabbed main display with one tab per message type from protocol.json — each tab shows the latest decoded dict for that message type. Treeview traffic log with columns: Time, Direction, Message, Raw Hex. View mode configurable: "mixed" (single chronological list, default) or "split" (TX and RX in separate panes). Queue polling on `root.after(50ms)` (UI_POLL_INTERVAL_MS = 50). Unknown message IDs show as raw hex in log (e.g. `[UNKNOWN] 0x07 | 4A 3B 2C ...`). Decode errors logged, not popped up. Connection status events update LED.

**Blocked by:** 13 (backend pipeline delivering DecodedFrames to queue), 14 (UI skeleton with PanedWindow and placeholders).

**Status:** resolved — split view #21'de tamamlandı

- [x] Tabbed main display: one tab per message type from protocol.json
- [x] Each tab shows latest decoded dict for that message type
- [x] Treeview traffic log: Time, Direction, Message, Raw Hex columns
- [x] Mixed view mode: single chronological list (default)
- [x] Split view mode: TX and RX in separate panes — dikey PanedWindow, iki Treeview (#21)
- [x] View mode toggle in UI — status bar'da mixed/split combobox, `ui.json:log_view`'e yazılıyor; geçişte satır geçmişi korunuyor
- [x] Queue polling on root.after(50ms)
- [x] Unknown message IDs show as raw hex in Unknown tab + log
- [x] Decode errors logged to traffic log, no popups
- [x] Connection status events update LED indicator
- [x] Verifiable: connect to device, see decoded messages in tabs and traffic in log
