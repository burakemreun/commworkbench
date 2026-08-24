# Map: CommWorkbench

## Destination

Config-driven binary protocol communication tool — single PyInstaller exe, tkinter GUI, TCP or serial (config-selected), JSON-defined message structures with bitfield support, ring buffer processing, saveable UI layout, visual connection indicators, per-message periodic sending, file logging.

## Notes

- Python 3 + tkinter, packaged with PyInstaller
- Binary protocol: header + payload + checksum, config-defined
- Multiple JSON config files (connection, messages, protocol, UI)
- Byte order configurable (big/little endian)
- Ring buffer: byte-by-byte scanning for header, checksum validation
- Main display: latest parsed message; side log: all traffic (raw + parsed)
- Each message type: editable fields form + send button
- Per-message periodic send option
- Full layout save/restore (position, size, panel arrangement)

## Decisions so far

- [Binary Protocol Definition Format](issues/01-protocol-definition-format.md) — Custom JSON schema with struct.Struct runtime compilation, flat bitfields, configurable checksum (CRC/XOR/sum), hierarchical endianness
- [Config File Structure](issues/02-config-schema.md) — Separate files in `configs/<project>/`, fixed names (connection, protocol, ui, tx-state), auto-discovered project folders, UI menu to switch
- [Ring Buffer Parser Architecture](issues/03-ring-buffer-architecture.md) — Fixed 8 KB ring buffer, explicit SCAN/IDLE/HEADER/PAYLOAD/CHECKSUM state machine, 5s partial-frame timeout, dedicated reader thread, queue.Queue delivery to UI, constants in `constants.py`
- [UI Panel Layout](issues/04-ui-layout.md) — Status bar + PanedWindow (tabbed main display | Treeview log) + scrollable send area, LED with text label, auto-save layout on exit, configurable mixed/split log view
- [Message Encoding/Decoding Pipeline](issues/05-message-encoding-decoding.md) — Separate Encoder/Decoder + FieldTypeRegistry, validate-first encoding, dedicated bitfield type, dict output, Decoder owns full frame→ID→unpack pipeline
- [Connection Manager](issues/06-connection-manager.md) — Single shared ConnectionManager wrapping TCP+serial, config-selected mode, dynamic serial port dropdown, same queue for status+frames, config-driven auto-reconnect with log visibility, no popups
- [Periodic Send & Logging](issues/07-periodic-send-and-logging.md) — Periodic send via tkinter.after(), ephemeral state, checkbox+interval UI per message. Single combined log per project (block format), configurable rotation, all traffic logged
- [Layout Persistence Detail](issues/08-layout-persistence-detail.md) — `ui.json` with version/geometry/log_view/panes(ratio), atomic save, minimal properties, ratio-based pane positions
- [Startup Sequence & Config Load Handling](issues/09-startup-sequence-config-load-handling.md) — Loading order protocol→connection→ui→tx-state, missing configs use defaults+log, invalid JSON skip+log with line, schema mismatch per-field defaults, unknown IDs show raw hex in log, first launch empty shell with create prompt, last-used project in separate app-state.json
- [Full MVP Spec](issues/10-full-mvp-spec.md) — Complete MVP implementation spec: queue.Queue seam, 9 modules in dependency order, 45 user stories, testing decisions, out of scope. resolved

## Implementation Tickets (tracer bullets)

- [11 — Scaffold + ConfigLoader](issues/11-scaffold-configloader.md) — resolved, `config_loader.py`
- [12 — ProtocolCodec](issues/12-protocol-codec.md) — resolved, `protocol_codec.py` (`step` constraint yok)
- [13 — Backend Pipeline](issues/13-backend-pipeline.md) — resolved, `connection_manager.py` + `parser.py`
- [14 — UI Skeleton + LED](issues/14-ui-skeleton-led.md) — resolved, `ui.py`
- [15 — Main Display + Traffic Log](issues/15-main-display-traffic-log.md) — resolved, split view ertelendi
- [16 — Send Area + Periodic Send](issues/16-send-area-periodic-send.md) — resolved, `ui.py` send/periodic
- [17 — Logging + Layout Persistence](issues/17-logging-layout-persistence.md) — resolved, rotation `ui.json:max_log_entries`
- [18 — TX State + Startup + Project Switching](issues/18-tx-state-startup-project-switching.md) — resolved, `main.py` App
- [19 — PyInstaller Packaging](issues/19-pyinstaller-packaging.md) — resolved, exe build edildi + çalıştı (temiz makine testi yapılmadı)

## Ticket'sız gelen iş

- TX/RX yön desteği (`direction` alanı), `simulator.py`, `configs/Test1/` — commit ff0866f
- [docs/protocol-json-howto.md](../../docs/protocol-json-howto.md) — protocol.json yazım kılavuzu

## Not yet specified

<!-- fog cleared — all items graduated into tickets 08 and 09 -->

## Out of scope

- Split TX/RX log view (#15) — mixed view yeterli, ihtiyaç doğarsa aç
- `step` constraint (#12) — hiçbir config kullanmıyor
