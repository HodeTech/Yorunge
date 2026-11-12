---
id: P02-3f
phase: P02
status: verified
size: M
depends_on: [P02-3e]
capabilities: [C03, C12]
---
# P02-3f — Continuation v3 plan tarafı: bağlama, plan, onay, limit/maliyet işi ve politika

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 3 (ilk yarı). [ADR-0031](../../decisions/0031-upload-continuation.md) ve [continuation sözleşmesi](../../reference/dataset-upload-continuation.md) tipleri; kalıcılık ve HTTP yok. Ölçülen büyüklük bu kartı L yaptığından büyüme kuralı gereği ikiye bölündü: plan/onay/politika tarafı burada, kayıt/kontrol/doğrulama ve kullanıcı DTO’ları [P02-3t](p02-3t-continuation-records-and-dtos.md)’dedir.

## Kullanıcı sonucu ve mevcut eksik

Devam için gereken plan ve onay tipleri bugün yoktur; v2 tipleri kapalıdır ve alan eklenemez. Bu kart, v1/v2’yi değiştirmeden strict v3 plan/onay tiplerini, istek limiti ve maliyet işini, bağlama özetini ve yeni hata kodlarını sabitler.

## Giren ve girmeyen kapsam

`ContinuationBinding` (soy bağı, dataset kimliği, baseline özeti, kökten kopyalanan `intent_digest` (tip, bunun plan kapsamından türetilen değere eşitliğini doğrular; kökün saklı değeriyle eşitlik P02-3u okumasındadır), `file_indices`, `uncertain_indices`, `remote_present_count`, iki sınıflandırma özeti, `observed_at`); `DatasetContinuationPlanV3`; `DatasetUploadApprovalV3` (`acknowledge_unconfirmed_effects`); `ContinuationRequestLimits` ve `ContinuationCostWork` (create=0, link=0, M dosya; v3 iş özeti için ayrı domain ayırıcı); canonical kodlama ve bağlama özeti (`observed_at` hariç; plan digest’i ve bağlama özeti her yeni alandan, iş özeti yalnız istek limitlerinden etkilenir); baseline özeti (`baseline_digest`); politika reducer’ının continuation işiyle kullanımı (v2 matrisiyle aynı sonuç); `binding_matches` (üretici ve admission’ın plan bağını taze sınıflandırmayla karşılaştırması: seçim ve iki özet); saf üreticiler `yorunge.application.continuation_policy` (`continuation_limits`, `continuation_binding`, `prepare_continuation_v3`, `approve_upload_v3`: v2 `prepare_upload_v2`/`approve_upload_v2` karşılığı, I/O yok); seçilen baytların tam manifestle doğrulanması (`validate_continuation_selection`); ve yeni `continuation_not_possible` (`ContinuationNotPossible`, kapalı sıralı `blockers` ayrıntısı) ile `continuation_remote_changed` hata kodları (katalog, mesaj, exit) girer. v1/v2 plan ve onay doğrulaması ortak işlevlere (`validate_plan_facts`, `validate_approval_facts`, `check_acknowledgements`) taşınır ve davranışı, byte’ı ve digest’i değişmez; tek bilinçli fark, v2 onay giriş noktalarının (`require_acknowledgements`, `validate_approval_binding_v2`, `approve_upload_v2`) alt sınıf, v3 ve geçersiz girdiyi artık temiz bir hatayla reddetmesidir (`ValueError` / `upload_plan_not_valid`; önceden `AttributeError` veya kabul). Kayıt/kontrol/doğrulama/özet/rapor tipleri (P02-3t), repository/DDL, HTTP, koordinatör ve CLI/API yüzeyi girmez.

## Bağımlılıklar ve kararlar

P02-3e sınıf, engel ve özet tanımlarına bağlıdır. [ADR-0031](../../decisions/0031-upload-continuation.md) Accepted’dir (2026-11-06). Tip alanları [continuation sözleşmesindeki](../../reference/dataset-upload-continuation.md) tablodan kesinleşir; golden vektörler bağımsız (düz `hashlib`/`json` ile) üretilir. Plan yalnız indeksleri ve özetleri taşıdığından sınıf vektörü tip düzeyinde değil `binding_matches` ile denetlenir.

## Sözleşme ve uygulama sınırı

Hepsi strict/frozen/extra-forbid, zorunlu alanlı (nullable dahil), bool≠int; canonical ASCII JSON ve byte sınırları (16 KiB plan) v1/v2 ile aynı. Bağlama özeti soy bağını, dataset kimliğini, baseline özetini, `file_indices`, `uncertain_indices`, `remote_present_count`, iki özeti ve yeni istek bütçesini kapsar; `observed_at`, plan kimliği ve geçerlilik anları kapsamaz. v3 plan yalnız kendi onay sürümüyle eşleşir; v1/v2 çiftleri aynı kalır.

