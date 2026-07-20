Status: ready-for-agent
Type: task
Blocked by: 11

# 14 — UI Skeleton + LED

**What to build:** tkinter application skeleton with visual framework. Main window with status bar at top, horizontal PanedWindow splitting tabbed main display (placeholder) and traffic log (placeholder), scrollable send area at bottom. LED indicator using `tk.Canvas` oval (green=connected, red=disconnected) with text label showing connection details (IP:port for TCP, COM@baud for serial). Layout restore from `ui.json` on launch (geometry, log_view, panes ratio). Defaults on first launch: 1200x800 centered, mixed log, 50/50 pane split. Atomic save on exit (write temp, rename). Minimal serialization (version, geometry, log_view, panes). Ratio-based pane positions survive window resizing.

**Blocked by:** 11 (needs ConfigLoader for ui.json reading).

**Status:** ready-for-agent

- [ ] tkinter main window with status bar at top
- [ ] Horizontal PanedWindow: tabbed main display (placeholder) | traffic log (placeholder)
- [ ] Scrollable send area at bottom (placeholder)
- [ ] LED indicator: tk.Canvas oval (green=connected, red=disconnected) + text label
- [ ] LED text shows connection details (IP:port or COM@baud)
- [ ] Layout restore from ui.json on launch (geometry, log_view, panes ratio)
- [ ] Defaults on first launch: 1200x800 centered, mixed log, 50/50 split
- [ ] Atomic save on exit: write to ui.json.tmp, os.rename over ui.json
- [ ] Ratio-based pane positions (survive window resizing)
- [ ] Verifiable: app launches, LED shows disconnected, layout restores after resize+restart
