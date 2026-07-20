Status: resolved
Type: grilling
Blocked by: none

# 02 — Config File Structure

## Question

How should the multiple JSON config files be organized? We need configs for:
- Connection settings (TCP server/client, IP, port; serial port, baud rate, etc.)
- Protocol definition (header, message definitions, checksum)
- UI layout (panel positions, sizes, widget placement)
- Display preferences (field visibility, format choices for received messages)

Should these be:
- Separate files (connection.json, protocol.json, ui.json, display.json)?
- Nested structure within fewer files?
- One master config that references sub-configs?

Also: where do config files live? Same directory as exe? Subfolder? User app data?

Ask me one question at a time to resolve this.

## Answer

### Config file structure

**Separate files** in a `configs/` subfolder next to the exe. Fixed filenames within each project folder:

```
configs/
  project-a/
    connection.json    — TCP/serial settings
    protocol.json      — message definitions + per-field display prefs
    ui.json            — layout (panel sizes, positions, arrangement)
    tx-state.json      — last-used TX field values per message type
  project-b/
    ...
```

### Key decisions

- **Field-level display prefs** (visibility, number format, limits) live inside `protocol.json` message definitions — no separate display config.
- **TX state persistence** (`tx-state.json`) remembers last-used values so the app restores them on launch.
- **Project switching** via a dropdown/menu in the UI (not startup prompt, not CLI arg). Switch anytime mid-session.
- **Auto-discovery**: scan `configs/` for subdirectories containing the expected files. No registry — drop a folder in and it appears in the menu.
