# P01-3 uygulama ve kabul kaydı

**Tarih:** 2026-10-27. **Durum:** Uygulanıyor; ilk cache adımı doğrulanıyor, epik tamamlanmadı. **Dal:** feat/p01-3-capability-planning; **taban:** development@78d5d77. [Paket planı](../roadmap/p01-3-delivery-plan.md), [iki iş kartı](../roadmap/tasks/README.md).

## Onay ve yöntem

Kullanıcı ADR-0013/0014 ve bağlı ScopeV2 kararlarını onayladı; `6e91690` onay commit'idir. [Ön inceleme ve iki kullanıcı review'inin doğrulanması](p01-3-readiness-review.md) tasarım kanıtıdır; ürün uygulaması yerine sayılmaz. Her adım kod/test/belge → commit → yeni ajanlarla review 1 → doğrulanmış fix/commit → başka yeni ajanlarla review 2 → doğrulanmış fix/commit döngüsünü tamamlar. Sonunda tek development PR'ı kullanıcı incelemesine açılır; otomatik merge yoktur.

## Adım 1 — Açık capability cache ve clock

V1 modelleri ve offline builder değişmeden ayrı kapalı ScopeV2/evidence/record oluşturuldu. Public `query_capabilities` ve CLI `--cached`/`--refresh` aynı use case'i kullanır; arbitrary producer/evidence/authorization girdisi yoktur. Gerçek ürün producer'ı yalnız mevcut yerel politika/not-verified verir. Fixture'daki live-account kanıtı üretim desteği değildir.

SQLite migration 1→2 private store'a cache ve clock tablolarını ekler; eski checksum değişmez. Tam/tek satır validation, canonical key/projection/group, kaynak sürümü, quota/çelişki saklama, son UTC/monotonic süre kapısı ve güncel identity/target kontrolü vardır. Clock generation business rollback'ten bağımsız kalır. Kaynağı kayıp eski restore stage/live çifti aynı intent epoch/K ile yeni şemaya yükseltilir; reset cache'i etkisizleştirir, kimlik geçmişini korur. Unknown operation tüketicili runtime restore'u reddeder.

İlk hedefli scope/cache koşusunda 63 test, daha sonraki tam koşuda 903 test geçti (55,73 s). Foundation state/bakım alt takımı 184 testte başarılıdır. Bunlar Linux, gerçek Windows, canlı EVREN veya fiziksel güç kesintisi kanıtı değildir. Yeni platform kapıları ve son bütünleşik kontroller aşağıda gerçekleşince kaydedilir; review turları henüz tamamlanmadı.

Tarihsel v1 migration fault deneyleri yalnız o testlerde açık identity-only manifest fixture'ına bağlandı; güncel default store/CLI testi şema 2'yi, yeni integration testi gerçek 1→2 geçişini ve doğrulanmış v1 backup'ını denetler. Negatif/rollback kabulü kaldırılmadı. İki süreçli refresh çelişkisi, iki credential/rotation, unknown auth için historical-only sonuç, overflow ve aggregate TTL'den uzun proof saklama, reset/restore, eski intent'in stage yok/stage/live ve kaynak kaybı senaryoları gerçek dosya/DB/süreçlerle sınanır.

### İlk performans kanıtı

[Ham ölçüm](p01-3-step-1-startup.json): macOS 27.0.1 arm64, Apple M5 Max (yerel sysctl), CPython 3.11.18, editable `.venv`, SSD (yerel disk bilgisi). 1.024 gerçek kayıt; toplam payload 1.212.625 bayt, en büyük kayıt 1.233 bayt. Dataset yalnız `tests/fixtures/seed_capability_cache.py` ile sentetik olarak üretildi; public discovery backend'i değildir. Benchmark her komutta ilk süreç + üç ısınma + 30 ayrı süreç kullanır; OS/disk cache boşaltılmaz.

