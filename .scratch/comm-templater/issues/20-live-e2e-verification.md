Status: resolved
Type: task
Blocked by: 11, 12, 13, 14, 15, 16, 17, 18

# 20 — Canlı E2E Doğrulama

**What to build:** MVP'nin gerçek uygulamada canlı doğrulanması — simülatörle TX/RX turu, layout + tx-state restore, mid-session proje değiştirme. O ana kadar yalnızca birim testleri ve `verify_*` bileşen testleri vardı; gönderme/decode yolu canlı hiç çalıştırılmamıştı.

**Status:** resolved — 3 bug bulundu ve düzeltildi, iki yeni doğrulama scripti eklendi

## Ne eklendi

- `verify_e2e.py` — `simulator.py`'ı subprocess olarak `configs/Test1` ile ayağa kaldırır, gerçek `App`'i kurar (gerçek ConnectionManager/Parser/Codec/TrafficLogger/tkinter), Send butonunu `invoke()` eder, RX cevabını bekler. Doğruladıkları: LED/status bar, traffic log'da 1 TX + 1 RX satırı, tab'da decode (device_id/temperature/mode), `comm.log` blokları, periodic send start/stop (200 ms, durunca gerçekten duruyor). `mainloop` yerine `root.update()` pompası → lineer assert'ler. Test1'in `ui.json`/`tx-state.json`/`comm.log`'unu yedekler, sonunda geri yazar.
- `verify_session.py` — Part A: 980x640'a resize + sash taşı + alan doldur → kapat → `ui.json`/`tx-state.json` diske yazıldı mı → yeniden aç → geometry/oran/alan geri geldi mi. Part B: geçici `configs/ZZTemp` projesi yaratır, combobox üzerinden mid-session geçer, codec/parser/logger/send-area/tx-state/ui_cfg'nin swap edildiğini ve kapanışta yeni projenin `ui.json`'ının ezilmediğini doğrular; sonunda projeyi siler.

## Bulunan buglar

1. **Her TX iki kere loglanıyordu** (`ui.py:_send_message`) — satır hem doğrudan `_add_log_entry` ile hem de queue turundan `_process_frame` ile ekleniyordu. Traffic view'da çift satır, `comm.log`'da tek blok. Fix: doğrudan ekleme kaldırıldı, tek kaynak queue turu.
2. **Kaydedilen pane oranı hiç geri yüklenmiyordu** (`ui.py:_build_panes`) — klasik `tk.PanedWindow`'da `sashpos()` yok (o `ttk.Panedwindow` metodu). Kod yalnızca `winfo_width() > 1` iken çağırdığı için build sırasında hiç çalışmamış, AttributeError de hiç patlamamıştı. Fix: `sash_place()`, `<Configure>` → `after_idle` ile ertelenmiş uygulama (handler içinde yerleştirmek PanedWindow'un kendi relayout'una yeniliyor), `<ButtonRelease-1>` ile kullanıcı sürüklemesini geri okuma. Oran artık pencere yeniden boyutlandıkça korunuyor.
3. **Proje değiştirince yeni projenin `ui.json`'ı eziliyordu** (`main.py:_switch_project`) — `ui.ui_cfg` ve `_ratios` swap edilmiyordu, kapanışta eski projenin `log_view`/`max_log_entries`/`panes` değerleri yeni projenin dosyasına yazılıyordu. Fix: `CommWorkbenchUI.apply_ui_config()` — ui_cfg + ratios + max_log_entries + geometry'yi yeni projeninkilerle değiştirir (layout per-project olduğu için pencere de yeni projenin geometry'sini alır).

Ek: kapanışta `_poll_queue`'nun bekleyen `after` timer'ı iptal ediliyor (destroy sonrası "invalid command name" gürültüsü).

## Kapsam dışı kalan

- Temiz (Python'suz) Windows makinesinde exe testi — bu makinede doğrulanamaz (#19'daki açık madde).
- Seri port yolu — donanım yok, yalnızca TCP canlı test edildi.
