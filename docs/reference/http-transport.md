# HTTP taşıma sözleşmesi

**Durum:** Taslak; Proposed [ADR-0017](../decisions/0017-bounded-http-transport.md)'ye bağlıdır. Ürün taşıması henüz yok. **Tarih:** 2026-10-29.

## Port ve sahiplik

Application portu async, request ve response metadata'sı kapalı/tiplidir; HTTPX nesnesi public API/domain'e çıkmaz. Somut isimler uygulamada kesinleşebilir; aşağıdaki davranış değiştirilemez. Request yalnız seçilmiş `ServiceTarget`, hizmet ID'si, göreli endpoint, method, açık read-only politikası, sınırlı query/header/body, private credential taşıyıcısı ve mutlak deadline alır. Env/config yeniden çözmez. Header auth biçimini endpoint adaptörü seçer; generic transport Platform/LLM'ye tek header varsaymaz.

Bir owned session en çok iki bağlantı/keepalive taşır; istek başına yeni client açılmaz. Response sadece açık async context içinde okunur; task/PID/thread sahibi değiştirilemez. Async consumer bütün response tüketimini aynı task'ta bitirir. Sync köprü bu tam coroutine'i session-owned Runner'da çalıştırır; active loop/reentry/PID/thread kapısı composition girişinde, state/credential/arm öncesidir. Client/cookie/auth/env üzerinden örtük ikinci yetki kaynağı yoktur.

## Hedef ve istek sınırı

Production origin/API kökü mevcut normalize binding'dir; HTTPS/443 ve sertifika/hostname doğrulaması zorunludur. URL oluşturma düz string `urljoin` ile kullanıcı authority'sine geçmez. Endpoint göreli ve segment bazında doğrulanır; boş/dot segment, `//`, backslash, fragment, userinfo, CR/LF, encoded separator/dot/double-encoding kaçışı reddedilir. Query ayrı tipli çiftlerdir; URL'de auth/secret taşınmaz. Prepared wire URL origin/API kökü ve beklenen encoding ile yeniden karşılaştırılır. Geçersiz hedef sıfır ağ çağrısıyla `invalid_service_target` olur.

Başlıklar ASCII isim ve güvenli değerlerle sınırlıdır; CR/LF/NUL/control kabul edilmez. Caller Host, Content-Length, Cookie, Authorization veya proxy auth ekleyemez. Hizmet adaptörünün auth başlığı private taşıyıcıdan tek yerde eklenir. HTTP header'a taşınamayan credential kırpılmaz/encode edilerek değiştirilmez; `invalid_credential`. SecretValue'nun mevcut UTF-8 kabulü değiştirilmez; bu gönderim sınırının ek koşuludur. İstek body için uzunluk ve Content-Length somut gönderilen baytlarla tutarlıdır.

Redirect kapalıdır, hiçbir 3xx takip edilmez. `trust_env=False`, transport retries=0, HTTP/2 kapalıdır. `Set-Cookie` sonraki isteğe otomatik Cookie üretmez. Ham URL/header/exception repr veya provider body public hata/log değildir. Test CA ve loopback ephemeral port yönlendirmesi yalnız fixture composition'ındadır; production policy bypass'ı sunulmaz.

## Boyut ve süre

| Sınır | İlk uygulama |
|---|---|
| JSON request / tek JSON response | Her biri en çok 1 MiB UTF-8 |
| Her decoded JSON/NDJSON record | Container nesting en çok 32, JSON düğümü en çok 65.536; aşağıdaki tek sayım kuralı |
| Akış okuma parçası | En çok 32 KiB; dosyanın bütünü biriktirilmez |
| NDJSON frame | En çok 512 KiB UTF-8; LF hariç, CRLF kabulünde CR hariç |
| Raw stream toplamı | İstek için açık byte tavanı; en çok 1 GiB |
| Query/header metadata | En çok 64 çift, isim başına 128 ve değer başına 16.384 byte; toplam en çok 64 KiB |
| İstek phase timeout | Connect/read/write en çok 5 s, pool en çok 1 s; kalan total'dan büyük olamaz |
| Total | Çağıranın mutlak monotonic deadline'ı; default yeni yerel fixture çağrısında 30 s, operation'da mevcut daha dar port deadline'ı |

