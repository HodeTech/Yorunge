# HTTP taşıma sözleşmesi

**Durum:** Accepted [ADR-0017](../decisions/0017-bounded-http-transport.md) sözleşmesi; adım1 tipli byte/JSON taşıması uygulanıyor, review ve kart kabulü sürüyor; public ağ komutu yok. **Tarih:** 2026-10-29.

## Port ve sahiplik

Application portu async, request ve response metadata'sı kapalı/tiplidir; HTTPX nesnesi public API/domain'e çıkmaz. Somut isimler uygulamada kesinleşebilir; aşağıdaki davranış değiştirilemez. HttpRequest yalnız seçilmiş `ServiceTarget`, zorunlu `service_id`, göreli endpoint, method, açık read-only politikası, sınırlı query/header/body, private credential taşıyıcısı ve mutlak deadline alır. HttpCredential aynı target ve service_id'ye bağlıdır; target aynı olsa da cross-service auth reddedilir. Env/config yeniden çözmez. Header auth biçimini endpoint adaptörü seçer; generic transport Platform/LLM'ye tek header varsaymaz.

Bir owned session en çok iki bağlantı/keepalive taşır; istek başına yeni client açılmaz, loop/PID/thread sahibi değişmez. Response/timeout context'i yalnız onu açan aynı task içinde okunur/kapatılır. Async consumer bütün response tüketimini aynı task'ta bitirir. Sync köprü tam consume coroutine'ini session-owned Runner'da çalıştırır; ardışık tam çağrılar aynı loop'ta farklı task olabilir, açık response/timeout context'i task'lar arasında taşınamaz. Active loop/reentry/PID/thread kapısı composition girişinde, state/credential/arm öncesidir. Client/cookie/auth/env üzerinden örtük ikinci yetki kaynağı yoktur.

## Hedef ve istek sınırı

Production origin/API kökü mevcut normalize binding'dir; HTTPS/443 ve sertifika/hostname doğrulaması zorunludur. URL oluşturma düz string `urljoin` ile kullanıcı authority'sine geçmez. Endpoint göreli ve segment bazında doğrulanır; boş/dot segment, `//`, backslash, fragment, userinfo, CR/LF, encoded separator/dot/double-encoding kaçışı reddedilir. Query ayrı tipli çiftlerdir; URL'de auth/secret taşınmaz. Prepared wire URL origin/API kökü ve beklenen encoding ile yeniden karşılaştırılır. Geçersiz hedef sıfır ağ çağrısıyla `invalid_service_target` olur.

Başlıklar ASCII isim ve güvenli değerlerle sınırlıdır; CR/LF/NUL/control kabul edilmez. Caller Host, Content-Length, Cookie, Authorization veya proxy auth ekleyemez. Hizmet adaptörünün auth başlığı private taşıyıcıdan tek yerde eklenir. HTTP header'a taşınamayan credential kırpılmaz/encode edilerek değiştirilmez; `invalid_credential`. SecretValue'nun mevcut UTF-8 kabulü değiştirilmez; bu gönderim sınırının ek koşuludur. İstek body için uzunluk ve Content-Length somut gönderilen baytlarla tutarlıdır.

Redirect kapalıdır, hiçbir 3xx takip edilmez. `trust_env=False`, transport retries=0, HTTP/2 kapalıdır. `trust_env=False` cookie jar'ını kapatmaz. DefaultCookiePolicy'nin kabul/gönderim yollarını reddeden private CookieJar kullanılır; her response ve finally kapanışında client cookie jar'ı temizlenir. İstek explicit HTTPX Request ile oluşturulur; build_request/cookie/auth default merge yapılmaz. Set-Cookie aynı origin'de farklı path/hizmet veya retry'da sonraki isteğe Cookie üretmez. Ham URL/header/exception repr veya provider body public hata/log değildir. Test CA ve loopback ephemeral port yönlendirmesi yalnız fixture composition'ındadır; production policy bypass'ı sunulmaz.

## Boyut ve süre