İlk sıcak p95 help 34,383 ms, version 23,605 ms, context 79,017 ms ve cache 159,543 ms; 500/200 ms hedefleri geçti. Bu ilk uygulama ölçümüdür; bütün P01 veya gelecek plan/approval bütçesi sayılmaz. Test/ölçüm sıralı koştu; benchmark ile tam suite eşzamanlı yük oluşturmadı. Cache 32 KiB üst sınırında dolu kayıt deneyi değil, kaydedilen hacim için kanıttır.

## Sonraki adımlar

İlk adımın iki fresh review turu ve doğrulanmış düzeltmeleri bitmeden P01-3a verified veya P01-3b ready yapılmaz. Sonra execution hazırlığı/validity, ardından onay/yönetim/bakım ve bütünleşik PR kabulü aynı dalda sürer. Kalıcı plan/onay, run, operation/lease/jobs, HTTP, uzak keşif ve gerçek adaptör bu ilk cache adımında uygulanmış sayılmaz.

### Adım 1 / review 1

İlk ürün commit'i `a3287b0`. Üç yeni ajan state/saat (GPT-6 Astra/high), evidence/scope ve CLI/API/teslim (GPT-6.1 Sol/high) boyutlarını bağımsız inceledi. Ortak bulgular tekilleştirildi ve gerçek SQLite/public API ile doğrulandı:

- Son transaction örneği kayıt TTL'sini denetlemiyordu: commit öncesi TimeGate eklendi; tam expiry'de business yazımı rollback olur, gözlenen clock invalidation kalır.
- Clock COMMIT gecikmesi ve sonraki kayıt sorgusu önceki sonucu eskitebiliyordu: commit sonrası gözlenen saat kalıcılaştırılır; tüm public kayıtlar ortak son snapshot ile yeniden değerlendirilir. Kilit bekledikten sonraki UTC örneği kullanılır; eşzamanlı süreçlerin eski örneği sahte rollback üretmez.
- Bazı yerel nedenlerin insan açıklaması genelleşiyordu: proje/runtime/uyumsuzluk/araç açıklamaları tamamlandı.
- DB decoder duplicate key'i zaten reddediyordu; doğrudan v2 model JSON parser'ı reddetmiyordu: yalnız yeni WireModel sınırına recursive duplicate/nonfinite/UTF-8 kontrolü eklendi. V1 parser değişmedi.

Regresyonlar son transaction örneğini, COMMIT sonrası expiry/rollback'i ve iki kayıt arasında expiry/rollback'i doğrudan tetikler; tüm sonuçlar unknown'a düşer ve clock fence kalır. Eksik proje CLI açıklaması ve üst/iç JSON duplicate ayrıca sınanır. İlk yeni koşu iki süreç testinde kilit öncesi alınan UTC örneğinin yanlış fence üretmesini yakaladı; örnek kilit sonrasına taşındı, kabul/eşik gevşetilmedi.

Temiz kurulum smoke'u macOS `/var` symlink'ini güvenli state kökü olarak reddetti; denetim scratch konumunu kanonik fiziksel yola bağladı. Wheel/sdist iki temiz ortamda gerçek kurulu CLI/import ve refresh→cached smoke'u geçti; bunlar review düzeltmelerinin ara build kanıtıdır, final paket yerine sayılmaz.

### Adım 1 / review 2

Üç farklı yeni ajan invariants/state/saat (GPT-6 Astra/high), trust/scope ve CLI/teslim (GPT-6.1 Sol/high) incelemesini `cd8e812` üzerinde tamamladı. Trust ve teslimde doğrulanmış yeni bulgu yok: sırasıyla 77 ve 565 hedefli test; parser ve gerçek SQLite overflow/kota probları başarılı. State/saat ajanı producer başlangıcındaki UTC örneğinin sonradan üzerine yazılması nedeniyle gözlenen ileri→geri dönüşün ret/restart sonrasında eski supported'ı canlandırmasını doğruladı. Ara gözlemlerin high-watermark ve gereken nesil bağı kayıpsız tutuldu; producer öncesi/başarı/hata sonrası kısa kalıcı saat kapıları eklendi. İki sıçrama yönü, producer hatası ve restart; ayrıca tick öncesi üzerine yazılan örnek yeni regresyonlardır. Düzeltme sonrası cache integration 29 test ve strict lint/type başarılıdır. `cd8e812` tam suite sonucu 926 testtir (77,59 s); son düzeltmenin final kontrolleri ayrıca kaydedilir.