## Kabul

1. Her tip için literal canonical byte ve SHA-256 golden’ları (bağımsız üretilmiş: plan, M=0 ve M=N planları, onay, iş özeti, baseline özeti ön görüntüsü); v1/v2 golden’ları değişmez.
2. Doğrulayıcı negatifleri: sırasız/tekrarlı/aralık dışı indeks, `uncertain_indices ⊄ file_indices`, limit–M uyuşmazlığı, create/link ≠ 0, pencere ≤0 veya >900 s, sürüm eşleşmesi (plan v3+onay v2 vb.), bilinmeyen/eksik alan, bool-as-int, gereksiz/eksik `acknowledge_unconfirmed_effects`, `remote_present_count` ≠ N−M, plan kapsamından türetilenden farklı `intent_digest`; seçilen bayt toplamı tam manifestle sınanır. `binding_matches` negatifleri: seçim, `uncertain_indices`, `remote_present_count` ve iki özetin her biri, değişen uzak durum/zincir durumu, güvenilmez envanter (`inventory_unreliable`, örn. cursor döngüsü; ulaşım hatası değil) ve çağıranın engeli.
3. Bağlama özeti: bağımsız değişebilen her yeni alanın tek tek değiştirilmesi özeti değiştirir (mutasyon testi; `intent_digest` ve `remote_present_count` diğer alanlardan türediği için değişimleri golden’larla sabitlenir); `observed_at`, plan kimliği ve geçerlilik anları belgelenen şekilde dışarıdadır.
4. v2 politika reducer matrisi (96 satır) continuation işinde aynı sonucu verir; tip bunu bilinçle v2 ile aynı bırakır, verified-only veya sağlayıcı oracle’sız kaynağın devamını yasaklamak tip kuralı değil üretici ve uygunluk kuralıdır (`source_ineligible`, P02-3h/3i). `M=0` plan geçerlidir ve ack kuralları değişmez.
5. Yeni hata kodları için istisnanın kendi zarfı (`ContinuationNotPossible.envelope()`: mesaj, exit 2, kapalı sıralı `blockers`, operation kimliği; `source_active` taşınamaz) testlidir. Akış `ErrorDetails` modeli ve üç yeniden sarma noktası (`streams.error_payload`, `stream_results._bound`, `cli.output._bound_error`) bugün `blockers` taşımaz; bunlar P02-3i’de genişletilir ve oradaki testlerle (JSON/NDJSON ve CLI stderr yolu) kanıtlanır.
6. Saf üreticiler (`continuation_limits`, `continuation_binding`, `prepare_continuation_v3`, `approve_upload_v3`): dört golden plan ve iki golden onay bayt bayt yeniden üretilir; limitler seçilen dosyaların tam baytını verir (M=0, M=N dahil) ve sırasız/tekrarlı/aralık dışı/tipsiz indeksi reddeder; sınıflandırmadan kurulan bağ o sınıflandırmayla `binding_matches` verir ve engelli sınıflandırmayı reddeder; plan ömrü pencere ve kanıtların en erken bitişidir, gözlem anı sonradan hazırlanan planda değişmez; Manifest uyuşmazlığı `input_changed`, geçersiz politika seçimi `invalid_request`, seçilen bayt uyuşmazlığı `ValueError`; onay penceresi `[prepared_at, expires_at)`, yanlış digest/draft/yanlış tür `upload_plan_not_valid`, eksik ack `approval_required`, gereksiz/tipsiz ack `invalid_request` (gereksiz olan eksik olandan önce yargılanır).

## Doğrulama

Contract/unit testleri, golden fixture’ları, v1/v2 plan ve politika testlerinin değişmeden geçmesi, Ruff ve strict mypy; belge kontrolleri. Kalıcılık ve ağ davranışı iddia edilmez.

## Teslim kaydı

