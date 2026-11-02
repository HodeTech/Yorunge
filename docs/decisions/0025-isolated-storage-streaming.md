# ADR-0025: Depolama hedefi ve sınırlı dosya gönderiminin hizmet HTTP'sinden ayrılması

**Durum:** Proposed; kullanıcı onayı bekleniyor. **Tarih:** 2026-11-02. **İş:** P02-2b. [Araştırma](../research/p02-2-readiness-review.md), [transfer önerisi](0024-durable-dataset-transfers.md), [kanonik taslak](../reference/dataset-transfer.md). Uygulanmış signed URL/streaming upload desteği değildir.

## Bağlam

[ADR-0017](0017-bounded-http-transport.md) göreli endpoint ve ≤1 MiB bytes request'i kabul eder; genel signed URL veya büyük streaming request yoktur. SDK credentialed client ile dönen URL'ye PUT yapar; güncel web istemcisi ise `direct_upload_url` için ayrı credentialsız XHR, `upload_url` için hizmet proxy'si kullanır. İki yolun auth/hedef/expiry kuralları eşit varsayılamaz. İmzalı URL'nin query'si yetki taşır; yeniden urlencode edilmesi imzayı değiştirebilir.

## Önerilen karar

### İki açık hedef türü

Private `StorageRequest` portu async bounded byte kaynağı ve strict hedef descriptor'ı alır. Platform JSON/credential request portunun endpoint/query veya body sınırı gevşetilmez; mevcut bütün tüketiciler aynı kalır. Ortak HTTPX kaynak sahipliği, TLS, cookie reddi, log filtresi ve timeout cleanup mekanizmaları kullanılır; ayrı retry sahibi veya SDK eklenmez.

| Hedef türü | İzin ve auth sınırı |
|---|---|
| API proxy | Yalnız saved Platform origin/API kökü altında, exact dataset ID ve doğrulanmış upload path/query sözleşmesi. Yalnız aynı hedefe bağlı Platform credential eklenebilir; LLM key veya başka header kaynağı yoktur |
| Direct signed storage | Planın **önceden açık seçilmiş exact HTTPS/443 origin allowlist'i** ve provider path/prefix sözleşmesi. Platform/LLM credential, Cookie, proxy auth veya caller Authorization **asla** eklenmez. Yetki yalnız doğrulanmış kısa ömürlü URL/header descriptor'ıdır |

Presign yanıtı allowlist'i genişletemez. Wildcard/suffix/subdomain tahmini veya yalnız aynı hostname testi yoktur. Custom origin ancak kullanıcı plan hazırlarken açık seçilmişse kullanılabilir; local/private adresler için örtük otomatik erişim açılmaz. Hedefin ilgili ortam için kabulü ayrı kaynak/pilot kanıtına bağlıdır; public internet SSRF sandbox'ı iddia edilmez. Redirect hiçbir türde takip edilmez; signed URL başarısızsa proxy'ye veya başka host'a fallback yapılmaz.

URL'de userinfo, fragment, control/CRLF, backslash, traversal/encoded-separator kaçışı, scheme-relative authority veya değişmiş API kökü reddedilir. Signed URL ≤16 KiB ASCII; özgün path/query byte sırası ve percent encoding korunur. HTTPX'in prepared wire hedefi descriptor'la eşit değilse ağdan önce ret vardır. İmzayı koruma path güvenlik denetimini atlamaz; desteklenmeyen encoding fail-closed reddedilir. Literal credential'ın dinamik path/query/yerel alanlara taşınması mevcut kısa/tam-eşitlik ve ≥8 UTF-8 byte alt-dize kuralıyla engellenir.

Direct descriptor'da doğrulanmış expiry şarttır; yok/bozuk/geçmiş süre kabul edilmez. Mevcut total, lease veya URL expiry'den önce **5 s pay** bırakılır. İstek için yeterli kalan süre yoksa yeni presign yapılmaz; mevcut iş güvenle durur. Proxy expiry/authorization kuralı ayrıca provider contract'tan gelir; direct expiry kuralı tahmin edilerek proxy'ye uygulanmaz.

### Sırlar ve kalıcılık

Signed URL, imzalı query/header değerleri, provider error body ve ham HTTP exception yalnız private çağrı ömründedir; DB/journal/plan, Result/NDJSON, artifact, receipt, repr veya log'a girmez. URL hash'i de public korelasyon kimliği yapılmaz. Kalıcı kimlikler yalnız operation/stage/dataset ve tüketici için güvenli olduğu doğrulanmış bounded object-key/file bağlarıdır. Object key'in kendisi yetki taşıyorsa saklanmaz; exact uzlaştırma için gereken güvenli kimlik sözleşmesi kapanmadan yol ready olmaz.