### Adım 1 kapanışı — 2026-10-28

Round2 saat bulgusu aynı reviewer'ın dört gerçek SQLite başarı/hata probuyla yeniden doğrulandı: ret, unknown, kalıcı generation2 ve restart miss; bulgu kapandı. Çok kayıtlı okuma tek transaction ve ortak son snapshot'a toplandı; iki kayıt arasındaki saat değişimi regresyonu gerçek `_read` sınırında sürer.

Son tam takım **929 passed (60,14 s)**; Ruff format/lint, strict mypy 34 kaynak, 104 belge/0 sorun ve altı skill/yedi kart/0 sorun geçti. Wheel34/sdist197 üyeli build ve iki temiz kurulu import/CLI/refresh→cached smoke başarılıdır; son paket bütün epik sonunda yeniden üretilir.

[Clock kapıları sonrası ilk ölçüm](p01-3-step-1-clock-gate-startup.json) cache p95 223,335 ms ile 200 ms bütçesini **geçemedi**. Profiling, her kayıt için ayrı clock commit'lerini gösterdi. İşlem/süre/güven kapıları kaldırılmadan çoklu okuma ortak transaction'a alındı. [Son ölçüm](p01-3-step-1-final-startup.json): aynı CPU/SSD/editable kurulumda 1.024 kayıt, toplam payload 1.212.625 bayt; 30 ayrı süreçte p95 help23,565, version25,217, context91,039 ve cache157,082 ms. Her örnek gerçek fresh hit olduğunu doğrular. Eşik gevşetilmedi; başarısız ham kayıt da tutuldu.

P01-3a kendi kabulüyle verified; P01-3b adım 2 başladı. Cache temizliğinin gerçek plan/onayları koruması P01-3b/bütünleşik kabulde ayrıca tamamlanacaktır. Epik ve PR henüz tamamlanmadı.

## Adım 2 — Kalıcı execution hazırlığı ve validity

2026-10-28: Ayrı ExecutionPlan v2 ve immutable digest; prepare/list/show/validate API/CLI, trusted validation portu ve ürünün açık blocked politikası uygulandı. SQLite2→3 gerçek plan tüketicisi, bounded cursor listesi, 1.024 plan/64KiB/128 input limiti, plan-aware preview v2 ve restore/reset full validation eklendi. API yalnız composition yapar; güncel validation uygulama katmanında, dosya/SQL adaptörleri tipli portların arkasındadır. Cache ile ortak tam scope builder kullanılır; v1 modelleri değişmedi.

Descriptor walk her root/ara/son bileşende no-follow kullanır; FIFO okunmaz. Önce/sonra stat ve zincir kimliği, içerik hash'i, root anchor/inode, CWD değişimi ve byte-identical root değişimi sınanır. 16MiB/256MiB/1GiB sparse sentetik dosyada tam okuma ve Python allocation peak<8MiB testi geçti; gerçek model/data closure veya fiziksel I/O garantisi değildir. 1GiB+ ve toplam30s retleri, hash sırasında root/içerik değişimi, path traversal ve descriptor kapanışı testlidir.

İlk execution/input alt takımı37 test geçti. İlk tam takım965 başarılı/1 başarısızdı: yeni execution_plans tablosu eski exact şema assertion'ında yoktu; assertion gerçek şemayla güncellendi. Sonraki execution/input/state/platform alt takımı253 testte başarılı; mypy38 kaynak ve Ruff geçti. Yeni komutlarda üç platform/fcntl senaryosu gerçek ayrı süreçte simüle edilir; gerçek Windows koşusu değildir. İki review turu henüz başlamadan bu kanıt ürün kapanışı sayılmaz. Approval/revoke/forget sonraki adımdadır.
