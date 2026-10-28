# Execution planı v2

**Durum:** P01-3 dört adımın yerel kabulü ve ikişer bağımsız review tamamlandı; development PR/CI ve kullanıcı incelemesi ayrıca kaydedilir. Prepare/list/show/validate/approve/revoke/forget vardır. **Tarih:** 2026-10-28. [Accepted ADR-0014](../decisions/0014-execution-plan-validity-and-approval.md) politika kaynağıdır. Eski offline Plan v1 ve digest'i değişmez.

## Kullanıcı akışı

```sh
yorunge plan execution prepare --task llm.train --state-dir ./private-state --output json
yorunge plan execution list --limit 50 --state-dir ./private-state --output json
yorunge plan execution show --plan-id PLAN_UUID --state-dir ./private-state --output json
yorunge plan execution validate --plan-id PLAN_UUID --state-dir ./private-state --output json
```

Prepare mevcut task/recipe/config/profile/project/tool/execution seçeneklerine ek `--input-root PATH` alır. Yerel `data.manifest` varsa root açıkça gereklidir. Public producer yalnız mevcut yerel politika/not-verified üretir; araç, uzak auth ve tam girdi kapanışı doğrulanmadığından ürün planı draft ve yürütülemezdir. Manifest hash'i yalnız dosyanın kendi içeriğini bağlar. `prepared` kabulünün pozitif testleri yalnız test portlarıyladır; ürün görev/backend listesine fixture eklenmez.

Validate güncel `--config`, `--profile`, `--project` alır; recipe/task/tool/execution/root override almaz. Seçimler ve parametreler kaydedilmiş gövdeden korunur. Config her çağrıda bir kez yüklenir; explicit config verilmezse güncel varsayılan kullanılır. Saved custom config/profil/proje güncel context yerine geçirilmez; kullanıcı bunları tekrar açık seçmelidir. Seçilen hizmetin env değeri bir kez okunur; registry ve trusted validator aynı private snapshot'ı kullanır. Public gövdeye Profile, secret referansı, ham secret/tag/K girmez.

List/show güncel validity iddia etmez; env veya girdi içeriği okumaz. Store açılışının migration ve yerel bütünlük kontrolü yapabileceği state sözleşmesine tabidir. List tarihsel ID/digest/görev/hazırlık-expiry/status özetleri verir. Default limit 50, max 100; sıralama artan `(prepared_at, plan_id)`, `next_cursor` opak canonical base64url çiftidir. Cursor yeni sayfada aynı filtre/sıralamayı sürdürür; eşzamanlı yeni planlar için donmuş snapshot listesi iddia edilmez.

## Python ve sonuç

Aynı ortak çekirdek `api.prepare_execution_plan`, `list_execution_plans`, `show_execution_plan`, `validate_execution_plan` olarak kullanılabilir. Path argümanları strict Path, plan ID canonical UUIDv4'tür. Prepare önceki seçim seçeneklerine input_root/state_dir, validate yalnız config/profile/project/state_dir alır. List limit/cursor/state_dir, show plan_id/state_dir alır. Public API producer, proof, authorization, verified veya imported plan kabul etmez.

Prepare/show `Result[ExecutionPlanView]`: `plan`, `validity`, `approval`. Show validity=null; prepare raporu aynı çağrının son kontrolüdür. Validate `Result[ExecutionValidity]`: plan_id, digest, valid, checked_at, valid_until, reasons ve ayrı approval durumunu. Valid=false normal sorgu sonucudur, çıkış 0; malformed/state/I/O hataları kontrollü çıkış 2 (credential eksikliği 3). Hiçbir sonuç dispatch bileti değildir; operation_id=null, executable=false kalır.

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