- PR/commit: tek development PR’ı ([PR #15](https://github.com/HodeTech/Yorunge/pull/15)) bu daldan açıldı ve 2026-11-12’de [69efc8d](https://github.com/HodeTech/Yorunge/commit/69efc8d465078257257d6494e15fda0e360b01e2) merge commit’iyle development’a alındı; adım commit’leri artık development tarihçesindedir: uygulama [810b365](https://github.com/HodeTech/Yorunge/commit/810b365cf1b247522c84aa2a58a3bc3ba3532aa3), özdenetim `3b1a0f7`, R1 düzeltmeleri `861f6f5`, mutasyon yeniden kontrolü `2ea7439`, R2 düzeltmeleri `042c1b5` ve `8857bf9`, R3 düzeltmeleri [113ad15](https://github.com/HodeTech/Yorunge/commit/113ad154e8905a2d47ab48acaf9a854d5c8fb56a); kontrol çıktıları ve review kaydı [uygulama kaydındadır](../../research/p02-3-implementation-validation.md#adım-3--p02-3f-continuation-v3-plan-tarafı).
- Sonuç: Strict v3 plan, onay, bağlama, istek limiti ve maliyet işi tipleri, v2 politika matrisinin (96 satır) continuation işinde aynı sonucu vermesi, iki yeni hata kodu ve plan/onay/limit/bağ üretiminin saf işlevleri bağımsız üretilmiş golden’larla bayt bayt sınanmıştır (313 + 73 test; tam paket 7446 passed, 1 skipped; sonraki commit sonrası contracts ve unit 4961 passed; Ruff, strict mypy, check-docs ve check-agent-guides temiz). R1 (sözleşme/golden ve onay bütünlüğü/düşmanca girdi), R2 (aşağı akış uyumu/belge ve doğruluk/sağlamlık/gerilemesizlik) ve üreticiler için R3 reviewer’larının doğrulanmış bulguları işlendi; v1/v2 refaktörü eski ve yeni ağaçta 4.175 olguluk ve ~60.000 çağrılık fark testlerinde özdeş bulundu (tek fark kasıtlı tür korumaları); 131 + 94 + 86 + 55 reviewer mutantı ile 35 + 66 özdenetim mutantından eşdeğersiz hiçbiri hayatta kalmadı.
- Kalan sınır: *Dilim kapanışındaki durum; tarihsel kayıt olarak korunur. Sonradan: `blockers` taşıyan API/akış hata ayrıntısı P02-3i ile teslim edildi. Güncel durum [epik kapanışındadır](../../research/p02-3-implementation-validation.md#development-merge-kapanışı).* Dilim kapanışında: Yalnız saf tipler ve işlevlerdir: kalıcılık/okuma (P02-3g, P02-3u, P02-3v), yazma kapıları ve onayın `approved`/süre denetimi (P02-3r), taze envanterin iş akışına bağlanması ve üreticinin pencere/`ContinuationCostWork` bileşimi (P02-3h), CLI/API ve akış `ErrorDetails`ının `blockers` taşıması (P02-3i) sonraki dilimlerdedir. `binding_matches` manifesti karşılaştırmaz; `intent_digest`in kökün saklı değeriyle eşitliği depo okumasında doğrulanır. Doğrulayıcı hatalarının üretici ve depo eşlemesi çağıranındır. Canlı davranış iddiası yoktur.

Seçilen adlar ve yerleşim:

- `yorunge.domain.dataset_continuation`: `ContinuationBinding`, `DatasetContinuationPlanV3`, `DatasetUploadApprovalV3`, `baseline_digest`, `require_continuation_acknowledgements`, `validate_approval_binding_v3`, `validate_continuation_selection` ve `binding_matches`.
- `yorunge.domain.upload_costs`: `ContinuationRequestLimits` ve `ContinuationCostWork` (v3 iş özeti için `yorunge-upload-cost-work-v3` domain ayırıcısı); `complete_cost`/`validate_cost_binding` iki iş türünü de kabul eder.
- `yorunge.domain.dataset_upload_v2`: v1/v2 davranışı değişmeden ortak `validate_plan_facts`, `validate_approval_facts` ve `check_acknowledgements`; `reduce_upload_policy` iki iş türünü de kabul eder.
- `yorunge.domain.upload_resume.ContinuationNotPossible` (kod `continuation_not_possible`, exit 2, operation kimliği ve ayrıntıda kapalı sıralı `blockers`) ve `continuation_remote_changed` hata kodu.
- `yorunge.application.continuation_policy`: `continuation_limits`, `continuation_binding`, `ContinuationPreparation`, `prepare_continuation_v3` ve `approve_upload_v3` (saf; v2 üreticilerinin karşılığı). `application/upload_policy.py::approve_upload_v2` ve v2 onay giriş noktaları yalnız tür koruması kazandı (yukarıdaki bilinçli fark).
- Golden fixture’lar `tests/fixtures/dataset-continuation-{plan-v3,plan-v3-verification-only,plan-v3-all-files,plan-v3-evidenced,approval-v3,approval-v3-evidenced,cost-work-v3}.json` (plan, M=0 ve M=N planları, kanıtlı ve kısmi seçimli plan, iki onay, iş özeti) düz `hashlib`/`json` ile bağımsız üretildi; testler özetleri yeniden hesaplar ve üreticiler bu planları ve onayları bayt bayt yeniden üretir.

Commit, kontrol çıktıları ve review kaydı [uygulama kaydındadır](../../research/p02-3-implementation-validation.md#adım-3--p02-3f-continuation-v3-plan-tarafı).
