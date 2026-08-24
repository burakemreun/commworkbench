Status: resolved
Type: task
Blocked by: 12, 13, 14, 22

# 23 — Adresli Header Formatı + Bağlantı Çubuğu

**What to build:** (1) `[gonderen_id][alan_id][mesaj_id][boy]` gibi çok alanlı, config'te
tanımlı header desteği — parser byte byte kayarak header'ın *tüm* alanlarını doğrulasın.
(2) Arayüzde düzenlenebilir bağlantı çubuğu (Type / Host / Port / Mode / Connect).

**Status:** resolved

## 1. `protocol.header` — config'te tanımlı header

Önceki wire format sabitti: `[msg_id (id_size bayt)][payload][checksum]` ve msg ID
offset 0'da olmak zorundaydı. Adresli protokoller ifade edilemiyordu.

`protocol.header` artık sıralı bir alan listesi; her alan opsiyonel bir `role` taşır:

| role | anlamı |
|------|--------|
| `msg_id` | mesaj tipi (zorunlu, tam bir tane) |
| `src_addr` | gönderen — mesajın `src` alanıyla eşleşmeli |
| `dst_addr` | alan — mesajın `dst` alanıyla eşleşmeli |
| `length` | payload boyu — encode'da otomatik yazılır, decode'da doğrulanır |
| *(yok)* | düz bayt, `constant` ile sabitlenebilir (sync marker vb.) |

`length` alanı `counts` alır: `"payload"` (varsayılan) veya `"after_self"` (kendinden
sonraki tüm baytlar: kalan header + payload + checksum).

`protocol.nodes` bir isim→adres tablosu (`{"PC": 1, "DSP": 2}`); mesajlar `"src": "PC"`
yazabilir. Ham sayı da kabul edilir.

`header` yoksa eski davranış aynen sürüyor (`id_size` baytlık tek `msg_id`), yani mevcut
configler ve testler etkilenmedi.

## 2. Parser: header doğrulama

SCAN artık `header_size` baytlık pencereyi peek edip **her role'ü** kontrol ediyor.
Bilinen bir ID tek başına yetmez — aynı ID iki yönde de gider.

- ID bilinmiyor ya da `src`/`dst` tutmuyor → header burada tutmuyor, 1 bayt kay. Atlanan
  baytlar eskisi gibi `unknown` girdisi olarak trafik loguna düşüyor.
- Adresleme tuttu ama `length` tutmadı → **error** girdisi (tanınan bir mesajın yanlış
  boyu hat gürültüsü değil, protokol hatası), sonra 1 bayt kayıp resync.

Tek ID'ye birden çok mesaj bağlanabildiği için (aynı komut iki düğüme) `_id_to_msg` artık
aday listesi tutuyor; header'ı tutan ilk aday kazanıyor.

`ProtocolCodec.decode()` de aynı kontrolü yapıyor, böylece doğrudan decode çağıran
simülatör de sessizce yanlış çözmüyor.

## 3. Örnek config: `configs/PcDsp/`

Kullanıcının verdiği protokol: PC=1, DSP=2, checksum kapalı.
`CitIstek` → `01 02 01 00`, `CitCevap` → `02 01 02 04 aa bb cc dd`.
Ayrıca PC tarafının parametrik sorgusu için `ParamOku`/`ParamCevap` çifti.

## 4. Bağlantı çubuğu

Pencerenin en üstünde `Connection` LabelFrame: `Type` (tcp/serial), tcp için
`Host`/`Port`/`Mode` (client/server), serial için `Port`/`Baud`, sağda Connect/Disconnect
düğmesi. Değerler `connection.json`'dan yükleniyor, düğme canlı `ConnectionManager`'ı
sürüyor, kapanışta atomik olarak `connection.json`'a yazılıyor. Proje değişince
`apply_connection_config()` ile yeni projenin dosyasına bağlanıyor.

Geçersiz port/baud bağlanmayı engelliyor ve dosyaya yazılmıyor — status bar'da hata.

`Baud` ve `Port` (COM) kutuları bilerek `readonly` **değil** — listede olmayan bir değer
elle yazılabiliyor. Baud listesinde `9600..921600` var. COM kutusu açıldığında
(`postcommand`) `serial.tools.list_ports` ile makine taranıyor, üstüne gelince tooltip'te
port açıklaması + üretici + hwid görünüyor; taranamayan/typed bir port için "not detected
on this PC" yazıyor. pyserial kurulu değilse tarama boş dönüyor, kutu yine yazılabilir.
Tooltip için tkinter'da hazır bir şey yok, `_Tooltip` (~25 satır) eklendi.

## 4b. Ham byte gönderme

Send area'nın en üstünde `Raw Bytes` satırı: hex kutusu + Send (Enter de gönderiyor).
Mesaj tanımından tamamen bağımsız — `01 02 01 00`, `0102 0100`, `0x01,0x02` hepsi kabul.
Geçersiz hex bağlanmadan reddediliyor. Trafik loguna ve `comm.log`'a `[RAW]` adıyla TX
olarak düşüyor. tx-state'e kaydedilmiyor (anlık iş, mesaj adı değil).

## 5. Simülatör

`calc_field_size` kopyası silindi (codec'in `field_size`/`payload_size`'ı var), header'a
göre çerçeve boyu hesaplıyor, cevap alanlarını protokolden üretiyor (artık sensör
demosuna gömülü değil), config'in ilk tx/rx çiftini seçiyor.

## Doğrulama

- `tests/test_parser.py`: `test_addressed_header_wire_format` (kullanıcının verdiği tam
  baytlar), `..._rejects_wrong_sender`, `..._length_mismatch_is_an_error`,
  `..._resync_after_garbage`, `test_xor_checksum_over_whole_frame`,
  `test_length_counts_after_self`
- `verify_session.py` Part D: bağlantı çubuğu yükle/toggle/geçersiz port/port taraması +
  tooltip/elle yazılan baud/kaydet/geri yükle
- `verify_e2e.py`: ham byte gönderme — bozuk hex reddi, elle yazılan geçerli çerçeveye
  cihazın cevap vermesi, `[RAW]` satırının loga ve `comm.log`'a düşmesi
- `verify_e2e.py` (Test1, eski format) ve canlı PcDsp E2E (simülatör + gerçek
  ConnectionManager + Parser): `02 01 02 04 <4 bayt>` çözüldü

## Not

`docs/protocol-json-howto.md`: `protocol.header`, `protocol.nodes`, mesaj `src`/`dst`,
Örnek 4 ve `checksum.covers` satırının koda göre düzeltilmesi.

## Bilinen sınır

Bir mesajın payload boyu sabit varsayılıyor (`boy` alanların toplamına eşit olmalı).
Aynı mesajın gerçekten değişken uzunlukta geldiği bir cihaz çıkarsa `bytes` alanına
`size_from: "<length alanı>"` gerekir.
