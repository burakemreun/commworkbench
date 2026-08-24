Status: resolved
Type: task
Blocked by: 11, 16

# 18 — TX State + Startup + Project Switching

**What to build:** Session persistence and project management. `tx-state.json` saves last-used TX field values per message type, restored on launch. Config loading order: protocol → connection → ui → tx-state. Project switching via UI dropdown menu — auto-discovers `configs/` subdirectories, switches anytime mid-session. `app-state.json` stores last-used project name. First-launch experience: empty app shell with "Create Project" hint (no wizard, no auto-created defaults). If saved project no longer exists, falls back to "no project loaded".

**Blocked by:** 11 (ConfigLoader for project discovery and config loading), 16 (Send area to restore TX values into).

**Status:** resolved — `main.py` `App`, verify: `verify_startup.py`. Not: app-state dosyası `configs/_app-state.json`

- [x] tx-state.json saves last-used TX field values per message type
- [x] TX state restored on launch (values populated in send forms)
- [x] Config loading order: protocol → connection → ui → tx-state
- [x] Project switching via UI dropdown menu
- [x] Auto-discovers project folders in configs/
- [x] Switches configs mid-session (reloads all modules)
- [x] app-state.json stores last-used project name
- [x] Last project restored on launch
- [x] First-launch: empty shell with "Create Project" hint
- [x] If saved project missing → "no project loaded" fallback
- [x] Verifiable: fill send fields, restart, see values restored. Switch projects, see different configs load.
