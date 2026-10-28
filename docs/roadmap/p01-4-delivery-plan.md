# P01-4 — Kalıcı koordinasyon ve yerel iş geçmişi

**Durum:** Karar/onay hazırlığı; ürün uygulaması başlamadı. **Tarih:** 2026-10-28. **Dal:** `feat/p01-4-operations`; taban development `a9f1f2e`. **Güncel onay:** P01-4 uygulaması kullanıcı tarafından istendi; yeni ADR için ayrıca açık onay istenmesi de aynı talebin parçasıdır. [ADR-0016](../decisions/0016-operation-admission-and-ownership.md) Proposed; onaya bağımlı ürün kodu başlamaz. Bu belge hazır planı anlatır, uygulanmış kabul iddiası değildir.

## Paket ve korunacak teslim

P01-4a temeli PR #6'da tamamlandı; tekrar uygulanmaz. Kalan [P01-4b](tasks/p01-4b-operation-coordination.md) + [P01-4c](tasks/p01-4c-local-jobs.md) tek development PR'ına girer. Alt kartlar ve aşağıdaki adımlar commit/kabul/review birimleridir; ayrı PR/merge beklemez. Master aktarımı ve release kullanıcıdadır.

Aynı dalda önceden yetkilendirilip tamamlanan `fae087b`, `cabb36b`, `7462103`, `fc867fc` belge kapanışı/startup ölçüm/CLI optimizasyon commit'leri korunur; [bakım kanıtı](../research/startup-ci-reliability.md). Bunlar P01-4 operation kabulü veya bu yeni adımların review'u sayılmaz. Kullanıcının tercihiyle ayrı PR/test merge yapılmaz; Linux PR/merge ölçümü P01-4 tesliminde incelenir. Önceki merge'in kırmızı performans sonucu yeni ürün çalışmasını bloke etmez.

## Baştan onaya sunulan seçimler

Tek yeni karar paketi ADR-0016 ve ona bağlı [operations wire](../reference/operations.md)'dır. Üç ana seçim birlikte değerlendirilir:

1. **Plan başına tek operation ve geri alınmayan gönderim niyeti.** Sadece başarılı intent commit'inin ilk sahibi bir kez start çağırabilir. Crash/lease/reset/yeni onay ikinci izin üretmez; gönderilmemiş iş dahi konservatif unknown kalabilir. Admission'daki aynı approval arm'a kadar etkin kalır; revoke→yeni onay mevcut operation'ı canlandırmaz. Revoke/reset'in intent sonrası dış etkiyi kesin durduramadığı açık sınırdır.
2. **30 s UTC lease + mevcut clock/fencing ve bounded kalıcı geçmiş.** 1.024 operation / 16 attempt / 256 business geçişi; otomatik silme yok, dolunca güvenli ret. Reset preview v3, history koruma ve owner invalidation; operation runtime restore/recover yasağı mevcut Accepted sınır olarak uygulanır. Saat eski business zamanının gerisine alınmışsa o işin mutasyonu/reset'i UTC yetişene kadar kontrollü bekler. İş ömrüyle 5/30 s yerel çağrı bütçeleri karıştırılmaz.
3. **P01-4 public yüzeyi yalnız yerel jobs list/show.** Genel Result v1 ve plan digest'leri korunur. Trusted observation ve sentetik subprocess yalnız iç/test portundadır; public run/backend/remote kontrol P01-5/P02/P03 kapsamındadır.

Bu seçimler onaylanmadan ürün kodu yazılmaz. ADR dışı rutin dosya/yardımcı isimleri için ek onay döngüsü yoktur. Uygulamada gerçek yeni ürün/uyumluluk kararı çıkarsa somut belgeyle kullanıcıya sunulur; settled kararlar yeniden açılmaz.

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
- Karar: ADR-0016 Proposed; kullanıcı yanıtı henüz yok.
- Uygulama adımları/review/test/PR: başlamadı; gelecek sonuçlar tarih/head ile ayrı uygulama kabul kaydına bağlanacak.
