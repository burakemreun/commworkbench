Status: resolved
Type: grilling
Blocked by: none

# 04 — UI Panel Layout

## Question

Design the tkinter UI structure with multiple panels:

Requirements:
- Multi-panel layout (panels can be resized)
- Connection status visual indicators (LED-style)
- Main display area: latest parsed message shown meaningfully
- Side log panel: all sent/received messages (raw + parsed)
- Message send area: each message type gets editable fields + send button
- Periodic send toggle per message
- Full layout save/restore

Key decisions:
- Panel container approach (PanedWindow? Grid? Custom?)
- How to dynamically generate message forms from config
- How to handle the log panel (Text widget? Treeview? ScrolledText?)
- How to implement LED-style indicators in tkinter
- Layout save format (JSON? pickle? tkinter state?)

Ask me one question at a time to resolve this.

## Answer

**Layout structure:** Status bar top, `PanedWindow` horizontal split (main display | traffic log), send area bottom.

**Main display:** Tabbed — one tab per message type, each shows the latest decoded message for that type.

**Traffic log:** `tk.Treeview` with columns: Time, Direction, Message, Raw Hex. View mode configurable via `log_view` in `ui.json` — `"mixed"` (single chronological list, default) or `"split"` (TX and RX in separate panes).

**Send area:** All message types visible simultaneously, stacked vertically, scrollable if many. Each message form has: label, editable field entries (generated from `protocol.json` message definitions), Send button, and a periodic send config row (interval input in ms + Start/Stop button).

**Periodic send:** Separate config row per message — interval input + Start/Stop button (not a simple toggle).

**LED indicator:** `tk.Canvas` oval (green=connected, red=disconnected) + text label showing connection details (IP:port for TCP, COM@baud for serial).

**Layout save/restore:** Auto-save on exit to `ui.json` — saves `root.geometry()`, pane positions, and `log_view` setting. Restored on next launch.
