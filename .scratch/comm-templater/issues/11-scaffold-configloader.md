Status: ready-for-agent
Type: task
Blocked by: none

# 11 — Scaffold + ConfigLoader

**What to build:** Project setup and configuration loading infrastructure. Create the Python project structure (pyproject.toml, requirements.txt, .gitignore), install dependencies (pyserial, crc), and implement a ConfigLoader module that reads/validates all JSON config files from `configs/<project>/`. Returns typed dicts or sensible defaults. Logs errors with file path and line number. Missing configs → defaults + warning. Invalid JSON → skip + log with line. Schema mismatch → per-field defaults + warnings.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] pyproject.toml with project metadata and dependencies (pyserial, crc)
- [ ] requirements.txt generated from pyproject.toml
- [ ] .gitignore for Python projects
- [ ] ConfigLoader reads connection.json, protocol.json, ui.json, tx-state.json from `configs/<project>/`
- [ ] Auto-discovers project folders in `configs/` (subdirectories containing expected files)
- [ ] Returns typed dicts for each config file
- [ ] Missing config file → uses sensible defaults + logs warning
- [ ] Invalid JSON → skips file, uses defaults, logs error with file path and line number
- [ ] Schema mismatch → per-field defaults with warnings (preserves valid fields)
- [ ] Verifiable: run a script that loads configs and prints correct dicts back
