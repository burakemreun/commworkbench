Status: ready-for-agent
Type: task
Blocked by: 11, 16

# 18 — TX State + Startup + Project Switching

**What to build:** Session persistence and project management. `tx-state.json` saves last-used TX field values per message type, restored on launch. Config loading order: protocol → connection → ui → tx-state. Project switching via UI dropdown menu — auto-discovers `configs/` subdirectories, switches anytime mid-session. `app-state.json` stores last-used project name. First-launch experience: empty app shell with "Create Project" hint (no wizard, no auto-created defaults). If saved project no longer exists, falls back to "no project loaded".

**Blocked by:** 11 (ConfigLoader for project discovery and config loading), 16 (Send area to restore TX values into).

**Status:** ready-for-agent

- [ ] tx-state.json saves last-used TX field values per message type
- [ ] TX state restored on launch (values populated in send forms)
- [ ] Config loading order: protocol → connection → ui → tx-state
- [ ] Project switching via UI dropdown menu
- [ ] Auto-discovers project folders in configs/
- [ ] Switches configs mid-session (reloads all modules)
- [ ] app-state.json stores last-used project name
- [ ] Last project restored on launch
- [ ] First-launch: empty shell with "Create Project" hint
- [ ] If saved project missing → "no project loaded" fallback
- [ ] Verifiable: fill send fields, restart, see values restored. Switch projects, see different configs load.
