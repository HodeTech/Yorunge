---
id: P02-3g
phase: P02
status: draft
size: M
depends_on: [P02-3f]
capabilities: [C03, C12]
---
# P02-3g — Continuation kalıcı okuma tarafı: 3 tipli decode, v3 graf doğrulama, kapasite ve bakım

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 4. Okuma/doğrulama yarısı; yazma kapıları P02-3r’dedir. Ayrım ölçülmüş: create-ilk varsayan doğrulayıcıların listesi tek başına bir review birimidir.

## Kullanıcı sonucu ve mevcut eksik

v3 tipleri kalıcı geçmişte okunup doğrulanamadan kapasite hesabı, list/show, reset önizlemesi ve tam doğrulama çalışmaz: `decode_versioned` iki tip imzalıdır, graf doğrulayıcıları create-ilk ve 2+3N varsayar, rezervasyon formülü her kayıt okumasında doğrulanır ve her plan satırı kapasite/snapshot hesabında çözülür. Bu yarım yapılmadan herhangi bir v3 satırı store genelinde `state_invalid` üretir.

## Giren ve girmeyen kapsam

Girer: `decode_versioned`in üçüncü sürümü bütün çağrı noktalarında; **salt okuma zincir/baseline çözümleyicisi** (kaynak → kök görünümü, 3 tipli doğrulanmış → CreateReceiptV2; özeti `baseline_digest` ile eşit; uyuşmazlık/kopukluk `state_invalid`) ve ona geçirilecek çağrı noktalarının kontrol listesi (`created_dataset`/`legacy_create_without_baseline`, `require_created_baseline`, `_baseline_in_view`, arm, acquire_read, read_failed, prepare_initial_read, `_verified`, original producer’ın detail↔baseline karşılaştırması); `validate_graph` v3 için `StageGraphSpec` ile (gerekli aşamalar, öncül, `request_digest` plan bağından, `_stage_outcome` dataset kimliği plandan, `_operation_header`: `intent_digest` saklı alan olarak kökle eşit, latch kuralı v2 ile aynı (`bool(intents)==latched`; `verification_only` kayıt unlatched succeeded olabilir) ve `len(intents) ≤ 3M`, v3 namespace invariant’ı `namespace.create_operation_id == baseline_operation_id`, `verification_after` boş makbuzla, `_verify` 3M makbuz + N dosya proof ve sürüm eşliği); `operation_reservation` ve `capacity()` plan türüne göre; summary/review projeksiyonunun v3’ü `legacy_history_only` saymaması; reset önizleme/`upload_snapshot` parmak izi ve global expiry hesabı; eski-binary etkisinin belgelenmesi. Girmez: save/approve/admit/arm/receipt/read/proof yazma kapıları, HTTP, public yüzey, DDL.

## Bağımlılıklar ve kararlar

P02-3f tipleri verified olmalıdır. [ADR-0031](../../decisions/0031-upload-continuation.md) Accepted’dir (2026-11-06). DDL gerekirse koddan önce kullanıcı kararı alınır. Eski binary uyumu [ADR-0031](../../decisions/0031-upload-continuation.md) §6’daki kontrollü `state_invalid` retidir; etki alanı (aynı state dizinini paylaşan eski binary’nin upload komutlarını ve reset önizlemesini yitirmesi) belgelenir.

## Sözleşme ve uygulama sınırı

Mevcut ortak primitive’ler yeniden kullanılır; v1/v2 yolları davranışsal olarak aynı kalır. Doğrulama doğrudan SQLite satırlarına yazılmış sentetik v3 geçmişleriyle sınanır (yazma kapısı bu dilimde yoktur). Restore/recover yasağı değişmez; upload tabloları geri yüklenebilir küme dışındadır.

**P02-3d devir notu.** `StageGraphSpec` bugün yalnız v1/v2 grafiğini bilir; bu dilim v3 için aynı belirtimi genişletir ve plan sürümü taşımayan dört tüketiciyi (`upload_preparation._limits`, `UploadCostWork.quantities`, `UploadIntentReview`, test dışında çağrılmayan `dataset_transfer.operation_reservation`; hepsi `ORIGINAL_PLAN_VERSION` adını verir) gözden geçirir. Dataset kimliğinin kaynağı v3’te kabul edilmiş create makbuzu değil plan/baseline’dır: `request_digest`, `_receipt` ve `_receipt_key` bugün `takes_created_dataset`/`takes_presign_key` ile kabul edilmiş create makbuzundan okur; `acknowledged_stages`, `_stages` ve `_arm_predecessors` create-ilk ve N dosya varsayar. `files` ve `put_batches` demettir, alt küme indekslerini ifade eder. Bu noktalar P02-3d R2 mutasyon incelemesinde testlerle kilitlidir (`tests/contracts/test_upload_graph_wiring.py`, journal testleri); v3 davranışı o testleri bilinçli olarak günceller, sessizce geçmez.

## Kabul

1. Sentetik v3 geçmişleri (admitted, running, unknown, cancelled, succeeded; `verification_only` M=0; kök+iki continuation zinciri; kök + intent’siz `cancelled` torun — zincire katkısız ve kaynak olamaz) hot ve full doğrulamadan, list/show’dan ve reset önizlemesinden geçer; çözümleyici baseline özeti uyuşmazlığını ve kopuk soyu `state_invalid` reddeder.
2. Geçersiz geçmişler `state_invalid` ile reddedilir: intent’siz ama latch’li kayıt, `verification_only` olmayan latch’siz `succeeded`/`unknown`, yetim makbuz, yanlış namespace, `len(intents)>3M`, v3 içinde create/link intent’i, `file_indices` dışı indeks, baseline uyuşmazlığı, yanlış sürüm eşleşmeleri, döngülü/kopuk zincir.
3. Kapasite: continuation plan/operation 128/128, dosya 4.096, 16 MiB sınırlarına yeniden sayılır; v1/v2 rezervasyon doğrulaması ve golden’ları değişmez; v3 satırı varken `require_capacity`/list/reset önizlemesi çalışır.
4. Eski-binary benzeri 2 tipli decode v3 satırını mutasyonsuz `state_invalid` reddeder; restore/recover yasağı değişmez.
5. v1/v2 geçmişi, golden’lar ve mevcut regresyon ağı değiştirilmeden geçer.

## Doğrulama

Gerçek SQLite integration/contract testleri, mevcut kota/maintenance/migration regresyonları, Ruff ve strict mypy. Ağ ve yazma kapısı iddiası yoktur.

## Teslim kaydı

Draft; uygulama, commit veya review kanıtı yoktur.
