# P01-4 — Kalıcı koordinasyon ve yerel iş geçmişi

**Durum:** ADR-0016 Accepted; dört adım ikişer fresh review ve son kaynak yerel kabulüyle kapandı. P01-4b/4c bu dalda verified; development aktarımı PR/kullanıcı incelemesine tabidir. **Tarih:** 2026-10-29. **Dal:** `feat/p01-4-operations`; taban development `a9f1f2e`. **Güncel onay:** Kullanıcı review düzeltmeleri ve iki fresh revizyon turu tamamlandı; verilen yetkiyle Accepted geçişi yapıldı. Önceki Proposed/onay-bekleyen, kabulün henüz yapılmadığı veya kontrollerin çalıştırılmadığı ifadeler ilgili aşamanın tarihsel kaydıdır; güncel yerel paket kabulü bu girişte ve son uygulama kaydındadır.

## Paket ve korunacak teslim

P01-4a temeli PR #6'da tamamlandı; tekrar uygulanmaz. Kalan [P01-4b](tasks/p01-4b-operation-coordination.md) + [P01-4c](tasks/p01-4c-local-jobs.md) tek development PR'ına girer. Alt kartlar ve aşağıdaki adımlar commit/kabul/review birimleridir; ayrı PR/merge beklemez. Master aktarımı ve release kullanıcıdadır.

Aynı dalda önceden yetkilendirilip tamamlanan `fae087b`, `cabb36b`, `7462103`, `fc867fc` belge kapanışı/startup ölçüm/CLI optimizasyon commit'leri korunur; [bakım kanıtı](../research/startup-ci-reliability.md). Bunlar P01-4 operation kabulü veya bu yeni adımların review'u sayılmaz. Kullanıcının tercihiyle ayrı PR/test merge yapılmaz; Linux PR/merge ölçümü P01-4 tesliminde incelenir. Önceki merge'in kırmızı performans sonucu yeni ürün çalışmasını bloke etmez.

## Baştan onaya sunulan seçimler

Tek yeni karar paketi ADR-0016 ve ona bağlı [operations wire](../reference/operations.md)'dır. Üç ana seçim birlikte değerlendirilir:

1. **Plan başına tek operation ve geri alınmayan gönderim niyeti.** Başarılı intent commit'inin ilk sahibi PID'ye bağlı tek permit ile start çağırır. Her credential admission/takeover/arm transaction'ında tekrar karşılaştırılır. Aynı etkin approval gerekir; revoke→reapprove yeni execution hakkı üretmez. Latch boş/owner ölü/onay geçersiz işi ayrı cleanup izin vermeden terminalleştirir. Intent sonrası reset/revoke dış etkiyi kesin durdurmaz.
2. **30 s UTC lease + recovery ve bounded kalıcı geçmiş.** 1.024 lifetime operation/16 attempt/256 normal business geçişi; bütün plan slotları bağlanınca yeni plan üretimi durur, otomatik silme yoktur. Recovery sahipliği/reset slot tüketmez, orphan terminal reserve'i yeni sahibi de kullanır. Event sequence/clock epoch gerçek UTC gerilemesini temsil eder; +1 yıl ileri saat credential reset veya yeni epoch reconciliation'ını kilitlemez. Port için min(kalan çağrı,kalan lease)−5 s deadline ve sonuç payı; I/O için fiziksel duvar saati garantisi verilmez. Restore/recover yasağı mevcut Accepted sınırdır.
3. **P01-4 public yüzeyi yalnız yerel jobs list/show.** Genel Result v1 ve plan digest'leri korunur. Trusted observation ve sentetik subprocess yalnız iç/test portundadır; public run/backend/remote kontrol P01-5/P02/P03 kapsamındadır.

2026-10-29 talebi bu revizyonların kapanışı sonrası Accepted geçişini ve uygulamayı yetkilendirir. ADR dışı rutin dosya/yardımcı isimleri için ek onay döngüsü yoktur. Gerçekten bu paketin dışında yeni ürün/uyumluluk kararı çıkarsa somut belgeyle kullanıcıya sunulur; settled kararlar yeniden açılmaz.

## Uygulama sırası

