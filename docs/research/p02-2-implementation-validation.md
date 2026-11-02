# P02-2 uygulama ve kabul kaydı

**Tarih:** 2026-11-02. **Dal:** feat/p02-2-private-upload; development tabanı 50d68b1, P02-1 kapanışı 973cec5. **Durum:** Yerel temel uygulanıyor; remote producer/upload/live kabulü yoktur. ADR-0024/0025 Accepted; [hazırlık ve yetkili beş GET](p02-2-readiness-review.md) ayrı kanıttır. 200 CR geliştirme tavanı fiyat veya write yetkisi değildir.

## Adım 1 — P02-2d yerel plan sözleşmesi

Ayrı strict upload scope/root/manifest referansı/parameters/storage/grant/cost/plan ve approval wire'ı ile private application snapshot factory uygulandı. Literal canonical plan/approval fixture'ları; manifestin canonical encoded byte hash'i ile iç digest ayrımı; sıralı blocker reducer; exact yetki/maliyet scope ve en erken expiry; plan/intent/semantic binding digest'leri ve onay bağları doğrulanır. Prepared snapshot bile executable=false'tur; public caller proof/verified flag almayan kompozisyon henüz ürün CLI'sına bağlanmadı. Fixture grant/cost nesneleri ürün producer'ı değildir.

Mevcut local manifest ve execution/Recipe/jobs wire/digest'leri değiştirilmedi. Yerel tarama veya current authority bu pure factory'den uydurulmaz; factory yalnız trusted composition'ın yakalanmış girdisini seal eder. Kalıcı kayıt/CLI, sonraki P02-2e ve üst a/c kabullerindedir.

İlk uygulama kontrolü: yeni upload sözleşmesi + mevcut manifest ve core boundary kümesinde **420 passed / 2,78 s**; iki yeni kaynak strict mypy ve Ruff format/lint geçti. Son raw byte sınırı/constructed instance negatifleriyle hedefli küme **422 passed / 2,69 s** verdi; tüm src/scripts strict mypy **82 dosyada** geçti. **164 Markdown, 6 skill/27 kart** ve diff denetimleri geçti. Yeni kaynağa ait native referans henüz alınmadı. Adımın iki fresh review turu henüz tamamlanmadı; kart verified değildir.

## Kaynak ve ölçüm sınırı

Hazırlık aşamasındaki 375 arşiv ve üç mevcut v3 referans, o sırada değişmemiş eski runtime kaynağını doğruluyordu. Yeni src/test değişimi sonrası bu referanslar yeni kaynağın kabulü sayılmaz; paket sonunda yeni isimli fresh startup/jobs/dataset ve upload-native ölçümler alınır. Eski başarısız veya başarılı ölçümler ezilmez. Bu adımda tam takım/build/native veya yeni hesap çağrısı yapılmadı; dış create/link/format/storage/price kapıları korunur.


Adım 1 ilk kod commit'i **5d1ddcf**. Fresh R1 domain/state-contract (GPT-6 Astra/high) ve consumer/schema/evidence (GPT-6.1 Sol/high) incelemeleri kodda doğrulanmış bulgu bulmadı; her kol yeni 82 upload contract testini ayrıca geçti. İkinci kolun plan teslim metnindeki eski “ürün geliştirmesi/testi yapılmadı” P3 ifadesi doğrulandı; tarihsel hazırlık ile güncel local uygulama/beş GET ayrılarak düzeltildi. Henüz ikinci fresh tur kapanmadı.


