# Upload continuation sözleşmesi

**Durum:** Taslak sözleşme — [ADR-0031](../decisions/0031-upload-continuation.md) Proposed; uygulama ve canlı kabul yok. **Tarih:** 2026-11-06. Komut, alan ve hata adları onay sonrası uygulama kartlarında kesinleşir; bu belge çalışan örnek değildir. Kaynak v1/v2 sözleşmeleri ([transfer](dataset-transfer.md), [v2](dataset-upload-v2.md), [uzlaştırma](dataset-upload-reconciliation.md), [public yüzey](dataset-upload-public.md)) ve onların byte/digest/golden’ları değişmez.

## Planlanan yüzey

```text
yorunge datasets upload resume-report --operation-id UUID --accept-unverified-read [--config FILE] [--profile NAME] [--state-dir PATH]
yorunge datasets upload resume        --operation-id UUID --accept-unverified-read
                                      [--accept-unconfirmed-effects] [--config FILE] [--profile NAME] [--state-dir PATH]
```

`resume-report` salt okumadır ve yerel plan yazmaz; `resume` aynı gözlemi yapar, uygunsa yerel continuation planı kaydeder. İkisi de uzak yazma yapmaz. Sonraki adımlar mevcut `review`, `approve`, `revoke`, `start`, `list`, `show` ve `reconcile` komutlarıdır. Python karşılıkları aynı kullanım senaryolarına bağlı iki API’dir. Kaynak politikası kaynaktan devralınır; verified-only kaynaktan veya sağlayıcı oracle’ı olmadan devam yoktur. Anahtar argüman değildir.

## Uygunluk ve donma

| Koşul | Sonuç |
|---|---|
| Kaynak yok | `operation_not_found` |
| Kaynak `succeeded` veya `cancelled` | `operation_conflict`; devam yok (başarı için gerek yok, iptal edilmiş iş için yeni plan) |
| Etkin write/read owner (lease dolmamış) | `operation_conflict`; lease bitince tekrar |
| Lease dolmuş `running` | Mevcut execution izni üretmeyen `cleanup_expired` yolu kaynağı `unknown`/`request_uncertain` yapar (fence+1); sonra devam |
| `unknown` veya `failed`, accepted CreateReceiptV2 var | Uygun |
| Create receipt/dataset ID yok | `continuation_not_possible` (create unknown; sahiplenme yok) |
| Başka non-terminal transfer operation aynı dataset’te | `operation_conflict` (mevcut kimlik gösterilir) |
| Proje üyeliği exact bir kez gözlenmedi veya detail↔baseline uyuşmuyor | `continuation_not_possible` |
| Yerel klasör/Manifest uyuşmuyor | `input_changed`/`input_invalid` |

Donma yerel CAS’tır; eski sürecin zaten gönderilmiş isteğini geri çekmez. Etkili hak üretmez.

## Kanıt sınıfları ve karar tablosu

Girdi: kaynak journal’ındaki dosya başına durum ve taze, tam, sayfalı uzak envanter. “Exact item” = Manifest’teki (ad, boyut, SHA-256) üçlüsüyle aynı, tekil ve başka kimlikle çakışmayan tek item. Aşağıdaki tablo tam ve kapalıdır:

| Kaynak: confirm | Uzak envanter | Sınıf |
|---|---|---|
| accepted makbuz | exact item | `confirmed` |
| accepted makbuz | yok / farklı içerik / kopya | `drift_missing` (veya `conflict`: aynı adda farklı içerik, aynı SHA farklı ad, kopya) |
| intent var, makbuz yok | exact item | `observed` |
| intent var, makbuz yok | yok | `pending_uncertain` |
| intent var, makbuz yok | aynı ad farklı içerik / kopya | `conflict` |
| intent yok | exact item | `observed` |
| intent yok | yok | `pending_clean` |
| intent yok | aynı ad farklı içerik / kopya | `conflict` |
| herhangi | Manifest dışı fazladan item (envanter düzeyi) | `conflict` (plan düzeyi sayaç) |

`file_indices` = `pending_clean` ∪ onaylı `pending_uncertain`. Tek `drift_missing`/`conflict` veya fazladan item plan hazırlamaz (`continuation_not_possible`); `resume-report` neden sayaçlarını gösterir. `M=0` (hepsi `confirmed`/`observed`) geçerlidir.

## Kapalı tipler (v3 farkları)

Hepsi strict/frozen/extra-forbid, zorunlu alanlı (nullable dahil), bool sayı değildir; canonical ASCII JSON ve byte sınırları v1/v2 ile aynıdır.

