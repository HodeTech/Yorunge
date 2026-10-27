# Execution planı v2

**Durum:** P01-3 adım 2 uygulandı; bağımsız review/kabul sürüyor. Prepare/list/show/validate vardır; approve/revoke/forget sonraki uygulama adımındadır. **Tarih:** 2026-10-28. [Accepted ADR-0014](../decisions/0014-execution-plan-validity-and-approval.md) politika kaynağıdır. Eski offline Plan v1 ve digest'i değişmez.

## Kullanıcı akışı

```sh
yorunge plan execution prepare --task llm.train --state-dir ./private-state --output json
yorunge plan execution list --limit 50 --state-dir ./private-state --output json
yorunge plan execution show --plan-id PLAN_UUID --state-dir ./private-state --output json
yorunge plan execution validate --plan-id PLAN_UUID --state-dir ./private-state --output json
```

Prepare mevcut task/recipe/config/profile/project/tool/execution seçeneklerine ek `--input-root PATH` alır. Yerel `data.manifest` varsa root açıkça gereklidir. Public producer yalnız mevcut yerel politika/not-verified üretir; araç, uzak auth ve tam girdi kapanışı doğrulanmadığından ürün planı draft ve yürütülemezdir. Manifest hash'i yalnız dosyanın kendi içeriğini bağlar. `prepared` kabulünün pozitif testleri yalnız test portlarıyladır; ürün görev/backend listesine fixture eklenmez.

Validate güncel `--config`, `--profile`, `--project` alır; recipe/task/tool/execution/root override almaz. Seçimler ve parametreler kaydedilmiş gövdeden korunur. Config her çağrıda bir kez yüklenir; explicit config verilmezse güncel varsayılan kullanılır. Saved custom config/profil/proje güncel context yerine geçirilmez; kullanıcı bunları tekrar açık seçmelidir. Seçilen hizmetin env değeri bir kez okunur; registry ve trusted validator aynı private snapshot'ı kullanır. Public gövdeye Profile, secret referansı, ham secret/tag/K girmez.

List/show güncel validity iddia etmez; env veya girdi içeriği okumaz. Store açılışının migration ve yerel bütünlük kontrolü yapabileceği state sözleşmesine tabidir. List tarihsel ID/digest/görev/hazırlık-expiry/status özetleri verir. Default limit50, max100; sıralama artan `(prepared_at, plan_id)`, `next_cursor` opak canonical base64url çiftidir. Cursor yeni sayfada aynı filtre/sıralamayı sürdürür; eşzamanlı yeni planlar için donmuş snapshot listesi iddia edilmez.

## Python ve sonuç

Aynı ortak çekirdek `api.prepare_execution_plan`, `list_execution_plans`, `show_execution_plan`, `validate_execution_plan` olarak kullanılabilir. Path argümanları strict Path, plan ID canonical UUIDv4'tür. Prepare önceki seçim seçeneklerine input_root/state_dir, validate yalnız config/profile/project/state_dir alır. List limit/cursor/state_dir, show plan_id/state_dir alır. Public API producer, proof, authorization, verified veya imported plan kabul etmez.

Prepare/show `Result[ExecutionPlanView]`: `plan`, `validity`. Show validity=null; prepare raporu aynı çağrının son kontrolüdür. Validate `Result[ExecutionValidity]`: plan_id, digest, valid, checked_at, valid_until ve reasons. Valid=false normal sorgu sonucudur, çıkış0; malformed/state/I/O hataları kontrollü çıkış2 (credential eksikliği3). Hiçbir sonuç dispatch bileti değildir; operation_id=null, executable=false kalır.

Planın static `status=prepared` alanı ilk kayıt anındaki trusted hazırlığı anlatır. Commit gecikmesinde expiry gözlenirse immutable kayıt tutulabilir; dönen validity=false olur ve kayıt gizlenmez. Show/list static status'u güncel yetki olarak sunmaz. Sonraki tüketici kendi güncel doğrulamasını yapmalıdır. Güncel validator'ın yalnız zamanları ilerlemesi planı yeniden yazmaz veya ilk expiry'yi uzatmaz.

## Kapalı gövde ve bütünlük