| Adım | Kart / somut teslim | Kapanış odağı |
|---|---|---|
| 1 | P01-4b: strict operation/attempt/outcome modelleri, yeni V2 şema/repository ve gerçek decode/snapshot consumer; plan FK/restrict; operation-runtime restore/recover kapısı | Immutable 1–5; gerçek DB/migration/bozuk kayıt/plan forget ve eski intent retleri; yoğun migration bütçesi |
| 2 | P01-4b: aynı çağrı güncel admission, approval snapshot, lease/renew/takeover/fencing, tek kullanımlık dispatch sınırı ve composition portu | İki süreçte tek operation/tek intent/en çok bir sentetik etki; expiry/clock/ownership ve commit kesinti sınırları |
| 3 | P01-4b: unknown/trusted reconciliation/terminal sonuç, bounded geçiş/kapasite ve reset preview v3/tarihçe invalidation bütünleşmesi | Wrong-target/not-found/cancel/delivery negatifleri; reset/revoke/credential/forget yarışları; full yoğun/bütçe kabulü; kart kapanışı |
| 4 | P01-4c: ortak CLI/Python jobs list/show, exact cursor/filter/text/JSON ve kullanıcı belgesi | Restart/boş liste/snapshot/bozuk kayıt, kurulu artefaktlar, normal/yoğun 30-process 200 ms kabulü; paket kapanışı |

Her adımda önce geliştirme ve anlamlı kontroller → açık dosya listesiyle commit → bağımsız fresh reviewer'larla birinci çok boyutlu tur → bulguyu mevcut kodda doğrula, geçerliyse minimal fix/test/commit, değilse gerekçeyi kaydet → farklı fresh reviewer'larla ikinci tur → doğrulanmış fix/test/commit. İnceleme uzmanlıkları en az domain/SQLite-dayanıklılık ve public sözleşme/UX/test/kaynak boyutlarını kapsar. Model/effort karmaşıklığa göre seçilir; her turun kapsam/head/bulgu disposition'ı gerçek kanıtta tutulur. Gerçek blocker yoksa sonraki adıma otomatik geçilir.

Kart P01-4b adım 1–3 birlikte kanıtlandıktan sonra verified olabilir; ilk schema commit'i kartı tamamlamaz. P01-4c doğrudan bağımlılığı gerçek commit/review kanıtı olmadan ready yapılmaz. Uygulama henüz yokken kartların draft olması bilinçlidir.

## Bütünleşik kapanış ve PR

Her kartın ayrıntılı kabulü kendi belgesindedir; burada tekrar edilmez. Adım 4 sonunda tam test/Ruff/mypy/belge/ajan/diff, wheel/sdist üye kontrolü ve iki temiz kurulum; mevcut lazy/stateless v1/cache/execution ile yeni jobs smoke yapılır. Migration ve normal/yoğun startup/jobs raw JSON'ları source/OS/CPU/Python/disk/fixture bilgileriyle tutulur; önceki kaynak bütçeleri gevşetilmez. CLI optimizasyonunun 30 yardım çıktısı eşliği ve izole paired CI ölçüm akışı korunur.

Ardından current/faz/matris/modül/reference/README/changelog yalnız kanıtlı sınıra güncellenir, bir development PR'ı açılır ve head CI sonuçları değerlendirilir. PR kullanıcı incelemesine bırakılır; otomatik merge/release yoktur. CI'da gerçek yeni hata çıkarsa inceleme/fix sürer; uzak performans sonucu yerel kabul diye gizlenmez. P01-4 bitince sıradaki paket P01-5a/5b'dir; bu plan P01-5 uygulaması yetkisi değildir.

## Kayıt

- Ön inceleme: [P01-4 hazırlık raporu](../research/p01-4-readiness-review.md).
- Karar: 2026-10-29 kullanıcı yanıtı, doğrulanan düzeltmeler ve iki fresh tur sonrası ADR-0016 Accepted.
- Uygulama: adım 1 şema/repository commit'i a73608a, birinci review fix'i 1049ab2; ikinci fresh tur ve doğrulanmış son fix'ler tamamlandı. [Kabul kaydı](../research/p01-4-implementation-validation.md#adım-1--ikinci-review-ve-kapanış). Adım 2 admission/lease/dispatch 7d75322, review fix'leri 2ba731e/ee7f7a3 ile iki fresh turda kapandı; 1.469 test geçti. Adım 3 83f55bc/0092d40 ile iki fresh turda kapandı; 1.594 test, son kaynakta 27/27 operation + 24/24 migration kabulü geçti. P01-4b bu dalda verified; adım 4 5c7ad8c/4941bf3/17de965 ile iki fresh turda kapandı. Son ürün kaynağında 1.700 full test, iki temiz kurulum, 30-process jobs/paired startup ve 27 operation + 24 migration kabulü tamamlandı; development PR'ı kullanıcı incelemesine sunulur.
