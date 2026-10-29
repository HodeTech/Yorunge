# Operation ve yerel jobs sözleşmesi

**Durum:** Accepted tasarım — [ADR-0016](../decisions/0016-operation-admission-and-ownership.md) kullanıcı review'u ve iki fresh tur sonrası benimsendi; iç çekirdek adım 1–3 bu dalda verified; public jobs CLI/Python yolu uygulandı, adım 4 review/artefakt/performans kabulü sürüyor. **Tarih:** 2026-10-29. [Mevcut public alt küme](cli-contract.md#uygulanan-alt-küme).

## Sınır ve kaynak

Operation, immutable execution planından ayrı kalıcı bir iştir. Planı hazırlamak/onaylamak operation oluşturmaz. P01-4'te public yürütme veya fixture backend yoktur; jobs yalnız gerçek store kayıtlarını okur. Lifecycle, admission/approval snapshot, dispatch latch, lease/fencing, kotalar ve bakım kurallarının tek normatif karar kaynağı ADR-0016'dır. Burada CLI/Python ve wire ayrıntıları tanımlanır; tasarım kullanıcı tarafından uygulamadan önce onaylandı. Public jobs sorgusu uygulandı; paket kabulü ve development PR teslimi sürüyor.

Uygulanan CLI:

```text
yorunge jobs list [--status STATUS] [--plan-id UUID] [--limit N] [--cursor CURSOR] [--state-dir PATH]
yorunge jobs show --operation-id UUID [--state-dir PATH]
```

Uygulanan Python:

```text
api.list_jobs(*, status: str | None = None, plan_id: str | None = None,
    limit: int = 50, cursor: str | None = None, state_dir: Path | None = None) -> Result[JobsPage]
api.show_job(operation_id: str, *, state_dir: Path | None = None) -> Result[JobView]
```

CLI `--state-dir` jobs aile seviyesinde veya fiilden sonra, `--output text|json` ve `--non-interactive` ortak seçenekleri mevcut parser ilkeleriyle kabul edilir. `--config/profile/project/recipe/task/tool/execution/confirm` üst seviyede verilse de reddedilir. İstek/kayıt malformed ise kontrollü hata; seçenek kısaltma, tekrar edilen tekil seçenek veya bilinmeyen fiil/alan kabul edilmez. Python Path/int/string/bool kontrolleri strict'tir; bool sayısal limit sayılmaz. `state_dir=None` mevcut yerel store seçimini kullanır; env davranış override'ı eklenmez.

## Salt sorgunun anlamı

İki sonuç genel `Result` zarfının v1 biçimindedir: dış `status=completed`, `operation_id=null`, warnings listesi. Bu dış durum **sorgunun** tamamlanmasıdır; kayıtlı işin durumu data içindedir. Unknown/failed/cancelled işi okumak exit 0'dır; plan/body/ilişki bozukluğu boş liste veya unknown'a çevrilmez.

Show operation, plan, attempt ve outcome'u tek SQLite read snapshot'ından alır. Read-only iş sorgusu env/config/girdi içeriği okumaz, provider sorgulamaz, güncel validation/approval veya yeni execution hakkı vermez. Explicit store erişimi mevcut açılış/migration/hot-journal davranışını taşır; fiziksel DB'nin hiç yazılmayacağı sözü değildir. Eksik store mevcut açık store kuralıyla kurulur; normal draft prepare yine DB açmaz.

Lease expiry kendi başına SQL geçişi çalıştırmaz. Açık iç recover/takeover kullanım senaryosu toparlanmayı tetikler; jobs bunu çağırmaz. Her jobs Result warnings listesinde local_history_only bulunur; metin de submitted/running dahil son kaydın stale olabileceğini belirtir. Provider veya canary sorgusu yapılmış gibi gösterilmez.

## Kapalı wire

Bütün nesneler strict/frozen/extra-forbid; JSON duplicate key, non-finite, bilinmeyen sürüm/alan ve bool-as-int reddedilir. Mevcut canonical UUIDv4, lowercase SHA-256, canonical UTC ve domain task/tool/execution kimlikleri kullanılır. Alanlar aşağıda tamdır; `?` yalnız null olabilen değeri belirtir, anahtarın atlanmasını değil. Diziler JSON listesi, sayı alanları strict int'tir.