| Tip | Alanlar ve kural |
|---|---|
| `ContinuationBinding` | `source_operation_id`, `baseline_operation_id` (UUIDv4; accepted CreateReceiptV2’yi taşıyan kök), `dataset_id` (provider UUID), `baseline_digest` (immutable `created_dataset` DTO’sunun canonical SHA-256’sı; DTO’nun kendisi planda yok), `file_indices` (sıralı, tekil, 0..N−1), `uncertain_indices` (⊆ `file_indices`), `classification_digest`, `inventory_digest`, `observed_at`. Tekrarlı/aralık dışı indeks ret |
| `DatasetContinuationPlan v3` | v2’nin bütün alanları (kök, Manifest ref’i, parametreler kaynakla **birebir**), `schema_version=3`, `policy_version=3`, `kind=dataset_upload_continuation_plan`, `continuation: ContinuationBinding`, `request_limits` (create=0, project_link=0, presign=PUT=confirm=M, bayt tavanı = seçilen dosyaların toplamı), yeni 0<aralık≤900 s `execution_window`. Politika/risk reducer’ı v2 ile aynıdır; politika kaynaktan devralınır |
| `DatasetUploadApproval v3` | v2 alanları + `acknowledge_unconfirmed_effects` (strict bool); plan/binding özeti bütün continuation alanlarını kapsar. true yalnız `uncertain_indices` boş değilse geçerli; gerekli ve eksik → `approval_required`, gereksiz true → `invalid_request` |
| `TransferRecord v3` | v2 alanları; `dataset_id` admission’da plandan dolu (v2 kuralı bu tür için yoktur); write owner/fence/access digest kuralları v2 ile aynı. Kaynak ve continuation aynı store’da iki ayrı kayıttır |
| `TransferControl v3` | v2 neden kataloğu; sürüm kayıtla eşleşir |
| `TransferVerification v2` | Değişmez yeniden kullanılır: dataset/project/scope/authorization policy/grant/`observed_at` ve **N** `VerifiedFile` (manifest sırası) |
| `DatasetUploadSummary v3` | v2 alanları + `continuation_of` (kaynak operation kimliği), `continuation_files`, `observed_files`, `confirmed_files`; yol/baseline/receipt alanları yok. v1/v2 özetleri değişmez |
| `DatasetUploadResumeReport v1` | `schema_version=1`, `kind=dataset_upload_resume_report`, kaynak operation/dataset kimliği, `eligible`, kapalı `blockers`, sınıf sayıları, N, M, M için toplam bayt, `unconfirmed_ack_required`, `classification_digest`, `inventory_digest`, `observed_at`, nullable `plan_id`/`plan_digest`, bounded örnek yollar (sorunlu sınıf başına ≤8) |

`classification_digest`: `{index, class}` çiftlerinin sıralı canonical JSON’u ile kaynak journal özetinin (dosya başına intent/makbuz durumu) SHA-256’sı. `inventory_digest`: uzak envanterin sıralı `(path, size, sha256)` kümesinin SHA-256’sı; item kimlikleri ve sağlayıcı zamanı digest’e girmez.

## Stage grafiği ve kapılar

Graf yalnız `{(presign,i),(put,i),(confirm,i): i ∈ file_indices}` kümesidir (3M intent, her biri tek accepted makbuz). Presign’ın öncülü yoktur; PUT/confirm öncülleri v2’deki gibidir. Create/link intent’i bu operation’da hiçbir zaman oluşmaz (arm kapısı reddeder). Reservation ve kapasite formülü plan türüne göre sürümlüdür; v1/v2 satırlarının doğrulaması değişmez. Kapılar:

| İşlem | v3 farkı |
|---|---|
| prepare | v2 kapıları + kaynak uygunluğu + taze envanter + sınıflandırma; yerel root/Manifest **tam** yeniden hash’lenir |
| approve | v2 ack kuralları + `acknowledge_unconfirmed_effects` kuralı; draft onaylanmaz |
| admit/start | v2 kapıları + envanter yeniden sınıflanır; özet farklıysa `upload_plan_not_valid`; kaynak donmuş; dataset’te başka non-terminal operation yok; ad/proje niyeti kök operation’a ait olduğundan yeni create hakkı doğmaz |
| arm | Yalnız presign/put/confirm; `file_indices` dışı indeks ve create/link reddedilir; geri kalan v2 |
| read/proof | Başarı: M için tam 3M makbuz + N dosyalık ordered metadata + kök baseline eşliği; authority/pricing/remote-bytes yükseltilmez |

## Hata ve çıktı

Yeni kapalı kod: `continuation_not_possible` (exit 2, `details={}`); neden `resume-report`ta kapalı sayaçlar ve `blockers` olarak görünür. Diğer retler mevcut kodlardır (`operation_conflict`, `operation_not_found`, `approval_required`, `upload_plan_not_valid`, `input_changed`, `remote_access_denied`/`transport_*`, `operation_uncertain`). JSON/NDJSON Result v1 korunur; sır, provider gövdesi, `created_dataset` ve yol listesi tam dökülmez. Kabul ve sınırlar [ADR-0031](../decisions/0031-upload-continuation.md#sonuçlar-ve-kabul)’tedir.
