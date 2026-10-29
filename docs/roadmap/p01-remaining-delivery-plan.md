# P01 kalan işler — Taşıma, akış ve faz kapanışı

**Durum:** ADR-0017/0018 Accepted; P01-5a, P01-5b ve P01-6b çalışma dalında verified. Altı adımın review ve kabulü, gerçek üç hücreli CI ve kaynak bağlı performans kapısı [kapanış kaydında](../research/p01-remaining-implementation-validation.md#faz-kapanışı-ve-gerçek-ci). Tek development PR üzerinden son-head kontrolü ve kullanıcı incelemesi izlenir; merge kullanıcıdadır. **Tarih:** 2026-10-29. **Dal:** feat/p01-5-transport. **Taban:** development 805f8bd; mevcut d686c8f P01-4 kapanış belgeleri korunur.

## Paket sınırı

Kullanıcının kalan bütün Faz 1 işleri talebiyle **P01-5a + P01-5b + P01-6b tek nihai development PR'ında** tamamlanır. Önceki epik başına PR tercihinin bu kapanış paketi için istisnasıdır; her kart/adımın commit ve iki fresh review turu korunur. Önceki P01-1–4 teslimi yeniden yapılmaz. Master/release ve canlı EVREN pilotu kapsamda değildir.

Önce [hazırlık incelemesi](../research/p01-remaining-readiness-review.md), ardından Accepted [ADR-0017](../decisions/0017-bounded-http-transport.md), [ADR-0018](../decisions/0018-stream-results-and-cancellation.md), [HTTP](../reference/http-transport.md) ve [stream](../reference/stream-results.md) sözleşmeleri okunur. 2026-10-29 kullanıcı yetkisiyle review düzeltmeleri ve Accepted geçişi tamamlandı; bağımlı ürün uygulaması başlatıldı ve tamamlandı. Bu hazırlık commit'i ürün adımının tamamlanması değildir.

## Baştan sunulan kararlar

1. HTTPX async + session-owned sync Runner köprüsü; doğrudan SDK core bağımlılığı yok. Tek total deadline, read-only GET/HEAD'de en çok2 ve effectful'da1 attempt; proxy/redirect/TLS/secret sınırı ADR-0017'de.
2. Result v1 korunur; ayrı StreamEvent v1 ve mevcut normal CLI komutlarına tek-result NDJSON. Yerel cancel/output kapanışı uzak cancelled sayılmaz; arm sonrası unknown/5 değişmez. Ayrıntı ADR-0018'de.

Sayı/sınırlar önerilen sözleşmelerde somuttur; yeni hizmet endpoint'i, ödünç provider başarısı veya fake public backend açma onayı istenmez. CI matrix/isim ve doküman hizalaması mevcut görevin rutin uygulamasıdır. Başka ürün/güven sınırı kararı ortaya çıkarsa uygulamadan önce somut belgeyle sunulur; settled ADR'ler yeniden açılmaz.

## Sıra ve review birimleri

| Adım | Kart ve teslim | Gerekli kapanış |
|---|---|---|
| 1 | P01-5a: tipli async request/response/deadline/retry portu, HTTPX adaptörü ve lazy bağımlılık/lock; kapalı hedef/header/body politikası | Gerçek TLS loopback, prepared URL, env/proxy/cookie/header/redirect/secret, slow-header/body ve total timeout; wheel/sdist etkisi |
| 2 | P01-5a: owned session/Runner, cancellation/resource/bounded pool, StartPort/ReadPort fixture composition'ı | Arm öncesi bridge guard; bir effect ve kayıp cevapta unknown/restart; read-only retry sayısı, after-arm cancel/deadline ve late reply |
| 3 | P01-5b: kapalı StreamEvent, strict bounded codec, terminal/EOF/backpressure ve typed sonuç hattı | Gerçek chunk/UTF-8/duplicate/oversize/trailing/slow-consumer; secret reflection; resource cleanup ve task cancellation |
| 4 | P01-5b: ortak CLI renderer/NDJSON/error ve SIGINT/BrokenPipe; kullanıcı/API belgeleri | Bütün normal komutlarda eski text/JSON eşliği; single-result NDJSON, parseöncesi hata; mutation/commit uncertainty önceliği; subprocess/pipe ve lazy help |
| 5 | P01-6b: gerçek loopback/süreç/SQLite ile bütünleşik kabul, restart/unknown ve kurulu artefakt smoke'u | Config→kimlik→kanıt→plan/onay→operation→taşıma/stream→jobs; sıfır ikinci dispatch ve bağımsız beklenen sonuçlar |
| 6 | P01-6b: ortam/CI matrisi, bütün kaynak ve performans kapıları, kanıt/son belge kapanışı | Tam test/lint/type/docs/agent/evidence; wheel+sdist iki kurulum; Linux3.11/3.14 + macOS3.11 gerçek sonuç; startup/jobs/stream RSS ve bütçeler; nihai PR |

Her adım geliştirme/anlamlı kontrol/commit → **birinci fresh review** → mevcut kodda doğrulanan minimal fix/test/commit → **farklı fresh ajanlarla ikinci tur** → fix/test/commit döngüsünden geçer. En az iki uzmanlık: ağ/güvenlik/dayanıklılık ve sözleşme/UX/test/kaynak. Model/effort iş karmaşıklığına göre seçilir; head/kapsam/bulgu/skip gerekçesi kayıtlı olur. Yeni bulgu aynı settled kararı kişisel tercih diye yeniden açmaz.

Kart P01-5a adım1–2 ve gerçek kabul/review bitince verified; P01-5b adım3–4; P01-6b adım5–6 sonunda bütün kanıtla verified olabilir. P01-6b'ye başlamak için P01-5b'nin aynı dalda gerçek verified kabulü yeterlidir; ayrı merge beklenmez. Draft kart hazır bağımlılık veya başarılı test diye sunulmaz.

## Kapanış ve PR

Kaynak kimliği, tüm başarısız/başarılı örnekler ve ölçüm ortamı korunur; eski PR #10 ölçümleri yeni bağımlılık/taşıma kaynağının kabulü sayılmaz. [Kartlar](tasks/README.md) ayrıntılı kabulün, [performans](../standards/performance.md) ve [kanıt](../standards/research-evidence.md) ortak bütçe/yöntemin tek kaynağıdır. Test/build ile aynı anda benchmark koşturulmaz. Hedefler sessiz gevşetilmez, atlanan/çalıştırılmayan matris hücresi başarılı gösterilmez.

Son current/faz/matris/reference/modül/README/changelog kayıtları yalnız uygulanan sınıra güncellenir. Bir development PR'ı açılır; son head'in CI ve review sonuçları izlenir, kullanıcı review/merge'ü beklenir. Merge/release yapılmaz. P01 tamamlandı ifadesi bütün kart kabulü bitmeden yazılmaz; P02/P03 canlı hizmet/araç kapsamı P01 teknik borcu diye içeri alınmaz.

## Hazırlık kaydı

Aşağıdaki durum yalnız hazırlık anına aittir; sonraki uygulama ve kabul yukarıdaki kapanış kaydındadır.

Bu plan ve üç kart hazırlanmıştır; ürün kodu başlamamıştır. İki fresh belge review turu ve doğrulanan iki P2 sözleşme düzeltmesi kapandı. İki ADR, kullanıcının 2026-10-29 yanıtı ve bulgu disposition'larıyla Accepted yapıldı; adım1'e geçilir. Belge review/doğrulama sonucu [hazırlık raporuna](../research/p01-remaining-readiness-review.md#bağımsız-belge-review-kaydı) kaydedilir; henüz ürün testi/CI/PR kapanışı yoktur.
