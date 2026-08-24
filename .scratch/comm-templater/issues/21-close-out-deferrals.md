Status: resolved
Type: task
Blocked by: 12, 15, 17, 20

# 21 — Ertelenen İşlerin Kapatılması

**What to build:** "Out of scope" işaretli iki iş (#15 split log view, #12 `step` constraint) ile debt ledger'daki iki `SHORTCUT` (1-byte msg ID, log rotation'da tüm dosyayı yeniden yazma) kapatılsın.

**Status:** resolved — dördü de kapandı, ledger boş (`grep SHORTCUT:` → 0 marker)

## 1. `step` constraint (#12)

`ProtocolCodec.validate()` artık `step` kontrol ediyor: değer `min + k*step` olmalı (`min` yoksa 0'dan sayılır). Float alanlar hiçbir zaman tam basamağa oturmadığı için 1e-6 bağıl tolerans var. Test: `test_step_constraint` (min'den sayma + float toleransı dahil).

## 2. Split TX/RX log view (#15)

- `ui.json:log_view` = `"mixed"` (tek kronolojik Treeview) veya `"split"` (dikey PanedWindow, TX ve RX ayrı Treeview).
- Status bar'da mixed/split combobox → `ui_cfg`'ye yazar, `rebuild_panes()` çağırır, kapanışta `ui.json`'a düşer.
- Satırlar `_log_entries`'te tutuluyor (o zamana kadar ölü olan alan), view değişince yeniden basılıyor → geçmiş kaybolmuyor. Proje değişince `clear_display()` hem etiketleri hem trafiği siliyor (trafik ait olduğu projeye ait).
- Doğrulama: `verify_session.py` Part C.

## 3. SHORTCUT: 1-byte msg ID → `protocol.id_size`

`protocol.json`'da `protocol.id_size` (1/2/4, varsayılan 1, global byte order ile yazılır). Geçersiz değer `ValueError`. Dokunulan yerler: `protocol_codec` (`pack_id`/`unpack_id`, checksum bölgeleri `id_size`'a göre), `parser` (SCAN artık `id_size` baytlık pencereyi *peek* edip eşleşmezse 1 bayt kayıyor), `simulator.calc_frame_size`. Varsayılan 1 olduğu için mevcut configler etkilenmedi. Testler: `test_id_size`, `test_wide_id_framing` (baştaki çöp baytla resync dahil).

## 4. SHORTCUT: rotation'da tüm dosyayı yeniden yazma

`TrafficLogger._write_block` artık append-only; blok sayısı bellekte tutuluyor (mevcut dosya varsa ilk yazımda bir kez sayılıyor), yalnızca sayı `max_entries + COMPACT_SLACK`'i (100) aştığında dosya son `max_entries` bloğa sıkıştırılıyor. Mesaj başına maliyet O(1); önceden her mesajda tüm dosya okunup yeniden yazılıyordu (1000 bloklu logda periodic send altında ciddi I/O).

**Semantik değişiklik:** `max_log_entries` artık sert tavan değil, sıkıştırma hedefi — dosya geçici olarak `max + 100` bloğa kadar çıkabilir. `test_rotation` bu invariant'a göre güncellendi (`test_rotation_survives_reopen` de eklendi: yeni bir logger mevcut dosyanın üstüne yazınca sayaç sıfırlanıp dosya sınırsız büyümemeli).

## Not

`docs/protocol-json-howto.md`'ye `protocol.id_size` ve field `step` satırları eklendi.
