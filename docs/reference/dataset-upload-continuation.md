# Upload continuation sözleşmesi

**Durum:** Taslak sözleşme — [ADR-0031](../decisions/0031-upload-continuation.md) Accepted (2026-11-06); uygulama ve canlı kabul yok. **Tarih:** 2026-11-06. Komut, alan ve hata adları onay sonrası uygulama kartlarında kesinleşir; bu belge çalışan örnek değildir. Kaynak v1/v2 sözleşmeleri ([transfer](dataset-transfer.md), [v2](dataset-upload-v2.md), [uzlaştırma](dataset-upload-reconciliation.md), [public yüzey](dataset-upload-public.md)) ve onların byte/digest/golden’ları değişmez; yalnız **v3 continuation kayıtları** için başarı grafiği tanımı farklıdır (kısmi değişiklik notları ADR-0031’dedir). Bu belge continuation hata kodlarının **kanonik** tablosudur; [CLI sözleşmesi](cli-contract.md) buraya bağlanır, kopyasını tutmaz.

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
| Kaynak politikası `verified_only` (sağlayıcı oracle’ı/yetki yok; `--accept-unverified-read` kabul edilmez) | `source_ineligible`; devam yok |
| Kaynağın iptal edilmemiş (`cancelled` olmayan) torunu var: intent’li `unknown`/`running`/`failed` veya başarıyla biten `succeeded` (`verification_only` dahil) | `source_superseded`; rapor torunun kimliğini (`related_operation_id`) verir: torun `unknown` ise `resume --operation-id <torun>`, başarıyla bitmişse devam gerekmez. `cancelled` (sıfır-intent’li) torun kaynağı bloke etmez |
| Etkin write/read owner (lease dolmamış) veya lease’i dolmamış non-terminal torun | `source_active`; eylem `wait`, lease bitince tekrar. `--prepare`: `operation_conflict` (torunun kimliği ve `resume --operation-id <torun>` önerisi) |
| Lease’i dolmuş `admitted` torun | Engel değil: rapor eylemi `prepare`; `--prepare` torunu `cancelled/lease_expired` yapar ve devam eder |
| Lease dolmuş `running` (`running` her zaman latch’lidir: etki durumları kalıcı latch ister) | Rapor yerel durumu değiştirmez; `--prepare` mevcut execution izni üretmeyen `cleanup_expired` yoluyla kaynağı `unknown`/`request_uncertain` yapar (fence+1) ve lease’i dolmuş `admitted` torunları `cancelled` yapar. Zaten `unknown` kaynağa dokunulmaz (neden alanı korunur, fence/revision artmaz) |
| `unknown` (reset, rotasyon veya `identity_reset` dahil), kök CreateReceiptV2 var, zincirde `rejected` makbuz yok | Uygun; plan **güncel** scope ile kurulur |
| Kaynağın kendi grafiği zaten tam (tam 2+3N veya v3 için 3M makbuz), yalnız kanıt eksik | `reconcile_available`: `resume` M=0 yerine mevcut `reconcile`ı önerir |
| Zincirde herhangi bir `rejected` makbuz | `known_negative` (bilinen olumsuz sonuç; not: üretim yolu bugün bunu yazmaz, [ADR-0031 §2](../decisions/0031-upload-continuation.md#2-uygunluk-yalnız-dosya-aktarım-fazının-kalanı)) |
| Create receipt/dataset ID yok (kök create unknown) | `create_unknown` (sahiplenme yok) |
| Zincirde döngü, farklı dataset kimliği, kopuk soy, baseline özeti uyuşmazlığı | `state_invalid` (hata) |
| Proje üyeliği exact bir kez gözlenmedi veya detail↔baseline uyuşmuyor | `membership_unobserved` |
| Yerel klasör/Manifest uyuşmuyor | `local_changed` (rapor); `--prepare`: `input_changed`/`input_invalid` |

Donma yerel CAS’tır; eski sürecin zaten gönderilmiş isteğini geri çekmez. Etkili hak üretmez.

## Kanıt sınıfları ve karar tablosu

Girdi: **kaynağın soyunun (kök → kaynak) journal’larının birleşimi** — kaynak zincirin ucu olduğundan bu, dataset’in bütün intent’li geçmişidir (dosya başına: herhangi bir operation’da accepted confirm makbuzu var mı; yoksa herhangi birinde confirm intent’i var mı; sıfır-intent’li operation hiçbir şey katmaz; intent’li dal dışı makbuz olamaz çünkü kaynağın intent’li torunu varsa kaynak `source_superseded` olur) ve taze, tam, sayfalı uzak envanter. “Exact item” = Manifest’teki (ad, boyut, SHA-256) üçlüsüyle aynı, tekil ve başka kimlikle çakışmayan tek item. Tablo tam ve kapalıdır:

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
| envanter düzeyi | Manifest dışı fazladan item | (dosya sınıfı yok) plan düzeyi `extra_remote` engeli |

**Öncelik ve güvenilirlik.** Gözlenmiş çelişki (aynı adda farklı boyut/SHA, aynı adda iki farklı kimlik, aynı SHA başka adda) pozitif kanıttır ve her zaman `conflict`tır. Envanter güvenilir değilse yokluk ve tekillik iddia edilemez: çelişkisi olmayan her dosya `inventory_unreliable` olur ve o liste için `confirmed`, `observed`, `drift_missing`, `pending_clean` veya `pending_uncertain` üretilmez (eksik bir listede “yok” demek var olan dosyayı yeniden göndermeye ya da kullanıcıyı yanlış bir drift işlemine yönlendirmeye yol açardı); sonra yeniden denenir. Envanter şu hâllerde güvenilmezdir: herhangi bir item’ın `sha256_hash` değeri null; aynı kimliğin iki kez listelenmesi; `total` değerinin sayfalar arasında değişmesi veya toplanan item sayısına eşit olmaması; tekrarlanan cursor; 128 sayfa sınırı; 1.024 item sınırı. Güvenilir envanterde tablo olduğu gibi uygulanır. Ayrıntılar: “kopya item” aynı adda iki farklı kimlikli item’dır (`conflict`); “kopya kimlik” aynı kimliğin birden çok kez listelenmesidir (sayfalama kayması gibi; `inventory_unreliable`). 1.024 aşımı hem `inventory_unreliable` hem `inventory_too_large` engelini üretir. 128 sayfa sınırı: 128. sayfa son sayfaysa sorun yoktur, 128. sayfadan sonra yeni cursor varsa güvenilmezdir; okuma bütçesi (16 MiB yanıt) bundan önce dolarsa sonuç sınıf değil `upload_limit_exceeded` hatasıdır. Özetteki yinelenen satırlar korunur (küme değil çoklu küme) ve sıra kod noktası sırasıdır. Envanter okuyucusu manifest ile karşılaştırma yapmaz ve içerik tutarsızlığında hata vermez (bu hâller yukarıdaki gibi sınıfa dönüşür); biçimi bozuk sayfa, başka dataset’e ait item, yerel sözdizimini bozan item (taşınabilir olmayan ad, 500 MB üstü boyut, küçük harf dışı hash, UUID olmayan kimlik) ve taşıma/erişim hataları hata olarak kalır (`invalid_response`, `remote_*`): böyle bir item yabancı item sayılıp `extra_remote` olmaz, sağlayıcı yanıtı biçimsiz sayılır ve uzak durumun Platform arayüzünden incelenmesi gerekir. Presign/PUT durumu sınıfı değiştirmez (confirm intent’i yoksa dosya `pending_clean`dır). `file_indices` her zaman `pending_clean ∪ pending_uncertain` kümesinin tamamıdır ve `uncertain_indices` tam olarak `pending_uncertain` kümesidir; kısmi seçim yoktur. `remote_present_count` = `confirmed`+`observed` sayısıdır (= N−M). Tek `drift_missing`/`conflict`/`inventory_unreliable` veya fazladan item plan hazırlamaz; saf sınıflandırıcı engel varken seçim (`file_indices`, `uncertain_indices`, `remote_present_count`) vermez, plana yalnız engelsiz sonuçtan geçilir. `M=0` geçerlidir (yalnız doğrulama). Envanter üst sınırı **1.024 item**’dır; aşılırsa `inventory_unreliable` sınıfı ve `inventory_too_large` engeli oluşur (plan hazırlanmaz, veri sessizce kesilmez). Manifest ≤128 dosya olduğundan bu, Manifest dışı çok sayıda item içeren bir dataset demektir; rapor sabit mesajla devamın desteklenmediğini ve uzak durumun Platform arayüzünden incelenmesi gerektiğini söyler.

## Kapalı tipler (v3 farkları)

Hepsi strict/frozen/extra-forbid, zorunlu alanlı (nullable dahil), bool sayı değildir; canonical ASCII JSON ve byte sınırları v1/v2 ile aynıdır.

| Tip | Alanlar ve kural |
|---|---|
| `ContinuationBinding` | `source_operation_id`, `baseline_operation_id` (UUIDv4; accepted CreateReceiptV2’yi taşıyan kök), `dataset_id` (provider UUID), `baseline_digest` (immutable `created_dataset` DTO’sunun canonical SHA-256’sı; DTO’nun kendisi planda yok), `intent_digest` (kökün değerinin kopyası ve kökle eşitliği doğrulanan fazladan bağlama denetimi; türetim hedef/owner/proje/addandır, scope’un credential alanlarını içermez), `file_indices` (sıralı, tekil, 0..N−1), `uncertain_indices` (= `pending_uncertain` kümesi, ⊆ `file_indices`), `remote_present_count` (= N−M), `classification_digest`, `inventory_digest`, `observed_at`. Tekrarlı/aralık dışı indeks ret |
| `DatasetContinuationPlan v3` | v2’nin bütün alanları (kök, Manifest ref’i, parametreler kaynakla **birebir**), `schema_version=3`, `policy_version=3`, `kind=dataset_upload_continuation_plan`, `continuation: ContinuationBinding`, `request_limits` (create=0, project_link=0, presign=PUT=confirm=M, bayt tavanı = seçilen dosyaların toplamı), yeni 0<aralık≤900 s `execution_window`. Politika/risk reducer’ı v2 ile aynıdır; politika kaynaktan devralınır |
| `DatasetUploadApproval v3` | v2 alanları + `acknowledge_unconfirmed_effects` (strict bool); plan/binding özeti bütün continuation alanlarını kapsar. true yalnız `uncertain_indices` boş değilse geçerli; gerekli ve eksik → `approval_required`, gereksiz true → `invalid_request` |
| `TransferRecord v3` | v2 alanları; `dataset_id` admission’da plandan doludur; ek strict `verification_only` (true ⇔ `file_indices` boş); `len(intents) ≤ 3M`; latch ilk intent’te kurulur (v2 ile aynı); `verification_only` kayıt hiç intent üretmez, latch’lenmez ve `unknown` olamaz; write owner/fence/access digest kuralları v2 ile aynı; durum yolu aşağıda |
| `TransferControl v3` | v2 neden kataloğu; sürüm kayıtla eşleşir |
| `TransferVerification v3` | v2 ile aynı alanlar (dataset/project/scope/authorization policy/grant/`observed_at` ve **N** `VerifiedFile`, manifest sırası); `schema_version=3` (kayıt/kontrol/kanıt sürüm eşitliği korunur) |
| `DatasetUploadSummary v3` | v2 alanları + `continuation_of` (kaynak operation kimliği), `continuation_files`, `observed_files`, `confirmed_files`; yol/baseline/receipt alanları yok. v1/v2 özetleri değişmez |
| `DatasetUploadResumeReport v1` | `schema_version=1`, `kind=dataset_upload_resume_report`, kaynak operation/dataset kimliği, `eligible`, kapalı `blockers`, sınıf sayıları, N, M, M için toplam bayt, `unconfirmed_ack_required`, önerilen eylem (`prepare|reconcile|wait|none`), nullable `related_operation_id` (etkin veya iptal edilmemiş torun), kota etkisi (yeniden sayılacak dosya/payload), `classification_digest`, `inventory_digest`, `observed_at`, nullable `plan_id`/`plan_digest` (`--prepare` ile), sorunlu sınıf başına ≤8 örnek göreli yol (literal-secret taramalı) |

`classification_digest`: `{index, class}` çiftlerinin sıralı canonical JSON’u ile zincir journal özetinin (dosya başına birleşik confirm durumu) SHA-256’sı. `inventory_digest`: uzak envanterin sıralı `(path, size, sha256)` kümesinin SHA-256’sı; item kimlikleri ve sağlayıcı zamanı digest’e girmez. Kesin ön görüntüler (canonical ASCII JSON, sıralı anahtarlar): `classification_digest` = `{"chain":{"rejected":bool,"states":[…]},"files":[[index,class],…],"kind":"upload_classification"}` (`states` dosya başına `none`/`intent`/`accepted`; kaynak grafiğinin tamlığı sınıf değil engel olduğundan girmez); `inventory_digest` = `{"items":[[path,size,sha256|null],…],"kind":"upload_inventory"}` (satırlar `(path, size, sha256)` sıralı, null `sha256` en küçük).

## Rapor ve hata ayrımı

Kapalı `blockers` (rapor modunda exit 0): `source_active`, `source_ineligible`, `source_superseded`, `source_terminal`, `reconcile_available`, `create_unknown`, `membership_unobserved`, `known_negative`, `drift_missing`, `conflict`, `extra_remote`, `inventory_unreliable`, `inventory_too_large`, `local_changed`. **Eylem önceliği.** `blockers` bütün geçerli engelleri taşır; tek `önerilen eylem` şu sırayla seçilir: `source_terminal` → `none`; `source_active` → `wait`; `source_superseded` → `none` (+ `related_operation_id`); `source_ineligible`, `create_unknown`, `membership_unobserved`, `known_negative` → `none`; `reconcile_available` → `reconcile`; `local_changed`, `drift_missing`, `conflict`, `extra_remote`, `inventory_unreliable`, `inventory_too_large` → `none`; engel yoksa `prepare`. Hatalar yalnız şunlardır: `operation_not_found`, `state_invalid`, bayrak/ack hataları (`invalid_request`, `approval_required`), taşıma/erişim (`remote_access_denied`/`transport_*`), biçimsiz sağlayıcı yanıtı veya aşılan okuma bütçesi (`invalid_response`, `upload_limit_exceeded`) ve yerel girdi bozulması. Kapalı mesaj/eylem eşlemesi uygulama kartında bu tablonun kolonu olarak kesinleşir (her engel için tek cümle neden + tek sonraki adım).

## Stage grafiği, durum yolu ve kapılar

Graf yalnız `{(presign,i),(put,i),(confirm,i): i ∈ file_indices}` kümesidir (3M intent, her biri tek accepted makbuz). Presign’ın öncülü yoktur; PUT/confirm öncülleri v2’deki gibidir. Create/link intent’i bu operation’da hiçbir zaman oluşmaz (arm kapısı reddeder). `request_digest` dataset kimliğini plan bağından alır; create makbuzuna bakmaz. Namespace: plan kökün `intent_digest`ini kullanır (kopya; türetimle aynı değer, `read_plan`’ın namespace payload eşitliği değişmez), `_namespace_available` bu tür için atlanır, hot/full invariant “`namespace.create_operation_id == baseline_operation_id`”dir; yeni create hakkı doğmaz. Kök baseline, kök görünümünden salt okuma **zincir çözümleyicisiyle** okunur (kaynak → kök görünümü → CreateReceiptV2; özeti `baseline_digest` ile eşit olmalı); arm, renew, acquire_read, read_failed, prepare_initial_read, verified ve original producer’ın detail↔baseline karşılaştırması bu çözümleyiciyi kullanır. Reservation ve kapasite formülü plan türüne göre sürümlüdür; v1/v2 satırlarının doğrulaması değişmez.

**Durum yolu.** Latch ilk intent’te kurulur (v2 ile aynı). Kayıt ilk intent’ten önce etkisizdir; kapalı uç-durum tablosu ([ADR-0031 §5](../decisions/0031-upload-continuation.md#5-yürütme)):

| Olay | Sonuç | Kalıcı kayıt |
|---|---|---|
| `M=0` okuma ve proof başarılı | `metadata_verified` | `succeeded` |
| Okuma/proof hatası (ilk intent öncesi) | kaynağın kendi kodu (exit 1/3); `operation_uncertain` değil | `cancelled`/`local_cancelled` |
| SIGINT/Task iptali (ilk intent öncesi) | `request_cancelled`/6 | `cancelled`/`local_cancelled` |
| Lease kaybı/SIGKILL (ilk intent öncesi) | sonraki `resume --prepare`/`cleanup_expired` | `cancelled`/`lease_expired` |
| İlk intent’ten sonra kesinti | mevcut v2 kodları | `unknown`/`request_uncertain` (okuma hatasında `read_unavailable`, yalnız v3 için açık dal) |

`verification_only` kayıt: admission → okuma → proof → `succeeded`/`metadata_verified`; hiçbir zaman `unknown` olmaz. Başarıyla biten `verification_only` torun kaynağı `source_superseded` yapar; `show` kaynak için torunun kimliğini gösterir (tekrarlanan doğrulama kota harcamaz). v3 için açık yazılacak dallar: `prepare_initial_read` (`admitted` ⇔ `verification_only`), `read_failed`, `_uncertain_verification`, `stop_local` nedeni. Mevcut `reconcile`, 3M makbuzu tam ama proof’u eksik v3 unknown kaydı için aynı operation’da çalışır.

**Confirm oracle.** `created=1`, `batch_duplicates=0` ve varsa `actual_count ∈ {remote_present_count + k + 1, k + 1}` (k = bu operation’da kabul edilmiş confirm sayısı). Dolu veri setindeki anlam **gözlenmemiştir** (yalnız taze veri setinde 1, 2 gözlendi): kümülatif (`taban+k+1`) ve yalnız-işlem (`k+1`) anlamlarının ikisi de kabul edilir, kümenin dışı reddedilir; taban 0 iken tek değerdir. v2 yolunun tabanı 0’dır ve değişmez; resume canlı kabulü hangi anlamın gerçekleştiğini kayda geçirir.

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
