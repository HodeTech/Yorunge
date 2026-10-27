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
