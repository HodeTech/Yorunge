---
id: P01-5b
phase: P01
status: verified
size: M
depends_on: [P01-5a, P01-4b]
capabilities: [C12, C13]
---
# P01-5b — Tipli akış, NDJSON ve yerel iptal

**Tarih:** 2026-10-29. **Paket:** [Kalan P01](../p01-remaining-delivery-plan.md), adım 3–4. ADR-0018 Accepted; P01-5a iki adım/ikişer fresh review ve final artifact kabulüyle verified; adım 3–4 ikişer farklı fresh review turu, gerçek TLS/süreç ve iki temiz artifact NDJSON kabulüyle tamamlandı/verified.

## Kullanıcı sonucu ve mevcut eksik

Kartın başlangıcında CLI yalnız text/json üretiyordu; ortak stream/NDJSON ve kontrollü pipe/iptal hattı eksikti. Bu kartla kullanıcı mevcut sonuçları satır tabanlı otomasyonda alır; kesilme/yerel iptal completed veya uzak cancelled sayılmaz. Result v1 ve kalıcı operation anlamı korunmuştur.

## Giren ve girmeyen kapsam

Kapalı StreamEvent v1, bounded strict NDJSON codec, ortak tipli sonuç/hata/render hattı, mevcut normal komutlarda opt-in NDJSON, SIGINT/pipe ve async resource cleanup girer. Çok olaylı gerçek taşıma fixture composition'ındadır. Public demo/run/watch/stop/reconcile, SSE/EVREN endpoint codec'i ve yeni senkron public API cancellation parametresi yoktur; bunlar mevcut faz kapsamının dışındadır.

## Bağımlılıklar ve kararlar

P01-4b verified; P01-5a aynı pakette ec2d202 runtime kaynağı ve iki review/kurulum kabulüyle verified; doğrudan bağımlılık kanıtı uygulama kaydındadır. [ADR-0018](../../decisions/0018-stream-results-and-cancellation.md) Accepted; [ADR-0017](../../decisions/0017-bounded-http-transport.md) kaynak/deadline temelidir. 2026-10-29 kullanıcı yetkisi ve belge review düzeltmeleri tamamlandı; ayrı merge gerekmez.

## Sözleşme ve uygulama sınırı

Exact event/sequence/ID/payload/terminal/EOF/byte limitleri [stream referansında](../../reference/stream-results.md), hata/exit [CLI referansında](../../reference/cli-contract.md) kanoniktir. CLI yalnız parse/render; aynı typed event/result/application consumer'ı Python ve fixture composition kullanır. Eski Result/plan digest/state şeması değiştirilmez; provider raw dict/exception public olmaz.

## Kabul

1. Bütün mevcut normal komutlar text/JSON anlamını korur; NDJSON başarı tek sequence 1/result, payload Python/JSON Result v1 ile eşleşir. Help/version insan metadata'sı; erken parser hatası --output=ndjson dahil stdout boş/stderr JSON; seçenek yerleşimi/tekrar ve non-TTY saflığı sınanır.
2. Gerçek loopback byte stream'inde UTF-8/JSON chunk bölünmesi, CRLF, 1 MiB Result/1 MiB + 1 KiB event sınır−1/sınır/sınır + 1, nesting/node, duplicate/nonfinite/unknownfield/version/booleans/order/streamID/operationID bozukluğu sınanır. Terminal adayı messageEOF/trailing doğrulanmadan completed publish etmez; cleanEOF/reset/chunkedtruncation/partialline/terminalsonrası veri ve timeout için referanstaki kesin hata önceliği doğrulanır. Aynı negatifler bağlanmış operation ID ile de çalışır; üretilen tek error ID'yi ve aynı code/exit'i korur, job durumunu değiştirmez.
3. Açık çok-olay consumer'da sıralı progress + tam 1 terminal; first-publish öncesi hata stderr, sonrası tek error stdout. Sahte başarı/ikinci hata/terminal sonrası emit yoktur. Sonuç beklenen kapalı domain modeliyle doğrulanır; provider mantıksal hata 2xx'le success olmaz.
4. HTTP provenance kuralındaki uzun canary farklı chunk/UTF-8 parçalarında yansırsa publish edilmez; kısa sır/sabit field-code çakışması testleri mutlak alt dize yasağı koymaz. Buffer/queue sınırlı, tüketici yavaşken backpressure ve tek total deadline işler. Normal erken close/context exit kaynak kapatıp istisnasız biter; Task.cancel cleanup sonrası CancelledError yayar. İkisi ayrı testtir; retry/resubscribe yoktur.
5. LC_ALL=C/PYTHONIOENCODING=ascii altında nonASCII result/error geçerli UTF-8 byte olarak çıkar; traceback yoktur. Gerçek subprocess SIGINT, BrokenPipe ve diğer output I/O kontrollü exit/hata üretir; ikinci stdout write/atexit traceback yoktur. Critical local config/DB commit çevresi iptalinde kesin rollback, kesin publish ve belirsiz publish ayrımı korunur. Store'daki terminal başarı render hatasıyla unknown olmaz.
6. StartPort arm sonrası iptal/timeout/bozuk receipt operation_uncertain/5 ve ID/latch'i korur; salt izleme iptali request_cancelled/6 ve provider cancelled değildir. Aynı işi tekrar başlatma veya yeni approval ile latch'i açma yoktur. Async CancelledError cleanup sonrası yükselir; global BaseException yutulmaz.
7. Yeni output seçeneğinin beklenen help farkları dışında lazy komut/argument ve v1 wire/digest regresyonu yoktur. Ortak renderer'ın kurulu wheel ve sdist CLI smoke'u gerçek entry point'ten yürür; ayrı fixture formatter başarı sayılmaz.

## Doğrulama

Contract/API/CLI/stream model testleri, TLS loopback ve gerçek subprocess/pipe/signal integration. Ruff/mypy ve doküman/ajan kontrolü; kurulu artefakt ve startup etkisi [P01-6b](p01-6b-phase-acceptance.md)'de son kaynakla birleştirildi. NDJSON protokolü sağlayıcı SSE desteği veya canlı EVREN kanıtı değildir.

## Teslim kaydı

- PR/commit: [0bf70a4](https://github.com/HodeTech/Yorunge/commit/0bf70a4) bu kartın adım 4 runtime/CLI düzeltmesi; [2515533](https://github.com/HodeTech/Yorunge/commit/2515533) gerçek TLS/ayrı süreç kabulü. Nihai development PR’ı paket sonunda açılır.
- Sonuç: İki adım, ikişer farklı fresh review turu ve son fixture review’leri kapandı. Strict tipli olay/codec, normal komutlarda NDJSON/UTF-8, cancel/output ve belirsizlik öncelikleri gerçek TLS/süreç/state testleriyle doğrulandı; iki ayrı artifact’ta gerçek konsol NDJSON ve v1 eşliği geçti. [Kanıt](../../research/p01-remaining-implementation-validation.md#adım4-ve-p01-5b-kapanışı).
- Kalan sınır: Bütünleşik faz/son kaynak kurulumu, performans ve gerçek CI matrisi P01-6b’nin [bf652f6 kaynak/bellek kabulünde](../../research/p01-remaining-implementation-validation.md#kullanıcı-review-kapanışı) bf652f6 kaynağı için verified; son-head startup CI takibi açıktır; public uzak watch/run/SSE veya canlı EVREN/ForgeLM adaptörü teslim edilmez. Eski Result/plan wire korunur.