Prepare göreli root'u platform/tür kapılarından sonra, config/recipe çözümlemesi ve state/env işlemlerinden önce çağrı başlangıcındaki CWD'ye bir kez bağlar; mutlak root veya null için CWD gerekmez. CWD okunamıyorsa kontrollü input_invalid döner; saved mutlak UTF-8 anchor + device/inode sonraki validate'da kullanılır. Root mutlak olabilir; girdi mutlak/traversal/boş/dot bileşen içeremez. `/` descriptor'ından başlayan no-follow directory walk ve son dosyada no-follow/nonblocking open, regular fstat, 1 MiB bloklu SHA-256, önce/sonra stat ve path zinciri yeniden kontrolü uygulanır. Gözlenen root/ancestor/dosya değişimi reddedilir; hata yolunda descriptor kapanır. Eksik platform/flag/dir_fd desteği içerik/env öncesi input_unsupported üretir.

Hash ilk fstat ile görülen boyut kadar okur; her read isteği kalan dosya/çağrı baytları ve 1 MiB blok sınırıyla kısıtlanır. Tam sınırda EOF aramak için ek bayt okunmaz; kısa okuma ve son fstat/signature değişimi input_changed ile reddedilir. İlk stat sonrası büyüyen dosyanın yeni baytları bütçe dışına taşarak okunmaz; sonraki gözlenmeyen değişimler için aynı güven sınırı geçerlidir.

Toplam hazırlık/validation bütçesi 30 s ve bir çağrıda okunan içerik 1 GiB; SQL lock en çok 1 s ve toplam bütçenin içindedir. Plan ömrü en çok 300 s ve gereken kanıt/tahminin en erken expiry'siyle sınırlıdır. Son transaction ve commit sonrası çıktı kapıları tam expiry, monotonic deadline, clock generation/anomaly ve credential bağlarını tekrar kontrol eder. Clock invalidation business ret/rollback'ten bağımsız kalır.

input_invalid/input_changed/input_budget_exceeded/execution_timeout, plan_not_found/plan_not_valid/plan_capacity_exceeded kontrollü çıkış 2'dir; mesajlar path veya sır eklemez. Validation gözlenen içerik/root değişimini valid=false/inputs_changed olarak raporlar. Aynı-UID/root saldırısı, inode yeniden kullanımı, mount/rename ve sonraki gözlenmeyen değişimler için sandbox garantisi yoktur; [ADR sınırı](../decisions/0014-execution-plan-validity-and-approval.md#girdi-ve-güncel-bağ-doğrulaması) korunur.

## State ve bakım

Gerçek consumer migration 2→3 execution_plans ve sıralama index'ini ekler. Eski migration/checksum değişmez; okumada body/digest/index ilişkisi, full validation'da bütün kayıtlar/kota denetlenir. Cache temizliği planları silmez. Reset geçmiş planı korur; yeni epoch onu etkisizleştirir. Restore snapshot sonrası planları kaybedebilir ve eski snapshot planları tarihsel kalır. Preview v2 plan sayısı/fingerprint ile onayı bağlar; plan değişimi confirmation'ı eskiltir, cache/clock-only güncelleme eskiltmez. Approval aynı restore sınırına dahildir; operation runtime restore yasağı sürer.


## Digest onayı ve yerel yönetim

```sh
yorunge plan execution approve --plan-id PLAN_UUID --confirm FULL_PLAN_DIGEST --state-dir ./private-state --output json
yorunge plan execution revoke --plan-id PLAN_UUID --state-dir ./private-state --output json
yorunge plan execution forget --plan-id PLAN_UUID --confirm FULL_PLAN_DIGEST --state-dir ./private-state --output json
```

Python `approve_execution_plan(plan_id, confirmation=None, *, config=None, profile=None, project=None, state_dir=None)`, `revoke_execution_approval(plan_id, *, state_dir=None)` ve `forget_execution_plan(plan_id, confirmation=None, *, state_dir=None)` aynı çekirdektir. Approve validate ile aynı explicit context seçeneklerini kullanır; revoke/forget config/profile/project almaz, env/girdi okumaz. Eksik/yanlış confirmation `approval_required` çıkış 4; doğru digest ile blocked/geçersiz plan `plan_not_valid` çıkış 2. Prompt, sessiz onay veya otomatik tekrar yoktur.

