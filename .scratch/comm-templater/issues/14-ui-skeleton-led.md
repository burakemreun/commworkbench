Status: resolved
Type: task
Blocked by: 11

# 14 — UI Skeleton + LED

**What to build:** tkinter application skeleton with visual framework. Main window with status bar at top, horizontal PanedWindow splitting tabbed main display (placeholder) and traffic log (placeholder), scrollable send area at bottom. LED indicator using `tk.Canvas` oval (green=connected, red=disconnected) with text label showing connection details (IP:port for TCP, COM@baud for serial). Layout restore from `ui.json` on launch (geometry, log_view, panes ratio). Defaults on first launch: 1200x800 centered, mixed log, 50/50 pane split. Atomic save on exit (write temp, rename). Minimal serialization (version, geometry, log_view, panes). Ratio-based pane positions survive window resizing.

**Blocked by:** 11 (needs ConfigLoader for ui.json reading).

**Status:** resolved — `commworkbench/ui.py`, verify: `verify_ui.py`

- [x] tkinter main window with status bar at top
- [x] Horizontal PanedWindow: tabbed main display (placeholder) | traffic log (placeholder)
- [x] Scrollable send area at bottom (placeholder)
- [x] LED indicator: tk.Canvas oval (green=connected, red=disconnected) + text label
- [x] LED text shows connection details (IP:port or COM@baud)
- [x] Layout restore from ui.json on launch (geometry, log_view, panes ratio)
- [x] Defaults on first launch: 1200x800 centered, mixed log, 50/50 split
- [x] Atomic save on exit: write to ui.json.tmp, os.rename over ui.json
- [x] Ratio-based pane positions (survive window resizing)
- [x] Verifiable: app launches, LED shows disconnected, layout restores after resize+restart
