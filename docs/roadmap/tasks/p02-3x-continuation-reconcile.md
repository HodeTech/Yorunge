---
id: P02-3x
phase: P02
status: draft
size: M
depends_on: [P02-3y]
capabilities: [C03, C12]
---
# P02-3x — Continuation `reconcile` bağlaması

**Tarih:** 2026-11-07. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 6 (devam); P02-3h’nin ölçülen kapsamından ayrıştırıldı. Mevcut `reconcile` komutunun v3 kayıtlar ve devam edilmiş kaynaklar için bağlanması.

## Kullanıcı sonucu ve mevcut eksik

3M makbuzu tam ama proof’u eksik kalan bir v3 `unknown` kaydın kullanıcı yeni bir devam planı yapmadan, aynı operation’da kanıtlanıp kapanabilmesi gerekir; bugün `reconcile` yalnız v2 plan ve kayıtlarını tanır. Ayrıca bir devam admit edildikten sonra kaynağın okuma lease’i ve yerel `reconcile` yazıcısı hâlâ çalışır; bunun kararı verilmemiştir.

## Giren ve girmeyen kapsam

Girer: (1) `upload_reconcile_local.load_read_input`, `upload_reconciliation` ve metadata kapanışı v3 plan/kayıt/proof birleşimini tanır: kök baseline **zincir çözümleyicisiyle** (kaynak → kök görünümü → `CreateReceiptV2`), 3M graf (`acknowledged_stages`), detail↔baseline karşılaştırması, `TransferVerificationV3` (N dosya, açık okuma politikası) ve `read_failed` v3’te `unknown/read_unavailable`; 3M makbuzu tam ama proof’u eksik unknown kayıt aynı operation’da `succeeded/metadata_verified` olur, graf eksikse `operation_uncertain` (unknown kalır). (2) **Karar ve uygulama:** `acquire_read` ve yerel `reconcile`ın yazıcısı (`load_read_input`un `cleanup_expired` çağrısı) kaynağın iptal edilmemiş torunu varken ne yapar — reddetmek (`operation_conflict`, torunu işaret etmek) ya da bugünkü davranışı (fence/revision artışı, `read_unavailable`/`identity_reset` nedeninin ezilmesi; geçerliliği bozmaz) belgelemek; seçilen davranış testlidir. Girmez: aşama yürütücüsü ([P02-3w](p02-3w-continuation-stage-executor.md)), başlatma ([P02-3y](p02-3y-continuation-start.md)), public API/CLI, canlı kabul.

## Bağımlılıklar ve kararlar

P02-3y verified olmalıdır (kapanış okuması ve proof kurucusu orada yazılır). Davranış [ADR-0031](../../decisions/0031-upload-continuation.md) §5 ve [sözleşme](../../reference/dataset-upload-continuation.md) (“Mevcut `reconcile`, 3M makbuzu tam ama proof’u eksik v3 unknown kaydı için aynı operation’da çalışır”); ADR değişmez.

## Sözleşme ve uygulama sınırı

v2 `reconcile` ve v2 original yolu davranışsal olarak aynı kalır; torunu olmayan v1/v2 kaynaklarda `acquire_read` ve `cleanup_expired` byte-byte aynıdır. Kök baseline çözümleyicisi `require_created_baseline` ile paylaşılır; `created_dataset` bir devam için hata verir.

**P02-3r R2 devri.** `acquire_read` bir devam admit edildikten sonra kaynakta okuma lease’i alabilir ve yerel `reconcile`ın `cleanup_expired` çağrısı kaynağın fence/revision’ını artırıp nedenini ezebilir; tam grafli bir kaynağa devam edilemediğinden ve eksik grafli kaynak `reconcile` ile `succeeded` olamadığından bu geçerliliği bozmaz (R2-A/R2-B probları). Karar bu kartta verilir.

## Kabul

1. Gerçek TLS/SQLite ile: 3M makbuz tam + proof eksik v3 unknown kayıt → `reconcile` → `succeeded/metadata_verified` (aynı operation kimliği, N dosya proof, kök baseline eşliği); graf eksik → `operation_uncertain` ve kayıt `unknown`; yanlış dataset/baseline ya da içerik farkı → mevcut hata kodları ve kayıt değişmez; v3 `read_failed` → `unknown/read_unavailable`.
2. Devam edilmiş kaynak kararı: seçilen davranış her iki yönde testlidir (kaynağın fence/revision/nedeni ya da reddin kodu ve torun kimliği); torunsuz v1/v2 kaynaklarda `reconcile` ve `acquire_read` mevcut testlerle byte-byte aynıdır.
3. v2 original yolu ve v2 `reconcile` mevcut testlerle değişmeden geçer; sır/yol sızıntısı yoktur; `tests/contracts` ve sürüm dağıtım listesi yeşildir.

## Doğrulama

Gerçek TLS/süreç/SQLite integration testleri, v1/v2 farklı-ikili karşılaştırması, Ruff ve strict mypy.

## Teslim kaydı

Draft; uygulama, commit veya review kanıtı yoktur.
