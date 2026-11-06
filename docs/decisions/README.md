# Mimari karar kayıtları

**Güncellendi:** 2026-11-05. `Accepted` tasarımın benimsendiğini gösterir; uygulama durumunu [yetenek matrisi](../capability-matrix.md) belirtir.

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
| [0012](0012-credential-identity-and-change-detection.md) | B13 opak kimlik/nesil, özel HMAC doğrulayıcı ve yerel key yaşam döngüsü | Accepted — P01-2b identity gözlem/reset/restore verified; operation tüketicisi ADR-0016 ve PR #10 ile teslim edildi |
| [0013](0013-scoped-capability-cache.md) | P01-3 kapsamlı capability cache, kanıt otoritesi, tazelik/saat ve saklama | Accepted — 2026-10-27 kullanıcı onayı; PR #8 teslimi verified; PR #9 takibi development’a alındı |
| [0014](0014-execution-plan-validity-and-approval.md) | Ayrı execution v2, geçerlilik/onay ve P01-3 bakım uyumluluğu | Accepted — 2026-10-27 kullanıcı onayı; PR #8 teslimi verified; PR #9 takibi development’a alındı |
| [0015](0015-checksummed-data-migrations.md) | ADR-0011'in yalnız yeni V2 adımlarındaki checksum tanımına kısmi değişiklik; V1 1–4 korunur | Accepted — 2026-10-28 kullanıcı onayı; PR #9 uygulama/review/bütçe doğrulandı; development’a merge edildi |
| [0016](0016-operation-admission-and-ownership.md) | P01-4 tek operation/gönderim bağı, lease/fencing, unknown, bounded geçmiş ve yerel jobs | Accepted — 2026-10-29 kullanıcı yetkisi; review revizyonları ve iki fresh tur tamamlandı; dört adımın ürün kabulü verified; PR #10 development merge/CI tamamlandı; canlı EVREN ayrı |
| [0017](0017-bounded-http-transport.md) | Async HTTPX, tek deadline/retry ve SDK sınırı | Accepted — 2026-10-29 kullanıcı yetkisi; P01-5a verified; P01-6b/ADR-0019 kaynak ve CI kabulü verified; PR #11 ile development’a teslim edildi |
| [0018](0018-stream-results-and-cancellation.md) | Result v1 korunarak ayrı stream/NDJSON ve yerel iptal | Accepted — 2026-10-29 kullanıcı yetkisi; P01-5b verified; P01-6b/ADR-0019 kaynak ve CI kabulü verified; PR #11 ile development’a teslim edildi |
| [0019](0019-reference-startup-performance.md) | Startup 500/200 ms kabulünün kaynak bağlı M5 referansına taşınması; Linux tanısının korunması | Accepted — kullanıcı onayı 2026-10-30; uygulama, Sonar/fresh referans ve gerçek CI kabulü verified; PR #11 ile development’a teslim edildi |
| [0020](0020-service-bound-context-discovery.md) | P02-0 hizmete bağlı salt okunur keşif; seçilmiş context, gözlenen principal ve izin ayrımı | Accepted — kullanıcı 2026-10-31 review düzeltmeleri sonrası uygulamayı yetkilendirdi; LLM/Platform kapıları bağımsız; ADR-0021 ile başlangıç/metadata/wire, ADR-0022 ile nihai dar gözlem/kabul kapsamı kısmen değiştirildi |
| [0021](0021-platform-discovery-observations.md) | Platform unverified projeksiyon/başlangıç ve kesin seçim wire’ı; nihai tüketici/kabul hükmü ADR-0022 ile kısmen değişti | Accepted — 2026-11-01 revize karar kullanıcı tarafından onaylandı; uygulama yetkili; nihai dar gözlem/kabul için ADR-0022 geçerli |
| [0022](0022-observed-platform-consumer-contract.md) | Gözleme dayalı sınırlı Platform consumer sözleşmesini nihai sınır yapmak; unknown yetki/kimlik ve seçili canlı proje kapısı korunur | Accepted — kullanıcı 2026-11-01 revize kararı onayladı; ADR-0020/0021’in yalnız Platform nihai tüketici/kabul hükmünü kısmen değiştirir |
| [0023](0023-local-dataset-manifests.md) | Yerel normal dosya envanteri, taşınabilir Manifest v1 ve root dışı no-clobber artifact | Accepted — P02-1, 2026-11-01 kullanıcı review düzeltmeleri sonrası uygulamayı yetkilendirdi |
| [0024](0024-durable-dataset-transfers.md) | P02-2 ayrı private transfer planı, aşama intent/receipt, proje bağı ve ilk recovery sınırı | Accepted — 2026-11-02 kullanıcı review düzeltmeleri sonrası uygulama yetkisi; dış otorite/wire kapıları korunur; ADR-0028 ile tekrarlı içerik kabulü kısmen değiştirildi |
| [0025](0025-isolated-storage-streaming.md) | Ayrı storage hedef/auth politikası ve bounded descriptor request streaming | Accepted — 2026-11-02 kullanıcı review düzeltmeleri sonrası uygulama yetkisi; provider hedef/expiry/wire kapısı korunur |
| [0026](0026-explicit-unverified-transfer-attempts.md) | Verified varsayılanını koruyan açık unverified/unpriced transfer deneme politikası; v2 plan/onay | Accepted — kullanıcı review revizyonu ve iki fresh tur kapandı; ADR-0024 authority/cost/read hükümlerini kısmen değiştirir |
| [0027](0027-durable-created-dataset-context.md) | Create cevabının iki sahiplik alanını dar v2 receipt ile atomik korumak | Accepted — 3 Kasım kullanıcı review düzeltmeleri ve iki fresh tur kapandı; ADR-0026 receipt/legacy/new-success hükümlerini kısmen değiştirir |
| [0028](0028-platform-upload-content-cardinality.md) | İlk Platform upload’ında tekrarlı içerik hash’ini erken reddetme ve özgün çoklu-ad ihtiyacını takip etme | Accepted — 4 Kasım kullanıcı review revizyonu ve iki fresh teyit sonrası uygulama yetkisi; ADR-0024/P02-2 kabulü kısmen değişir |
| [0029](0029-evidence-provenance-privacy.md) | Kayıpsız kanıtta sınırlı tarihsel provenance ve yeni çıktı gizliliği | Accepted — 95 hash bağlı tarihsel kayıt; yeni Git/CI çıktılarında bounded gizlilik kapısı |

