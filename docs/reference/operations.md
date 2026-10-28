# Operation ve yerel jobs sözleşmesi

**Durum:** Proposed — [ADR-0016](../decisions/0016-operation-admission-and-ownership.md) onayı bekleniyor; bu dosyadaki yeni tip/komutlar uygulanmadı. **Tarih:** 2026-10-28. [Mevcut public alt küme](cli-contract.md#uygulanan-alt-küme).

## Sınır ve kaynak

Operation, immutable execution planından ayrı kalıcı bir iştir. Planı hazırlamak/onaylamak operation oluşturmaz. P01-4'te public yürütme veya fixture backend yoktur; jobs yalnız gerçek store kayıtlarını okur. Lifecycle, admission/approval snapshot, dispatch latch, lease/fencing, kotalar ve bakım kurallarının tek normatif karar kaynağı ADR-0016'dır. Burada CLI/Python ve wire ayrıntıları tanımlanır; kod başlamadan bu öneri birlikte onaylanır.

Önerilen CLI:

```text
yorunge jobs list [--status STATUS] [--plan-id UUID] [--limit N] [--cursor CURSOR] [--state-dir PATH]
yorunge jobs show --operation-id UUID [--state-dir PATH]
```

Önerilen Python:

```text
api.list_jobs(*, status: str | None = None, plan_id: str | None = None,
    limit: int = 50, cursor: str | None = None, state_dir: Path | None = None) -> Result[JobsPage]
api.show_job(operation_id: str, *, state_dir: Path | None = None) -> Result[JobView]
```

CLI `--state-dir` jobs aile seviyesinde veya fiilden sonra, `--output text|json` ve `--non-interactive` ortak seçenekleri mevcut parser ilkeleriyle kabul edilir. `--config/profile/project/recipe/task/tool/execution/confirm` üst seviyede verilse de reddedilir. İstek/kayıt malformed ise kontrollü hata; seçenek kısaltma, tekrar edilen tekil seçenek veya bilinmeyen fiil/alan kabul edilmez. Python Path/int/string/bool kontrolleri strict'tir; bool sayısal limit sayılmaz. `state_dir=None` mevcut yerel store seçimini kullanır; env davranış override'ı eklenmez.

## Salt sorgunun anlamı

İki sonuç genel `Result` zarfının v1 biçimindedir: dış `status=completed`, `operation_id=null`, warnings listesi. Bu dış durum **sorgunun** tamamlanmasıdır; kayıtlı işin durumu data içindedir. Unknown/failed/cancelled işi okumak exit 0'dır; plan/body/ilişki bozukluğu boş liste veya unknown'a çevrilmez.

Show operation, plan, attempt ve outcome'u tek SQLite read snapshot'ından alır. Read-only iş sorgusu env/config/girdi içeriği okumaz, provider sorgulamaz, güncel validation/approval veya yeni execution hakkı vermez. Explicit store erişimi mevcut açılış/migration/hot-journal davranışını taşır; fiziksel DB'nin hiç yazılmayacağı sözü değildir. Eksik store mevcut açık store kuralıyla kurulur; normal draft prepare yine DB açmaz.

## Kapalı wire

Bütün nesneler strict/frozen/extra-forbid; JSON duplicate key, non-finite, bilinmeyen sürüm/alan ve bool-as-int reddedilir. Mevcut canonical UUIDv4, lowercase SHA-256, canonical UTC ve domain task/tool/execution kimlikleri kullanılır. Alanlar aşağıda tamdır; `?` yalnız null olabilen değeri belirtir, anahtarın atlanmasını değil. Diziler JSON listesi, sayı alanları strict int'tir.

| Tip | Tam alan kümesi |
|---|---|
| JobsPage | `schema_version=1`, `jobs: JobSummary[]`, `next_cursor: string?` |
| JobSummary | `operation_id`, `plan_id`, `plan_digest`, `task`, `tool`, `execution`, `created_at`, `updated_at`, `status`, `execution_status`, `delivery_status`, `attempt_count` |
| JobView | `schema_version=1`, `operation: JobSummary`, `plan: ExecutionPlan`, `attempts: AttemptView[]`, `outcome: OperationOutcome?` |
| AttemptView | `attempt_id`, `number`, `created_at`, `updated_at`, `status`, `provider_run_id: string?`, `provider_status: string?`, `provider_exit_code: int?`, `reason_code: string?` |
| OperationOutcome | `schema_version=1`, `recorded_at`, `execution_status`, `delivery_status`, `provider_exit_code: int?`, `reason_code: string?` |

İsimle türü açık olmayan alanlar: ID'ler UUIDv4 string; digest SHA-256 string; zamanlar UTC string; `task/tool/execution` plandaki seçimin aynısı (nullable tool null kalır); attempt_count 1–16; attempt number 1–16 ve kesintisiz/tekil. Show attempts numara artan sıradadır. Durum enum'ları ADR-0016 ile aynıdır. Geçerli index/payload/FK, operation-plan digest, aşağıdaki durum eşlemeleri ve zaman sırası full ve sıcak okuma doğrulamasında denetlenir. Provider exit 0 tek başına succeeded değildir.

Public provider run ID/status yalnız trusted adaptörün sır içermediğini garanti ettiği küçük kimlik/durum alanıdır; ham cevaptan doğrudan kopyalanmaz. ID en çok 256, status en çok 128 ASCII karakter; izinli karakterler `[A-Za-z0-9._:-]`, boş string/control/URL reddedilir. Provider exit code nullable signed-32 int; reason code aşağıdaki OperationReason v1 enum'udur. Serbest açıklama/body/argv/env/secret/HMAC/owner permit eklenmez. Yeni provider/status gereksinimi geldiğinde parser'ın bu sınırı sessizce gevşetilmez.

Operation kabul payload'ı UUID/store/plan/approval bağları, public authorization snapshot ve sabit correlation içerir; provider secret ve mutable Profile/config içermez. Owner/fence ve özel permit jobs çıktısına girmez. Public show geçmiş planı gösterir, planın şu an geçerli/onaylı olduğunu söylemez. Geçiş kaydı DB içindedir; bu pakette yeni history/export komutu yoktur. Payload ve çıktı byte kotaları ADR-0016'dadır.

## Durum ve neden invariantları

Güncel attempt, dispatch bağı varsa onun gösterdiği attempt; yoksa en büyük numaralı attempt'tir. Daha eski attempt'ler yalnız abandoned'dır, değişmez ve outcome ile eşitlik zorunluluğu taşımaz. Her business geçişinin summary projection'ı DB payload'ıyla aynı olmalıdır; farklı enum eksenleri birbirine eşitlenmez.

| Toplam operation | Güncel attempt | Execution/delivery ve outcome koşulu |
|---|---|---|
| admitted | claimed | execution not_started; outcome null |
| submitted | submitted | execution submitted; outcome null veya nonterminal özet |
| running | running | execution running; veya execution succeeded + delivery pending; outcome varsa aynı eksenler |
| unknown | unknown | execution unknown; veya kesinleşmiş execution succeeded + delivery unknown/pending; outcome varsa aynı eksenler |
| succeeded | succeeded | execution succeeded + delivery complete/not_required; outcome zorunlu |
| failed | failed | execution failed/not_started; veya execution succeeded + delivery failed; outcome zorunlu |
| cancelled | cancelled | dispatch öncesi execution not_started, sonrasında kesin kanıtla cancelled; outcome zorunlu |

Not_started iken delivery yalnız pending/not_required; kesin olmayan execution iken delivery complete olamaz. Not_required yalnız admission'da sabitlenen trusted teslim politikasından gelir. Unknown'dan doğrulanmış running'e geçiş yeni dispatch/attempt üretmez. Terminal zaman/durum/sonuç değişmez; created_at ≤ updated_at ve attempt/outcome zamanı operation aralığında olmalıdır. Public updated_at yalnız business geçişi zamanıdır; heartbeat'in private lease zamanı/revision'ı summary/outcome zamanını veya semantic fingerprint'i değiştirmez. Bilinen provider_run_id aynı operation'da bir kez bağlanır, başka ID'ye değiştirilemez.

**OperationReason v1 tam değer kümesi:** `identity_reset`, `local_cancelled`, `approval_revoked`, `approval_expired`, `approval_changed`, `plan_invalid`, `credential_changed`, `lease_expired`, `clock_changed`, `owner_changed`, `dispatch_interrupted`, `provider_unavailable`, `provider_not_found`, `provider_unauthorized`, `provider_rejected`, `provider_failed`, `provider_cancelled`, `delivery_pending`, `delivery_failed`, `evidence_mismatch`, `outcome_write_failed`, `capacity_exceeded`. Alan/schema sürümü 1 bu enum'u kullanır; yeni wire anlamı için katalog/reference ve consumer testleri birlikte güncellenir.

Attempt ve varsa güncel outcome için neden eşlemesi aşağıdadır; outcome'un kendi overall status alanı yoktur, bağlı operation durumu esas alınır. Tarihsel abandoned attempt kendi nedenini korur.

| Durum | İzinli reason_code |
|---|---|
| claimed/submitted/succeeded | Yalnız null |
| running | null; execution succeeded + delivery pending ise yalnız delivery_pending |
| unknown | identity_reset, lease_expired, clock_changed, owner_changed, dispatch_interrupted, provider_unavailable, provider_not_found, provider_unauthorized, evidence_mismatch, outcome_write_failed, delivery_pending, capacity_exceeded; null yasak |
| abandoned | owner_changed, lease_expired, clock_changed; null yasak |
| failed | plan_invalid, provider_rejected, provider_failed, delivery_failed; yalnız gönderim öncesinde approval_revoked/approval_expired/approval_changed/credential_changed da olabilir; null yasak |
| cancelled | identity_reset/local_cancelled yalnız gönderim öncesinde; provider_cancelled yalnız gönderim sonrası kesin kanıtla; null yasak |

Onay/credential kontrolü reddinde kayıt yoksa yeni job yaratılmaz. Birden çok neden olduğunda eylemi durduran ilk kapının kodu kullanılır; serbest metin veya provider hata adı kabul edilmez.

Bu kalıcı nedenler exception kodu değildir. İç hata zarfının `details.reason_code` alanı ADR'deki kapalı ErrorCode kataloğunu kullanır; örneğin state_write_failed, kalıcı özette outcome_write_failed olabilir. Jobs okuması kayıtlı nedeni public error'a dönüştürmez.

## Sayfalama ve filtre

- `limit=50`; strict int 1–100. Yalnız tek status ve tek plan_id filtresi; birlikte AND. Status tam operation enum değeri, plan_id canonical UUIDv4'tür. Geçerli ama bulunmayan plan filtresi boş liste verir; bozuk UUID hata verir.
- Artan `(created_at, operation_id)` keyset sırası; immutable created_at kullanılır, offset/sort override yoktur. SQL `limit+1` ile next_cursor kararını verir; attempt_count indeksli aggregate/summary ile alınır, N+1 query yapılmaz ve tüm payload geçmişi belleğe yüklenmez.
- Cursor en çok 1.024 ASCII byte canonical padded base64url'dür. Çözülen canonical JSON tam `{version:1, store_id, status, plan_id, created_at, operation_id}` anahtarlarını taşır; status/plan_id filtre yoksa null. Version strict int; JSON kodlaması mevcut canonical utility'dir, yeniden encode eşitliği gerekir. UTF-8/duplicate/non-finite/extra/oversize cursor reddedilir.
- Cursor store ve filtreleri çağrıyla aynen eşleşir; caller filtreyi sonraki sayfada tekrar verir. Uyuşmazlık `invalid_request`; cursor imza/yetki değildir. Sentetik seek anahtarı oluşturmak gizli execution hakkı vermez.
- Her sayfa ayrı read snapshot'tır; bütün liste için donmuş snapshot garantisi yoktur. Yeni kayıtlar veya durum değişimi özellikle status filtresinde sonraki sayfalarda atlanan/görülen kaydı etkileyebilir. Aynı immutable anahtar sayfa içinde yinelenmez; cursor'un arkasındaki yeni kayıt tekrar gösterilmez.

## Metin ve hata

Text list her kayıtta operation ID, task, toplam durum ve execution/delivery durumlarını ayrı gösterir; boş listede kayıt olmadığını söyler. Show plan ID/digest, attempt sırası, son kayıtlı durum/sonuç ve bunun yerel tarihsel okuma olduğu bilgisini verir. Ham JSON/sağlayıcı mesajı metne dökülmez. JSON stdout yalnız tek Result; hata stdout boş ve stderr tek mevcut hata zarfıdır. Aynı seçimde text ve JSON aynı tipli okuma sonucundan üretilir.

`operation_not_found` canonical ID bulunamadığında exit 2; malformed istek/cursor/filtre `invalid_request`; bozuk kayıt `state_invalid`. State platform/kilit/I/O/bütçe/repair kodları mevcut davranıştadır. `retryable=false`; path/SQL/secret/traceback yoktur. Operation'a bağlı plan forget `plan_in_use` exit 2 verir. İç coordination hataları/operation_uncertain jobs sonucuyla karıştırılmaz. Kanonik public kod/exit tablosu uygulama adımında [CLI referansına](cli-contract.md) bağlanacaktır.