| Tip | Tam alan kümesi |
|---|---|
| JobsPage | `schema_version=1`, `jobs: JobSummary[]`, `next_cursor: string?` |
| JobSummary | `operation_id`, `plan_id`, `plan_digest`, `task`, `tool`, `execution`, `created_at`, `updated_at`, `status`, `execution_status`, `delivery_status`, `attempt_count`, `revision`, `clock_anomaly` |
| JobView | `schema_version=1`, `operation: JobSummary`, `plan: ExecutionPlan`, `attempts: AttemptView[]`, `outcome: OperationOutcome?` |
| AttemptView | `attempt_id`, `number`, `created_at`, `updated_at`, `status`, `provider_run_id: string?`, `provider_status: string?`, `provider_exit_code: int?`, `reason_code: string?` |
| OperationOutcome | `schema_version=1`, `recorded_at`, `execution_status`, `delivery_status`, `provider_exit_code: int?`, `reason_code: string?` |

İsimle türü açık olmayan alanlar: ID'ler UUIDv4 string; digest SHA-256 string; zamanlar UTC string; `task/tool/execution` plandaki seçimin aynısı (nullable tool null kalır); attempt_count 1–16; attempt number 1–16 ve kesintisiz/tekil. Show attempts numara artan sıradadır. Durum enum'ları ADR-0016 ile aynıdır. Geçerli index/payload/FK, operation-plan digest, aşağıdaki durum eşlemeleri ve zaman sırası full ve sıcak okuma doğrulamasında denetlenir. Provider exit 0 tek başına succeeded değildir.

Public provider run ID/status yalnız trusted adaptörün sır içermediğini garanti ettiği küçük kimlik/durum alanıdır; ham cevaptan doğrudan kopyalanmaz. ID en çok 256, status en çok 128 ASCII karakter; izinli karakterler `[A-Za-z0-9._:-]`, boş string/control/URL reddedilir. Provider exit code nullable signed-32 int; reason code aşağıdaki OperationReason v1 enum'udur. Serbest açıklama/body/argv/env/secret/HMAC/owner permit eklenmez. Yeni provider/status gereksinimi geldiğinde parser'ın bu sınırı sessizce gevşetilmez.

Admission payload tam alanları: `schema_version=1`, `operation_id`, `plan_id`, `plan_digest`, `store_id`, `admission_identity_epoch`, `admission_clock_generation`, `approval` (mevcut kapalı ExecutionApproval snapshot), `authorities: AdmissionAuthority[]`, `correlation` (UUIDv4), `delivery_required` (strict bool). En çok üç authority (local ve iki mevcut hizmet); service/hedef sırasına göre tekil/sıralı. Kaynak saved plan scope'u ve aynı çağrının onunla eşleşmiş current credential/authorization snapshot'ıdır; aynı metadata tekrar çözülmez.

AdmissionAuthority tam alanları `service_id`, `service_origin`, `api_base_path`, `account_id`, `project_id`, `credential_id`, `credential_revision`, `authorization_scope`'tur. Service ID mevcut enum; local service'de origin/base/credential ID/revision/authorization null, account/project saved context'i korur. Uzak service'de origin/base/credential UUID/revision zorunlu; account/project/scope saved scope'un nullability ve mevcut kapalı AuthorizationScope kurallarını izler. Nullable anahtarlar atlanmaz. BoundCredential/CredentialBinding/Profile serialize edilmez: K, key_check, tag/verifier, ham secret/hash, env/reference_name/type ve config hiçbir alanın değeri olamaz. Üçten fazla authority gerektiren plan bu sürümde kontrollü reddedilir; 8 KiB toplam admission kotası ayrıca uygulanır.

Owner/fence ve permit jobs çıktısına girmez. Show geçmiş planı gösterir, güncel geçerlilik/onay iddiası değildir. Geçiş kaydı DB içindedir; yeni history/export komutu yoktur. Payload/çıktı byte kotaları ADR-0016'dadır.

