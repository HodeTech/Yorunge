# Upload continuation sözleşmesi

**Durum:** Taslak sözleşme — [ADR-0031](../decisions/0031-upload-continuation.md) Proposed; uygulama ve canlı kabul yok. **Tarih:** 2026-11-06. Komut, alan ve hata adları onay sonrası uygulama kartlarında kesinleşir; bu belge çalışan örnek değildir. Kaynak v1/v2 sözleşmeleri ([transfer](dataset-transfer.md), [v2](dataset-upload-v2.md), [uzlaştırma](dataset-upload-reconciliation.md), [public yüzey](dataset-upload-public.md)) ve onların byte/digest/golden’ları değişmez; yalnız **v3 continuation kayıtları** için başarı grafiği tanımı farklıdır (kısmi değişiklik notları ADR-0031’dedir). Bu belge continuation hata kodlarının **kanonik** tablosudur; [CLI sözleşmesi](cli-contract.md) buraya bağlanır, kopyasını tutmaz.

## Planlanan yüzey

```text
yorunge datasets upload resume --operation-id UUID --accept-unverified-read
    [--prepare [--accept-unconfirmed-effects]] [--config FILE] [--profile NAME] [--state-dir PATH]
yorunge datasets upload approve --plan-id UUID --confirm DIGEST [--accept-unverified-authority]
    [--accept-unpriced-cost] [--accept-unconfirmed-effects] [...bağlam]
```

`resume` varsayılan olarak **salt okuma raporudur**: yerel plan yazmaz, uzak yazma yapmaz ve uygunluk/sınıflandırma sonucu ne olursa olsun exit 0 ile `DatasetUploadResumeReport` döndürür. `--prepare` aynı gözlemi yapar ve uygunsa yerel continuation planı kaydeder; uygun değilse hata verir (aşağıda). `--accept-unconfirmed-effects` yalnız `--prepare` ile ve yalnız `pending_uncertain>0` iken anlamlıdır (aksi `invalid_request`); `pending_uncertain>0` iken bayraksız `--prepare` plan yazmadan `approval_required`/4 verir. Okuma gözlemi mevcut `reconcile` ile aynı açık insan seçimini (`--accept-unverified-read`) ister. Sonraki adımlar mevcut `review`, `approve`, `revoke`, `start`, `list`, `show` ve `reconcile` komutlarıdır; `approve` yukarıdaki yeni bayrağı alır (gerekli olup eksikse `approval_required`). Python karşılığı aynı kullanım senaryosuna bağlı tek API’dir. Politika kaynaktan devralınır; verified-only kaynaktan veya sağlayıcı oracle’ı olmadan devam yoktur. Anahtar argüman değildir.

## Uygunluk ve donma

Kaynak, kök operation’ın (`baseline_operation_id`) accepted CreateReceiptV2’sine zincirle bağlı bir operation’dır; kaynak continuation ise `dataset_id` kökle eşit olmalıdır. Rapor modunda aşağıdaki sonuçlar `blockers` olarak döner (exit 0); `--prepare` modunda `source_active` `operation_conflict`, diğer her engel `continuation_not_possible` olur.