`ExecutionPlan` bütün alanları kapalı ve strict v2 JSON'dur; extra/duplicate/yanlış enum/tip, nonfinite ve UTF-8 ihlalleri reddedilir. Hash biçimi [ScopeV2 canonical JSON](capability-scope-v2.md#ortak-türler-ve-kodlama) ile aynıdır; yalnız digest dışarıda tutulur. SHA-256 provenance veya insan kimliği imzası değildir. Her body ≤64KiB, input bağları ≤128, store ≤1.024 plan; otomatik plan silinmez.

| Alan grubu | Exact alanlar |
|---|---|
| Kimlik | schema_version=2, policy_version=1, mode=execution, plan_id/store_id/identity_epoch UUIDv4, clock_generation positive int64 |
| Sabit istek | context (sır içermeyen Context), selection (mevcut strict Selection), recipe (strict v1 Recipe) |
| Girdi | input_root=null veya `{anchor,device,inode}`; inputs sıralı/tekrarsız `{role,path,size,digest}[]` |
| Değerlendirme | assessment `{capabilities,inputs_verified,blockers,effects,parameter_mapping,parameter_losses,cost}` |
| Zaman/sonuç | prepared_at/expires_at canonical UTC, status draft/prepared, executable=false, digest SHA-256 |

Capabilities ayrı v2 kayıtlarıdır; tam namespace/task ve gerekli tool/model/execution bağları planla eşleşir. Prepared için taze supported kanıt, tam girdi doğrulaması ve kayıpsız parametre eşlemesi gerekir. Effects `{kind: local_read|remote_write|execution, service_id, description_code}`; mapping `{source,destination}`; cost null veya `{units,unit,source,checked_at,expires_at}` nonnegative int64 tahmindir. Bilinmeyen maliyet null'dır. Tipli alan varlığı gerçek maliyet/araç desteği değildir.

## Dosya ve süre sınırı

Prepare root'u CWD'ye bir kez bağlar; saved mutlak UTF-8 anchor + device/inode sonraki validate'da kullanılır. Root mutlak olabilir; girdi mutlak/traversal/boş/dot bileşen içeremez. `/` descriptor'ından başlayan no-follow directory walk ve son dosyada no-follow/nonblocking open, regular fstat, 1MiB bloklu SHA-256, önce/sonra stat ve path zinciri yeniden kontrolü uygulanır. Gözlenen root/ancestor/dosya değişimi reddedilir; hata yolunda descriptor kapanır. Eksik platform/flag/dir_fd desteği içerik/env öncesi input_unsupported üretir.

Toplam hazırlık/validation bütçesi30s ve bir çağrıda okunan içerik1GiB; SQL lock en çok1s ve toplam bütçenin içindedir. Plan ömrü en çok300s ve gereken kanıt/tahminin en erken expiry'siyle sınırlıdır. Son transaction ve commit sonrası çıktı kapıları tam expiry, monotonic deadline, clock generation/anomaly ve credential bağlarını tekrar kontrol eder. Clock invalidation business ret/rollback'ten bağımsız kalır.

input_invalid/input_changed/input_budget_exceeded/execution_timeout, plan_not_found/plan_not_valid/plan_capacity_exceeded kontrollü çıkış2'dir; mesajlar path veya sır eklemez. Validation gözlenen içerik/root değişimini valid=false/inputs_changed olarak raporlar. Aynı-UID/root saldırısı, inode yeniden kullanımı, mount/rename ve sonraki gözlenmeyen değişimler için sandbox garantisi yoktur; [ADR sınırı](../decisions/0014-execution-plan-validity-and-approval.md#girdi-ve-güncel-bağ-doğrulaması) korunur.

## State ve bakım

Gerçek consumer migration2→3 execution_plans ve sıralama index'ini ekler. Eski migration/checksum değişmez; okumada body/digest/index ilişkisi, full validation'da bütün kayıtlar/kota denetlenir. Cache temizliği planları silmez. Reset geçmiş planı korur; yeni epoch onu etkisizleştirir. Restore snapshot sonrası planları kaybedebilir ve eski snapshot planları tarihsel kalır. Preview v2 plan sayısı/fingerprint ile onayı bağlar; plan değişimi confirmation'ı eskiltir, cache/clock-only güncelleme eskiltmez. Approval entegrasyonu sonraki adımda tamamlanır; operation runtime restore yasağı sürer.