## Durum ve neden invariantları

Numaralar kesintisiz 1…N≤16; güncel attempt en büyük numaralı attempt'tir, diğerleri yalnız abandoned ve değişmezdir. Dispatch bağı varsa aynı operation'ın **bu en büyük** attempt'ine gitmelidir; bağlı attempt claimed/abandoned olamaz ve sonradan attempt eklenemez. Latch null iken yalnız admitted veya kesin gönderim öncesi failed/cancelled vardır. Farklı enum eksenleri literal eşitlenmez; toplam status tek saf reducer'dan gelir.

Son event dahil her normal event'in fence'i bağlı attempt numarasından küçük olamaz; admission ile aynı clock alanındaysa attempt oluşturulmasından önce gözlenemez. Dispatched event aynı kalıcı dispatch attempt'ine bağlıdır; recovery marker bu bağı kaldırmaz. Gönderim öncesi ownership kontrolleri normal event üretmediğinden latch null/admitted iş tam bir, latch null/yerel terminal iş tam iki normal event taşır. Liste bunları zaten batch okuduğu verilerle denetler.

Her normal event'in semantic revision'ı en az sequence değeridir. Latch dolu ve toplam iki normal event varsa sonuncusu zorunlu ilk submitted intent'tir; admission clock'u ve tarihsel approval zaman aralığı aynen denetlenir. Recovery marker ilk gönderimin yetki bağını ortadan kaldırmaz.

| Toplam operation | Güncel attempt | Execution/delivery ve outcome koşulu |
|---|---|---|
| admitted | claimed | execution not_started; outcome null |
| submitted | submitted | execution submitted; outcome null |
| running | running | execution running; veya execution succeeded + delivery pending; outcome null |
| unknown | unknown | execution unknown; veya execution succeeded + delivery unknown; outcome null |
| succeeded | succeeded | execution succeeded + delivery complete/not_required; outcome zorunlu |
| failed | failed | execution failed/not_started; veya execution succeeded + delivery failed; outcome zorunlu |
| cancelled | cancelled | dispatch öncesi execution not_started, sonrasında kesin kanıtla cancelled; outcome zorunlu |

Tam execution/delivery cross-product aşağıdaki whitelist'tir; diğer çiftler reddedilir. Not_required iff admission delivery_required=false; bu durumda diğer delivery değerleri yasaktır. Delivery_required=true iken not_required yasaktır. Not_started'ın terminal yerel nedeni reducer'ın ayrı strict failed/cancelled/null girdisidir; bu girdi dispatch sonrası kullanılamaz.

| Execution | İzinli delivery → toplam durum |
|---|---|
| not_started | pending/not_required → admitted; kesin yerel terminal girdi varsa failed/cancelled |
| submitted | pending/not_required → submitted |
| running | pending/not_required → running |
| unknown | pending/unknown/not_required → unknown |
| succeeded | pending → running; unknown → unknown; failed → failed; complete/not_required → succeeded |
| failed | pending/not_required → failed |
| cancelled | pending/not_required → cancelled |

OperationOutcome **yalnız terminal** kayıt, terminale geçişte bir kez yazılır; diğer durumlarda null. Summary, güncel attempt ve outcome eksenleri bu tabloya göre eşleşir. Kesinleşmiş execution succeeded, belirsiz delivery yüzünden execution unknown'a çevrilmez. Unknown'dan trusted submitted/running'e dönüş aynı attempt/latch'i kullanır.

Execution succeeded ise current attempt ve varsa outcome exit code'u yalnız null veya 0 olabilir; sıfır dışı exit ile başarı çelişkisi port gözleminde olduğu gibi list/show/full kalıcı tüketicilerinde de reddedilir. Bu kural delivery beklerken toplam durum running/unknown/failed olsa da execution eksenini izler.

