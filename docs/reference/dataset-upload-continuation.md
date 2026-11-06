# Upload continuation sözleşmesi

**Durum:** Taslak sözleşme — [ADR-0031](../decisions/0031-upload-continuation.md) Proposed; uygulama ve canlı kabul yok. **Tarih:** 2026-11-06. Komut, alan ve hata adları onay sonrası uygulama kartlarında kesinleşir; bu belge çalışan örnek değildir. Kaynak v1/v2 sözleşmeleri ([transfer](dataset-transfer.md), [v2](dataset-upload-v2.md), [uzlaştırma](dataset-upload-reconciliation.md), [public yüzey](dataset-upload-public.md)) ve onların byte/digest/golden’ları değişmez; yalnız **v3 continuation kayıtları** için başarı grafiği tanımı farklıdır (kısmi değişiklik notları ADR-0031’dedir).

## Planlanan yüzey

```text
yorunge datasets upload resume --operation-id UUID --accept-unverified-read
    [--prepare [--accept-unconfirmed-effects]] [--config FILE] [--profile NAME] [--state-dir PATH]
yorunge datasets upload approve --plan-id UUID --confirm DIGEST [--accept-unverified-authority]
    [--accept-unpriced-cost] [--accept-unconfirmed-effects] [...bağlam]
```

`resume` varsayılan olarak **salt okuma raporudur**: yerel plan yazmaz, uzak yazma yapmaz. `--prepare` aynı gözlemi yapar ve uygunsa yerel continuation planı kaydeder; `--accept-unconfirmed-effects` yalnız `--prepare` ile ve yalnız `pending_uncertain>0` iken anlamlıdır (aksi `invalid_request`). Okuma gözlemi mevcut `reconcile` ile aynı açık insan seçimini (`--accept-unverified-read`) ister. Sonraki adımlar mevcut `review`, `approve`, `revoke`, `start`, `list`, `show` ve `reconcile` komutlarıdır; `approve` yukarıdaki yeni bayrağı alır. Python karşılığı aynı kullanım senaryosuna bağlı tek API’dir. Politika kaynaktan devralınır; verified-only kaynaktan veya sağlayıcı oracle’ı olmadan devam yoktur. Anahtar argüman değildir.

## Uygunluk ve donma

Kaynak, kök operation’ın (`baseline_operation_id`) accepted CreateReceiptV2’sine zincirle bağlı bir operation’dır; kaynak continuation ise `dataset_id` kökle eşit olmalıdır.

