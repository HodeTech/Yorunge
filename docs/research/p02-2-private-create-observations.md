# P02-2 ilk private oluşturma gözlemi

**Tarih:** 2026-11-02. **Sonuç:** İlk küçük pilot kontrollü durdu; upload veya P02-2 kabulü değildir. Kullanıcının scope/tarife bulunamadığında denemeyi ve 200 CR aşımını kabul eden sonraki talimatı kapsamındadır. [Yetki/method hazırlığı](p02-2-readiness-review.md#küçük-araştırma-pilotunun-yürütücü-hazırlığı), [frozen kaynak ve testler](probes/platform-upload-pilot-20261102/README.md), [receipt](p02-2-private-create-observations.json).

| Çağrı | HTTP | Tüketilen raw gövde | Sonuç |
|---|---:|---:|---|
| Seçilmiş private proje GET | 200 | 395 byte | Beklenen ID/private ve owner/org türleri kontrol edildi |
| Private VISION dataset POST | 201 | 842 byte | Canonical dataset ID alındı; yalnız private journal'a kaydedildi |
| `GET /datasets/{id}` | 405 | 0 byte | Hata gövdesi tüketilmeden kapatıldı; akış durdu |

**3 HTTP denemesi / 2 mantıksal GET / 1 etkili istek / 1.237 tüketilen byte / 1,159029 s.** Proje link, presign, PUT ve confirm sayıları **0**; sentetik 237 byte görsel yüklenmedi. Yeniden create/otomatik retry/DELETE/terms accept yapılmadı. Oluşturulan kaynak hesapta kaldı; bilinen ID ve üretilmiş ad private journal'da saklıdır. Bu rapor ID, gerçek ad, principal, hesap/profil alanı veya ham gövde yayımlamaz.

### Yöntem hatası ve açığa çıkan rota

Helper'ın `GET /datasets/{id}` detail varsayımı kamu istemcisinin gerçek okuma rotasıyla yeterince eşlenmemişti. Bu test fixture'ında da aynı varsayım vardı; 67 çevrimdışı test ve iki review turu provider uyumluluğunu kanıtlamadı. Kamu dataset istemcisindeki `getBySlug(username, slug)` bunun yerine **`GET /datasets/{username}/{slug}`** kullanır. 405 yalnız denenen metoda/rotaya ilişkin gözlemdir; API-key ile bütün dataset okumalarının desteklenmediği veya anahtarın yetkisiz olduğu sonucu çıkarılmaz. Private create 201 de genel create/link/upload yetkisi veya maliyet garantisi değildir.

İlk belirsizlikte durma kuralı uygulandı. Frozen yürütücü tekrar çalıştırılmaz ve canlıdan sonra değiştirilmez. Aynı oluşturulan kaydın API-key okunabilirliği için owned listesinden exact ID'yi bulma, o cevaptan gelen username/slug ile detail ve exact ID my-role okumaları ayrı dar salt okuma takibinde hazırlanır; yeni write/upload/cleanup yoktur. Yeni kaynak/test ve ayrı çağrı yetkisi kapanmadan bu takip çalıştırılmaz. Bu takip ilk pilotu geriye dönük başarılı yapamaz.

### Bütünlük ve kabul sınırı

Kaynak commit `fdef9901fa2258e48671a8eb37dd402ae19c62d1`; source_unchanged=true. Probe SHA-256 `c7a192c3ac9b5f25613fe817d4138951d18814376058705ae141f375e3e984cf`; test SHA-256 `6159e47fdae207a52034689918478e759965e5c74045790b3614f77801ca6fe9`. Receipt **1.031 byte**, SHA-256 `0037e574f193476498b1bc1fed945adfb5a246177c8c4a76ecfd4b2518613a9e`; private receipt ile byte eşliği ve iki kaynak hash'i doğrulandı. Sayaç tüketilen body chunk'larını ölçer; header/TLS ve okunmadan kapatılan 405 gövdesi dahil değildir.

Tarife, kullanılan CR, süreğen storage maliyeti ve server spending cap bilinmiyor; bakiye/ledger endpoint'i çağrılmadı. `authority_verified=false`, `pricing_verified=false`. Public ürün prepared/authority/cost-bound kapıları, gerçek project link, upload wire ve bütünleşik/native/CI kabulü açık kalır. P02-2a/b/c ve epik draft; d/e/f yalnız yerel çalışma dalında verified'dır.