Approve her çağrıda güncel trusted validation yapar. Hâlâ geçerli aynı onay idempotent olarak aynı record'ı döndürür; yeni daha kısa kanıt süresi effective valid_until değerini kısaltır. İlk plan/record expiry'si uzatılmaz. Revoked/expired onaydan sonraki açık approve yeniden doğrulayarak yeni approval_id üretir. Revocation saat anomalisi veya plan expiry'si sırasında da yapılabilir. Validation planın bağ geçerliliğini `valid` olarak, onayın güncel etkinliğini ayrı `approval.effective` olarak verir; geçerli ama onaysız/revoked plan dispatch yetkisi değildir.

Onay ayrı `ExecutionApproval` kapalı JSON kaydıdır: schema_version=1, approval_id/plan_id UUIDv4, plan_schema_version=2, plan_digest, binding_digest (zaman dışındaki context/selection/recipe/input/assessment bağlarının SHA-256'sı), store_id/identity_epoch/clock_generation, approved_at/expires_at canonical UTC, status approved/revoked ve zorunlu nullable revoked_at. İlişkiler/digest/süre her tam kayıt okumasında doğrulanır; list payload okumadan yalnız tarihsel index özeti sunar. Migration 3→4 execution_approvals ekler; plan başına tek güncel kayıt ve plan FK'si vardır. Bu tam insan audit geçmişi veya kriptografik kimlik kanıtı değildir.

Approve/revoke sonucu `ExecutionApprovalState`: plan_id, plan_digest, record veya null, effective, checked_at, valid_until ve reasons. Show aynı tarihsel record'ı effective=null/checked_at=null olarak verir; list approval_status yalnız kayıt durumudur. Son SQL transaction'da bütün bağlar/süreler ve mevcut idempotent onayın süresi tekrar denetlenir; son DB işi ardından yeni UTC/monotonic kontrolü vardır. Plan/onay nesli ve gözlenen expiry rollback/restart ile canlanmaz. Onay yazıldıktan sonra commit gecikmesinde geçersizleşir veya son kontrol timeout/state/I/O hatasıyla tamamlanamazsa çıkış 2 `plan_not_valid` olur; text kaydın oluştuğunu söyler, JSON details `{plan_id,approval_id,recorded:true,reason_code}` taşır. Revoke COMMIT sonrasındaki son kontrol hata verirse bilinen kalıcı kayıt için aynı plan_not_valid/details zarfı verilir; record yoksa özgün son kontrol hatası korunur. COMMIT öncesi hata kalıcı revoke yapılmış gibi raporlanmaz. Kayıt show ile görülebilir; etkin başarı veya otomatik yeniden onay sunulmaz.

Forget yalnız doğrulanan seçili planı ve transaction anında bağlı güncel onayı atomik siler; eski onay durumunu pinlemez. Başka plan/cache/identity/backup silinmez, uzak iptal yapılmaz. Sonuç plan_id/digest/forgotten=true/local_only=true/approval_removed taşır. Kota doluysa list ile ID/digest bulup seçili forget sonrası yeni prepare yapılabilir. Eşzamanlı approve/revoke/forget için plan tekrar okunur ve FK/cascade sınırı korunur; validate/approve sırasında unutulmuş/değişmiş plan state_changed olur. Gelecek operation tüketicisi plan silmeye aynı transaction'da FK/restrict sınırı eklemek zorundadır.

Preview v2 current/source ayrıca approval_count/approval_fingerprint taşır; onay/iptal değişimi eski confirmation'ı bozar, cache-only churn bozmaz. Reset plan/onay geçmişini koruyup yeni epoch ile etkisizleştirir; restore snapshot sonrası plan/onay geçmişini kaybedebilir. Eski runtime schema 1/2/3 intent, stage ve live çifti kaynak kaybında da yeni şemaya yükseltilmeden intent kaldırılmaz. Bozuk plan/onay yeni epoch ile aklanmaz.