| [0030](0030-development-performance-acceptance.md) | Yerel M5 kabulünü açık takipte tutarak geliştirme CI/teslimini sürdürmek | Proposed — kullanıcı kararı bekleniyor; mevcut reference kapıları değişmedi |
| [0031](0031-upload-continuation.md) | Kesintiye uğramış private transferin soy bağlı, kanıta dayalı ve yeni onaylı devamı (aynı operation canlandırılmaz) | Proposed — kullanıcı onayı bekleniyor; ADR-0024 “restart yalnız read” hükmünü kapalı yolda tamamlar |
| [0032](0032-bounded-download-and-verification-levels.md) | Sınırlı akışlı indirme, no-clobber yayın, resume ve kapalı doğrulama seviyeleri; dataset baytı hariç | Proposed — kullanıcı onayı bekleniyor; ADR-0025 GET/expiry hükmünü kısmen değiştirir |
| [0033](0033-dataset-version-references.md) | Veri sürümü ve bölme sayımlarının salt okuma, değişmez referansı; freeze ertelenir | Proposed — kullanıcı onayı bekleniyor |

Yeni karar sıradaki dört haneli numarayla açılır. Zorunlu alanlar: durum/tarih, bağlam, karar, değerlendirilen alternatifler ve sonuçlar. Karar hâlâ açıksa Proposed; geçersizleşmişse yeni karara Superseded bağlantısı kullanılır. İlk kayıtlardaki kabul, ürün talimatları ve bu çalışma kapsamında oluşturulan başlangıç tasarımını ifade eder; dış API erişimi veya yayımlanmış kod onayı değildir.
