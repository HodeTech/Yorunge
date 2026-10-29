# Kalan P01 işleri: belge, taşıma ve faz kabulü incelemesi

**Tarih:** 2026-10-29. **Dal/taban:** feat/p01-5-transport / development 805f8bd; önceki kapanış commit'i d686c8f. **Durum:** Hazırlık/karar önerisi; P01-5/P01-6 ürün uygulaması veya kabulü değil. Kullanıcı kalan işleri adım/commit/iki fresh review turuyla tek nihai PR'da tamamlama talebinde bulundu.

## İnceleme kapsamı ve gerçek eksik

AGENTS/ilgili beş skill, current/faz/backlog/kart şablonu, ürün kapsamı/matris; mimari overview/integration/execution, ADR-0003/0006/0008/0011–0016 ve reference CLI/config/credential/execution/operation/state sınırları; Python/güvenlik/hata/test/performance/UX/belge/kanıt/Git standartları incelendi. API/CLI, secret/target normalizasyonu, operation coordinator/ports, Result/error modelleri, mevcut contract/integration/kurulum/startup helper'ları ve CI ile karşılaştırıldı. Üç bağımsız ön inceleme taşıma/SDK, stream/iptal, faz kabulü boyutlarını ayrıca değerlendirdi.

P01-1–4 development'a teslim edildi; tekrar uygulanmaz. Açık alt işler **P01-5a, P01-5b, P01-6b**'dir. Bunların ayrıntılı kartları henüz yoktu. Public `Result` completed/null v1, CLI text/json, StartPort/ReadPort sync; HTTP, NDJSON ve düzenli stream/output iptal sınırı yoktur. P01-4 latch/ownership/unknown kararları yeni taşımanın önkoşuludur, yeniden tasarlama gerekçesi değildir.

## HTTP/SDK karşılaştırması

29 Ekim resmî PyPI metadata'sı ve birincil proje belgeleri okundu; paketler ürün ortamına kurulmadı. Sürüm/lisans bilgisi bu okumayı tarihler, bütün sürümlerin uyumunu kanıtlamaz.

