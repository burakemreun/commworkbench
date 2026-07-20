Status: resolved
Type: grilling
Blocked by: none

# 09 — Startup Sequence & Config Load Handling

## Question

What is the application startup sequence and how are config load failures handled?

Decisions so far established separate config files in `configs/<project>/` (issue #02), auto-discovery of project folders, and connection/protocol/UI configs. But the initialization order and error handling are unspecified:

- What is the config loading order? (protocol first? connection? does it matter?)
- What default state is used when a config file is missing on first launch?
- What happens if a config file contains invalid JSON?
- What happens if the JSON structure doesn't match the expected schema? (e.g. missing required fields, wrong types)
- How does the app handle a received message ID that doesn't exist in the loaded protocol config?
- What is the first-launch experience when `configs/` is empty or doesn't exist?
- What is the default project selection behavior? (last used? first found? prompt?)

Ask me one question at a time to resolve this.

## Answer

### Loading order

**Protocol → Connection → UI → TX State.** Protocol defines message types and field schemas that connection setup may reference. UI config references message types from protocol (to render send forms). TX state depends on protocol (field names to restore values into).

### Missing config on first launch

**Start with sensible defaults, log a warning.** First launch should feel welcoming, not blocking. Log which file is missing so the user knows what to fill in.

### Invalid JSON

**Skip that file, use defaults, log error with file path and line number.** The user can open the file in a text editor to fix it. Example: `protocol.json: invalid JSON at line 14 — using defaults`.

### Schema mismatch

**Per-field defaults with warnings.** Log each missing or wrong-type field individually. Preserve the 90% of the file that's valid rather than rejecting the whole thing. Example: `connection.json: "port" missing — using default 5000`.

### Unknown message ID received

**Show raw hex in the traffic log.** Display `[UNKNOWN] 0x07 | 4A 3B 2C ...` in the log. No popups, no flashing — just a clear line so the user can see what arrived without disruption.

### First-launch experience (empty configs)

**Empty app shell with a "Create Project" prompt.** No wizard, no auto-created defaults. The status bar or main area hints at how to start (e.g. "No projects found — create one from the File menu"). Gives the user full control.

### Default project selection

**Last used project, stored in a separate `app-state.json` file.** If the saved project no longer exists, fall back to "no project loaded" (the empty shell). Not stored in `tx-state.json` — dedicated file for app-level state.
