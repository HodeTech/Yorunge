---
id: P02-3t
phase: P02
status: draft
size: M
depends_on: [P02-3f]
capabilities: [C03, C12]
---
# P02-3t — Continuation v3 kayıt, kontrol, doğrulama ve kullanıcı DTO tipleri

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 3 (ikinci yarı); [P02-3f](p02-3f-continuation-domain-v3.md)’nin ölçülen büyüklük nedeniyle bölünen yarısıdır. [ADR-0031](../../decisions/0031-upload-continuation.md) ve [continuation sözleşmesi](../../reference/dataset-upload-continuation.md) tipleri; kalıcılık ve HTTP yok.

## Kullanıcı sonucu ve mevcut eksik

Continuation operasyonunun kayıt, kontrol ve doğrulama tipleri ile kullanıcıya dönen özet ve rapor tipleri bugün yoktur; v2 tipleri kapalıdır. Bu kart, v1/v2’yi değiştirmeden strict v3 kayıt/kontrol/doğrulama tiplerini ve gizli alan taşımayan kullanıcı DTO’larını sabitler; P02-3g bunları depoda okur, P02-3i bunları yüzeyde gösterir.

## Giren ve girmeyen kapsam

`TransferRecord v3` (plandan dolu `dataset_id`, latch ilk intent’te, `verification_only` bayrağı ve kuralları: intent üretmez, latch’lenmez, `unknown` olamaz, unlatched `succeeded` yalnız `verification_only`; `len(intents) ≤ 3M`), `TransferControl v3`, `TransferVerification v3` (v2 ile aynı alanlar, N dosyalık sıralı kanıt), `DatasetUploadSummary v3` (`continuation_of`, `continuation_files`, `observed_files`, `confirmed_files`; yol/baseline/makbuz alanı yok), `DatasetUploadResumeReport v1` (kapalı `blockers`, sınıf sayıları, N, M, M için toplam bayt, `unconfirmed_ack_required`, önerilen eylem, nullable `related_operation_id`, kota etkisi, iki özet, nullable `plan_id`/`plan_digest`, sorunlu sınıf başına ≤8 örnek göreli yol), canonical kodlama ve byte sınırları ile kayıt/kontrol/doğrulama sürüm eşitliği girer. Repository/DDL, HTTP, koordinatör, CLI/API yüzeyi girmez.

## Bağımlılıklar ve kararlar

P02-3f plan ve onay tiplerine bağlıdır. [ADR-0031](../../decisions/0031-upload-continuation.md) Accepted’dir (2026-11-06). Tip alanları sözleşmedeki tablodan kesinleşir; golden vektörler bağımsız hesaplanır.

## Sözleşme ve uygulama sınırı

Hepsi strict/frozen/extra-forbid, zorunlu alanlı (nullable dahil), bool≠int; canonical ASCII JSON ve byte sınırları v1/v2 ile aynı. Kayıt/kontrol/doğrulama sürümü eşleşir; v3 `decode` yalnız kendi tür/sürüm çiftlerini kabul eder (üç tipli decode’un depoya bağlanması P02-3g’dedir). Raporun M, M-bayt ve `unconfirmed_ack_required` alanları engel varken sınıf vektöründen türetilen bilgi amaçlı değerlerdir; plan alanları yalnız engelsiz `selection()`dandır.

## Kabul

1. Her tip için literal canonical byte ve SHA-256 golden’ları; v1/v2 golden’ları değişmez.
2. Doğrulayıcı negatifleri: v3 kaydında `dataset_id=null`, `verification_only` ile `file_indices` boşluğunun eşleşmemesi, `verification_only` olmayan unlatched `succeeded`, `verification_only` + intent/latch/`unknown`, sürüm eşleşmeleri (kayıt v3+doğrulama v2 vb.), bilinmeyen/eksik alan, bool-as-int, N dosyadan az/fazla veya sırasız doğrulama dosyası.
3. v3 özet/rapor DTO’ları `created_dataset`, owner/org/ad, makbuz alanı, tam yol listesi ve literal-secret taşımaz (sentinel); rapor örnek yolları literal-secret taramasından geçer ve sorunlu sınıf başına en çok 8’dir.
4. Rapor alanları engel varken ve engelsizken tutarlıdır (plan kimlikleri yalnız `--prepare` sonrası dolu).

## Doğrulama

Contract/unit testleri, golden fixture’ları, Ruff ve strict mypy; belge kontrolleri. Kalıcılık ve ağ davranışı iddia edilmez.

## Teslim kaydı

Draft; uygulama, commit veya review kanıtı yoktur.