| Sınır | İlk uygulama |
|---|---|
| JSON request / tek JSON response | Her biri en çok 1 MiB UTF-8 |
| Her decoded JSON/NDJSON record | Container nesting en çok 32, JSON düğümü en çok 65.536; aşağıdaki tek sayım kuralı |
| Akış okuma parçası | En çok 32 KiB; dosyanın bütünü biriktirilmez |
| NDJSON frame | En çok 1 MiB + 1 KiB UTF-8; LF/CRLF hariç; Result payload en çok 1 MiB encoded JSON |
| Raw stream toplamı | İstek için açık byte tavanı; en çok 1 GiB |
| Encoded wire URL | En çok65.536 ASCII byte; query percent-encoding sonrası ayrıca denetlenir, aşım sıfır ağ/invalid_request |
| Query/header metadata | En çok 64 çift, isim başına 128 ve değer başına 16.384 byte; toplam en çok 64 KiB |
| İstek phase timeout | Connect/read/write en çok 5 s, pool en çok 1 s; kalan total'dan büyük olamaz |
| Total | Çağıranın mutlak monotonic deadline'ı; production caller için zorunlu, default yok; fixture açık 30 s verir, operation mevcut daha dar port deadline'ını verir |

Sınırlar bool/float ile gevşetilmez; süreler sonlu/pozitif olmalı. Geçmiş deadline sıfır ağ çağrısıdır. Dış timeout tüm acquire/header/body/consumer/backoff'u kapsar; her faz/deneme yeni 30 s başlatmaz. Deadline clock'u `time.monotonic()`'tir; asyncio loop clock'una geçerken `loop.time() + max(0, deadline - time.monotonic())` ile kalan süre aktarılır ve dönüşte özgün deadline tekrar denetlenir. Farklı clock epoch'larının eşit olduğu varsayılmaz. `Accept-Encoding: identity`; ilk P01 decoder sıkıştırılmış content-encoding'i reddeder, otomatik açılmış sınırsız içerik yoktur. Başka content codec'i ihtiyaç duyulan endpoint'in ayrı P02 kabulüdür.

JSON/NDJSON için tek yapısal sayım: scalar depth=0, object/array depth=1+en derin child container depth; dolayısıyla root container depth=1'dir. Düğüm sayısı scalar için1, array için1+elemanların düğüm toplamı, object için1+her key başına1+her value'nun düğüm toplamıdır. Key string ayrıca sayılır, container value iki kez sayılmaz. Tam sınır kabul, bir üstü ret; küçük/azami/aşan fixture'lar aynı parser'dan hesaplanmış beklentiye dayanmaz. Request JSON ve endpoint response JSON'a da aynı sınırlar uygulanır; P01 yalnız NDJSON decoder'ında koruma uygulamış sayılmaz.

Gövde başlamadan Content-Encoding yok/identity değilse invalid_response; Accept-Encoding: identity tek başına güvence değildir. Yalnız `aiter_raw(chunk_size=32768)` ile incremental byte okuma yapılır; her parçada total ve frame sınırı uygulanır. `aread`, `.json()`, `.text`, `aiter_bytes`/`aiter_lines` boyut/encoding doğrulayıcısının yerine kullanılamaz. UTF-8 strict çözülür, duplicate/nonfinite/depth/node/size ve beklenen endpoint modeli doğrulanır; şema seviyesinde 2xx mantıksal hata da başarısızdır. Raw byte portu yalnız trusted bounded consumer'a gider, public Result/terminale doğrudan chunk basmaz. NDJSON buffer/sıra/terminal kuralları [ayrı referanstadır](stream-results.md).

Sır kontrolünün girdisi typed response modelindeki provider kaynaklı **dinamik serbest string değerler ve map anahtarlarıdır**; model alan adları, sabit Literal/enum değerleri ve yerel hata/message kodları değildir. Credential kontrolü açıkken extra=forbid olmayan model, computed field, field/model/Annotated/custom serializer veya rich scalar çıktı dönüşümü sessiz atlanmaz; açık codec desteği yoksa invalid_response ile fail-closed reddedilir. Normal alan adının serialization/type olması codec tanımı sayılmaz. Generic JSON parser hiçbir kullanıcı schema_version anahtarına tür dayatmaz; strict sürüm denetimi beklenen Yörünge modeline aittir. Belirsiz union container'da Literal dalı runtime class'tan tahmin edilmez; konservatif dinamik alan kontrolü uygulanır. Tüm boylarda tam eşitlik, ≥8 UTF-8 byte sırda ayrıca literal alt dize eşleşmesi invalid_response olur. <8 byte sırda gömülü parçayı bulma veya sabit kod/mesajlarda tesadüfî eşliği silme garantisi yoktur; credential'ın mevcut 1–16.384 byte kabulü değişmez. Dinamik tam eşitlikte kısa sır da kontrollü reddedilir; hata ham değeri taşımaz. Bir byte a, sabit hata koduyla eşit veya sabit schema alan adıyla eşit sırlar ve normal serbest metinde kısa eşleşme ayrı fixture'lardır; mutlak bütün stdout alt dize assert'i kullanılmaz. Uzun canary'nin aynı record'un farklı chunk'larına bölünmesi kontrolü atlatmaz.

