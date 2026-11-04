---
id: P02-2a
phase: P02
status: draft
size: L
depends_on: [P02-0a, P02-0d, P02-1]
capabilities: [C03, C12, C13]
---
# P02-2a — Private oluşturma planı ve kalıcı işlem

**Tarih:** 2026-11-02. L kapsam [paket planındaki](../p02-2-delivery-plan.md#adımlar-ve-review-döngüsü) 1–3 S/M review adımlarına bölünmüştür; tek kod adımı değildir. ADR-0024/0025/0026 Accepted; gerçek producer/wire ve bütünleşik kart kabulü açıkken üst kart draft kalır.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı exact owner/proje ve güncel yerel içerikle private create niyetini planlar, digest ile onaylar; kalıcı operation ID'si olmadan dış etki başlamaz. Yerel plan/journal ve v2 politika temelleri çalışma dalındadır; gerçek provider producer/public yüzey d–w dilimlerinde yerel verified; üst teslimin nihai kabulü açıktır. Discovery izin üretmez.

## Giren ve girmeyen kapsam

Ayrı immutable upload planı/manifest, güncel onay/revoke, 6→7 state/migration, kapasite ve aşama primitive'leri, gerçek create/link producer/codec girer. Upload byte gönderimi P02-2b, restart read reconciliation ve paket kapanışı P02-2c'dir. ForgeLM/eğitim, browser JWT, public görünürlük, silme, version/freeze, imported proof/verified flag ve eski execution wire değişimi girmez.

## Bağımlılıklar ve kararlar

P02-0a/d PR #12/9f30fd2 ve P02-1 PR #13/50d68b1 ile development'tadır. [ADR-0024](../../decisions/0024-durable-dataset-transfers.md) ve [0025](../../decisions/0025-isolated-storage-streaming.md) Accepted — 2 Kasım kullanıcı review düzeltmeleri sonrası yerel uygulama yetkili. [ADR-0026](../../decisions/0026-explicit-unverified-transfer-attempts.md) default verified_only kapısını korur; yalnız explicit_attempt v2 risk/onay/current kurallarıyla attempt_ready olabilir. [Gerçek tüketici referansı](../../reference/platform-upload-consumer.md) endpoint/owner/project/private oracle'ıdır; hiçbir mod wire kapısını veya bilinen reti atlamaz.

## Sözleşme ve uygulama sınırı

Kanonik yeni [transfer referansı](../../reference/dataset-transfer.md) uygulama öncesi exact DTO/Python imzası/CLI argümanı/error tetik/exit/DB alanı düzeyine tamamlanır. Domain strict modelleri ve bağımsız literal byte/digest vektörleri; application kullanım senaryoları; adapter SQL/file/Platform; CLI parse/render/composition olur. Eski Plan/Execution/Recipe/Result/jobs biçimleri korunur. Tüm dosya listesinin hash bağını kapatmadan plan hazırlanmış sayılmaz.

## Kabul

1. Canonical request/plan/manifest ve onay byte/digest oracle'ları literal fixture ile bağımsızdır; duplicate/extra/wrong type/bool/nonfinite/version/root/128+ dosya/byte sınırı retleri sıfır etkilidir. Sır/env/tag/K plan, DB veya çıktı değildir.
2. Owner/project/private bildirilen alan eşliği aynı credential/hedefte denetlenir; görünürlük/digest onayı/UUID permission değildir. Bilinen ret veya uyuşmazlık her modda etki öncesi durur. Verified_only tam gerçek grant/cost ister; explicit_attempt bilinmeyen authority'yi risk ve unpriced seçimini ayrı onayla taşır. Prepared ve attempt_ready aynı iddia değildir.
3. Prepare'da credential/epoch/clock/input ve niyet bağı, approve'da saved plan/güncel doğrulama/onay CAS'i, admission'da aynı etkin approval, effect arm'da ayrıca current owner/fence/lease karşılaştırılır; iki süreçli rotation/revoke/reset **intent commit öncesinde** olursa yeni permit/port sıfırdır; intent önce commit etmişse son kontrol–HTTP arası duraklamada mevcut tek permit'in çağrıya ulaşabileceği ayrı oracle'dır. Eski sahibin sonraki state yazısı/yeni permit'i reddedilir; env re-resolve yoktur.
4. Plan başına tek transfer, namespace/name niyeti başına kalıcı create bağı ve aşama başına tek intent vardır. Concurrent start tek kayda yakınsar; commit/receipt belirsizliği ID'yi korur ve ikinci create/link açmaz.
5. Eski migration/checksum/record/wire golden'ları korunur; SQL-only yükseltmede yeni tabloların boşluğu, eski payload/checksum ve frontier eşliği ayrıca kanıtlanır. Yeni full/hot validator, quota sayaçları, global expiry index/formülü, preview fingerprint ve reset bütün transfer tüketicilerini kapsar; restore yasağı korunur. Bozuk kayıt yeni epoch ile aklanmaz.
6. 128 plan/operation, 4.096 global file/16 MiB canonical payload sınırı, son intent kapasite rezervi ve dolu sahipsiz işin read/reset toparlanması geçer. Yoğun yeni state/migration mevcut 5 s kontrol bütçesinde başarılı referans kabulünü ayrıca sağlar; timeout ret testi başarı ölçümü değildir.
7. Kullanıcı private create + **ayrı** project link etkisini ve kalacak kaynağı onay özetinde görür. Yalnız create HTTP 2xx, eksik/wrong-parent yanıt veya link belirsizliği tamamlanmış upload diye sunulmaz.

## Doğrulama

Contract/state/process/TLS ve CLI/Python pozitif/ret testleri; format/lint/strict type, doküman/skill/diff denetimleri. Yerel kayıt adımlarında fixture authority ürün backend'i yapılmaz. Remote codec kabulü gerçek tüketici sözleşmesine ve scoped live yetkisine bağlıdır; authority bilinmezliği yalnız ADR-0026 açık yolunda risk kalabilir. [Paket planı](../p02-2-delivery-plan.md) her alt adım commit+iki fresh review ve final kurulum/native/CI işini bağlar.

## Teslim kaydı

D–w alt kartlarının kodu, ortak provider/API/CLI ve her dilimin iki fresh review turu çalışma dalında tamamlandı. [R5 canlı kabulü](../../research/p02-2-implementation-validation.md#4-kasım--r5-tam-canlı-metadata-kabulü) iki farklı içerikli PNG ile tam 8 accepted aşama ve exact metadata sonucu verdi. [07 ölçümü ve ortam etiketi reddi](../../research/p02-2-implementation-validation.md#4-kasım--pr-review-kapanışı-ve-nötr-07-kaynak-kabulü) startup/jobs/dataset/raw/upload süre/bellek kapılarını geçti; exact disk etiketi nedeniyle reference verifier’ları reddetti, 08 beklenir. Eski partial/unknown canlı denemeler ve başarısız ölçümler korunur; metadata sonucu yetki/fiyat/uzak byte kanıtı değildir.

Üst kart, son üç ortam CI/altı temiz kurulum ve yeni Linux çıktılarının kalıcı saklanması kapanana kadar draft kalır. [Kanonik kabul kaydı](../../research/p02-2-implementation-validation.md) ve [current](../current.md#sıradaki-iş-ve-kalan-kapsam) gerçek kalan işi gösterir; P02-1 veya eski bir kaynak sonucu bu kabulün yerine sayılmaz.