Fresh R2 (a5e5ecc, önceki reviewer'lardan farklı GPT-6.1 Sol/high ve GPT-6 Astra/high) yeni doğrulanmış bulgu bulmadı. İki kol da 82 upload testini geçti; biri mevcut manifest/CLI/operation/core regresyonlarında 578 test ve 57 bağımsız negatif/immutability deneyi, diğeri 157 raw-wire ret probu yürüttü. Bu örtüşen kümeler tek toplam test sayısına eklenmez. R2'nin ad hoc harness'ında yanlış reseal edilen eksik digest kontrolü reviewer tarafından düzeltildi; ürün kodu değişmedi. **P02-2d verified** (çalışma dalında); sonraki state/storage ve gerçek upload kabulleri korunur.

## Adım 2 — P02-2e kalıcı transfer temeli

SQL-only V2 schema 7 boş transfer tablo/indeksleri; immutable plan/manifest ve tarihsel approval; create intent'inde namespace CAS; her aşamada tekil intent/immutable receipt; PID permit; current credential/epoch/generation/onay/input/authority/cost kapıları uygulandı. Aynı plan/operation lookup'ı ağ/credential/hash/onay gerektirmez ve ikinci permit vermez. Ayrılmış payload alanı, iki recovery/terminal kontrol slotu, read-only takeover, reset preview v4 ve yedi indeksli global frontier çalışır. Eski migration 1–6 SQL/checksum'ları değiştirilmedi. Generic jobs ve eski v2/v3 bakım wire tipleri korunur; yeni runtime reset v4 üretir.

Yeni integration kümesi **40 passed / 19,74 s**: gerçek SQLite/kill-before-ID/two-process arm, iki bağlantıyla credential değişimi, commit öncesi/sonrası ayrımı, bozuk full/warm graph, +366 gün UTC/reset, 386 intent'li fixture üzerinde dolmayan recovery rezervi, gerçek 128 plan/4.096 file kotası ve rollback. Fixture'ın 386 receipt'i gerçek provider kabulü değildir. Yeni bağımsız journal wire/negatif/hata sözleşme kümesi **44 testtir**; önceki birleşik 79-test koşusu geçti. Ek değişikliklerden sonra bu kümenin ve ilgili regresyonların son kontrolü yapılır.

Mevcut operation/execution/discovery/wire kümesindeki ilk **291 passed / 1 failed** koşusunda v4 reset text'inin v3'e özgü güvenlik açıklamasını atladığı saptandı; renderer v3/v4 için ortak açıklamayı ve transfer geçmişi notunu gösterecek şekilde düzeltildi. Sonraki state/core ve yeni model kümesinde **192 passed / 1 failed**, yeni schema 7 tablolarını içermeyen eski exact-table fixture beklentisiydi; fixture açık yeni tablo listesiyle güncellendi. Bu eski başarısız sonuçlar sonraki başarıya çevrilmez. Strict mypy src/scripts 87 dosyada; Ruff, 164 Markdown/6 skill/27 kart ve diff kontrolleri geçti.

Bu adımda public upload CLI/API, gerçek producer/provider adapter, storage/native ölçüm veya yeni hesap çağrısı yoktur. P02-2e hâlâ in_progress; ilk commit ve iki farklı fresh review turu/kapanış kanıtı aşağıya eklenecek. Remote/live/ücret kapıları açık, P02-2 verified değildir.

### Adım 2 fresh R1 ve düzeltmeler

İki bağımsız reviewer (GPT-6 Astra/high ve GPT-6.1 Sol/high) aynı read renewal P2'sini doğruladı; safety kolu ayrıca dolu kotada revoke P2'sini gösterdi. Güncel credential/read grant ile edinilen read lease, tarihsel plan scope'u yüzünden yenilenemiyordu. Read heartbeat açık güncel grant ve exact eski target/owner/project bağıyla doğrulanacak şekilde düzeltildi. Safety kolu normal repository çağrılarıyla gerçek 16.777.216-byte sınırını doldurup revoke sonrası 16.777.240 ve state_invalid sonucunu üretti; üretim cap'i değiştirmedi. Plan kaydında 16 KiB approval/revoke alanı ayrılmasıyla bu büyüme artık önceden bütçelenir; doluluk revoke'u engellemez. Kalıcı regresyonlar iki kimlik değişimini ve onay alanı büyümesini kapsar.

Her iki reviewer'ın ilk 84-test koşusu **83 passed / 1 failed** idi; 128-plan fixture kurulumu aynı 5 s store ömrüne dahil olduğu için yoğun eşzamanlı test yükünde state_busy verdi. Ayrı tekrarlar **1 passed / 4,43 s** ve **1 passed / 3,82 s**; ürün kapasite kusuru diye sunulmadı. Fixture hazırlığı ayrı 30 s test hazırlığına taşındı, gerçek overflow/rollback/full kontrolü yeni default 5 s store fazında kaldı. Ürün süre sınırı artırılmadı.

Parent capability/cache/maintenance/identity regresyonu **332 passed / 1 failed** verdi: her frontier sorgusunda schema taraması 500 VM-adımı kapısını 1.798'e çıkarıyordu. Tarihsel tablo seçimi tek bounded schema sorgusuyla yapıldı; yedi expiry araması ve özgün 500-adım eşiği korundu. Ayrıca ADR-0024'ün her arm'da aynı write owner lease'ini 150 s yenileme koşulu atomik arm'a taşındı; owner/fence/epoch/generation/mode CAS'i ve güncel DB lease süresi otoritedir. Salt heartbeat consent fingerprint'ini değiştirmez.

Düzeltmeler sonrası yeni journal/contract ve özgün yoğun frontier kapısı birlikte **89 passed / 20,61 s**. Ruff format/lint, src/scripts strict mypy **87 dosya**, **164 Markdown / 6 skill / 27 kart** ve diff kontrolleri geçti. İkinci fresh tur henüz kapanmadı; P02-2e in_progress ve remote/live/native kabulü açık kalır.

### Adım 2 fresh R2 ve güvenlik kapanışı

Farklı iki fresh reviewer 5eaf6dd üzerinde inceleme yaptı. Consumer/migration kolu (GPT-6.1 Sol/high) **272 passed / 5 deselected / 93,12 s** ve dolu v4 preview için API/text/JSON/NDJSON eşliği bildirdi; bulgu yoktu. Adversarial kol (GPT-6 Astra/high) **85 passed / 3 deselected / 27,65 s** ile iki gerçek kusur gösterdi: **P1**, başka PID'nin DB'den okuduğu lease ile sonraki stage'i arm edebilmesi; **P2**, confirm öncesi metadata gözleminin başarı kanıtı kabul edilmesi. Bunlar yayımlanmış development kodu değil, bu dalın henüz kapanmamış yerel adımıydı.

P1 için admission'da yalnız ilk başarılı çağrıya verilen immutable volatile `TransferWriteAccess` eklendi: rastgele nonce, operation/initial-owner bağı, issuer PID ve ilk monotonic deadline. DB yalnız nonce özetini tutar; show ve existing admit claim üretemez. Her write owner kapısı exact claim/PID/özet/deadline eşliğini ister. Fork, yeniden repository açma, aynı ID'lerle başka claim kurma, copy/pickle ve deadline uzatma negatifleri; aynı ilk process'te iki connection/thread'in aynı stage yarışında yalnız bir intent üretmesi doğrulandı. Önceki iki-process testi restart'a yanlışlıkla izin verdiği için artık iki child'ın da write reddini sınar; legitimate aynı-process yarış ayrı testtir.

P2 için aynı clock neslinde proof gözleminin son confirm'den sonra olması hem verified yazımında hem graph doğrulamasında zorunlu oldu; tam terminal digest'i yeniden hesaplanmış eski proof da reddedilir. Predecessor receipt → sonraki intent kronolojisi de denetlenir. Reset/clock nesilleri arasında eski yanlış UTC karşılaştırılmaz; güncel read grant ve aynı neslin recovery marker'ı yeni gözlemin alt sınırıdır. +366 gün yanlış saat geçmişi sonrası fresh read verification testi bu kurtarma yolunu ayrıca kapsar.

Claim ve zaman düzeltmelerinin ilk birleşik contract/journal koşusu **94 passed / 24,68 s** verdi; ek future-clock recovery testi ayrıca kontrol edildi. Bu fixlerin bağımsız teyidi ve kart kapanışı henüz bu satırda tamamlanmış sayılmaz. Native/paket/son CI ve bütün remote/live kabulleri P02-2c'de kalır; yeni hesap çağrısı yoktur.
