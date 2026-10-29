# ADR-0017: Ortak HTTP taşıması ve SDK sınırı

**Durum:** Accepted — 2026-10-29 kullanıcı yetkisiyle review düzeltmeleri sonrası benimsendi; ürün uygulaması bu karardan sonra başlar. **Tarih:** 2026-10-29. **İş:** P01-5a / B01 ve B03 ön incelemesi.

## Bağlam

P01-1–4 yerel çekirdeği teslim etti. Gerçek HTTP taşıması yok; güncel `StartPort` ve `ReadPort` senkron trusted iç portlardır. [ADR-0008](0008-offline-core-stack.md) HTTP seçimini açık bıraktı. HTTP timeout'u, yeniden deneme, secret/hedef ve iptal politikası farklı adaptörlerde tekrar edilmemeli. [Ön inceleme](../research/p01-remaining-readiness-review.md) istemci/SDK kaynaklarını ve mevcut kodu karşılaştırır; canlı EVREN kabulü değildir.

HTTPX'in connect/read/write/pool timeout'ları toplam istek deadline'ı değildir. Header veya gövdenin yavaş damlatılması, yalnız senkron socket timeout'u ve chunk arası kontrolle güvenilir biçimde sınırlandırılamaz. Bir thread'i terk etmek de devam eden isteği durdurduğunu kanıtlamaz. SDK'nın kendi retry ve ortamdan credential seçimi dış katman politikasıyla çarpışabilir.

## Karar

### İstemci ve composition

HTTPX **0.28.1** ilk doğrulanacak runtime alt sürüm adayıdır; önerilen aralık `>=0.28.1,<0.29`, tam transitif sürümler/hash'ler lock'ta tutulur. İlk uygulama `AsyncClient`/HTTP/1.1 kullanır; HTTP/2 extra'sı, aiohttp, requests, EVREN SDK veya eğitim paketi eklenmez. Domain/application HTTPX tipini import etmez; somut adaptör tipli taşıma portunu uygular. HTTP importları yalnız açık ağ composition'ında yapılır, mevcut yerel CLI/API ve metadata yollarına taşınmaz.

Async taşımanın sahibi açık, aynı task içinde kullanılan async context'tir. Havuz context ömründe paylaşılır, çıkışta response ve client kapanır. İlk bağlantı ve keepalive sınırı **2**, okuma parçası **32 KiB**'dır; sınırsız task/queue/arka plan worker yoktur. Backpressure tüketicinin bir sonraki okumayı istemesiyle uygulanır.

Mevcut senkron operation portları değiştirilmez. Ağ kullanan senkron composition, tek session boyunca sahip olduğu `asyncio.Runner` ile **tam exchange/consume coroutine'ini** çalıştırabilir. Aktif event loop, eşzamanlı/reentrant kullanım, başka thread veya PID/fork'ta kullanım kontrollü `invalid_request` ile **credential/env/DB/ağ ve admit/arm öncesinde** reddedilir. `start` içindeki geç kontrol yeterli sayılmaz. Her `anext` için başka task üretip açık timeout context'ini task'lar arasında taşıyan köprü veya terk edilen thread eklenmez. Mevcut salt senkron public `api.*` işlevlerinin event loop içinden kullanımı bu yeni köprü yasağından etkilenmez.

### Hedef ve sır

Üretim taşıması yalnız [binding v1](../reference/credential-binding-v1.md)'in normalize ettiği HTTPS/443 origin ve API kökünü kabul eder. Endpoint adaptörü açık göreli yol/parametre verir; tam URL, authority değişimi, dot segment, kök kaçışı ve belirsiz encoding ağdan önce reddedilir. İstek hazırlanırken HTTPX'in son URL'si de seçilen hedef/kök ile karşılaştırılır. Otomatik redirect **kapalıdır**; aynı-origin dahil 3xx takip edilmez.

TLS doğrulaması açık kalır. `trust_env=False` env proxy/CA/netrc davranışını kapatır; cookie izolasyonunu tek başına sağlamaz. Client, kabul/gönderim yapmayan CookiePolicy ve her response/finally sonunda cookie temizliği kullanır; request explicit kurulur, client cookie/header/auth merge API'si kullanılmaz. Aynı origin'de farklı path/hizmet ve retry dahil ikinci istekte Cookie yoktur. Kullanıcı `Host`/`Authorization` override'ı yoktur. Yalnız hizmet adaptörünün belirlediği auth header'a seçilmiş credential snapshot'ı eklenir; Platform/LLM header biçimi ortak taşıma tarafından uydurulmaz. Yeni host, DNS/IP allowlist veya genel SSRF engeli iddiası yoktur: hedef kullanıcının açık config'idir, HTTPS doğru hedef politikasının tek başına kanıtı değildir. İmzalı depolama URL'si ve credential'sız farklı-origin aktarım ayrı P02 endpoint sözleşmesidir.

Gerçek TLS loopback fixture'ı test CA'sına güvenen, yalnız test composition'ının verdiği explicit hedef kullanır. Ephemeral loopback portu için istisna yalnız fixture'dadır; production hedef doğrulamasını gevşeten flag/env/config/public URL seçeneği eklenmez. Başarılı TLS, yanlış CA/host, 3xx ve iki ayrı sunucuda header sızıntısı birlikte sınanır.

