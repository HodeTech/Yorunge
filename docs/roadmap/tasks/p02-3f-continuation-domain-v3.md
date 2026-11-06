---
id: P02-3f
phase: P02
status: draft
size: M
depends_on: [P02-3e]
capabilities: [C03, C12]
---
# P02-3f — Continuation v3 kapalı tipleri, politika ve golden’lar

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 3. [ADR-0031](../../decisions/0031-upload-continuation.md) ve [continuation sözleşmesi](../../reference/dataset-upload-continuation.md) tipleri; kalıcılık ve HTTP yok.

## Kullanıcı sonucu ve mevcut eksik

Devam için gereken plan/onay/kayıt/kontrol/doğrulama/özet/rapor tipleri bugün yoktur; v2 tipleri kapalıdır ve alan eklenemez. Bu kart, v1/v2’yi değiştirmeden strict v3 tiplerini ve doğrulayıcılarını sabitler.

## Giren ve girmeyen kapsam

`DatasetContinuationPlan v3`, `ContinuationBinding`, onay v3 (`acknowledge_unconfirmed_effects`), kayıt v3 (plandan dolu `dataset_id`; latch ilk intent’te; `verification_only` bayrağı), kontrol v3, `TransferVerification v3` (v2 ile aynı alanlar), `DatasetUploadSummary v3`, `DatasetUploadResumeReport v1`, `UploadRequestLimits`/maliyet iş özeti v3 (create=0, link=0, M dosya), canonical kodlama ve özetler, politika reducer’ının continuation için kullanımı, kökten kopyalanan saklı `intent_digest` (scope’tan türetilmez; kökle eşitlik doğrulanır), `remote_present_count`, v3 için `request_digest` kuralı (dataset kimliği plan bağından) ve yeni `continuation_not_possible` (kapalı `blockers` ayrıntısı) ile `continuation_remote_changed` hata kodları (katalog, mesaj, exit) girer. Repository/DDL, HTTP, koordinatör, CLI/API yüzeyi girmez.

## Bağımlılıklar ve kararlar

P02-3e sınıf ve özet tanımlarına bağlıdır. [ADR-0031](../../decisions/0031-upload-continuation.md)’in Accepted olması gerekir (bugün Proposed). Tip alanlarının tam listesi bu kartta [continuation sözleşmesi](../../reference/dataset-upload-continuation.md) taslağından kesinleşir; golden vektörler bağımsız elle hesaplanır.

## Sözleşme ve uygulama sınırı

Hepsi strict/frozen/extra-forbid, zorunlu alanlı (nullable dahil), bool≠int; canonical ASCII JSON ve byte sınırları v1/v2 ile aynı. Bağlama özeti (plan, onay, kayıt, maliyet işi) soy bağını, dataset kimliğini, baseline özetini, `file_indices`, `uncertain_indices`, sınıflandırma ve envanter özetlerini ve yeni istek bütçesini kapsar. v3 `decode` yalnız kendi tür/sürüm çiftlerini kabul eder; v1/v2 çiftleri aynı kalır; kayıt/kontrol/doğrulama sürüm eşitliği korunur.

## Kabul

1. Her tip için literal canonical byte ve SHA-256 golden’ları; v1/v2 golden’ları değişmez.
2. Doğrulayıcı negatifleri: sırasız/tekrarlı/aralık dışı indeks, `uncertain_indices ⊄ file_indices`, limit–M uyuşmazlığı, create/link ≠ 0, pencere ≤0 veya >900 s, sürüm eşleşmesi (plan v3+onay v2; kayıt v3+doğrulama v2 vb.), bilinmeyen/eksik alan, bool-as-int, gereksiz/eksik `acknowledge_unconfirmed_effects`, v3 kaydında `dataset_id=null`, `verification_only` ile `file_indices` boşluğunun eşleşmemesi, `verification_only` olmayan unlatched `succeeded`, `uncertain_indices` ≠ sınıflandırmadaki `pending_uncertain` kümesi, `file_indices` ≠ `pending_clean ∪ pending_uncertain`, `remote_present_count` ≠ N−M, kökten farklı `intent_digest`.
3. Bağlama özeti: her yeni alanın tek tek değiştirilmesi özeti değiştirir (mutasyon testi); `observed_at` hariç olanlar belgelenen şekilde dışarıdadır.
4. v2 politika reducer matrisi (96 satır) continuation tipinde aynı sonucu verir; verified-only ve sağlayıcı oracle’sız yol continuation’a açılmaz. `M=0` plan geçerlidir ve ack kuralları değişmez.
5. Yeni hata kodları için zarf, mesaj, exit 2, kapalı `blockers` ayrıntısı ve CLI hata kataloğu uyumu testlidir; v3 özet/rapor DTO’ları `created_dataset`, owner/org/ad ve receipt alanı taşımaz (sentinel).

## Doğrulama

Contract/unit testleri, golden fixture’ları, Ruff ve strict mypy; hata kataloğu belge kontrolü. Kalıcılık ve ağ davranışı iddia edilmez.

## Teslim kaydı

Draft; uygulama, commit veya review kanıtı yoktur.
