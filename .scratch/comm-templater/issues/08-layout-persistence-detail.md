Status: resolved
Type: grilling
Blocked by: none

# 08 — Layout Persistence Detail

## Question

How exactly is UI layout state serialized to `ui.json`?

Issue #04 decided: auto-save on exit to `ui.json`, saving `root.geometry()`, pane positions, and `log_view` setting. But the details are unresolved:

- What is the exact JSON structure of `ui.json`?
- What properties are serialized beyond geometry, pane positions, and log_view? (e.g. window maximized state, send area scroll position, tab selection, column widths in Treeview)
- How are pane positions represented? (pixel offset? ratio? sash index?)
- What happens on first launch when `ui.json` doesn't exist? What are the sensible defaults?
- What happens if `ui.json` is corrupt or partially written? (crash mid-save, power loss)
- Should the save be atomic (write to temp, then rename)?

Ask me one question at a time to resolve this.

## Answer

**JSON structure:**
```json
{
  "version": 1,
  "geometry": "1200x800+100+50",
  "log_view": "mixed",
  "panes": {
    "main_log": 0.5
  }
}
```

- `version`: integer, for future schema migrations
- `geometry`: raw `root.geometry()` string
- `log_view`: `"mixed"` or `"split"`
- `panes.main_log`: ratio (0.0–1.0) of main vs log pane width

**Defaults on first launch** (no `ui.json`): 1200x800 centered, `mixed` log, 50/50 pane split.

**Atomic save:** write to `ui.json.tmp`, then `os.rename()` over `ui.json` — never half-written.

**Minimal serialization:** only `geometry`, `log_view`, and `panes`. No column widths, scroll positions, tab selection, or maximized state — cosmetic, low value, edge cases for v1.

**Pane position:** ratio-based, not pixel-based — survives window resizing, computed from current window width on restore.
