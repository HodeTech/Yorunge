---
id: P01-5a
phase: P01
status: verified
size: M
depends_on: [P01-2a, P01-4b]
capabilities: [C01, C02, C12, C13]
---
# P01-5a — HTTP taşıma ve SDK sınırı

**Tarih:** 2026-10-29. **Paket:** [Kalan P01](../p01-remaining-delivery-plan.md), adım 1–2. ADR-0017/0018 2026-10-29 kullanıcı yetkisiyle review düzeltmeleri sonrası Accepted; iki ürün adımı, ikişer fresh review turu ve artifact kontrolleriyle tamamlandı/verified; P01-6b bf652f6 kaynak/bellek kabulü kayıtlı; son-head startup CI takibi ve ADR-0019 onayı açık.

## Kullanıcı sonucu ve mevcut eksik

Gelecek hizmet adaptörü seçilmiş hedef/credential ile bounded ve iptal edilebilir ağ çağrısı yapabilmeli; katmanlar istekleri kontrolsüz tekrar etmemeli. Bugünkü API yalnız yerel kullanım senaryoları ve sync trusted operation portları taşır; HTTP istemcisi seçilmedi.

## Giren ve girmeyen kapsam

Async tipli port, HTTPX adaptörü/lazy bağımlılık/lock, hedef/TLS/sır, tek deadline/retry ve owned Runner köprüsü girer. Gerçek TLS loopback/operation fixture composition'ı kabul içindir. EVREN SDK core bağımlılığı, gerçek hizmet endpoint adaptörü, credential'sız signed-URL aktarımı, SSE, HTTP/2, public URL/debug/demo/run/watch/stop ve canlı hesap istekleri yoktur. B03'ün P02 endpoint sınırı korunur.

## Bağımlılıklar ve kararlar

P01-2a PR #6, P01-4b PR #10 ile verified. B01/B03 [ön incelemesi](../../research/p01-remaining-readiness-review.md) tamamlandı; [ADR-0017](../../decisions/0017-bounded-http-transport.md) Accepted. Kullanıcı, bulgular doğrulanıp düzeltildikten sonra Accepted geçişini ve uygulamayı açıkça yetkilendirdi; önceki iki fresh belge turu ve kullanıcı review disposition'ı raporda kayıtlıdır.

## Sözleşme ve uygulama sınırı

Domain/application somut HTTPX bilmez; adapter private request/response/context ve exact [HTTP sözleşmesini](../../reference/http-transport.md) uygular. Existing credential/ServiceTarget ve operation latch/portdeadline korunur. Sink raw chunk'ı public API/çıktı saymaz; endpoint modeli gereklidir. CLI/provider başlık biçimi uydurmaz. Bounded JSON/raw stream aynı resource lifecycle'ını kullanır.

## Kabul