Sır yalnız private request/auth taşıyıcısındadır; ham request/response/header/body/URL veya exception public çıktıya kopyalanmaz. Bilinen sır kontrolü provider kaynaklı dinamik serbest string değer ve dinamik map anahtarlarında bütün uzunluklarda tam eşitlik, en az 8 UTF-8 byte sırda ayrıca literal alt dize eşleşmesidir; strict modelin sabit alan adları/Literal enum'ları ve yerel hata kodu/mesajları taranmaz. Kısa sırın başka bir metindeki tesadüfî karakter eşliği sızıntı kanıtı sayılmaz; kısa sırın gömülü parçalarını bulma garantisi yoktur. Tam eşit dinamik değer kısa olsa da fail-closed reddedilir; ham credential kabulü 1–16.384 byte kalır. Çakışma hatası yalnız yerel güvenli katalogdan kurulur; örneğin credential a iken sabit message/code içindeki a yasaklanmaz. Chunk bölünmesi aynı record üzerinde kontrolü atlatamaz. HTTPX/httpcore INFO ve DEBUG kayıtları owned çağrı bağlamında context-local filtreyle bastırılır; global logging seviyesi/diğer çağrılar değiştirilmez. Ayrıntılı provenance ve canary kabulü HTTP referansındadır; bütün PII veya bütün çıktı alanlarında mutlak alt dize yokluğu iddiası değildir.

### Tek deadline ve tek retry sahibi

Her çağrı mutlak monotonic deadline alır; havuz bekleme, DNS/connect/TLS, header, gövde, doğrulama, backoff ve bütün denemeler bu deadline'ı paylaşır. HTTPX faz timeout'ları kalan süreyi aşmaz; dış `asyncio.timeout_at` tüm await edilebilir exchange/consume'u kapsar. Tüketici callback'i de aynı bütçededir. OS scheduler/bloke olmuş senkron kod veya sistem I/O'su için fiziksel duvar saati garantisi verilmez; kontrol geri geldiğinde geç sonuç başarıya çevrilmez. Cleanup kaynakları kapatır, yeni istek üretmez.

Retry sahibi yalnız ortak uygulama politikasıdır; HTTPX transport retry **0**. Varsayılan **1 deneme**; trusted endpoint adaptörünün açık `read_only` işaretlediği yalnız GET/HEAD için en çok **2 deneme**. Method tek başına güven kanıtı değildir. Effectful/POST/dispatch, `ConnectError` dahil hiçbir otomatik tekrar yapmaz; provider idempotency desteği varsayılmaz. 401/403, redirect, TLS/şema/encoding/oversize ve başladıktan sonra kesilen body/stream retry edilmez. Read-only retry, response verisi tüketiciye verilmeden önce bağlantı/geçici 408/429/502/503/504 hatasıyla sınırlıdır.

İlk backoff uniform `[0, 0,25]` s jitter'dır; `Retry-After` geçerli delta veya HTTP-date ise gereken beklemenin altına inilmez. Geçersiz değer normal backoff'a düşer, deadline'a sığmayan bekleme/ikinci deneme yapılmaz. Sınırsız `Retry-After`, her katmanda yeni bütçe veya parçadan sonra akışı yeniden başlatma yoktur. Kesin tip/limit/hata sözleşmesi [taşıma referansındadır](../reference/http-transport.md).

### SDK sınırı

EVREN SDK çekirdek bağımlılığı yapılmaz. B03'ün P01 çıktısı, ortak taşıma politikasını atlatan SDK kullanımının yasak olduğudur; gerçek SDK/endpoint uyumu P02'de güncel sürüm sabitlenerek denetlenir. SDK'nın retry, timeout, env, redirect, stream ve hata davranışı bu portun kabulünü karşılamadan adaptör hazır sayılmaz. Bu karar SDK'nın bütün işlevlerinin uygunsuz olduğunu veya canlı endpoint desteğini kanıtlamaz.

## Alternatifler

- Senkron HTTPX/requests: mevcut sync yüzeye yakındır; bütün header/body beklemesi için cooperative toplam iptal/deadline çözümü eksik kalır.
- aiohttp: async ve total timeout sağlar; bu çekirdek için ikinci bir istemci eklemek veya sync köprü ihtiyacını ortadan kaldırmak yönünde avantaj kanıtlanmadı.
- Standart `urllib`: bağımlılık azdır; redirect/proxy/auth/pooling/iptal politikasının daha büyük bölümünü elle sahiplenmek gerekir.
- SDK'yı doğrudan kullanmak: endpoint kapsamı yararlı adaydır; mevcut kaynakta farklı default retry/timeout/env kararları bulundu. P02 endpoint incelemesi korunur.

## Sonuçlar ve kabul

Yeni runtime bağımlılığı iki temiz kurulum ve mevcut startup kapılarıyla kabul edilir. Async karmaşıklığı ağ sınırında tutulur; bütün API/SQLite katmanı yeniden yazılmaz. Public HTTP/debug/demo/run komutu açılmaz. [P01-5a kartı](../roadmap/tasks/p01-5a-http-transport.md) gerçek loopback/TLS, slow-header/body, iptal, retry sayısı, sır/hedef, havuz/resource ve kurulu artefakt kabulünü tanımlar. Effectful kayıp cevabı [ADR-0016](0016-operation-admission-and-ownership.md)'daki latch/unknown sözleşmesini değiştirmez.

Birincil kaynaklar (erişim 2026-10-29): [HTTPX timeout](https://www.python-httpx.org/advanced/timeouts/), [async/client kapanışı](https://www.python-httpx.org/async/), [TLS](https://www.python-httpx.org/advanced/ssl/), [env](https://www.python-httpx.org/environment_variables/), [transport retry](https://www.python-httpx.org/advanced/transports/), [Python timeout/cancellation](https://docs.python.org/3.11/library/asyncio-task.html#timeouts), [Runner sınırları](https://docs.python.org/3.11/library/asyncio-runner.html).