Created_at ilk gerçek UTC gözlemidir ve immutable cursor anahtarıdır. Updated_at ve outcome recorded_at son gerçek UTC gözlemidir; wall clock epoch/generation değişiminde created_at'ten eski olabilir. Global created≤updated kuralı **yoktur**. Private normal event tam sıra anahtarı (operation_id, sequence), gözlem identity_epoch/clock_generation ve gerçek observed_at taşır; normal event sequence 1…256, revision positive int64 olur. Aynı clock alanında UTC sırası denetlenir; farklı alanda sıra otoritesi sequence/revision'dır. Saat gerilemesi yaşayan operation'da sticky clock_anomaly=true; eski event timestamp'i değişmez, sahte max(old,now) yazılmaz. Böylece +1 yıl saat→reset→düz UTC→reconcile desteklenir. Heartbeat semantic revision/updated_at/fingerprint'i değiştirmez.

Recovery owner/invalidation normal event eklemeden bounded güncel kontrol kaydını ve semantic revision'ı değiştirir. Recovery marker varsa etkili summary/attempt unknown projection'ı son normal event'ten farklı olabilir; decoder yalnız bu açık marker ile bu farkı kabul eder. En son normal event'in terminal olduğu durumda marker yoktur ve terminal summary/outcome tam eşleşir. Kapasite yüzünden nonterminal observation yazılamazsa marker capacity_exceeded ile unknown kalır; son terminal slotu yeni yetkili recovery sahibine açıktır. Provider_run_id bir kez bağlanır, aynı operation'da değiştirilemez.

Aynı owner altında running → unknown → submitted toparlanmasında ara recovery normal event tüketmez; ardışık normal event'ler arasındaki en az iki semantic revision artışı bu kontrol mutasyonunun kalıcı tanığıdır. Fence artışıyla takeover da aynı toparlanmaya izin verir. Doğrudan running → submitted gözlemi evidence_mismatch/unknown olur; recovery revision boşluğu veya yeni fence olmadan bu iki normal event ardışık olamaz. Heartbeat revision artırmadığından toparlanma tanığı sayılmaz.

**OperationReason v1 tam değer kümesi:** `identity_reset`, `local_cancelled`, `approval_revoked`, `approval_expired`, `approval_changed`, `plan_invalid`, `credential_changed`, `lease_expired`, `clock_changed`, `owner_changed`, `dispatch_interrupted`, `provider_unavailable`, `provider_not_found`, `provider_unauthorized`, `provider_rejected`, `provider_failed`, `provider_cancelled`, `delivery_pending`, `delivery_failed`, `evidence_mismatch`, `outcome_write_failed`, `capacity_exceeded`. Alan/schema sürümü 1 bu enum'u kullanır; yeni wire anlamı için katalog/reference ve consumer testleri birlikte güncellenir.

Attempt ve varsa güncel outcome için neden eşlemesi aşağıdadır; outcome'un kendi overall status alanı yoktur, bağlı operation durumu esas alınır. Tarihsel abandoned attempt kendi nedenini korur.

| Durum | İzinli reason_code |
|---|---|
| claimed/submitted/succeeded | Yalnız null |
| running | null; execution succeeded + delivery pending ise yalnız delivery_pending |
| unknown | identity_reset, lease_expired, clock_changed, owner_changed, dispatch_interrupted, provider_unavailable, provider_not_found, provider_unauthorized, evidence_mismatch, outcome_write_failed, delivery_pending, capacity_exceeded; null yasak |
| abandoned | owner_changed, lease_expired, clock_changed; null yasak |
| failed | plan_invalid, provider_rejected, provider_failed, delivery_failed; yalnız gönderim öncesinde approval_revoked/approval_expired/approval_changed/credential_changed/capacity_exceeded da olabilir; null yasak |
| cancelled | identity_reset/local_cancelled yalnız gönderim öncesinde; provider_cancelled yalnız gönderim sonrası kesin kanıtla; null yasak |

Onay/credential kontrolü reddinde kayıt yoksa yeni job yaratılmaz. Birden çok neden olduğunda eylemi durduran ilk kapının kodu kullanılır; serbest metin veya provider hata adı kabul edilmez.

Bu kalıcı nedenler exception kodu değildir. İç hata zarfının `details.reason_code` alanı ADR'deki kapalı ErrorCode kataloğunu kullanır; örneğin state_write_failed, kalıcı özette outcome_write_failed olabilir. Jobs okuması kayıtlı nedeni public error'a dönüştürmez.

