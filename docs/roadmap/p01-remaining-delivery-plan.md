# P01 kalan işler — Taşıma, akış ve faz kapanışı

**Durum:** Tamamlandı; ADR-0017/0018/0019 Accepted, P01-5a/b ve P01-6b verified ve [PR #11](https://github.com/HodeTech/Yorunge/pull/11) ile development’a [bc9532c](https://github.com/HodeTech/Yorunge/commit/bc9532cd66c76dc4126162fabd4307c2fdaf4027) merge’ünde teslim edildi. [Merge/kayıt kapanışı](../research/p01-remaining-implementation-validation.md#development-merge-kapanışı) kanoniktir. **Tarih:** 2026-10-30. **Uygulama dalı/tabanı:** feat/p01-5-transport / development 805f8bd. Aşağıdaki uygulama, onay, PR/merge ve saklama bekleyen ifadeler ilgili aşamanın tarihsel kaydıdır; Master/release ayrı kalır.

## Paket sınırı

Kullanıcının kalan bütün Faz 1 işleri talebiyle **P01-5a + P01-5b + P01-6b tek nihai development PR'ında** tamamlanır. Önceki epik başına PR tercihinin bu kapanış paketi için istisnasıdır; her kart/adımın commit ve iki fresh review turu korunur. Önceki P01-1–4 teslimi yeniden yapılmaz. Master/release ve canlı EVREN pilotu kapsamda değildir.

Önce [hazırlık incelemesi](../research/p01-remaining-readiness-review.md), ardından Accepted [ADR-0017](../decisions/0017-bounded-http-transport.md), [ADR-0018](../decisions/0018-stream-results-and-cancellation.md), [HTTP](../reference/http-transport.md) ve [stream](../reference/stream-results.md) sözleşmeleri okunur. 2026-10-29 kullanıcı yetkisiyle review düzeltmeleri ve Accepted geçişi tamamlandı; bağımlı ürün uygulaması başlatıldı ve tamamlandı. Bu hazırlık commit'i ürün adımının tamamlanması değildir.

## Baştan sunulan kararlar

1. HTTPX async + session-owned sync Runner köprüsü; doğrudan SDK core bağımlılığı yok. Tek total deadline, read-only GET/HEAD'de en çok 2 ve effectful'da 1 attempt; proxy/redirect/TLS/secret sınırı ADR-0017'de.
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
| 6 | P01-6b: ortam/CI matrisi, bütün kaynak ve performans kapıları, kanıt/son belge kapanışı | Tam test/lint/type/docs/agent/evidence; wheel+sdist iki kurulum; Linux 3.11/3.14 + macOS 3.11 gerçek sonuç; startup/jobs/stream RSS ve bütçeler; nihai PR |

Her adım geliştirme/anlamlı kontrol/commit → **birinci fresh review** → mevcut kodda doğrulanan minimal fix/test/commit → **farklı fresh ajanlarla ikinci tur** → fix/test/commit döngüsünden geçer. En az iki uzmanlık: ağ/güvenlik/dayanıklılık ve sözleşme/UX/test/kaynak. Model/effort iş karmaşıklığına göre seçilir; head/kapsam/bulgu/skip gerekçesi kayıtlı olur. Yeni bulgu aynı settled kararı kişisel tercih diye yeniden açmaz.

Kart P01-5a adım 1–2 ve gerçek kabul/review bitince verified; P01-5b adım 3–4; P01-6b adım 5–6 sonunda bütün kanıtla verified olabilir. P01-6b'ye başlamak için P01-5b'nin aynı dalda gerçek verified kabulü yeterlidir; ayrı merge beklenmez. Draft kart hazır bağımlılık veya başarılı test diye sunulmaz.

## Kapanış ve PR

Kaynak kimliği, tüm başarısız/başarılı örnekler ve ölçüm ortamı korunur; eski PR #10 ölçümleri yeni bağımlılık/taşıma kaynağının kabulü sayılmaz. [Kartlar](tasks/README.md) ayrıntılı kabulün, [performans](../standards/performance.md) ve [kanıt](../standards/research-evidence.md) ortak bütçe/yöntemin tek kaynağıdır. Test/build ile aynı anda benchmark koşturulmaz. Hedefler sessiz gevşetilmez, atlanan/çalıştırılmayan matris hücresi başarılı gösterilmez.

Son current/faz/matris/reference/modül/README/changelog kayıtları yalnız uygulanan sınıra güncellenir. Bir development PR'ı açılır; son head'in CI ve review sonuçları izlenir, kullanıcı review/merge'ü beklenir. Merge/release yapılmaz. P01 tamamlandı ifadesi bütün kart kabulü bitmeden yazılmaz; P02/P03 canlı hizmet/araç kapsamı P01 teknik borcu diye içeri alınmaz.

## Hazırlık kaydı

### ADR-0019 uygulama takibi — 2026-10-30

Kullanıcı, iki kanıt sözleşmesi review bulgusu kapatıldıktan sonra ADR-0019'un Accepted yapılmasını ve uygulamayı yetkilendirdi. Wheel'in tarihsel kimliği/güncel runtime eşliği ve Linux tanısının görünürlük/kalıcı saklama sorumluluğu kararda ayrıldı. Linux'a özgü yavaşlamanın M5 kapısına rağmen geçebilmesi açık bir kabul sınırıdır.

1. Kapalı startup evidence biçimi, güncel kaynak/kurulu runtime/fixture ve her süreçte süre dışı typed çıktı doğrulaması; bağımsız pozitif/negatif vektörler ve reference verifier. Commit, iki fresh review turu ve doğrulanan fix'ler.
2. Strict Linux diagnostic sınıflandırması, görünür summary/warning/receipt ve 90 günlük artifact; zorunlu M5 startup/jobs ve Linux raw kapıları. Katkı/performans/kanıt belgeleri, CI hata testleri; commit ve iki fresh review turu.
3. Kaynak dondurulduktan sonra yeni wheel/sdist/temiz kurulum, seri fresh M5 startup/jobs/raw kanıtı, üç ortam CI ve kalıcı kayıtlar. Geçmiş başarısızlıklar korunur; açık saklama takibi ve son-head sonuçlarıyla PR #11 güncellenir. Kullanıcı merge eder.

Aşağıdaki durum yalnız hazırlık anına aittir; sonraki uygulama ve kabul yukarıdaki kapanış kaydındadır.

Bu plan ve üç kart hazırlanmıştır; ürün kodu başlamamıştır. İki fresh belge review turu ve doğrulanan iki P2 sözleşme düzeltmesi kapandı. İki ADR, kullanıcının 2026-10-29 yanıtı ve bulgu disposition'larıyla Accepted yapıldı; adım 1'e geçilir. Belge review/doğrulama sonucu [hazırlık raporuna](../research/p01-remaining-readiness-review.md#bağımsız-belge-review-kaydı) kaydedilir; henüz ürün testi/CI/PR kapanışı yoktur.

## PR #11 kullanıcı incelemesi takibi

Kısa secret yanlış pozitifliği, eski high-water baseline'ın ek belleği maskeleyebilmesi, büyüme kararının yalnız tanı olması ve referans komutunun disk etiketi doğrulandı. Ayrıca PR tabanında da bulunan arm commit-sonrası bütçe sınırı mevcut belirsizlik/ID sözleşmesi içinde ele alınır; yalnız eski olması gerekçesiyle ertelenmez. Bu takip aynı PR/dalda kalır; yeni ADR, ürün API’si veya temel bağımlılık kararı gerektirmez. 64 MiB bütçe korunur; üç boyutun mevcut büyümeme şartı önceden ilan edilmiş sonlu aralık kapısıyla sayısallaştırılır.

1. Kaynak düzeltmeleri: provider metadata'sında ortak literal secret kuralı; gerçek commit sınırında belirsizlik; anlık native RSS baseline ve ölçüm penceresi HWM aralıkları; kapalı raw v2 producer/verifier ve bağımsız yanlış-yeşil negatifleri; doğru referans komutu. Anlamlı testler ve commit sonrası iki farklı fresh çok boyutlu review turu, doğrulanan fix/test/commit ile kapanır.
2. Kabul ve belge kapanışı: sabit son kaynakta tam takım/statik/belge denetimleri, iki temiz kurulum, seri startup/jobs/raw v2; eski arşivler korunarak yeni isimler ve güncel kaynak kapısı. Yeni bellek kapısı geçmeden P01-6b verified yapılmaz. Kaynak/ölçüm eşliği ve rapor ayrıca bağımsız incelenir; son PR head'in gerçek üç CI hücresi, Sonar ve review sonuçları izlenir. Kullanıcı merge eder.

Anlık baseline Linux'ta `stat.rss`/gerçek page boyutuyla, Darwin'de `MACH_TASK_BASIC_INFO.resident_size` ile alınır; sonrası native `ru_maxrss` HWM doğrudan baseline'dan çıkarılır. Linux `status.VmHWM` yaklaşımı native sınır testinde reddedildi; ham page ve KiB dönüşümü de kanıtta doğrulanır. Eski tepe nedeniyle gerçek pencere tepesinin kesin olmadığı durum interval olarak kalır; bu belirsizlik boyutlar arası kapıda saklanmaz. OS sayaçlarının sınırları ve sabit 8 MiB çapraz boyut aralığı [performans standardında](../standards/performance.md#kurulu-jobs-ve-raw-stream-ölçümü) kanoniktir. Eski raw v1 kayıtları yeniden etiketlenmez veya güncel kabul diye sunulmaz.
