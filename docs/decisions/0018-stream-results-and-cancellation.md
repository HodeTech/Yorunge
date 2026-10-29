# ADR-0018: Sürümlü akış sonucu ve yerel iptal

**Durum:** Proposed — kullanıcı onayı bekleniyor; ürün kodu uygulanmadı. **Tarih:** 2026-10-29. **İş:** P01-5b.

## Bağlam

Genel `Result[T]` v1 yalnız `completed`/null operation ID taşır. İşin kendi durumu jobs data içindedir. CLI text/JSON uygular; NDJSON, ortak akış doğrulayıcı ve düzenli output kesintisi davranışı yoktur. `OperationCoordinator` arm sonrası belirsizliği zaten korur. Result enum'unu execution/stream durumlarıyla genişletmek eski tüketiciyi bozabilir. Gerçek uzak run/watch/stop P01'e dahil değildir.

## Karar önerisi

### Ayrı event, korunan sonuç

`Result` v1 ve eski JSON/text anlamı korunur. Ayrı kapalı `StreamEvent` v1 eklenir; `progress`, `result`, `error` etiketli union'dır. Tam wire, limit ve sıralama [akış referansında](../reference/stream-results.md), public hata/exit tablosu yalnız [CLI referansında](../reference/cli-contract.md) tutulur. Stream ID invocation'a ait rastgele UUIDv4'tür; operation ID veya tekrar gönderim izni değildir.

CLI'nin mevcut normal komutlarında `--output ndjson` başarılı tek-sonuç çağrısını **tek `result` olayı** içinde taşır; payload eski tipli Result v1'in aynısıdır. Metadata help/version insan odaklı kalır. Yapay progress, public fixture/demo/backend, public run/watch/stop/reconcile veya gerçek EVREN desteği eklenmez. Çok olaylı gerçek taşıma/süreç kabulü test composition'ında aynı ürün decoder/event/renderer hattını kullanır; ayrı fixture renderer ürün kabulünün yerine geçmez.

İlk tam event publish'inden önce hata stdout boşken stderr'de mevcut JSON hata zarfıdır. Başlamış NDJSON akışında terminal hata stdout'ta **bir `error` olayıdır**, stderr'e ikinci hata zarfı yazılmaz. Başarılı açık akışta tam bir terminal result; başarısız açık akışta tam bir terminal error olur. Terminalden sonra veri yoktur. EOF/bağlantı kapanışı terminal kanıtı yerine geçmez; terminalden sonra veri de protokol hatasıdır. Kısmi satır başarılı event sayılmaz. JSON modu hiçbir zaman art arda JSON parçaları üretmez.

Upstream codec hizmet adaptörüne aittir. Ortak event wire'ı sağlayıcının SSE veya NDJSON biçimi varsayılmaz; P01'in strict NDJSON codec kabulü SSE adaptörü teslimi değildir. Ham body/header/provider açıklaması event'e kopyalanmaz. Bilinen secret kontrolü ve strict model doğrulaması tamamlanmadan veri publish edilmez. Kırpılmış/eksik output üzerine yapay completed özeti eklenmez.

### Kaynak ömrü ve iptal

Async stream context'i response, deadline ve sahip task'ı birlikte taşır. `Task.cancel()`/context exit/`aclose` okumayı ve yerel beklemeyi bitirir; finally cleanup'tan sonra `CancelledError` kütüphane sınırında yeniden yükseltilir. Herhangi bir event'i önceden yutma, yeni stream/retry, background worker veya uzak stop çağrısı yoktur. Mevcut public senkron API imzalarına kullanılmayan cancellation token eklenmez; gerçek async taşıma tüketicisi [ADR-0017](0017-bounded-http-transport.md)'nin owned composition'ıdır.

CLI sınırında SIGINT kontrollü `request_cancelled`/6, kapalı stdout `output_closed`/6 olur: anlamı **yerel çağrı/izlemenin bırakılmasıdır**; kayıtlı işin veya yerel yazının geri alındığını, uzak işin `cancelled` olduğunu söylemez. Kritik yayın/commit belirsizliği ve bilinen operation hatası genel iptal tarafından ezilmez. Arm sonrası start çağrısındaki timeout/iptal/bozuk cevap mevcut `operation_uncertain`/5 ve operation ID'yi korur; latch silinmez, ikinci start yoktur. Read-only izlemeyi bırakmak tek başına job durumunu değiştirmez. Kesin uzak `cancelled` yalnız mevcut trusted observation kanıtıyla kaydedilir.

SIGINT'in critical write/commit sınırında görüldüğü yollar ayrıca sınanır: kesin tamamlanan yazı yeniden denenmez, kesin rollback iptal olarak biter, sonucu belirlenemeyen config yayını mevcut `config_write_uncertain`/5 olur. Sonucu bilinen başarıdan sonraki render/output hatası başarılı kalıcı işi unknown'a dönüştürmez. Yeni bir genel catch ile bütün `BaseException` türleri bastırılmaz.

BrokenPipe sonrası stdout'a yeniden terminal basılmaz veya kapanış flush traceback'i üretilmez. Kaynaklar kapatılır, safe stderr hatası mümkünse bir kez yazılır; stderr de kapalıysa çıktı zorlanmaz. Önceden belirlenmiş belirsiz yan etki exit 5 önceliğini korur. Açık pipe'ta terminal yazımı hedefi, alıcısı kapanmış bir pipe için teslim garantisi değildir.

## Alternatifler

- Genel Result v1'e running/unknown/cancelled eklemek eski yerel sözleşmeyi gereksiz değiştirir; reddedildi.
- Her komutta yapay progress veya public test backend açmak gerçek kullanıcı işi üretmez; reddedildi.
- Yerel task iptalini provider stop başarısı saymak veya kesilmiş yanıtı boş başarılı sonuç yapmak mevcut etki sözleşmesini bozar; reddedildi.
- Her senkron API'ye cancel parametresi ve thread köprüsü eklemek gerçek tüketici olmadan kapsamı büyütür; seçilmedi.

## Sonuçlar ve kabul

Kullanıcı mevcut yerel komutları satır tabanlı otomasyona bağlayabilir; gerçek uzak stream komutu teslim edilmez. Akış codec'i katı byte/line/event sınırı, backpressure, terminal ve resource ownership testlerini geçer. [P01-5b kartı](../roadmap/tasks/p01-5b-stream-results.md) CLI/Python eşliğini, split UTF-8, slow/truncated stream, cancel/output ve after-arm unknown kabulünü bağlar. İlk uygulama eski v1 plan/Result digest'lerini değiştirmez; yeni output seçeneği help çıktısındaki beklenen fark olarak ayrıca kaydedilir.

Birincil kaynaklar (erişim 2026-10-29): [Python task cancellation](https://docs.python.org/3.11/library/asyncio-task.html#task-cancellation), [async generator kapanışı](https://docs.python.org/3.11/reference/expressions.html#asynchronous-generator-iterator-methods), [Runner/SIGINT](https://docs.python.org/3.11/library/asyncio-runner.html#handling-keyboard-interruption), [BrokenPipeError](https://docs.python.org/3.11/library/exceptions.html#BrokenPipeError), [NDJSON proje belirtimi](https://github.com/ndjson/ndjson-spec).