| Koşul | Sonuç |
|---|---|
| Kaynak yok | `operation_not_found` |
| Kaynak terminal (`succeeded`, `failed`, `cancelled`) veya `admitted` | `operation_conflict`; devam yok (başarı için gerek yok; `admitted` kaynakta create intent’i hiç yok; iptal edilmiş iş için yeni plan) |
| Etkin write/read owner (lease dolmamış) | `operation_conflict`; lease bitince tekrar. Rapor `source_active` engelini gösterir |
| Lease dolmuş `running` | Mevcut execution izni üretmeyen `cleanup_expired` yolu (yalnız `--prepare`) kaynağı `unknown`/`request_uncertain` yapar (fence+1); rapor yerel durumu değiştirmez |
| `unknown` (reset, rotasyon veya `identity_reset` dahil), kök CreateReceiptV2 var, zincirde `rejected` makbuz yok | Uygun; plan **güncel** scope ile kurulur |
| Zincirde herhangi bir `rejected` makbuz | `continuation_not_possible` (bilinen olumsuz sonuç; not: üretim yolu bugün bunu yazmaz, [ADR-0031 §2](../decisions/0031-upload-continuation.md#2-uygunluk-yalnız-dosya-aktarım-fazının-kalanı)) |
| Create receipt/dataset ID yok (kök create unknown) | `continuation_not_possible` (sahiplenme yok) |
| Zincirde döngü, farklı dataset kimliği, kopuk soy | `state_invalid` |
| Zincir dışında dataset’te veya kaynağın torunlarında non-terminal operation | `operation_conflict` (mevcut kimlik gösterilir) |
| Proje üyeliği exact bir kez gözlenmedi veya detail↔baseline uyuşmuyor | `continuation_not_possible` |
| Yerel klasör/Manifest uyuşmuyor | `input_changed`/`input_invalid` |

Donma yerel CAS’tır; eski sürecin zaten gönderilmiş isteğini geri çekmez. Etkili hak üretmez.

## Kanıt sınıfları ve karar tablosu

Girdi: **zincirin bütün journal’larının birleşimi** (dosya başına: herhangi bir operation’da accepted confirm makbuzu var mı; yoksa herhangi birinde confirm intent’i var mı) ve taze, tam, sayfalı uzak envanter. “Exact item” = Manifest’teki (ad, boyut, SHA-256) üçlüsüyle aynı, tekil ve başka kimlikle çakışmayan tek item. Tablo tam ve kapalıdır:

| Zincir journal’ı (confirm) | Uzak envanter | Sınıf |
|---|---|---|
| accepted makbuz | exact item | `confirmed` |
| accepted makbuz | yok | `drift_missing` |
| intent var, accepted makbuz yok | exact item | `observed` |
| intent var, accepted makbuz yok | yok | `pending_uncertain` |
| intent yok | exact item | `observed` |
| intent yok | yok | `pending_clean` |
| herhangi | aynı adda farklı boyut/SHA, kopya, aynı SHA başka ad | `conflict` |
| herhangi | null `sha256_hash`, `total` uyuşmazlığı, cursor döngüsü, kopya kimlik | `inventory_unreliable` |
| envanter düzeyi | Manifest dışı fazladan item | `conflict` (plan düzeyi sayaç) |

Öncelik: ad çakışması/kopya → `conflict`; yokluk → `drift_missing`; doğrulanamayan envanter → `inventory_unreliable` (sonra yeniden denenir). Presign/PUT durumu sınıfı değiştirmez (confirm intent’i yoksa dosya `pending_clean`dır). `file_indices` = `pending_clean` ∪ (ack ile) `pending_uncertain`. Tek `drift_missing`/`conflict`/`inventory_unreliable` veya fazladan item plan hazırlamaz; rapor kapalı `blockers` ve sayaçları gösterir. `M=0` geçerlidir. Envanter üst sınırı (örn. 1.024 item) aşılırsa `inventory_unreliable` olur; veri sessizce kesilmez.

## Kapalı tipler (v3 farkları)

Hepsi strict/frozen/extra-forbid, zorunlu alanlı (nullable dahil), bool sayı değildir; canonical ASCII JSON ve byte sınırları v1/v2 ile aynıdır.

| Tip | Alanlar ve kural |
|---|---|
| `ContinuationBinding` | `source_operation_id`, `baseline_operation_id` (UUIDv4; accepted CreateReceiptV2’yi taşıyan kök), `dataset_id` (provider UUID), `baseline_digest` (immutable `created_dataset` DTO’sunun canonical SHA-256’sı; DTO’nun kendisi planda yok), `file_indices` (sıralı, tekil, 0..N−1), `uncertain_indices` (⊆ `file_indices`), `classification_digest`, `inventory_digest`, `observed_at`. Tekrarlı/aralık dışı indeks ret |
| `DatasetContinuationPlan v3` | v2’nin bütün alanları (kök, Manifest ref’i, parametreler kaynakla **birebir**), `schema_version=3`, `policy_version=3`, `kind=dataset_upload_continuation_plan`, `continuation: ContinuationBinding`, `request_limits` (create=0, project_link=0, presign=PUT=confirm=M, bayt tavanı = seçilen dosyaların toplamı), yeni 0<aralık≤900 s `execution_window`. `intent_digest` kökünkiyle aynıdır. Politika/risk reducer’ı v2 ile aynıdır; politika kaynaktan devralınır |
| `DatasetUploadApproval v3` | v2 alanları + `acknowledge_unconfirmed_effects` (strict bool); plan/binding özeti bütün continuation alanlarını kapsar. true yalnız `uncertain_indices` boş değilse geçerli; gerekli ve eksik → `approval_required`, gereksiz true → `invalid_request` |
| `TransferRecord v3` | v2 alanları; `workflow_latched=true` ile **admission’da** oluşur ve `dataset_id` plandan doludur; `len(intents) ≤ 3M`; write owner/fence/access digest kuralları v2 ile aynı; durum yolu aşağıda |
| `TransferControl v3` | v2 neden kataloğu; sürüm kayıtla eşleşir |
| `TransferVerification v3` | v2 ile aynı alanlar (dataset/project/scope/authorization policy/grant/`observed_at` ve **N** `VerifiedFile`, manifest sırası); `schema_version=3` (kayıt/kontrol/kanıt sürüm eşitliği korunur) |
| `DatasetUploadSummary v3` | v2 alanları + `continuation_of` (kaynak operation kimliği), `continuation_files`, `observed_files`, `confirmed_files`; yol/baseline/receipt alanları yok. v1/v2 özetleri değişmez |
| `DatasetUploadResumeReport v1` | `schema_version=1`, `kind=dataset_upload_resume_report`, kaynak operation/dataset kimliği, `eligible`, kapalı `blockers`, sınıf sayıları, N, M, M için toplam bayt, `unconfirmed_ack_required`, kota etkisi (yeniden sayılacak dosya/payload), `classification_digest`, `inventory_digest`, `observed_at`, nullable `plan_id`/`plan_digest` (`--prepare` ile), sorunlu sınıf başına ≤8 örnek göreli yol (literal-secret taramalı) |

`classification_digest`: `{index, class}` çiftlerinin sıralı canonical JSON’u ile zincir journal özetinin (dosya başına birleşik confirm durumu) SHA-256’sı. `inventory_digest`: uzak envanterin sıralı `(path, size, sha256)` kümesinin SHA-256’sı; item kimlikleri ve sağlayıcı zamanı digest’e girmez. Kapalı `blockers`: `source_active`, `source_ineligible`, `create_unknown`, `membership_unobserved`, `known_negative`, `drift_missing`, `conflict`, `extra_remote`, `inventory_unreliable`, `inventory_too_large`, `local_changed`.

## Stage grafiği, durum yolu ve kapılar

Graf yalnız `{(presign,i),(put,i),(confirm,i): i ∈ file_indices}` kümesidir (3M intent, her biri tek accepted makbuz). Presign’ın öncülü yoktur; PUT/confirm öncülleri v2’deki gibidir. Create/link intent’i bu operation’da hiçbir zaman oluşmaz (arm kapısı reddeder). `request_digest` dataset kimliğini plan bağından alır; create makbuzuna bakmaz. Namespace: plan kökün `intent_digest`ini kullanır, `_namespace_available` bu tür için atlanır, hot/full invariant “`namespace.create_operation_id == baseline_operation_id`”dir; yeni create hakkı doğmaz. Reservation ve kapasite formülü plan türüne göre sürümlüdür; v1/v2 satırlarının doğrulaması değişmez.

**Durum yolu (M=0 dahil).** Admission `workflow_latched=true` ile `admitted` kaydı kurar. İlk intent veya proof okuması `running`/`admitted` kayıttan başlar; proof öncesi okuma hatası `unknown`/`read_unavailable`, lease/süre kaybı `unknown`/`request_uncertain`dır; başarı `succeeded`/`metadata_verified`. M=0 için intent yoktur: admission → okuma/proof → `succeeded`. Yerel iptal veya süre dolumu latched kaydı `unknown` yapar (cancelled değil).

**Confirm oracle.** `created=1`, `batch_duplicates=0` ve varsa `actual_count == (N−M) + bu operation’da kabul edilmiş confirm sayısı + 1` (sağlayıcıda sayı veri seti düzeyinde kümülatiftir; taban admission’daki uzak item sayısıdır). v2 yolunun tabanı 0’dır ve değişmez.

| İşlem | v3 farkı |
|---|---|
| prepare (`resume --prepare`) | v2 kapıları + kaynak uygunluğu + taze envanter + sınıflandırma; yerel root/Manifest **tam** yeniden hash’lenir |
| approve | v2 ack kuralları + `acknowledge_unconfirmed_effects` kuralı; draft onaylanmaz |
| admit/start | v2 kapıları + envanter yeniden sınıflanır; özet farklıysa `upload_plan_not_valid`; kaynak donmuş; zincir dışında non-terminal operation yok; yeni create hakkı doğmaz |
| arm | Yalnız presign/put/confirm; `file_indices` dışı indeks ve create/link reddedilir; geri kalan v2 |
| read/proof | Başarı: M için tam 3M makbuz + N dosyalık ordered metadata (`TransferVerification v3`) + kök baseline eşliği; authority/pricing/remote-bytes yükseltilmez |

## Hata ve çıktı

Yeni kapalı kod: `continuation_not_possible` (exit 2, `details={}`; sabit mesaj nedenler için `resume` raporuna yönlendirir, operation kimliği korunur). Diğer retler mevcut kodlardır (`operation_conflict`, `operation_not_found`, `approval_required`, `invalid_request`, `upload_plan_not_valid`, `input_changed`, `state_invalid`, `remote_access_denied`/`transport_*`, `operation_uncertain`). JSON/NDJSON Result v1 korunur; sır, provider gövdesi, `created_dataset` ve tam yol listesi dökülmez. `unknown` kaynakların `show` metin çıktısı yerel ön kontrol uygunsa `resume` yolunu önerir; DTO’lar değişmez. Kabul ve sınırlar [ADR-0031](../decisions/0031-upload-continuation.md#sonuçlar-ve-kabul)’tedir.
