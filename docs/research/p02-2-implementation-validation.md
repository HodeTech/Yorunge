# P02-2 uygulama ve kabul kaydı

**Tarih:** 2026-11-02. **Dal:** feat/p02-2-private-upload; development tabanı 50d68b1, P02-1 kapanışı 973cec5. **Durum:** Yerel temel uygulanıyor; remote producer/upload/live kabulü yoktur. ADR-0024/0025 Accepted; [hazırlık ve yetkili beş GET](p02-2-readiness-review.md) ayrı kanıttır. İlk 200 CR tutarı sonraki kullanıcı yanıtında küçük canlı deneme için esnetildi; bu tercih fiyat/authority kanıtı değildir, canlı yazma henüz yapılmadı.

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

37cbc6e düzeltme commit'i iki R2 reviewer tarafından ayrıca teyit edildi. Consumer kolu **70 passed / 25 deselected / 13,24 s**; eksik/düzenlenmiş claim digest, predecessor kronolojisi, preview/quota ve reset epoch davranışında yeni kusur yoktu. Adversarial kol özgün fork/reopen ve stale-proof reproducer'larının artık reddedildiğini, güncel proof'un succeeded olduğunu doğruladı; **92 passed / 3 deselected / 21,59 s** bildirdi. Ek **P2** olarak `NaN` total deadline'ın min/comparison üzerinden intent commit'ine ulaşabildiğini saptadı. Sonlu exact int/float (bool hariç), overflow ve geçmiş deadline kontrolü arm transaction'ından önce eklendi; yedi negatifte intent/permit sıfırdır.

Son birleşik journal/contract/özgün indexed-frontier kümesi **103 passed / 29,61 s** verdi. Bu sonuç önceki başarısızlıkları silmez ve native/paket/CI kabulü değildir. Kullanıcının yeni küçük canlı deneme/200 CR aşım tercihi plan/hazırlık kaydına işlendi; hiçbir hesap çağrısı yapılmadı. Son deadline fix'inin teyidi ve kart/current kapanışı sonraki kayıttadır.


Adım 2 son kapanış: adversarial reviewer b2a804d üzerindeki özgün NaN reproducer'ını ve geçerli/geçersiz deadline yollarını bağımsız tekrar etti: **9 passed / 49 deselected / 3,40 s**, yeni bulgu yok. NaN/±inf/bool/string/null/overflow → invalid_request, geçmiş deadline → execution_timeout, her hatada operation ID korunarak sıfır intent/latch false; geçerli deadline ile permit ve store doğrulaması geçti. Önceki P1/P2 kapanışları korundu. **P02-2e çalışma dalında verified**; iki fresh tur/fix/commit ve son bağımsız teyit tamamlandı. Sonraki bağımsız kart P02-2f; gerçek remote/live/paket/native/CI teslimi hâlâ açık ve epik draft'tır.


## Adım 4.1 — P02-2f hedef/request ve descriptor source

P02-2e kapanışından sonra f iki gerçek kod dilimine ayrıldı; her biri commit+iki fresh tur ister. Bu ilk dilim `StorageTarget`/`StorageRequest` kapalı auth/path/query/MIME/SHA-256/header ve response-limit metadata'sını, aynı task/PID/thread'de lazy descriptor `DescriptorByteSource` uygulamasını getirir. Client/DNS/peer backend ve gerçek TLS storage request 4.2'dir; burada uygulanmış iddia edilmez. Ürün provider codec/CLI/yazma pilotu yoktur.

Kaynak construction'da I/O yapmaz; no-follow root/ancestor/leaf, regular-file/size, 1 MiB pull, byte/hash, EOF'ta yeniden path/kimlik/stat/hash denetimi ve hata/cancel/context-close cleanup çalışır. Explicit iterator async-generator finalizer'ı yaratmaz. Erken normal close iptal üretmez; gerçek Task.cancel yayılır. Signed URL/private source repr ve pickle'a girmez. Shared `execution_timeout` mesajı 30 s execution'a özgü yanlış yönlendirmeden arındırıldı; numeric execution/transfer sınırları kendi sözleşmelerinde aynen kaldı.

Storage policy+gerçek source ilk kümesi **88 passed / 0,31 s**; Unicode/control/yanlış tip ekleri sırasında encoded bidi negatifinin ret edilmediği saptandı (**91 passed / 1 failed**); URI denetimi mevcut canonical `safe_text` control/bidi kuralına bağlandı. Son storage+mevcut upload plan kümesi **174 passed / 0,30 s** (82 eski upload plan testi dahil); src/scripts strict mypy **90 dosya** ve ilgili Ruff geçti. Bu bir native RSS/throughput, ağ veya canlı hesap kabulü değildir. 4.1 fresh review turları henüz kapanmadı; f in_progress.

