Status: resolved
Type: task
Blocked by: 12, 15, 21

# 22 — Doküman/Kod Uyuşmazlıkları

**What to build:** Kılavuzun ve ticket'ların iddia ettiği ama kodda karşılığı olmayan üç şey kapatılsın: byte order hiyerarşisi (`"inherit"` bug'ı), bilinmeyen msg ID'lerin loglanması, `bytes` + `constant` field tipleri.

**Status:** resolved — üçü de kapandı, testleri var

## 1. Byte order hiyerarşisi + `"inherit"` bug'ı

**Bug:** `_field_endian` alanın değerini olduğu gibi `_endian_char`'a veriyordu; `"inherit"` `ENDIAN_MAP`'te olmadığı için sessizce `<` (little) oluyordu. Big-endian protokolde `inherit` işaretli alan tel üzerinde ters gidiyordu. Encode/decode aynı yanlışı yaptığı için roundtrip testleri göremiyordu — yalnız gerçek cihaz fark ederdi.

- `_field_endian(field_def, msg_def)` artık field → message → protocol sırasıyla çözüyor; `"inherit"` bir sonraki seviyeye düşüyor. Message seviyesi ilk kez gerçekten çalışıyor (ticket 12'de "yapıldı" diye işaretliydi, kodda yoktu).
- `_endian_char` bilinmeyen değerde `ValueError` atıyor — sessiz default yok. Hatalı config send'de kırmızı hata satırı / RX'te error bloğu olarak görünür, uygulama düşmez.
- Test: `test_endianness_hierarchy` (message override, inherit'in düşmesi, field override, bozuk değer).

## 2. Bilinmeyen msg ID'leri artık görünür

**Bug:** Parser SCAN'de eşleşmeyen baytı sessizce atıyordu. MVP story #34 ve ticket 15 aksini iddia ediyordu.

- Parser atlanan baytları `_skipped`'de biriktirip senkron olunca (veya tampon bitince) tek bir `{"type": "unknown", "raw_hex": ...}` olayı yayıyor.
- UI bunu `[UNKNOWN]` satırı olarak trafik log'una ve `comm.log`'a yazıyor. Ayrı "Unknown tab" yok — spec "raw hex in log" diyor, kutu ona göre düzeltildi.
- Test: `test_unknown_id_reported` (çöp + arkasından geçerli frame), `verify_e2e.py`'de canlı adım (queue'ya `ab cd` enjekte → UI satırı + comm.log bloğu).

## 3. `bytes` ve `constant` field tipleri

Kılavuzda belgeliydi, kodda yoktu: `bytes` → `ValueError: unknown type: bytes`, `constant` → `struct.error`. Kılavuz AI'ya protocol.json yazdırmak için kullanıldığından aktif tuzaktı.

- `bytes`: `size` kadar sabit dizi. Encode `bytes`/`bytearray`/`list[int]`/hex string (`"de ad be ef"` — send form'un yazdığı) kabul ediyor, kısaysa sıfırla dolduruyor, uzunsa kesiyor (doküman semantiği). Decode `bytes` döner; UI değerleri hex olarak gösteriyor (`_fmt_value`).
- `constant`: encode kullanıcı girdisini yok sayıp sabiti yazar, decode baytları atlayıp sabiti döner, `validate()` sabit alanları kullanıcı girdisi gibi denetlemez. Send form'da sabit alanlara kutu açılmıyor (girdi değiller).
- `ProtocolCodec.field_size()` ortak boyut hesabı oldu; `parser._field_size` kopyası silindi (parser bytes alanlarını da böyle ölçüyor, yoksa state machine tıkanırdı).
- Test: `test_bytes_type`, `test_constant_field`, `test_bytes_and_constant_framing` (parser seam'i).

## Not

`docs/protocol-json-howto.md`: message tablosuna `endianness` satırı, field `endianness` satırına çözüm sırası, `id` satırı `id_size`'a göre güncellendi, bytes'a hex string satırı eklendi.