| Aday | Gözlem | Öneri |
|---|---|---|
| [HTTPX 0.28.1](https://pypi.org/project/httpx/0.28.1/) | Python≥3.8, BSD-3-Clause; async/sync, havuz/stream | Async sınırda ilk aday; lazy import ve lock/kurulum deneyi gerekli |
| [Requests 2.34.2](https://pypi.org/project/requests/2.34.2/) | Python≥3.10, Apache-2.0; sync, socket idle timeout | Toplam iptal/deadline için ek mekanizma gerekir |
| [aiohttp 3.14.5](https://pypi.org/project/aiohttp/3.14.5/) | Python≥3.10, Apache-2.0 AND MIT; async/ClientTimeout.total | Uygun alternatif; ikinci istemci yığınına ihtiyaç kanıtlanmadı |
| [urllib.request](https://docs.python.org/3.11/library/urllib.request.html) | Stdlib; blocking I/O, proxy/redirect default'ları | Havuz/iptal/politikanın daha çoğu özel kod olur |
| [EVREN SDK 0.11.0](https://pypi.org/project/evren-sdk/0.11.0/) | Python≥3.10, Apache-2.0, httpx≥0.27; endpoint istemcileri | Core bağımlılığı değil; P02'de sabit sürümle endpoint adaptör adayı |

HTTPX wheel SHA-256: `d909fcccc110f8c7faf814ca82a9a4d816bc5a6dbfea25d6591d6985b8ba59ad`. SDK wheel `evren_sdk-0.11.0-py3-none-any.whl`, SHA-256 `a3f0e191819c27c9df2047fdeeceb15d86140066c3f59e1efb6cb8c150416d92`; bağımsız ön incelemede indirilen byte'lar PyPI hash'iyle karşılaştırıldı, ana inceleme metadata hash'ini yeniden doğruladı. SDK kurulmadı/çalıştırılmadı. Kaynak incelemesi bütün endpoint'lerin audit'i değildir.

SDK'nın [sabit yayımlama commit'i](https://github.com/speker/evren-sdk/tree/f4eaa4a71f324e61058f24fb90c0aec7a58ae24f) incelendi: [LLM istemcisi](https://github.com/speker/evren-sdk/blob/f4eaa4a71f324e61058f24fb90c0aec7a58ae24f/evren_sdk/llm_client.py) default 600 s/iki retry, env'den key/base URL ve retry'da idempotency anahtarı kullanıyor; [retry kodu](https://github.com/speker/evren-sdk/blob/f4eaa4a71f324e61058f24fb90c0aec7a58ae24f/evren_sdk/llm_retry.py) ayrı politika sahibi. `trust_env=False` ayarlanmaması da örtük proxy/CA davranışı bırakıyor. Bunlar Yörünge'nin tek snapshot/tek retry/tek total bütçesine doğrudan devredilemez. SDK özelliklerini bütünüyle reddetmek yerine ortak taşıma sınırı korunmalı; endpoint uyumu B03/P02'de ayrıca kanıtlanmalı.

## Deadline ve sync/async bağı

[HTTPX timeout](https://www.python-httpx.org/advanced/timeouts/) faz bazlıdır. [HTTPcore 1.0.9 sync HTTP/1.1 kodu](https://github.com/encode/httpcore/blob/1.0.9/httpcore/_sync/http11.py#L155-L215) aynı read timeout'unu yeni socket okumalarında tekrar kullanır. Bu nedenle header'ı timeout'tan hızlı fakat toplam süreden uzun damlatma, uygulama chunk kontrolüne ulaşmadan bütçeyi aşabilir. Bu turda kaynak üzerinden doğrulandı; yeni ürün runtime deneyi yapılmadı.

Öneri async transport + tüm exchange/consume'u kapsayan [asyncio timeout](https://docs.python.org/3.11/library/asyncio-task.html#timeouts); mevcut sync port için session-owned [Runner](https://docs.python.org/3.11/library/asyncio-runner.html). Active-loop/reentry/thread/PID kapısı **arm öncesi** olmalı. Ayrı thread'i terk etmek veya her anext'i ayrı task'ta sürerek timeout context'ini taşımak seçilmedi. Sync yerel API yeniden yazılmaz. OS blocking/scheduler fiziksel duvar saati garantisi verilmez; slow-header/body/consumer ve cleanup gerçek loopback kabulüdür.

## Sonuç ve iptal uyumu

Result v1'i execution durumlarıyla genişletmek yerine ayrı kapalı StreamEvent önerildi. Mevcut normal komutun NDJSON'u tek terminal result; çok olaylı hat gerçek ürün codec/renderer ile fixture composition'ındadır. Akış EOF'u başarı kanıtı, task cancellation uzak stop başarısı sayılmaz. Output kırılması başarılı terminal store kaydını değiştirmez. Arm sonrası start kaybında mevcut operation_uncertain/5/latch korunur. Bugünkü coordinator BaseException'da unknown kaydını deneyip KeyboardInterrupt/CancelledError'ı yeniden yükseltir; yeni sınır bu bağlamı kaybetmeden CLI/fixture sonucunda ID ve exit5 önceliğini ayrıca uygulamalıdır. Akış terminal adayının trailing veri/EOF doğrulaması tamamlanmadan publish edilmemesi, sonradan hatalı completed çıktısı üretmeyi önler.

Yeni public seçenek, hata kataloğu, istemci ve kaynak ömrü kararları [ADR-0017](../decisions/0017-bounded-http-transport.md) / [ADR-0018](../decisions/0018-stream-results-and-cancellation.md) olarak **Proposed** bırakıldı. İlgili [HTTP](../reference/http-transport.md) ve [stream](../reference/stream-results.md) taslakları onay için somut sözleşmedir. Kullanıcı yeni ADR'leri uygulamadan önce onaylama talep ettiği için bağımlı ürün kodu başlamaz.

## Belge aksiyonları ve kapanış kabulü

- Son talebe uygun P01-5a→5b→6b tek nihai development PR'ı; eski epik başına PR tercihine bu kapanış için açık istisna. Alt kart/adım/kabul ve iki fresh review sınırı korunur; yeni yönetim/branch protection işlemi değildir.
- Testing standardının yalnız ilk offline dilimi anlatan başlığı, gerçekten uygulanmış SQLite/çok süreç/SIGKILL sınırlarıyla hizalanır. Performance standardının P01-4 dış CI'yı gelecek iş diye anlatan cümlesi tamamlanan PR #10 merge kanıtına bağlanır.
- Yeni üç kart, paket planı ve kanonik referans/araştırma/karar indeksleri hazırlanır. Hiçbiri onay veya test geçmeden verified yapılmaz. B01/B03 durumları uygulama/endpoint kapsamı ayrılarak korunur.
- Kapanışta config/state/credential→fixture capability→execution/onay→operation→gerçek TLS loopback→tipli sonuç→restart/jobs yolculuğu, belirsizlikte tek etki ve kesilen/iptal akış testleri gerekir. Gerçek EVREN/ForgeLM/uzak artefakt/Windows/power-cut kabulü değildir.
- Mevcut 500/200 ms startup/jobs ve state/coordinator bütçeleri korunur. Uygulanan raw stream için 16/256/1.024 MiB bounded RSS deneyi yapılır; sentetik byte aktarımı veri seti yükleme desteği değildir. Büyük ölçüm [kanıt politikasına](../standards/research-evidence.md) göre arşivlenir, genel review bağlamına dökülmez.

## Ortam ve yöntem sınırı

Mevcut kayıt Ubuntu24.04/CPython3.11 CI ve macOS/arm64 CPython3.11.18 yerel kanıtıdır. Bu tur salt ortam gözlemi macOS27.0.1 arm64, Python3.11.18, SQLite3.54.1; tam ürün testleri yeniden çalıştırılmadı. Python≥3.11 hedefi bütün üst sürümlerin testli olduğunu söylemez; SQLite≥3.37 hedefi gerçek 3.37 koşusu değildir.

Kapanış CI planı Linux'ta 3.11 ve 3.14, macOS'ta 3.11 uyumluluk işlerini içerir; bunlar **henüz koşulmadı**. Exact image/arch/build/SQLite ve paket kökeni sonuçta kaydedilir. Zorunlu offline-core adı korunur; alt iş fail/cancel/skip iken aggregate yeşil olamaz. Performans kabulü aynı-host referans akışıyla ayrıca yapılır; host değişimi kod regresyonu diye varsayılmaz. Windows testleri simülasyon olarak etiketlenir; jobs list/show aynı unsupported-platform guard matrisine eklenir. Yayın/Master/B12 güvenlik bildirim kanalı ayrı kapıdır.

## Bağımsız belge review kaydı

Üç ön inceleme tamamlandı; ilk taslak **6863582** ile commit edildi. Belge review'ü ürün kabulü değildir.

**R1:** İki fresh ajan, taşıma/güvenlik/dayanıklılık için gpt-6.1-terra/high ve stream/sözleşme/faz kabulü için gpt-6.1-sol/high, d686c8f..6863582 kümesini salt-okunur inceledi. Tek doğrulanmış P2: HTTP tek JSON için zorunlu depth/node sınırının sayısal eşik ve sayım kuralı eksikti. HTTP referansına JSON/NDJSON/request/response için ortak depth32/node65.536, root/scalar/key/container sayımı ve sınır/üstü bağımsız fixture kabulü eklendi; stream referansı tek kurala bağlandı. Ana inceleme monotonic→loop clock epoch dönüşümünü ayrıca netleştirdi. Coordinator'ın BaseException iptalini bugün ham yükselttiği uygulama riski kabul kartında zaten vardı; araştırma mevcut davranışı ve yeni ID/exit5 gereğini açık ayırdı. Sözleşme reviewer'ı ek önemli bulgu doğrulamadı; tercihe dayalı yeni bulgu üretilmedi.

**R2:** Farklı iki fresh ajan, güvenlik/dayanıklılık için gpt-6.1-sol/high ve sözleşme/teslim için gpt-6.1-terra/high, d686c8f..cdef7c6 revizyonunu salt-okunur inceledi. Tek doğrulanmış P2: bağlı operation ID taşıyan stream'in EOF/trailing genel hatasında stream referansı aynı ID'yi, CLI genel katalog ise null ID'yi gerektiriyordu. CLI/stream referansları OperationError(code, bound_operation_id), kapalı reason_code/capacity_kind=null ve aynı genel code/exit kuralına hizalandı; operation bağlamı olmayan genel hatanın null zarfı korundu. P01-5b'ye bağlı ID'li EOF/trailing negatif kabulü eklendi; ID taşımak job mutasyonu/unknown anlamına gelmez. Bulguyu bildiren reviewer güncel üç dosyada fix kapanışını yeniden doğruladı; bu bulgu kapsamında açık çelişki kalmadı. Güvenlik reviewer'ı yeni bulgu doğrulamadı.

**Hazırlık doğrulaması:** check-docs 125 Markdown/0 sorun, check-agent-guides 6 skill/12 kart/0 sorun, diff whitespace temiz. Bu hazırlık yalnız belge değiştirir; runtime testi, build/kurulum, yeni performans veya CI koşusu çalıştırılmadı. İki ADR Proposed ve kartlar draft; kullanıcı onayı sonrası altı ürün adımına geçilebilir. Yeni runtime kabulü geçmiş P01-4 test sayısıyla doldurulmaz.