| Koşul | Sonuç |
|---|---|
| Kaynak yok | `operation_not_found` (rapor dahil hata) |
| Kaynak terminal (`succeeded`, `failed`, `cancelled`) | `source_terminal` engeli; devam yok (başarı için gerek yok; `failed` kesin bir sağlayıcı reddi içerir; iptal edilmiş iş için yeni plan) |
| Kaynak `admitted` (intent’siz; latch yok) | `source_ineligible`; lease dolunca mevcut yerel yol onu `cancelled` yapar ve zincire bir şey katmaz |
| Etkin write/read owner (lease dolmamış) veya non-terminal torun | `source_active`; lease bitince tekrar. `--prepare`: `operation_conflict` (torunun kimliği ve `resume --operation-id <torun>` önerisi) |
| Lease dolmuş `running` | Rapor yerel durumu değiştirmez; `--prepare` mevcut execution izni üretmeyen `cleanup_expired` yoluyla kaynağı `unknown`/`request_uncertain` yapar (fence+1) ve lease’i dolmuş `admitted` torunları `cancelled` yapar |
| `unknown` (reset, rotasyon veya `identity_reset` dahil), kök CreateReceiptV2 var, zincirde `rejected` makbuz yok | Uygun; plan **güncel** scope ile kurulur |
| Kaynağın kendi grafiği zaten tam (tam 2+3N veya v3 için 3M makbuz), yalnız kanıt eksik | `reconcile_available`: `resume` M=0 yerine mevcut `reconcile`ı önerir |
| Zincirde herhangi bir `rejected` makbuz | `known_negative` (bilinen olumsuz sonuç; not: üretim yolu bugün bunu yazmaz, [ADR-0031 §2](../decisions/0031-upload-continuation.md#2-uygunluk-yalnız-dosya-aktarım-fazının-kalanı)) |
| Create receipt/dataset ID yok (kök create unknown) | `create_unknown` (sahiplenme yok) |
| Zincirde döngü, farklı dataset kimliği, kopuk soy, baseline özeti uyuşmazlığı | `state_invalid` (hata) |
| Proje üyeliği exact bir kez gözlenmedi veya detail↔baseline uyuşmuyor | `membership_unobserved` |
| Yerel klasör/Manifest uyuşmuyor | `local_changed` (rapor); `--prepare`: `input_changed`/`input_invalid` |

Donma yerel CAS’tır; eski sürecin zaten gönderilmiş isteğini geri çekmez. Etkili hak üretmez.

## Kanıt sınıfları ve karar tablosu

Girdi: **zincirin bütün journal’larının birleşimi** (dosya başına: herhangi bir operation’da accepted confirm makbuzu var mı; yoksa herhangi birinde confirm intent’i var mı; sıfır-intent’li operation hiçbir şey katmaz) ve taze, tam, sayfalı uzak envanter. “Exact item” = Manifest’teki (ad, boyut, SHA-256) üçlüsüyle aynı, tekil ve başka kimlikle çakışmayan tek item. Tablo tam ve kapalıdır:

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

Öncelik: ad çakışması/kopya → `conflict`; yokluk → `drift_missing`; doğrulanamayan envanter → `inventory_unreliable` (sonra yeniden denenir). Presign/PUT durumu sınıfı değiştirmez (confirm intent’i yoksa dosya `pending_clean`dır). `file_indices` her zaman `pending_clean ∪ pending_uncertain` kümesinin tamamıdır ve `uncertain_indices` tam olarak `pending_uncertain` kümesidir; kısmi seçim yoktur. `remote_present_count` = `confirmed`+`observed` sayısıdır (= N−M). Tek `drift_missing`/`conflict`/`inventory_unreliable` veya fazladan item plan hazırlamaz. `M=0` geçerlidir (yalnız doğrulama). Envanter üst sınırı **1.024 item**’dır; aşılırsa `inventory_unreliable` sınıfı ve `inventory_too_large` engeli oluşur (plan hazırlanmaz, veri sessizce kesilmez).

## Kapalı tipler (v3 farkları)

Hepsi strict/frozen/extra-forbid, zorunlu alanlı (nullable dahil), bool sayı değildir; canonical ASCII JSON ve byte sınırları v1/v2 ile aynıdır.

| Tip | Alanlar ve kural |
|---|---|
| `ContinuationBinding` | `source_operation_id`, `baseline_operation_id` (UUIDv4; accepted CreateReceiptV2’yi taşıyan kök), `dataset_id` (provider UUID), `baseline_digest` (immutable `created_dataset` DTO’sunun canonical SHA-256’sı; DTO’nun kendisi planda yok), `intent_digest` (kökün kayıtlı değerinin kopyası; scope’tan türetilmez), `file_indices` (sıralı, tekil, 0..N−1), `uncertain_indices` (= `pending_uncertain` kümesi, ⊆ `file_indices`), `remote_present_count` (= N−M), `classification_digest`, `inventory_digest`, `observed_at`. Tekrarlı/aralık dışı indeks ret |
| `DatasetContinuationPlan v3` | v2’nin bütün alanları (kök, Manifest ref’i, parametreler kaynakla **birebir**), `schema_version=3`, `policy_version=3`, `kind=dataset_upload_continuation_plan`, `continuation: ContinuationBinding`, `request_limits` (create=0, project_link=0, presign=PUT=confirm=M, bayt tavanı = seçilen dosyaların toplamı), yeni 0<aralık≤900 s `execution_window`. Politika/risk reducer’ı v2 ile aynıdır; politika kaynaktan devralınır |
| `DatasetUploadApproval v3` | v2 alanları + `acknowledge_unconfirmed_effects` (strict bool); plan/binding özeti bütün continuation alanlarını kapsar. true yalnız `uncertain_indices` boş değilse geçerli; gerekli ve eksik → `approval_required`, gereksiz true → `invalid_request` |
| `TransferRecord v3` | v2 alanları; `dataset_id` admission’da plandan doludur; ek strict `verification_only` (true ⇔ `file_indices` boş); `len(intents) ≤ 3M`; latch ilk intent’te kurulur (v2 ile aynı); `verification_only` kayıt hiç intent üretmez, latch’lenmez ve `unknown` olamaz; write owner/fence/access digest kuralları v2 ile aynı; durum yolu aşağıda |
| `TransferControl v3` | v2 neden kataloğu; sürüm kayıtla eşleşir |
| `TransferVerification v3` | v2 ile aynı alanlar (dataset/project/scope/authorization policy/grant/`observed_at` ve **N** `VerifiedFile`, manifest sırası); `schema_version=3` (kayıt/kontrol/kanıt sürüm eşitliği korunur) |
| `DatasetUploadSummary v3` | v2 alanları + `continuation_of` (kaynak operation kimliği), `continuation_files`, `observed_files`, `confirmed_files`; yol/baseline/receipt alanları yok. v1/v2 özetleri değişmez |
| `DatasetUploadResumeReport v1` | `schema_version=1`, `kind=dataset_upload_resume_report`, kaynak operation/dataset kimliği, `eligible`, kapalı `blockers`, sınıf sayıları, N, M, M için toplam bayt, `unconfirmed_ack_required`, önerilen eylem (`prepare|reconcile|wait|none`), kota etkisi (yeniden sayılacak dosya/payload), `classification_digest`, `inventory_digest`, `observed_at`, nullable `plan_id`/`plan_digest` (`--prepare` ile), sorunlu sınıf başına ≤8 örnek göreli yol (literal-secret taramalı) |

`classification_digest`: `{index, class}` çiftlerinin sıralı canonical JSON’u ile zincir journal özetinin (dosya başına birleşik confirm durumu) SHA-256’sı. `inventory_digest`: uzak envanterin sıralı `(path, size, sha256)` kümesinin SHA-256’sı; item kimlikleri ve sağlayıcı zamanı digest’e girmez.

## Rapor ve hata ayrımı

Kapalı `blockers` (rapor modunda exit 0): `source_active`, `source_ineligible`, `source_terminal`, `reconcile_available`, `create_unknown`, `membership_unobserved`, `known_negative`, `drift_missing`, `conflict`, `extra_remote`, `inventory_unreliable`, `inventory_too_large`, `local_changed`. Hatalar yalnız şunlardır: `operation_not_found`, `state_invalid`, bayrak/ack hataları (`invalid_request`, `approval_required`), taşıma/erişim (`remote_access_denied`/`transport_*`) ve yerel girdi bozulması. Kapalı mesaj/eylem eşlemesi uygulama kartında bu tablonun kolonu olarak kesinleşir (her engel için tek cümle neden + tek sonraki adım).

## Stage grafiği, durum yolu ve kapılar

Graf yalnız `{(presign,i),(put,i),(confirm,i): i ∈ file_indices}` kümesidir (3M intent, her biri tek accepted makbuz). Presign’ın öncülü yoktur; PUT/confirm öncülleri v2’deki gibidir. Create/link intent’i bu operation’da hiçbir zaman oluşmaz (arm kapısı reddeder). `request_digest` dataset kimliğini plan bağından alır; create makbuzuna bakmaz. Namespace: plan kökün saklı `intent_digest`ini kullanır, `_namespace_available` bu tür için atlanır, hot/full invariant “`namespace.create_operation_id == baseline_operation_id`”dir; yeni create hakkı doğmaz. Kök baseline, kök görünümünden salt okuma **zincir çözümleyicisiyle** okunur (kaynak → kök görünümü → CreateReceiptV2; özeti `baseline_digest` ile eşit olmalı); arm, renew, acquire_read, read_failed, prepare_initial_read, verified ve original producer’ın detail↔baseline karşılaştırması bu çözümleyiciyi kullanır. Reservation ve kapasite formülü plan türüne göre sürümlüdür; v1/v2 satırlarının doğrulaması değişmez.

**Durum yolu.** Latch ilk intent’te kurulur (v2 ile aynı). İlk intent’ten önce kesinti, yerel iptal veya süre dolumu kaydı `cancelled` yapar; kaynak değişmeden kalır ve aynı kaynaktan yeni plan hazırlanabilir. İntent’ten sonrası `unknown`/`request_uncertain` (okuma hatasında `unknown`/`read_unavailable`, yalnız v3 için açık dal) olur. `verification_only` kayıt: admission → okuma → proof → `succeeded`/`metadata_verified`; okuma hatası/kesinti/süre dolumu `unknown` değil hata veya `cancelled`dır. Mevcut `reconcile`, 3M makbuzu tam ama proof’u eksik v3 unknown kaydı için aynı operation’da çalışır.

**Confirm oracle.** `created=1`, `batch_duplicates=0` ve varsa `actual_count == remote_present_count + bu operation’da kabul edilmiş confirm sayısı + 1` (sağlayıcıda sayı veri seti düzeyinde kümülatiftir). v2 yolunun tabanı 0’dır ve değişmez.

| İşlem | v3 farkı |
|---|---|
| prepare (`resume --prepare`) | v2 kapıları + kaynak uygunluğu + taze envanter + sınıflandırma; yerel root/Manifest **tam** yeniden hash’lenir; lease’i dolmuş kaynak dondurulur |
| approve | v2 ack kuralları + `acknowledge_unconfirmed_effects` kuralı; draft onaylanmaz |
| admit/start | v2 kapıları + envanter yeniden sınıflanır; özet farklıysa `continuation_remote_changed`; kaynak hâlâ non-terminal ve lease’siz; zincir dışında non-terminal operation yok; yeni create hakkı doğmaz |
| arm | Yalnız presign/put/confirm; `file_indices` dışı indeks ve create/link reddedilir; geri kalan v2 |
| read/proof | Başarı: M için tam 3M makbuz + N dosyalık ordered metadata (`TransferVerification v3`) + kök baseline eşliği; authority/pricing/remote-bytes yükseltilmez |

## Hata kodları

| Kod | Exit | Tetik |
|---|---:|---|
| `continuation_not_possible` | 2 | `--prepare` ile uygunsuzluk; kapalı ayrıntı `blockers` (sıralı kapalı adlar); operation kimliği korunur; sabit mesaj `resume` raporuna yönlendirir |
| `continuation_remote_changed` | 2 | Admission öncesi taze sınıflandırma özeti kayıtlı plandan farklı; hiçbir etki yok, yeni `resume --prepare` gerekir |

Diğer retler mevcut kodlardır (`operation_conflict`, `operation_not_found`, `approval_required`, `invalid_request`, `upload_plan_not_valid`, `input_changed`, `state_invalid`, `remote_access_denied`/`transport_*`, `operation_uncertain`). JSON/NDJSON Result v1 korunur; sır, provider gövdesi, `created_dataset` ve tam yol listesi dökülmez. `unknown` kaynakların `show` metin çıktısı yerel ön kontrol uygunsa `resume` yolunu önerir; DTO’lar değişmez. Kabul ve sınırlar [ADR-0031](../decisions/0031-upload-continuation.md#sonuçlar-ve-kabul)’tedir.