## Sayfalama ve filtre

- `limit=50`; strict int 1–100. Yalnız tek status ve tek plan_id filtresi; birlikte AND. Status tam operation enum değeri, plan_id canonical UUIDv4'tür. Geçerli ama bulunmayan plan filtresi boş liste verir; bozuk UUID hata verir.
- Artan `(created_at, operation_id)` keyset sırası; immutable created_at kullanılır, offset/sort override yoktur. SQL `limit+1` ile next_cursor kararını verir; attempt_count indeksli aggregate/summary ile alınır, N+1 query yapılmaz ve tüm payload geçmişi belleğe yüklenmez.
- Cursor en çok 1.024 ASCII byte canonical padded base64url'dür. Çözülen canonical JSON tam `{version:1, store_id, status, plan_id, created_at, operation_id}` anahtarlarını taşır; status/plan_id filtre yoksa null. Version strict int; JSON kodlaması mevcut canonical utility'dir, yeniden encode eşitliği gerekir. UTF-8/duplicate/non-finite/extra/oversize cursor reddedilir.
- Cursor store ve filtreleri çağrıyla aynen eşleşir; caller filtreyi sonraki sayfada tekrar verir. Uyuşmazlık `invalid_request`; cursor imza/yetki değildir. Sentetik seek anahtarı oluşturmak gizli execution hakkı vermez.
- Liste, seçilen sayfanın plan/approval snapshot bağını, bütün aday/sonuç projeksiyonlarını ve indeksli history count/min/max + son event'i toplu sorgularla denetler. Bütün history payload zinciri full store validation ve show'da doğrulanır; list bunu taramaz. Bozuk seçili summary/ilişki boş sonuca dönüşmez.
- Her sayfa ayrı read snapshot'tır; bütün liste için donmuş snapshot garantisi yoktur. Yeni kayıtlar veya durum değişimi özellikle status filtresinde sonraki sayfalarda atlanan/görülen kaydı etkileyebilir. Aynı immutable anahtar sayfa içinde yinelenmez; cursor'un arkasındaki yeni kayıt tekrar gösterilmez.

## Metin ve hata

Text list her kayıtta operation ID, task, toplam durum ve execution/delivery durumlarını ayrı gösterir; boş listede kayıt olmadığını söyler. Show plan ID/digest, attempt sırası, son kayıtlı durum/sonuç ve bunun yerel tarihsel okuma olduğu bilgisini verir. Ham JSON/sağlayıcı mesajı metne dökülmez. JSON stdout yalnız tek Result; hata stdout boş ve stderr tek mevcut hata zarfıdır. Aynı seçimde text ve JSON aynı tipli okuma sonucundan üretilir.

`operation_not_found` canonical ID bulunamadığında exit 2; malformed istek/cursor/filtre `invalid_request`; bozuk kayıt `state_invalid`. State platform/kilit/I/O/bütçe/repair kodları mevcut davranıştadır. `retryable=false`; path/SQL/secret/traceback yoktur. Operation'a bağlı plan forget `plan_in_use` exit 2 verir. İç coordination hataları/operation_uncertain jobs sonucuyla karıştırılmaz. Kanonik kod/exit/tetik tablosu [CLI referansındadır](cli-contract.md#operation-hata-kataloğu).

## İç uzlaştırma sınırı

Public jobs sorgusu uzlaştırma yapmaz. İç ReadPort yalnız authorize/observe metodlarıyla çalışır; start, cancel veya artefakt fetch metodları içermez. Composition provider JSON'u veya caller verified bayrağı kabul eden bir public API açmaz. Geçmiş plan/onay expiry'si tek başına geçmiş işi okumayı engellemez; execution validator ve input hash tekrar çalıştırılmaz. Saved hizmet/origin/API base/account/project korunur, profil değişimi başka hedefe yönlendirmez. Aynı çağrının bir kez yakalanmış güncel read credential ID/revision/epoch/hedefi son transaction'da tekrar okunur; değişiklik state_changed/sıfır yeni start verir, env otomatik tekrar çözülmez. Kabuldeki credential/onay snapshot'ı değişmez.