Sınırlar bool/float ile gevşetilmez; süreler sonlu/pozitif olmalı. Geçmiş deadline sıfır ağ çağrısıdır. Dış timeout tüm acquire/header/body/consumer/backoff'u kapsar; her faz/deneme yeni 30 s başlatmaz. Deadline clock'u `time.monotonic()`'tir; asyncio loop clock'una geçerken `loop.time() + max(0, deadline - time.monotonic())` ile kalan süre aktarılır ve dönüşte özgün deadline tekrar denetlenir. Farklı clock epoch'larının eşit olduğu varsayılmaz. `Accept-Encoding: identity`; ilk P01 decoder sıkıştırılmış content-encoding'i reddeder, otomatik açılmış sınırsız içerik yoktur. Başka content codec'i ihtiyaç duyulan endpoint'in ayrı P02 kabulüdür.

JSON/NDJSON için tek yapısal sayım: scalar depth=0, object/array depth=1+en derin child container depth; dolayısıyla root container depth=1'dir. Düğüm sayısı scalar için1, array için1+elemanların düğüm toplamı, object için1+her key başına1+her value'nun düğüm toplamıdır. Key string ayrıca sayılır, container value iki kez sayılmaz. Tam sınır kabul, bir üstü ret; küçük/azami/aşan fixture'lar aynı parser'dan hesaplanmış beklentiye dayanmaz. Request JSON ve endpoint response JSON'a da aynı sınırlar uygulanır; P01 yalnız NDJSON decoder'ında koruma uygulamış sayılmaz.

Raw byte portu yalnız trusted bounded consumer'a gider; public Result veya terminale doğrudan chunk basmaz. JSON strict UTF-8/duplicate/nonfinite/depth/node/size ve endpoint modeli doğrulanır; şema seviyesinde 2xx mantıksal hata da başarısızdır. NDJSON'da buffer/sıra/terminal kuralları [ayrı referanstadır](stream-results.md). Decoder bilinen secret'ı taşıyan alanı public publish'ten önce reddeder; kontrol decoded string/key ve record sınırında yapılır, raw chunk sınırı güven sınırı değildir. Gövdedeki sır/hassaslık kontrolünü generic transport'un uzak anlamı doğruladığı iddiasıyla karıştırma.

## Retry ve hata

Varsayılan max_attempts=1. Yalnız trusted read-only GET/HEAD isteği max_attempts=2 olabilir. Body replay/dispatch/POST retry'si yoktur. Geçici bağlantı hatası veya 408/429/502/503/504 ilk response verisi consumer'a verilmeden retry adayıdır; TLS/401/403/3xx/decoder/oversize/partial-body/stream hatası aday değildir. HTTPX retry=0 ve SDK kullanılmaması bu tek sahipliği korur.

Bekleme ilk retry için uniform `[0, 0,25]` s jitter'dır. `Retry-After` delta veya geçerli UTC HTTP-date ise `max(jitter, gereken bekleme)` kullanılır. Parse için en çok 128 ASCII byte; taşan/negatif/bozuk değer invalid sayılır ve normal jitter'a düşer. Geçerli ama kalan total'a sığmayan bekleme kısaltılmaz; ikinci attempt yapılmaz ve son kontrollü hata döner. HTTP-date hesabı yalnız beklemeyi seçmek içindir; deadline monotonic kalır. Uyku/ikinci attempt öncesinde cancellation/deadline kontrol edilir.

Kararlı hata/exit kataloğunun tek kaynağı [CLI tablosudur](cli-contract.md#önerilen-p01-5-hata-kataloğu). Yeni transport hataları `retryable=false`, ham provider data/details yoktur. Effectful coordinator start hatasında mevcut OperationError ve operation ID/unknown/5 önceliklidir; transport hatası ikinci dispatch hakkı üretmez. Async iptal cleanup sonrası CancelledError olarak sahibine döner; CLI normalizasyonu taşıma içine kopyalanmaz.