### Adım 4.1 fresh R1

İki fresh reviewer 6ecb4aa'yı okudu. Files/cancellation kolu (GPT-6 Astra/high), **92 passed / 0,18 s** ve bağımsız read/close EIO, deadline, gerçek Task.cancel, thread/task ve EBADF FD kontrollerinde kusur bulmadı. Policy kolu (GPT-6.1 Sol/high), **92 passed / 0,20 s** sonrası **P2** gösterdi: path güvenlik doğrulaması dört decode katmanına bakarken literal sır denetimi yalnız ilk katmana bakıyordu. `a` ve `eight-byte-secret` çift percent-encoding ile bu denetimi geçiyordu.

Düzeltmede kabul edilen her raw/path decode katmanı aynı literal kuralıyla taranır; query'nin ayrı opaque/tek-decode politikası korunur. Bağımsız `unquote` oracle'ıyla iki secret uzunluğu ve 1–4 kat encoding/negatif pozitif çiftleri eklendi. Son policy/source **100 passed / 0,22 s**; Ruff ve src/scripts strict mypy **90 dosya** geçti. Expiry constructor'ın canonical format/presence kapısı ile clock'a bağlı freshness/5 s marjının 4.2 gerçek request kapısı olduğu kanonik bölümde açıklaştırıldı; 4.1 expired URL gönderme desteği değildir. Henüz ikinci fresh tur tamamlanmadı.

Fresh R2, farklı iki reviewer ile f10292c üzerinde tamamlandı. Policy/consumer kolu (GPT-6 Astra/high) **100 passed / 0,17 s**, files/source kolu (GPT-6.1 Sol/high) source/policy/eski input primitive kümesinde **142 passed / 0,82 s** ve altı bağımsız short-read/EIO/deadline/cancel/PID/thread deneyi bildirdi. Yeni doğrulanmış kusur yok; R1 path/literal düzeltmesi kapandı. Bu örtüşen kümeler toplanmaz. **4.1 kod dilimi yerel olarak tamamlandı**; f henüz verified değil, sıradaki 4.2 client/DNS/peer/gerçek TLS entegrasyonudur. Aynı branch ve tek nihai PR akışı korunur.

## Adım 4.2 — P02-2f guarded network ve ortak storage client