1. Gerçek TLS loopback'te CA/hostname olumlu; yanlış CA/host/HTTP/origin/API kökü/CRLF/absolute veya encoded kaçış negatif. Prepared URL tekrar denetlenir; iki sunucuda redirect sıfır ikinci request ve sıfır secret sızıntısı gösterir. Env proxy/CA/netrc ve kullanıcı auth/Host override'ı etkisizdir; aynı origin farklı path/hizmet ve retry sonrası Cookie yoktur, cookie jar ayrıca deny/clear ile sınanır.
2. Aynı credential snapshot kullanılır; non-ASCII/header'a uygun olmayan secret controlled invalid_credential, dönüşüm yoktur. Provider kaynaklı dinamik alanlarda bütün uzunluklarda tam eşitlik, ≥8 byte canary'de alt dize yansıması reddedilir; sabit alan adı/enum/yerel code/message taranmaz. 1 byte a, sabit hata kodu ve alan adıyla çakışan sır örnekleri kabul edilir; kısa sırın gömülü parçası için mutlak çıktı yasağı yoktur. Root INFO/DEBUG path/query canary'si loga çıkmaz; unrelated caller log'u değişmez. Private HTTPX istisnası/ham yol/header public zarf değildir.
3. Read-only GET/HEAD transient durumda en çok 2, effectful 1 attempt gerçek sunucu sayaçlarıyla doğrulanır. 401/403/3xx/TLS/malformed/oversize/partial-stream retry yok; jitter/Retry-After, shared total ve phase/pool timeout bağımsız beklentilerle sınanır. Geçmiş deadline ve invalid request sıfır ağdır.
4. Header/body damlatma, sessiz socket, havuz beklemesi, yavaş callback ve backoff total deadline'da kesilir. Cancel/erken consumer exit'te response/socket/task kapanır; background istek/worker kalmaz. Cleanup veya scheduler gecikmesi mutlak OS garantisi diye raporlanmaz.
5. Sync köprü active-loop/reentry/başka thread/PID ve fork'ta **env/DB/admit/arm/ağ öncesi** kontrollü ret verir. Aynı session havuzu tekrar kullanır; async context tek owner task'tır. Mevcut sync yerel API event loop içinden çalışmayı sürdürür.
6. Gerçek SQLite coordinator + loopback fixture: admission/onay/finalcredential/latch korunur; prearm iptal sıfır effect, start sonrası timeout/kayıp cevap/iptal en çok 1 effect ve kalıcı unknown/5. Restart/takeover/reset/new approval ikinci gönderim üretmez; read-only observer iptali provider_cancelled olmaz.
7. Domain ErrorCode/MESSAGES/exit kataloğu onaylı 10 kodla genişletilir; her kod için YorungeError/OperationError/afterarm reason_code ve exit 1/3/6 eşliği tablo testidir. ReadPort 404/401/403/network/5xx/malformed→observation/reason eşlemesi ayrı gerçek coordinator kabulüdür; jobs uzak sorgu yapmaz. Boyut/depth/node, gzip/bomb/invalidUTF8/NaN/duplicate/oversizeline ve raw-only okuma sınırları pozitif/negatif fixture ile kanıtlanır. Yeni bağımlılıkla wheel/sdist iki temiz kurulum ve HTTPX'in help/version/context/cache/jobs yerel yola import edilmediği kontrol edilir. Stream/RSS ve bütünleşik son performans kabulü P01-6b'dedir.

## Doğrulama

Unit/contract ve gerçek TLS/socket/SQLite/alt süreç integration; fault/timeout/cancellation/request-count/secret guard. Ruff/mypy/belge/ajan/evidence, frozen lock/build/iki kurulum. [CONTRIBUTING](../../../CONTRIBUTING.md#doğrulama-seçimi) geçerlidir. Ağ davranışı test double'ın kendi kendisine başarısı değil gerçek sınırda kanıtlanır.

## Teslim kaydı

- PR/commit: [ec2d202](https://github.com/HodeTech/Yorunge/commit/ec2d202) bu kartın adım kaynağıdır; adım 1 3c68e22/a2250db/2dee624 ve adım 2 61fe655/ec2d202 aynı paket dalındadır. [PR #11](https://github.com/HodeTech/Yorunge/pull/11) development hedefiyle açıktır; merge kullanıcı incelemesini bekler.
- Sonuç: İki adımın ikişer fresh review turu/fix'leri ve source-matched hedefli HTTP/JSON/TLS/session/SQLite/cancel/race/restart kontrolleri [uygulama kaydındadır](../../research/p01-remaining-implementation-validation.md). Son runtime kaynağında wheel/sdist iki temiz kurulum, import kökeni ve mevcut smoke'lar geçti; Ruff/strict mypy/belge/kart/diff temiz.
- Kalan sınır: Public HTTP/debug/run veya EVREN/SDK adaptörü yoktur. Stream/CLI P01-5b ve bütünleşik final kurulum/ortam/performans P01-6b’nin [bf652f6 kaynak/bellek kabulünde](../../research/p01-remaining-implementation-validation.md#kullanıcı-review-kapanışı) bf652f6 kaynağı için verified; son-head startup CI takibi açıktır; bu kart canlı hesap veya fiziksel güç kesintisi kanıtı değildir. Deadline cooperative kontrol ve ölçülebilir kabul hedefidir.
