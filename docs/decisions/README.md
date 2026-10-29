# Mimari karar kayıtları

**Güncellendi:** 2026-10-29. `Accepted` tasarımın benimsendiğini gösterir; uygulama durumunu [yetenek matrisi](../capability-matrix.md) belirtir.

| ADR | Karar | Durum |
|---|---|---|
| [0001](0001-platform-companion.md) | EVREN odaklı kapsamlı yardımcı ürün | Accepted |
| [0002](0002-forgelm-default-open-tools.md) | ForgeLM varsayılanı ve seçilebilir muadiller | Accepted |
| [0003](0003-lightweight-python-core.md) | Hafif, modüler Python çekirdeği | Accepted |
| [0004](0004-local-durable-operation-state.md) | Yerel işlemsel operasyon durumu | Accepted |
| [0005](0005-capabilities-and-contracts.md) | Kanıt/kapsam bağlı yetenek sözleşmeleri | Accepted |
| [0006](0006-cli-and-public-api.md) | Ortak çekirdek üzerinde CLI ve Python API | Accepted |
| [0007](0007-mit-and-documentation.md) | MIT ve tek kanonik belge yapısı | Accepted |
| [0008](0008-offline-core-stack.md) | Çevrimdışı ilk dilimin paket, CLI ve şema seçimi | Accepted — uygulandı |
| [0009](0009-development-and-release-branches.md) | Development PR ve Master release akışı; merge commit | Accepted |
| [0010](0010-roadmap-readiness-and-agent-skills.md) | Hazır iş kartı, dar faz sınırları ve ortak ajan skill kütüphanesi | Accepted |
| [0011](0011-state-foundation-and-migrations.md) | B02 yerel store, dayanıklılık ve işlemsel migration temeli | Accepted — P01-4a temeli verified; operation/lease tüketicisi ADR-0016 ve PR #10 ile teslim edildi |
| [0012](0012-credential-identity-and-change-detection.md) | B13 opak kimlik/nesil, özel HMAC doğrulayıcı ve yerel key yaşam döngüsü | Accepted — P01-2b identity gözlem/reset/restore verified; operation tüketicisi sonraki iş |
| [0013](0013-scoped-capability-cache.md) | P01-3 kapsamlı capability cache, kanıt otoritesi, tazelik/saat ve saklama | Accepted — 2026-10-27 kullanıcı onayı; PR #8 teslimi verified; PR #9 takibi development’a alındı |
| [0014](0014-execution-plan-validity-and-approval.md) | Ayrı execution v2, geçerlilik/onay ve P01-3 bakım uyumluluğu | Accepted — 2026-10-27 kullanıcı onayı; PR #8 teslimi verified; PR #9 takibi development’a alındı |
| [0015](0015-checksummed-data-migrations.md) | ADR-0011'in yalnız yeni V2 adımlarındaki checksum tanımına kısmi değişiklik; V1 1–4 korunur | Accepted — 2026-10-28 kullanıcı onayı; PR #9 uygulama/review/bütçe doğrulandı; development’a merge edildi |
| [0016](0016-operation-admission-and-ownership.md) | P01-4 tek operation/gönderim bağı, lease/fencing, unknown, bounded geçmiş ve yerel jobs | Accepted — 2026-10-29 kullanıcı yetkisi; review revizyonları ve iki fresh tur tamamlandı; dört adımın ürün kabulü verified; PR #10 development merge/CI tamamlandı; canlı EVREN ayrı |
| [0017](0017-bounded-http-transport.md) | Async HTTPX, tek deadline/retry ve SDK sınırı | Accepted — 2026-10-29 kullanıcı yetkisi; P01-5a verified; P01-6b son-head startup CI takibi açık; development PR review/merge ayrı |
| [0018](0018-stream-results-and-cancellation.md) | Result v1 korunarak ayrı stream/NDJSON ve yerel iptal | Accepted — 2026-10-29 kullanıcı yetkisi; P01-5b verified; P01-6b son-head startup CI takibi açık; development PR review/merge ayrı |
| [0019](0019-reference-startup-performance.md) | Startup 500/200 ms kabulünün kaynak bağlı M5 referansına taşınması; Linux tanısının korunması | Accepted — kullanıcı onayı 2026-10-30; uygulama sürüyor |

Yeni karar sıradaki dört haneli numarayla açılır. Zorunlu alanlar: durum/tarih, bağlam, karar, değerlendirilen alternatifler ve sonuçlar. Karar hâlâ açıksa Proposed; geçersizleşmişse yeni karara Superseded bağlantısı kullanılır. İlk kayıtlardaki kabul, ürün talimatları ve bu çalışma kapsamında oluşturulan başlangıç tasarımını ifade eder; dış API erişimi veya yayımlanmış kod onayı değildir.