İç ReadAccess kapalı alanları authorities (1–3 AdmissionAuthority), checked_at ve expires_at'tir. Authorize portu istenen aynı job/hedef için güncel okuma hakkını kanıtlar; uzak authority'nin authorization_scope.permissions kümesi read içermelidir. Target/account/project ve güncel credential metadata'sı aynı kalır; eski execution yetkisi bu okuma kanıtıyla yeniden etkinleşmez. Aralık checked_at ≤ current UTC < expires_at olmalı; gelecek tarihli, geçmiş veya yanlış hedef/yetki kanıtı observe öncesi reddedilir. Lease/generation ve yetki süreleri final transaction'da da denetlenir. ReadRequest sadece iç composition nesnesidir, private credential serialize edilmez.

Taşıma/yetki/malformed gözlem hatasının unknown marker'ı ve outcome_write_failed fallback'i de aynı current credential/request kontrolünden geçer; doğrulanmış ReadAccess varsa süresi ve metadata'sı son transaction'da tekrar denetlenir. Authorize kanıt üretmeden reddederse geçerli owner/current request ile yalnız provider_unauthorized belirsizliği kaydedilebilir; gözlem veya pozitif ilerleme üretilemez. İlk dispatch sonrası belirsizlik marker'ı, intent'in mevcut linearization sınırını korur.

İç OperationObservation tam alanları kind (observed/not_found/unauthorized/cancel_accepted/unavailable), correlation, authority, provider_run_id, provider_status, provider_exit_code, execution_status ve delivery_status'tur. ID/status/exit tür ve sınırları yukarıdaki wire ile aynıdır. Pozitif observed sonucu aynı correlation/authority ve kalıcı run ID'yi ister; ID ilk kez kesin correlation kanıtıyla bağlanabilir, sonradan değişmez. Yanlış bağ, çelişkili execution/exit/delivery, not_found, iptal isteği kabulü veya taşıma hatası terminal sonuç değildir. Bilinen credential secret'inin provider alanına yansıması kalıcılıktan önce reddedilir.

Receipt ve observation authority'si saved planın execution hizmetine ait olmalıdır: yerel LLM işinde local, llm.chat uzak işinde evren-llm, diğer işlerde evren-platform. Tam hedef/account/project ve ilgili execution/read snapshot üyeliği ayrıca korunur. Plan içindeki ayrı planning.offline/local authority uzak yürütme kanıtı değildir; bu authority ile gelen observation evidence_mismatch/unknown, receipt ise operation_uncertain verir.

Terminal sonucu yazarken I/O/bütçe veya commit dönüşü belirsizse bellekteki başarı döndürülmez: operation_uncertain/5, alttaki ErrorCode ve bilinen operation ID korunur. Yetkili yazı hâlâ mümkünse bounded outcome_write_failed/unknown marker'ı yazılır; zaten commit edilmiş terminal satır yeniden açılmaz. Son atomik kayıt korunur ve aynı job salt gözlemle uzlaştırılabilir; yeni start yoktur. Güncel read credential değişimi veya stale owner ise kendi state_changed/operation_lease_lost kodunu korur.

## Coordination hata sınırı

Yeni OperationError mevcut YorungeError alt sınıfıdır; tam zarf `schema_version=1, code, message, operation_id, retryable=false, details` olur. Operation ID biliniyorsa canonical UUID, bilinmiyorsa null. Details tam `{reason_code: ErrorCode, capacity_kind: store|attempt|transition|null}`; capacity_kind yalnız kapasite hatasında non-null'dır. reason_code exception kataloğundandır; kalıcı OperationReason ayrı tiptir. Eski hataların details={} davranışı değiştirilmez.

Kod/exit/tetik tablosunun kanonik yeri [CLI hata kataloğudur](cli-contract.md#operation-hata-kataloğu).

Her yeni kodun gerçek tetik/zarf/ID/exit testi gerekir; modelde kod bulunması tek başına teslim değildir.