HTTPX/httpcore INFO/DEBUG ham URL/path/query kaydı owned request context'inde context-local logging filtresiyle bastırılır. Global level/handler konfigürasyonu değiştirilmez; unrelated caller kayıtları etkilenmez. Root INFO/DEBUG ve path/query canary testi zorunludur; özel HTTP nesnesi exception zinciri/repr/loga taşınmaz.

## Retry ve hata

Varsayılan max_attempts=1. Yalnız trusted read-only GET/HEAD isteği max_attempts=2 olabilir. Body replay/dispatch/POST retry'si yoktur. Geçici bağlantı hatası veya 408/429/502/503/504 ilk response verisi consumer'a verilmeden retry adayıdır; TLS/401/403/3xx/decoder/oversize/partial-body/stream hatası aday değildir. HTTPX retry=0 ve SDK kullanılmaması bu tek sahipliği korur.

Bekleme ilk retry için uniform `[0, 0,25]` s jitter'dır. `Retry-After` delta veya geçerli UTC HTTP-date ise `max(jitter, gereken bekleme)` kullanılır. Parse için en çok 128 ASCII byte; taşan/negatif/bozuk değer invalid sayılır ve normal jitter'a düşer. Geçerli ama kalan total'a sığmayan bekleme kısaltılmaz; ikinci attempt yapılmaz ve son kontrollü hata döner. HTTP-date hesabı yalnız beklemeyi seçmek içindir; deadline monotonic kalır. Uyku/ikinci attempt öncesinde cancellation/deadline kontrol edilir.

Kararlı hata/exit kataloğunun tek kaynağı [CLI tablosudur](cli-contract.md#p01-5-hata-kataloğu). Yeni transport hataları `retryable=false`, ham provider data/details yoktur. Effectful coordinator start hatasında mevcut OperationError ve operation ID/unknown/5 önceliklidir; transport hatası ikinci dispatch hakkı üretmez. Async iptal cleanup sonrası CancelledError olarak sahibine döner; CLI normalizasyonu taşıma içine kopyalanmaz.

## ReadPort adaptör eşlemesi

Generic taşıma operation kimliği veya provider anlamı uydurmaz. ReadPort adaptörü aynı request/hedef/yetki bağını koruyarak HTTP404'ü not_found, 401/403'ü unauthorized (authorize aşamasında PermissionError), geçici network/5xx'i unavailable gözleme eşler. Authorize kanıt üretemeden hata verirse current credential/owner/request kapılarıyla yalnız provider_unauthorized/provider_unavailable/evidence_mismatch local unknown diagnostic'ı kaydedilir; ReadAccess olmadan observe/pozitif kanıt yoktur. Bozuk 2xx observation evidence_mismatch/ReadFailure olur; 2xx tek başına cancel_accepted veya cancelled kanıtı değildir. cancel_accepted yalnız endpoint'in doğrulanmış şemasındaki kabul anlamından gelir, kesin cancelled mevcut trusted observed kanıtıdır.

State_changed/lease/credential/current-authority hataları genel taşıma hatası sayılmaz ve kendi hata koduyla yükselir. Generic transport ErrorCode'ları bu adaptör sınırında eşlenir; coordinator'a yanlışlıkla YorungeError olarak kaçıp kalıcı observation marker'ını atlayamaz. Public jobs salt yerel okumadır, HTTP çağrısı yapmaz; unknown işi okumak exit0 kuralı değişmez. ReadPort sonucu/reason ve kayıtlı marker gerçek coordinator+TLS fixture'ıyla sınanır.