HTTPX/httpcore INFO/DEBUG kayıtları owned context'te filtrelenir; global logging ayarı değiştirilmez. Her iki client'ın cookie kabul/gönderimi kapalıdır; `trust_env=False`, redirects/retries=0, TLS doğrulaması açık, HTTP/2 kapalı kalır. Private kaynağın/payload'ın kapatılması her success/error/cancel yolunda aynı task'ta tamamlanır. Gerçek Task.cancel cleanup sonrası CancelledError olarak yayılır; bilinen operation ID ve belirsizliğin gözleneceği yol kaybolmaz. CLI yerel iptali uzak iptal saymaz; kalıcı belirsizlikte exit 5 önceliği korunur.

### Byte kaynağı ve bütçeler

Request bütün dosyayı bytes'a çevirmez. No-follow/nonblocking descriptor'dan bloklu async kaynak, exact Content-Length ve gönderilen byte/SHA-256 sayacını taşır. İlk stat boyutundan fazla byte okunmaz; kısa okuma/büyüme/root-zincir veya son stat farkı kontrollü değişimdir. Gönderim hash'i plandaki manifestle eşleşmeden confirm yoktur; önceden gönderilmiş nesnenin otomatik silindiği iddia edilmez.

En çok **2 dosya worker**, worker başına bir açık kaynak ve **1 MiB chunk**, toplam uygulama byte kuyruğu en çok **2 MiB** önerilir. HTTP iç buffer'ı dahil gerçek ek RSS ayrıca ölçülür; queue sınırı toplam bellek iddiası değildir. Storage request body genel üst sınırı 1 GiB'dır; P02-2 provider tüketicisinin daha dar dosya limiti uygulanır. Content-Length, MIME ve varsa provider-required checksum header'ı kapalı allowlist'ten üretilir; user Host/Content-Length/Cookie/auth/header dict'i kabul edilmez.

PUT tek denemedir; timeout/connection-refused/429/5xx bile otomatik replay veya URL yenilemesi üretmez. Phase connect/read/write en çok 5 s, pool 1 s; PUT total en çok 120 s, coordinator/lease/expiry kalanından büyük olamaz. Response ham body ≤64 KiB'dır; yalnız endpoint'in kapalı success oracle'ı kabul edilir. 2xx/ETag tek başına SHA-256 veya confirm kanıtı değildir. Sonraki list/read metadata ve gerektiğinde uzak byte doğrulaması ayrı seviyelerdir.

## Alternatifler

- Credentialed hizmet client'ına keyfî URL/body vermek: hedef ve sır sınırını siler; seçilmedi.
- Yalnız `https`/hostname testi veya presign'dan allowlist türetmek: yetkiyi yanıtın kendisine verir; seçilmedi.
- SDK upload metodu: bütün dosyayı okur, hedef/auth ve replay politikasını sahiplenir; ortak bounded port seçildi.
- Query'yi yeniden oluşturmak, credential'ı her PUT'a eklemek veya hata halinde proxy fallback: kanıtlanmış davranış değildir; seçilmedi.

## Sonuçlar ve kabul

ADR-0017'nin mevcut service request sözleşmesi korunur; yeni storage portunun güven sınırı bu karardır. Hangi direct origin/proxy path/header/expiry biçiminin gerçekten kullanıldığı provider wire ve ayrı yetkili canlı kabulde kapanır. Bu onay canlı çağrı veya genel indirme/resume desteği vermez.

Kabul; iki farklı gerçek loopback TLS sunucusuyla Platform key'in yalnız doğru origin'de bulunması, same-host/different-port/path/service, redirect, prepared URL değişimi, query canary/log/exception/cancel sızıntısı, eksik expiry, kısa/uzun credential, bozuk Content-Length ve partial PUT yollarını sınar. Gerçek streaming upload'da 16/256/1024 MiB toplam fixture, 2 worker/2 MiB queue ve [native RSS yöntemi](../standards/performance.md#kurulu-jobs-ve-raw-stream-ölçümü) ile U≤64 MiB/G≤8 MiB kabulü saklanır. 1.024 MiB consumer fixture'ı dosya başına 500.000.000 byte sınırını aşmayan birden çok dosyadır; genel port tek dosya 1 GiB sınırı ayrıca sınanır. Mevcut download benchmark'ı upload kanıtı yerine geçmez.
