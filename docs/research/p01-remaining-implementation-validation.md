# Kalan P01 uygulama ve doğrulama kaydı

**Tarih:** 2026-10-29. **Dal:** feat/p01-5-transport. **Taban:** development805f8bd; P01-4 kapanışı d686c8f korunur. **Durum:** P01-5a verified; P01-5b adım3 kapandı; adım4 CLI uygulaması sürüyor, paket ve faz kabulü tamamlanmadı. [Altı adımlı plan](../roadmap/p01-remaining-delivery-plan.md), [hazırlık/kullanıcı review disposition'ı](p01-remaining-readiness-review.md#kullanıcı-reviewi-ve-karar-kabulü--2026-10-29).

## Karar ve yetki

ADR-0017/0018, kullanıcının bulguları doğrulayıp düzelttikten sonra Accepted yapma ve uygulamaya başlama talebiyle **2f97118** commit'inde kabul edildi. Yeni ADR onayı tekrar istenmedi. Short-secret provenance, cookie/raw okuma/log, close/cancel ve ReadPort/error/UTF8/frame sınırları Accepted sözleşmelerdir. Public run/watch/demo veya gerçek EVREN istekleri açılmaz; Master/release kullanıcıdadır.

## Adım1 — Tipli HTTP portu, strict JSON ve gerçek TLS

Application HttpRequest/HttpCredential/HttpResponse/HttpTransport ve adapter HttpxTransport eklendi. HTTPX0.28.1; HTTPcore1.0.9, AnyIO4.15.1, certifi2026.10.23, h110.16.0, idna3.20 lock/hash ile sabitlendi. HTTP importu explicit adapter içindedir; mevcut yerel komutların subprocess guard'ı HTTPX/HTTPcore/AnyIO/certifi importunu ayrıca reddeder.

- Request canonical HTTPS443 hedef ve zorunlu hizmet ID'sine bağlı; aynı target'ta cross-service credential reddedilir. Auth/header/framing/query/endpoint/raw byte sınırları ağdan önce kontrol edilir. Dinamik endpoint/query'de credential URL'ye taşınamaz.
- Async session loop/thread/PID, her response/timeout context onu açan task sahibidir. Session havuzu ardışık tam consume task'larında aynı loop'ta kullanılabilir; açık timeout/task taşınmaz. En çok2 bağlantı/response slotu,1s pool ve faz/total deadline; response raw32KiB ve açık totalbyte tavanıyla okunur. Normal erken close ve gerçek task cancellation farklıdır.
- Cookie deny policy+clear, explicit request/no default merge, no redirect/env/proxy/auth/cookie; private context'te HTTPX/httpcore log filtresi, ilgisiz caller log'u etkilenmez. TLS doğrulanır. Response Content-Encoding/gövde/headers sınırları convenience decode öncesi uygulanır.
- Default1 attempt; explicit read-only GET/HEAD'de en çok2, transient status/connect hatası; Retry-After ve jitter tek kalan total'dadır. Partial body/TLS/auth/schema/oversize replay yoktur. Yeni10 ErrorCode/MESSAGES/exit1/3/6 ve OperationError reason_code eşliği eklendi.
- Strict JSON UTF8/duplicate/nonfinite/overflow/surrogate/sürüm ve byte/depth/node kontrolünden sonra beklenen tipli model doğrulanır. Dinamik serbest değer/map key provenance kuralıyla taranır; fixed keys/Literal/Enum muaf, belirsiz union container ve rich scalar sessiz kaçış oluşturmaz. Root incelemesinde exact service bağı, URL credential ve union dalı tahmin bypass'ı ayrıca kapatıldı.

### Yerel kontroller

macOS27.0.1 arm64, CPython3.11.18, SQLite3.54.1; editable frozen uv ortamı. İlk tam takım **1.973 passed /349,72s**; bu ilk kaynak revizyonudur. Sonraki hizmet-ID/union/URL/close sertleştirmeleri ve negatif testler ayrı hedefli koşuda **180 passed /23,04s**:144 contract +36 gerçekTLS/socket testi. Bu180 sonuç, son kaynağın tam takımını yeniden çalıştırmış gibi sunulmaz; final kaynak/kart/faz kabulü ilerleyen adımlarda ayrıca yapılacaktır. Ruff format/lint ve strict mypy55sourcefile geçti; belge/kart ve son diff kontrolleri commit öncesi çalıştırılır.

TLS fixture yalnız testte openssl ile ephemeral CA/SANlocalhost oluşturur; ağ guard'ı yalnız loopback'e açılır, gerçek HTTPX soketi/TLS çalışır. Sertifika/hostname negatifleri, redirect ikinci sunucuya sıfır istek, cookie path/hizmet/retry, rootINFO/DEBUG canary, gerçek Retry-After1s, header/body damlatma, yavaş consumer, pool1s, raw/gzip/bomb/byte limitleri, cancel/normalclose/task sınırı ve closure I/O hata önceliği geçti. Fiziksel güç kesintisi/canlı hizmet kabulü değildir.

İlk bağımlılık kurulum/build aşamasında ayrı wheel/sdist temiz venv kurulumları geçti: wheel53üye SHA-256 `c5506c646ca84d40ee3c4ac7ae5d245e546632069a184bb198a6eaa0f111e637`, sdist323üye `84d3b35a652d623856adad6f539a434c59628d86338d7734c7eef7b98cc6c436`. Her ikisinde origin/basic/cache/execution/jobs smoke başarılı. Bu artefaktlar sonraki source sertleştirmelerinin final kurulumu diye etiketlenmez; son paket kurulum/transport smoke'u P01-6b kapanışında tekrar alınır. Kaynak-sabit performans henüz bu adımda koşulmadı; önceki PR10 performansı yeni kaynak kabulü değildir.

### Review durumu

İlk ürün commit'i **3c68e22**. R1'de iki fresh ajan (gpt-6.1-terra/high ağ/dayanıklılık, gpt-6.1-sol/high sözleşme/test) bu head'i inceledi. Yedi doğrulanmış P2 kapatıldı: ham HTTPX exception context zinciri; foreign-task response context exit; ilk chunk sonrası iterator task devri; transient-response close OSError; generic JSON'da reserved schema_version dayatması; serializer/computed/extra çıktı yansıması; çok büyük integer deadline OverflowError. HTTP hata dönüşümü catch dışında/safe boundary'de yapılır; context wrapper generator/ContextVar'a dokunmadan owner exit'i denetler, her anext owner kapısıdır. Retry-close/cleanup safe hataya bağlanır; codec unsupported dönüşümlerde fail-closed, generic parser typed-version kararını modele bırakır. Büyük deadline ağdan önce invalid_request olur. Negatif fault regression'ları ve typed/plain codec pozitifleri eklendi. Son kaynak odaklı **213 test** (101request+64JSON+12lifecycle+36TLS), Ruff/lint/strict mypy geçti. İlk fault koşusundaki read exception-chain reddi gerçek ara başarısızlıktı; chunk kaynağında dönüşüm ve contextlib sınır temizliğiyle 12lifecycle testi tekrar geçti. R1 fix commit'i **a2250db**; ikinci fresh tur aşağıda kapandı. Kart henüz adım2 kabulü olmadan verified değildir. Adım2 Runner/operation/ReadPort bütünleşmesi, adım3–4 stream/CLI, adım5–6 faz kabulü başlamadı. Her tur/fix/kanıt burada gerçek head ile kaydedilir.

### Adım1 — R2 ve kapanış

İkinci farklı fresh çift: gpt-6.1-sol/high ağ, gpt-6.1-terra/high sözleşme. a2250db üzerinde R1 bulguları yeniden açılmadı. Üç yeni doğrulanmış P2 kapatıldı: validator'ın Literal/Enum tipinden saptırdığı gerçek değer muaf tutulamaz; sır içeren sıradan validator istisnası güvenli zarf dışına çıkamaz;64KiB metadata percent encoding ile HTTPX URL limitini aşamaz. Literal/Enum gerçek type/member/canonical identity ile denetlenir; model validation Exception'ları catch dışında invalid_response olur, CancelledError/KeyboardInterrupt/SystemExit korunur. Canonical ASCII wireURL≤65.536byte, aşım constructor'da sıfır ağ/invalid_request; adapter'da InvalidURL ayrıca zincirsiz dönüştürülür.

Her iki R2 reviewer kendi bulgusunun kapanışını güncel kaynakta/probe ile yeniden doğruladı:96JSON ve120request/lifecycle testi geçti;65.535/65.536byte URL HTTPX ile hazırlanabildi,65.537 ve percent genişlemesi kontrollü reddedildi. Root, consumer BrokenPipeError'ın genel network OSError yakalamasıyla yanlış sınıflanmamasını da kaynak IO sınırına taşıdı; output hatasının sahibi kalıcı işi değiştirmeden üst renderer'dır. Yeni exception testlerinde request/coroutine hazırlığı raises kapsamından çıkarıldı; yalnız incelenen çağrı assertions'ı sağlayabilir.

Son kaynak odaklı **252 passed /21,54s** (106request+96JSON+14lifecycle+36gerçekTLS), Ruff format/lint, strict mypy55sourcefile, belge/kart/diff kapıları geçti. İki fresh ürün review turu ve geçerli fix'leriyle **adım1 kapandı**. P01-5a bütünü henüz verified değil; adım2 Runner/operation/ReadPort kabulüne otomatik geçilir. İlk1973 tam koşu ve önceki artifact hash'leri yukarıda sürümleriyle korunur; nihai kaynak tam takım/kurulum/performans faz kapanışında tekrar kaydedilir.

## Adım2 — Owned Runner ve operation/ReadPort bütünleşmesi

HttpSession yalnız açık sync composition'a ait Runner ve HTTP client havuzunu taşır; ctor client/loop/ağ yaratmaz. Active-loop/reentry/foreignthread/PID/fork/closed kapısı consumer coroutine/factory yaratılmadan çalışır. API'nin private operation composition'ı ve dış port kullanacak coordinator girişleri optional typed PreflightPort ile env/DB/admit/arm'dan önce aynı kapıyı denetler. Eski public sync API ve legacy iç fixture portları değişmez; HTTPX yerel komut importuna taşınmaz.

Port çağrısındaki gerçek KeyboardInterrupt/CancelledError arm sonrası ID/latch ve operation_uncertain5/reasonrequest_cancelled ile döner; prearm control exception değişmez. Unknown save sırasında ikinci cancel ana belirsizliği6'ya düşürmez; kayıt yazılamasa da kalıcı latch korunur. Ham port exception'ı yeni public hatanın context zincirine eklenmez. Async HTTP kütüphanesinin task cancel'ı kendi sınırında hâlâ cleanup sonrası yayılır; sync operation use-case bunun etki/ID anlamını sahiplenir.

ReadPort'un authorize/observe HTTP/statü/codec hataları fixture adaptöründe kapalı negative observation/reason'a eşlenir. ReadAccessNone için mevcut kod currentcredential/owner/request denetimlerini yapıp yalnız local unknown diagnostic tutar; bu yolun operations referansındaki eski yalnız-unauthorized cümlesi ADR-0017 tüketicisiyle hizalandı. Pozitif observation/terminal yetkisi hâlâ geçerli ReadAccess gerektirir; state_changed/lease/credential hatası taşıma diye yutulmaz. Public jobs provider çağrısı yapmaz.

Root owned-loop kapanışında gerçek bir privacy probe yakaladı: callback/task shutdown istisnası default asyncio handler'a veya referanssız pending task GC'sinde sys.unraisablehook'a ham metin basabiliyordu. Owned loop exception handler yalnız bool failure latch tutar; taskfactory ek task üretmeden pending task'ı güçlü referansla tutar, tamamlananı hemen bırakır ve Runner.close sonrası referansları temizler. Global handler/log/unraisablehook değiştirilmez. Root probe sonrası controlled transport_failed ve boş stderr/asyncio log doğrulandı; önceden bilinen uncertainty5 cleanup'a üstün kalır.

### Yerel kontrol ve review başlangıcı

Son kaynak yeni birleşik **73 passed /28,07s**:32session +2preflight +4postarmcancel +35gerçekTLS/SQLite. Session testleri warnings-as-errors ile de geçti. Ayrı eski coordinator/reconciliation ve yeni preflight/cancel regresyon koşusu **127 passed /83,15s**; fixture agentının35yeniTLS+12mevcut credential/read yarışı **47 passed /32,92s**. Bu sayılar çakışan testleri toplam benzersiz sonuç gibi toplamaz. Ruff format/lint ve strict mypy56sourcefile geçti; belge/kart/diff commit öncesi kontrol edilir.

Gerçek loopback admission/start/access/observe, captured env snapshot, retry/pool, timeout/truncated reply/iptal/bozuk2xx, admission/arm ve read-final credential yarışları, reset/yeni onay sonrası latch, prearm control ve geçersiz context0HTTP, readcancel unchanged, yeni Python süreçte takeover/reconcile ve tek effect sınırı kanıtlandı. Sentetik provider yalnız tests/fixtures içindedir; public backend/uzak ürün desteği veya yeni DB şeması yoktur.

İlk adım2 ürün commit'i **61fe655**. İlk fresh tur aşağıda kapandı; P01-5a henüz verified değildir. Stream/CLI adım3–4 ve faz kapanışı5–6 başlamadı.

### Adım2 — R1

İki fresh reviewer (gpt-6.1-terra/high lifecycle ve gpt-6.1-sol/high sözleşme)61fe655 üzerinde birP1 ve birP2 doğruladı. P1: arm commit'inden hemen sonraki process denetimi try dışında kalıp cancel'ın ID/unknown5 olmadan kaçmasına izin veriyordu. Arm çağrısı ve dönüşü korumalı bölgeye alındı; arm return'ü kesilirse bounded güncel latch okunur. Kesin latchNone rollback/prearm cancellation kendi control exception'ını korur; latch varsa veya son okuma yapılamıyorsa conservative operation_uncertain5/ID/reasonrequest_cancelled, no replay ve best-effort unknown uygulanır. Commit dönüşü, hemen sonraki process callback'i ve okunamayan commit sınırı iki cancel türüyle gerçek DB regresyonudur.

P2: renew diğer girişlerden farklı olarak owned-session preflight'ını atlayabiliyordu. Aynı guard renew'e de eklendi; closed session ve active loop altında değişmeyen kalıcı lease/snapshot doğrulandı. Root hata taşımada pre-port capacity_kind/reason_code kapalı metadata'sının korunmasını da negatif fixture ile sabitledi. Son yeni cancellation+TLS kontrolü **48passed/29,45s**, format/lint/strict mypy56sourcefile geçti. İkinci farklı fresh çift fix commit'inden sonra inceleyecek; adım2 ve P01-5a henüz kapanmadı.

### Adım2 — R2, iki kurulum ve P01-5a kapanışı

İkinci farklı fresh çift gpt-6.1-sol/high lifecycle ve gpt-6.1-terra/high sözleşme, **ec2d202** üzerinde yeni doğrulanmış bulgu bulmadı. Lifecycle reviewer bağımsız geç-GC privacy probe'unda boş stderr ve32session+2preflight+13cancellation testinden **47passed/4,29s** doğruladı. Önceki48cancellation/TLS koşusu aynı ürün kaynağındadır; bu sonuçlar ortak testleri iki kez toplam benzersiz sayı olarak sunmaz. İki ürün adımının her biri commit/R1fix/R2 döngüsüyle kapandı; P01-5a verified oldu.

Ec2d202 runtime kaynağında yeni build ve iki ayrı temiz artifact install tekrar geçti. Wheel54üye SHA-256 `5f56e62a899a5c51c5dbcf547e38273b46e790c7a6ade7292afbba6993694d0b`; sdist331üye `70d5496aac7966fd9a5c06ecf80ea5c8b66be0cdffed1469996719f92030bb84`. Her ikisinde origin/basic/cache/execution/jobs smoke geçti. Bu kayıt sonradan eklenen doküman kapanışını veya sonraki stream/CLI kaynağını aynı artifact sanmaz. P01-6b final kaynak tam takım/transport+stream artifact smoke/performans/matris kabulü ayrıca kalır.

P01-5b adım3'e otomatik geçilir. Bütün paket/P01 henüz tamamlanmadı, PR açılmadı.


## Adım3 — Tipli olaylar ve bounded akış

Kapalı StreamEvent v1, tipli ResultEvent fabrikası ve yerel katalogdan yeniden kurulan güvenli ErrorEnvelope eklendi. Eski Result v1’in generic specialization’ı ve serialization kapsamı korunur; alt sınıfın yalnız kendi ek alanını taşımak için veri tipini yeniden tahmin etme yoktur. Sürüm/sıra/sayaçlar strict integer, kimlikler canonical UUIDv4, event ve details katalogları kapalıdır. Error ID/kapalı metadata korunur; provider mesajı yeniden yayımlanmaz. Ortak JSON/frame byte, depth ve node sınırlarının tek kaynağı domain wire_limits’tir; genel JSON parser’ın varsayılan 1MiB tavanı değişmedi.

Akış kabulü için yapılan kaynak incelemesinde HTTPX’in sabit chunk_size okuyucusunun küçük parçaları 32KiB/EOF’a kadar biriktirdiği doğrulandı. Raw yol convenience decode kullanmadan aiter_raw() okur, hazır büyük parçayı en çok32KiB’a böler ve küçük parçayı hemen teslim eder. Gerçek TLS fixture sunucusu ilk parçayı gönderip kalan gövdeyi consumer sinyali gelene kadar tutar; okuyucu ilk parçayı EOF beklemeden alıp sinyali verir. Önceden tanımlanan bounded parça/totalbyte/deadline ve owner kapıları korunur. HTTP referansı bu okuma davranışıyla hizalandı; bu bir codec veya hedef güven sınırı değişikliği değildir.

İlk model kontrolleri **191passed/0,25s**; ortak JSON/sınır kontrolleri **104passed**. Root birleşik model+JSON+sınır koşusu **295passed/0,38s**; gerçekTLS/lifecycle **51passed/21,88s**. Bu sonuçlar ortak testleri toplam benzersiz sayı olarak toplamaz. Codec/reader ve iki fresh review turu aşağıda gerçek son kaynakla ayrıca kaydedilecektir; adım3/kart/paket henüz tamamlanmadı. CLI adım4 henüz uygulanmadı.


Strict codec tam frame’i UTF-8/JSON/kapalı model/sıra/ID ve secret provenance ile doğrular; Result payload’ının gelen gerçek encoded span’ı ayrıca1MiB sınırındadır. Her consumer resume/close/exit aynı task/loop/thread/PID sınırını korur. Progress hemen döner; terminal aday yalnız HTTP message EOF sonrası döner. Trailing/partial line, empty/CR/BOM, reset/truncation ve timeout önceliği referanstaki gibidir; bound operation ID bütün bu hatalarda korunur. Erken normal close iptal/terminal uydurmaz; gerçek cancellation kaynakları kapatıp CancelledError yayar. Yavaş consumer da aynı total deadline içindedir. Bütün akış bir listede biriktirilmez.

Bağımsız contract hazırlığında constructed model’in Pydantic serializer uyarısının ham input repr yazabildiği doğrulandı; iki encode dump’ı warnings=error ile safe failure sınırına alındı, canary warning regresyonu geçti. Root son parse’den önce success flag’i atamama ve foreign PID/thread kapısı/iterator açılış cleanup sınırlarını ayrıca kapattı. Yavaş consumer testi timeout cleanup’ında ambient CancelledError context’i kaldığını yakaladı; dış context sınırında safe hatanın zinciri temizlendi. Bunlar geliştirme sırasında doğrulanmış düzeltmelerdir; fresh ürün review turları yerine sayılmaz.


Son birleşik odaklı koşu warnings-as-errors altında **444passed/38,43s**:191model+66codec+8limits+96JSON+14HTTP lifecycle+32streamTLS+37HTTP TLS. En son aclose hata zinciri sınırı için close/cancel/backpressure testleri ayrıca çalıştırıldı. Format/lint, strict mypy59sourcefile,126publicMarkdown,6skill/12kart ve diff kontrolleri geçti. İlk adım3 ürün commit’i sonrası iki fresh review turu bu kayda eklenecek; P01-5b bütününün CLI kabulü henüz yoktur.


### Adım3 — R1

İlk ürün head’i **16ebe8f** iki fresh reviewer tarafından incelendi: gpt-6.1-terra/high lifecycle/ağ ve gpt-6.1-sol/high tipli sözleşme/kaynak. BirP1 ve birP2 doğrulandı ve kapatıldı. P1: reader istekte zaten kullanılan credential’ı kendiliğinden sır listesine eklemiyor, çağıranın ek liste vermesine güveniyordu. Root gerçekTLS’de varsayılan seçenekle credential echo’nun kabul edildiğini red testle doğruladı; reader artık seçilmiş request credential’ını otomatik ekler, ek secrets korunur. Varsayılan ve ek credential yolları iki gerçekTLS testinde geçti. P2: model validator normalize sırasında payload’ı büyütürse yalnız final frame tavanı kontrol ediliyor, 1MiB+1byte payload daha geniş wrapper tavanından geçebiliyordu. Root doğal typed validator ve−1/0/+1 örneklerinde red testle doğruladı; final encoded payload span ayrıca1MiB denetlenir, yeni validation döngüsü eklenmez.

Son model/codec/sınır/gerçek stream TLS kontrolü warnings-as-errors ile **302passed/17,55s**. Değişen raw okumanın önceki Runner/operation/ReadPort tüketicilerinde **82passed/31,60s** regresyonu geçti. Format/lint ve strict mypy59sourcefile temiz. Reviewer’ın secrets boşken caller-owned açık BaseModel kabulü gözlemi mevcut HTTP sözleşmesinin credential denetimine bağlı codec kuralını değiştirmediğinden ayrı kusur sayılmadı; ürün domain modelleri kapalıdır. Bu bir yeni endpoint codec desteği iddiası değildir. İkinci farklı fresh çift fix commit’i üzerinden inceleyecek; adım3 henüz kapanmadı.


### Adım3 — R2 ve kapanış

İkinci farklı fresh çift gpt-6.1-sol/high lifecycle ve gpt-6.1-terra/high sözleşme, **8f2db99** ürün kaynağında ek doğrulanmış ürün kusuru bulmadı; R1’in iki düzeltmesi kapandı. Lifecycle reviewer ayrıca bağımsız34streamTLS testini warnings-as-errors ile geçirdi. Kabul kartındaki literal chunked truncation/TCP reset kanıtının mevcut Content-Length kesilmesi testlerinden ayrı kurulmadığı doğrulandı. Bu kabul boşluğu da kapatıldı: valid zero-chunk/messageEOF/aynı bağlantı reuse pozitif oracle; beş prefix’in Content-Length ve eksik son chunk matrisi; progress tesliminden sonra gerçek TCP abort ve bağlı ID’li stream_interrupted. TCP abort fixture’ı SO_LINGER ayarlayıp FD’yi orderly shutdown’dan önce detach/close eder. Doğrudan HTTPX eşli oracle testi normal kesilmede RemoteProtocolError, reset’te ReadError gözler; ürün testi safe normalization’ı ayrı sınar. İki R2 reviewer bu son fixture/test değişikliğini de yeniden inceledi, ek bulgu yoktur.

Son kaynak gerçekTLS stream+HTTP regresyonu warnings-as-errors ile **80passed/43,70s**; doğrudan reset oracle alt kümesi **3passed/1,85s**. Önceki model/codec/sınır **268passed** kaynakları değişmedi;302son test sayısındaki34stream yolu bu koşuda43oldu. Format/lint, strict mypy59sourcefile, belge/kart/diff kapıları geçti. **Adım3 iki fresh review turuyla kapandı.** P01-5b kartının CLI/UTF8/NDJSON/pipe/SIGINT adım4 kabulü henüz tamamlanmadığından kart in_progress kalır. P01-6b ve bütün paket henüz verified değildir; adım4’e otomatik geçilir.