`GuardedBackend/GuardedStream` bounded DNS sonucunu public IP politikasıyla denetler, seçilmiş numeric IP'ye bağlanır ve gerçek peer'i original SNI/certificate ile birlikte HTTP yazımından önce kontrol eder. `GuardedHttpTransport` HTTPcore'un [public async network backend](https://www.encode.io/httpcore/network-backends/) ve HTTPX'in [transport arayüzü](https://www.python-httpx.org/advanced/transports/) üzerinden tek pool'u korur; özel kütüphane alanı monkeypatch edilmez. Zaten transitive kurulu HTTPcore 1.0.9 doğrudan bağımlılık olarak bildirildi; offline lock'ta paket sürümü yükseltilmedi.

`TransferSession/TransferHttpxTransport` tek owned Runner/client/toplam iki slot üzerinde service ve storage paylaşır. Plan öncesi seçilmiş origin olmadan direct PUT yoktur; proxy yalnız aynı credential snapshot'ını doğru Platform hedefine taşır. Prepared URL/header eşliği, canonical expiry/5 s pay, source metadata snapshot'ı, bağımsız Content-Length/SHA-256 sayacı, 64 KiB raw response, no replay ve aynı-task cleanup gerçek TLS sınırında sınandı. Source sayacı provider kabulü değildir.

İlk network/storage/source/policy kümesi **186 passed / 17,25 s**; ek production private/mixed DNS, gerçek untrusted CA ve mutable source metadata negatifleri **7 passed / 1,87 s**. Eski session/request/HTTP/stream/core-boundary regresyonu **436 passed / 46,30 s**. Yeni TLS testlerinin geliştirme koşusunda eksik test `asyncio` import'u **23 passed / 1 failed** üretti; import düzeltildi, ürün hatası diye sunulmaz. Tamamlanmış önceki test çıktısı süreç oturumu kapandıktan sonra geri alınamadığı için kabul sayılmadı; yukarıdaki 186 testlik yeni koşu kaydedildi. Ruff, strict mypy **93 kaynak dosyası**, **164 Markdown / 6 skill / 27 kart** ve diff kontrolü geçti.

4.2 ilk commit sonrası iki fresh review turu henüz tamamlanmadı; f in_progress. Public upload komutu/provider codec/native RSS/build veya canlı yazma bu kabul değildir. Eski source-bound referanslar yeni kaynağa başarı diye kullanılmadı.

### Adım 4.2 fresh R1

31a6ec3 iki bağımsız eksende incelendi. Ağ kolu (GPT-6 Astra/high) bir **P2** doğruladı: numeric TCP adresi ilk DNS cevabıyken peer kapısı aynı cevap kümesindeki ikinci public adresi de kabul ediyordu. Private-IP bypass gösterilmedi; hata kanonik daha dar selected-IP eşliğindeydi. Consumer kolu da aynı ayrımı bağımsız gördü. Peer bağı yalnız seçilmiş IP'ye daraltıldı; ilk connect, TLS sonrası ve pool reuse için ikinci public DNS cevabının reddi üç bağımsız negatifle sabitlendi. Düzeltme sonrası network+gerçek TLS **96 passed / 18,63 s**; Ruff/strict mypy **93 dosya** geçti. İkinci fresh tur henüz tamamlanmadı.

R1 consumer kolu (GPT-6.1 Sol/high) ayrıca **193 storage / 18,78 s**, geniş legacy **557 / 76,86 s** ve bağımsız erken-200/FD/response/slot ret deneyi bildirdi; aynı exact-pin bulgusu ikinci kusur diye sayılmadı. İlk legacy komutunun yanlış dosya adı nedeniyle test çalıştırmadığı, düzeltilen komutun geçtiği kaydedildi.

### Adım 4.2 fresh R2

Farklı iki yeni reviewer 6c5e360'ı inceledi. Ağ kolu (GPT-6.1 Sol/high) **96 / 18,52 s** ve yeni bulgu yok bildirdi. Lifecycle kolu (GPT-6 Astra/high) **135 storage / 18,59 s**, **71 legacy / 21,86 s** ve bir **P2** doğruladı: ikinci expiry kontrolü deadline'ı kısaltınca dış asyncio zamanlayıcısı eski süreyi koruyordu. Gerçek TLS repro'da yeni kalan süre 0,1 s olmasına rağmen yavaş yanıtın son byte'ı 0,709 s'de okundu; ret yalnız context çıkışındaydı. Bu bloke OS I/O sınırı değil, cooperative timer hatasıdır.

Düzeltmede dış Timeout ikinci `_window` sonrasında yeni kalan süreye reschedule edilir. Gerçek TLS regresyonu yavaş 80-byte yanıtın tamamı okunmadan `transport_timeout`, kapalı source ve serbest pool doğruladı: **1 passed / 0,82 s**; Ruff/93 dosya strict mypy geçti. Bütün storage kümesi ve reviewer düzeltme teyidi henüz aşağıya eklenmedi; f in_progress.

Son storage/policy/source/network kümesi **197 passed / 19,35 s**; 164 Markdown, 6 skill/27 kart ve diff kontrolü geçti. R2 lifecycle reviewer özgün repro'yu 8eb1809 üzerinde tekrar yürüttü: **102 ms**, 30 byte'ın yalnız dördü okundu, yeni deadline sonrasında byte yok; tek request ve temiz source/slot/response. Etkilenen expiry/cancel/erken kapanış **7 passed / 4,71 s**; yeni regresyon yok. İki dilim ve her birinin iki fresh turu tamamlandı: **P02-2f çalışma dalında verified**. Provider, public UX, native, paket/CI ve live kabul hâlâ a/b/c kapsamındadır; uzak başarı veya development teslimi iddia edilmez.


## P02-2g — Exact-work maliyet v2

ADR-0026 kullanıcı bulguları, iki fresh belge revizyon turu ve koşullu onayla Accepted oldu (e58ea85). a8fbd7c exact-work/kapsam/dönem/storage modeli ve iki bağımsız literal fixture/digest'i ekledi; v1 modelleri/golden'ları değişmedi. 1 CR transfer-only veya dönem sonrası storage unknown kanıtı bütün-iş numeric bütçe garantisi değildir. Yanlış scope/manifest/root/parametre/storage/window/quantity bağı unknown'a yutulmadan reddedilir. Prod pricing source yoktur.

İlk iki contract dosyası 195 geçti; R1 maliyet kolu Astra/high, wire kolu Sol/high bağımsız 239 test geçti bildirdi; runtime kusuru yoktu. Wire kolunun test kanıtı iyileştirmesi 2c9aded ile kapandı: geçerli fixture'da aynı geçerli değeri tekrar eden duplicate ve yalnız whitespace ile byte aşımı sınanır; guard kaldırıldığında bu örnekler geçerli olur. Son cost/upload/transfer kümesi **241 passed / 0,32 s**. Ruff/strict mypy geçti. Farklı fresh R2 Sol/high ve Astra/high yeni doğrulanmış bulgu bulmadı; biri 241, diğeri 115 cost testini ve bağımsız scalar/semantic negatiflerini çalıştırdı. Örtüşen testler toplanmaz.

P02-2g çalışma dalında verified. Runtime v1 new-write yasağı j'nin atomik v2 geçişidir; bu kart saf domain modelidir. Public producer, gerçek fiyat/yetki, yeni hesap çağrısı, native/build/source CI kabulü yoktur; eski M5 kaydı yeni kaynak başarısı sayılmaz. H sıradaki dar uygulama birimidir.


## P02-2h — V2 plan, onay ve current modeli

Private snapshot factory, exact v2 policy reducer, approval acknowledgement/binding ve typed AuthorizationCheck/UploadObservation/UploadCurrentCheck eklendi. 96 literal beklenen matris 65 draft/2 prepared/11 attempt_ready/18 invalid durum içerir; 13 eligible durumun 9'u unpriced ack, 8'i authority ack ister. Literal plan/approval byte/digest vektörleri bağımsız JSON hesaplamasından üretilmiştir. Current null/partial→supplemental positive saved planı/approval'ı değiştirmez; eski baseline, bütün mevcut proof ve current action grant expiry'leri korunur. Gerçek grant veya fiyat backend'i eklenmedi.

İlk test geliştirme koşusu 39 passed/116 failed verdi: test helper ErrorCode'u Türkçe exception mesajında regex olarak arıyordu. Oracle .code alanını denetleyecek şekilde düzeltildi; ürün hata kodları değiştirilmedi. Ek current/expiry/wire sınırlarıyla son dört contract kümesi **410 passed**; src/scripts strict mypy **97 dosya**, ilgili Ruff başarılı. İki fresh kod review turu bu ilk kayıtta henüz tamamlanmadı; h in_progress. SQL union/new-write kapıları/producer/public CLI/live/native/build/CI sonraki kartlardadır.


H fresh R1: policy kolu Astra/high 96 Cartesian girişini ve oracle değerlerini bağımsız doğruladı; current kolu Sol/high 169 test ve üç ek dataset/my-role zaman negatifinde yeni kusur bulmadı. Policy kolunun P2'si yanlış confirmed_digest için approval_required/4 yerine normatif upload_plan_not_valid/2 gereğiydi; 7eacc8b ile düzeltildi ve ayrı regresyon eklendi. H son kümesi **170 passed / 0,41 s**. Farklı fresh R2 Sol/high ve Astra/high yeni bulgu bulmadı; her ikisi h+cost+v1 üzerinde **367 passed**, ikinci kol ayrıca on typed-current negatifini bağımsız doğruladı. Örtüşen sayılar toplanmaz. V1 source/golden değişmedi. P02-2h çalışma dalında verified; sıradaki i union/journal dilimidir. Gerçek provider/public/live veya son kaynak native/build/CI teslimi iddia edilmez.


## P02-2i — Versioned journal ve tam graph

Kapalı v1/v2 decoder, v2 record/control/verification ve immutable literal 11-stage graph eklendi. DDL/migration/checksum değişmedi. Versioned history/list/show/full validation ve reset aynı payload sürümünü korur. Legacy writer v2'yi v1'e çeviremez; V1 new-write yasağının atomik uygulaması j'de kalır. Başarı exact create/link+her dosya için presign/PUT/confirm kümesini ve tek accepted receipt'lerini ister; eksik intent, eş metadata ile doldurulamaz. Tam graph doğrulaması header/stage/control/proof sorumluluklarına ayrıldı.

İlk legacy journal geliştirme koşusu **90 passed/2 failed** idi: required_stages import'u eksikti; düzeltildi ve ilgili iki workflow testi **2 passed / 1,70 s** verdi. SQL fixture'ın ilk denemesinde stage tablosuna fazla placeholder ve daha sonra preview sayaçlarının current altında olduğu test hatası düzeltildi; ürün şeması/DTO değişmedi. Son versions+legacy journal kümesi **140 passed / 29,88 s**; ek max-128 proof ve gerçek public identity reset/epoch testleri eklendi. Son contract/history ortak kümesi **451 passed / 3,12 s**; ayrıca maintenance/data-migration/manifest regresyonu **200 passed / 64,28 s**. Bunlar örtüşen toplamlar olarak birleştirilmez. Ruff, src/scripts strict mypy **99 dosya** ve diff geçti.

İlk commit sonrası fresh R1/R2 henüz tamamlanmadı; i in_progress. Public upload writer/provider, yeni live çağrı, native/build/CI ve son source-bound kabul bu sonuç değildir.


I fresh R1: Astra/high graph ve Sol/high compatibility kolları aynı **P2**'yi bağımsız doğruladı. Unknown record'un recovery marker'ında yalnız revision üst sınırı vardı; gerçek SQLite'ta eski revision, reason/time/epoch/generation ile warm/full kontrol geçiyordu. Unknown için beş alan current record'la exact karşılaştırılır; running/terminal'deki eski recovery tarihçesi korunur. On warm/full negatif eklendi. Düzeltme sonrası versions/history/legacy journal **108 passed / 36,37 s**; test invocation ayrımı sonrası yeni küme **50 passed / 9,10 s**. İlk reviewer ayrıca 11 receipt'i ayrı kaldırınca ret ve reset sonrası yeni clock recovery floor davranışını bağımsız doğruladı. R2 henüz kapanmadı; i in_progress.


I fresh R2, farklı yeni Sol/high graph ve Astra/high compatibility ajanlarıyla 88218d2 üzerinde tamamlandı. İkisi de yeni doğrulanmış bulgu bulmadı; 50 yeni test sırasıyla 13,39/13,99 s geçti. Graph reviewer 47 ayrı missing receipt/intent operation-ID/sequence/request-digest ve re-bound malformed proof negatifini bağımsız doğruladı; her biri state_invalid verdi. R1 exact recovery marker düzeltmesi kapandı, terminal/running tarihsel marker ayrı korundu. P02-2i çalışma dalında verified; j sıradaki kod dilimidir. DDL/checksum ve eski v1 byte geçmişi değişmedi. Yeni writer/provider/public veya live/native/build/CI kabulü değildir.


## P02-2j — V2 durable write kapıları

Repository save/approve/revoke/admit/arm/receipt generic v1/v2 history üzerinde v2 current snapshot ve exact onay bağını uygular. Yeni v1 approve/admit/arm upload_plan_not_valid ile sıfır permit; existing admit yalnız yerel ID ve önceden arm edilmiş v1 receipt korunur. V2 nullable gerçek proof expiry'leri min'e girer; null için assert/sahte deadline yoktur. Yeni proof yazımında v2 freshness uygulanır; tarihsel full validation yaşlanmaz. V2 default verified_read ortak geçişte desteklenir; null-grant explicit read mutation k'dadır.

Önceki 58 journal race/PID/fork/reset/credential/lease/quota regresyonunun fixture'ı açık test-only current producer ile v2 prepared'e taşındı; v1 literal/domain/history ayrı korunur. Yeni v1 history/no-new-write/inflight receipt ve explicit unpriced iki-ack/known-negative/tek-arm testleri eklendi. İlk geçişte 2 passed/2 failed, fixture reader hâlâ legacy guard kullandığındandı; versioned reader'a taşındı. Sonraki yeni kümede 8 passed/1 failed, SQLite total_changes rollback edilen clock yazılarını da saydığı için test oracle'ı business tablolarını denetleyecek şekilde düzeltildi. Ürün clock/mutation güvencesi gevşetilmedi.

Son bütün upload policy/cost/v1/v2/domain/history/journal kümesi **529 passed / 40,53 s**; ilgili Ruff, src/scripts strict mypy **99 dosya**, diff geçti. Kalıcı stage slotu intent commit'inde ayrılır; actual HTTP body/read/response byte counter bağlantısı exact provider codec ile a/b'dedir. Public producer/CLI veya canlı yan etki bu dilimde yoktur. İlk commit sonrası iki fresh review henüz kapanmadı; j in_progress ve epik draft. Son source-bound native/build/CI/live kabulü hâlâ c sahibidir.
