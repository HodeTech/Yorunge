# Upload v2 politika, maliyet ve geçiş sözleşmesi

**Durum:** ADR-0026/0027 Accepted; kanonik v2 hedef sözleşmesi. Yerel v1 d/e/f temeli verified; v2 exact-work maliyet modeli P02-2g ile yerel verified; plan/policy/current P02-2h yerel verified; journal/history/reset uyumu P02-2i yerel verified; yazma kapıları P02-2j yerel verified; explicit read/recovery P02-2k yerel verified; l/m provider codec sınırları yerel verified. Bu yerel kabuller public upload, native/kurulum/source CI veya canlı teslim değildir. **Tarih:** 2026-11-02. [Karar](../decisions/0026-explicit-unverified-transfer-attempts.md), [v1 geçmişi ve ortak storage/journal sınırları](dataset-transfer.md). Bu belge v2'nin kanonik alan/reducer/gate/acceptance kaynağıdır; v1 golden'ları yeniden tanımlamaz.

## Kapalı tipler ve sürümler

Bütün DTO'lar strict/frozen/extra-forbid; nullable dahil alanlar zorunlu, bool integer değildir. Canonical ASCII JSON, duplicate/nonfinite/UTF-8/depth/node ve byte sınırları v1 ile aynıdır. Public API raw grant/quote/check/client/header dict'i almaz. Yeni producer yalnız v2 üretir. Üst Result v1 ve mevcut execution/jobs wire'ı değişmez.

- `DatasetUploadPlan v2`: v1'in bütün alanları; schema_version=2, policy_version=2, status=`draft|prepared|attempt_ready`, nullable budget_micros; ayrıca `admission_policy=verified_only|explicit_attempt`, `cost_policy=bounded_required|unpriced_accepted`, `risks` (en çok iki sorted/unique kapalı değer), `request_limits: UploadRequestLimits`, `execution_window: UploadExecutionWindow`. `grant` eski UploadGrant v1/null; `cost_bound` yalnız UploadCostBound v2/null. Executable=false kalır.
- `DatasetUploadApproval v2`: bütün v1 alanları; schema_version=2; ayrıca admission_policy, cost_policy, acknowledge_unverified_authority ve acknowledge_unpriced_cost (strict bool). Plan/binding digest bütün yeni semantik alanları bağlar.
- `TransferRecord v2`: schema_version=2, embedded approval v2; diğer v1 alan/limitleri. V2 reason kataloğu v1'in non-success nedenleri + metadata_verified/read_unavailable; eski verified string'i v2'de yoktur.
- `TransferVerification v2`: schema_version=2, dataset_id, project_id, scope (gözlem anındaki **güncel** UploadScope), authorization_policy=`verified_read|explicit_read_attempt`, grant (UploadGrant v1/null), observed_at, v1 ordered VerifiedFile tuple'ı. Operation'ın historical admission/approval scope'u değiştirilmez; bu ayrı immutable gözlemin scope'udur.
- `TransferControl v2`: bütün v1 alanları, schema_version=2, v2 reason. Operation/approval/control/verification sürümleri eşleşir. StageIntent/TransferLease v1 biçimi değişmez. StageReceipt v1 rejected create ve diğer accepted/rejected stage'lerde kalır; yeni v2 accepted create ayrı CreateReceiptV2 ister.

CreateReceiptV2 ≤2 KiB ve mevcut stage slotu/reservation değişmez. Plan/approval/record ≤16 KiB, control ≤2 KiB, verification ≤128 KiB ve mevcut `16 KiB+512N` proof rezervi ayrıca sağlanır; büyük wire tavanı rezerv aşımına izin vermez. DDL7'nin **payload JSON'undaki schema_version** discriminator'dır; ayrı payload_version SQL kolonu yoktur. Migration 1–7/checksum/golden'lar değişmez.

V1 decode/list/show/history/revoke ve mevcut güvenli read-recovery korunur. **Maliyet kapsamı eksik V1 prepared değeri tarihsel durumdur:** yeni approve, yeni admission ve yeni arm `upload_plan_not_valid`/2; sıfır yeni permit. Existing admit yalnız mevcut ID'yi yerel döndürebilir. Önceden arm edilmiş/inflight receipt ve mevcut geçmiş korunur; v1 plan/quote'a varsayılan v2 alanları eklenmez. Eski binary yeni v2 JSON'u `state_invalid`/2 ile, mutasyon/downgrade olmadan reddeder.

## Kalıcı create receipt ve tarihsel geçiş

[ADR-0027](../decisions/0027-durable-created-dataset-context.md) normatif amendment'ıdır; uygulama [P02-2p](../roadmap/tasks/p02-2p-created-dataset-context.md) kapsamındadır. UploadReceipt, ayrı strict CreateReceiptV2 veya StageReceipt v1 kapalı union'ıdır. CreateReceiptV2 tam alanları: schema_version=2, intent_id, recorded_at, result=accepted, dataset_id, object_key/sent_bytes/sent_sha256 zorunlu null, created_dataset:ProviderDataset. DTO.id=receipt.dataset_id=operation.dataset_id; selected user için owner_id, organization için org_id; name/modality/private/false planla eşleşir. Full iki owner alanı sonraki detail'de immutable baseline'a karşı eşleşir.

Ham create response 1 MiB ve mevcut raw JSON/literal kurallarında kalır; 2 KiB yalnız canonical receipt'tir. Yeni v2 accepted create insert'inde v1 ret/state_invalid; tarihsel v1 decode ayrı korunur. V1 plan/operation+v2 receipt veya yanlış intent-kind/ID/plan bağı state_invalid. Union/full graph sadece yapısal uyumu denetler; tarihsel v2+v1 terminal sonuç yeni baseline şartıyla bozulmaz. Yeni proof commit ayrıca v2 baseline ister.

Legacy v2 nonterminal+accepted create v1 için her yeni arm/renew/write/read-recovery lease/permit ve success HTTP öncesi operation_uncertain/5 + aynı ID ile kapanır. Local show/list/revoke/cleanup/reset korunur. Marker yalnız aynı geçerli owner/PID/fence/CAS veya mevcut expired-lease cleanup yolu ile yazılabilir; başka etkin owner devralınmaz. Marker reddinde business durum eski kalabilir; kapalı reason_code ile belirsizlik döner. Terminal geçmiş değişmez. Normal pre-create veya receipt'i kayıp create bu tarihsel özel durumdan ayrı mevcut kurallardadır. Post-dispatch invalid/oversize receipt/owner çelişkisi write sonucu unknown (marker mümkünse) ve exit 5'tir; yeni create/PUT veya owned/detail backfill yoktur. Geç receipt halen geçerli original owner/intent/lease kapılarından geçer; expiry/reset yeni hak üretmez.

## İşe ve döneme bağlı maliyet kanıtı

`UploadRequestLimits` tam zorunlu alanları: max_create=1, max_project_link=1, max_presign=N, max_put=N, max_confirm=N, max_read_requests=512, max_read_attempts=1024, max_control_request_bytes=4194304, max_control_response_bytes=16777216, max_upload_bytes=manifest.total_bytes. N manifest.file_count'tur. Bunlar aynı anda tamamlanma garantisi değildir; runtime kalan bütçeyi **intent'ten önce** ayırır. Effectful physical attempt sayısı 2+3N, her read en çok iki attempt; başarısızlıklar da sayılır. Mevcut 1 GiB/128 file, 900 s ve phase sınırları ayrıca geçerlidir. Raw body byte sayacı header/TLS değildir; provider'ın billable unit tanımı bununla eşleşmiyorsa yalnız bu sayaçtan fiyat bound'u türetilemez.

`UploadExecutionWindow`: not_before, not_after canonical UTC; 0<aralık≤900 s. Lokal hash hazırlığından sonra, quote/probe öncesinde seçilir. not_before≤prepared_at<plan.expires_at≤not_after. Sonraki current check saved window'u korur; saati her yenilemede kaydırmaz. Bu iş bütçesi tanımlı transfer workflow'ı ve onun neden olduğu retained storage içindir; kullanıcının sonradan başlattığı ayrı discovery/reconcile işleri veya hesabın diğer tüketimi için hesap-geneli tavan değildir. Bu kapsam özette görünür; eski iş bound'u yeni read çağrısına taşınmaz. Bu original start invocation kapsamıdır: onun pre-admission/current/freshness/metadata/cleanup okumaları aynı sayaçtadır. Ayrı prepare/approve/reconcile ve başarısız pre-admission start'ın sonradan yeniden çağrılması kendi bounded read invocation'larıdır; bunların birikimli maliyeti plan ömrü/hesap-geneli tavan diye sunulmaz. Existing operation lookup ağsızdır ve yeni invocation/probe/claim üretmez.

İş bağı aşağıdaki exact canonical nesnenin SHA-256'sıdır:

```text
work_digest = SHA256(b"yorunge-upload-cost-work-v2\0" + canonical({
  "scope": plan.scope, "root": plan.root, "manifest": plan.manifest,
  "parameters": plan.parameters, "storage": plan.storage,
  "request_limits": plan.request_limits, "execution_window": plan.execution_window
}))
```

Plan ID, quote, grant, approval ve plan digest bu nesnede yoktur; döngü oluşturulmaz. Manifest digest/encoded hash, N, total byte, storage, create parametresi, root veya scope değişimi bağı değiştirir.

`UploadCostBound v2` tam alanları: schema_version=2, scope, work_digest, maximum_micros (strict nonnegative int64), charge_categories, charge_period_start, charge_period_end, post_period_storage=`no_further_charge|unknown`, source_id, source_version, checked_at, expires_at. Categories en az bir, tekil ASCII sıralı kapalı tuple: **create, project_link, control, transfer, confirm, storage**. Control; presign, required context/freshness/metadata read ve bunların izinli başarısız physical attempt'lerini kapsar. Para CR başına 1.000.000 microcredit; float/bool/rounding/overflow yoktur.

Tutar **yalnız belirtilen kategori ve ücret doğurma dönemi** için provider kaynaklı üst sınırdır. `checked_at/expires_at` quote kullanım tazeliğidir; charge_period farklı, semantik ve binding digest'e dahildir. 0<charge period; complete olmak için period execution window'u kapsar. Storage'ın dönem bittikten sonra ücretsiz olduğu ancak gerçek kaynak guarantee'siyle `no_further_charge` olabilir. Yerelde period bitince silme, ücretsiz saklama veya ücret kesme varsayılmaz. `unknown` post-period storage numeric bütçe için complete değildir.

Trusted pricing producer yalnız kayıtlı source_id/version'daki exact provider quote kapsamını doğrulayarak veya sürümlü normatif tarifeyi bu **exact işin** quantity/request/byte/period sınırlarına uygulayarak kanıt üretebilir. Work digest'i quote'a etiketlemek tek başına hesap kanıtı değildir. Ücret birimi, bütün olası billed control/failed attempt'ler ve storage garantisi kaynakta kapanmalı; caller/fixture değeri veya genel fiyat sayfası tahmini buna dönüşmez. İlk observed consumer için böyle bir pricing source **yoktur**; prod cost=null döner, fake 0 üretilmez.

`complete_cost(plan,cost)` iff: cost nonnull, scope ve work_digest exact, bütün altı kategori, yeterli charge period ve post_period_storage=no_further_charge. Yanlış iş/scope/digest/type/ters dönem **invalid** (trusted producer `invalid_response`/1, saved wire `state_invalid`/2); unknown diye yutulmaz. Geçerli ama kısmi kategorili/kısa dönemli/unknown storage quote kısmi bilgi olarak saklanabilir; complete_cost=false. Aynı scope'taki başka manifest veya yalnız transfer için 1 CR bound, 200 CR bütçede prepared yapmaz.

Özet partial bound'u “şu kategoriler/dönem için ≤X CR” olarak gösterir; kalan kalemler ve süreğen storage unknown kalır. Whole-work numeric bound yalnız complete_cost ile gösterilir. Unpriced, complete quote varsa onu gerçek kapsamıyla gösterir ama kullanıcı CR tavanı seçildiğini iddia etmez. Pricing tazeliği plan ömrünü kısıtlar; ücret dönemi otomatik expiry'ye çevrilmez.

## Kesin v2 reducer ve tam matris

Önce yapısal gate: verified_only+unpriced, budget/cost_policy uyuşmazlığı, hem budget hem unpriced/hiçbiri → invalid_request/2. Scope/work/digest/expiry uyuşmazlığı status değil hatadır. Full grant dört REQUIRED_PERMISSIONS'ın tam eşliğidir; partial grant full sayılmaz.

```text
A = grant yok veya permissions tam değil
C = not complete_cost(plan,cost_bound)
O = bounded_required ve cost_bound nonnull ve maximum_micros > budget_micros
risks    = sorted({authority_unverified if A, cost_unverified if C})
blockers = sorted({inputs_unverified if not inputs_verified,
                   authority_unverified if verified_only and A,
                   cost_unverified if bounded_required and C,
                   cost_exceeds_budget if O})
status   = draft         if blockers
           prepared      if bounded_required and not risks
           attempt_ready otherwise
```

V1 upload_blockers/status invariant'ı **v2 için tekrar kullanılmaz veya gevşetilmez**. Risks ve blockers değerleri kesişebilir; roller farklıdır. Explicit_attempt'ta geçerli input/cost kapısından sonra authority_unverified yalnız risk kalır. Inputs_unverified her policy'de blocker'dır. Unpriced+full grant+complete quote: risks=[]/blockers=[] fakat attempt_ready.

Tam acceptance matrisi faktörleri: bounded_required için policy={verified_only,explicit_attempt}, grant={none,partial,full}, cost={none,partial_within,partial_over,complete_within,complete_over}, inputs={false,true}: **60** durum. Explicit_attempt+unpriced için grant aynı üç değer, cost={none,partial,complete}, inputs iki değer: **18** durum. Verified_only+unpriced aynı 18 durumda invalid_request/2. Toplam **96 literal bağımsız beklenen satır**, her birinde status/risks/blockers/ack_authority/ack_cost veya error vardır. Input=false her legal satıra inputs_unverified ekler ve status draft olur; diğer risk/blocker'ları silmez. Draft/invalid satırda ack oracle alanları null (uygulanamaz); approve gate flag incelemesinden önce planı reddeder.

Input=true bounded özet matrisi (A=none/partial grant, F=full; her A literalda iki satır):

| Policy | Grant | Cost | Status | Risks | Blockers |
|---|---|---|---|---|---|
| verified_only | A | none/partial_within | draft | authority,cost | authority,cost |
| verified_only | A | partial_over | draft | authority,cost | authority,cost,over |
| verified_only | A | complete_within | draft | authority | authority |
| verified_only | A | complete_over | draft | authority | authority,over |
| verified_only | F | none/partial_within | draft | cost | cost |
| verified_only | F | partial_over | draft | cost | cost,over |
| verified_only | F | complete_within | prepared | [] | [] |
| verified_only | F | complete_over | draft | [] | over |
| explicit_attempt | A | none/partial_within | draft | authority,cost | cost |
| explicit_attempt | A | partial_over | draft | authority,cost | cost,over |
| explicit_attempt | A | complete_within | attempt_ready | authority | [] |
| explicit_attempt | A | complete_over | draft | authority | over |
| explicit_attempt | F | none/partial_within | draft | cost | cost |
| explicit_attempt | F | partial_over | draft | cost | cost,over |
| explicit_attempt | F | complete_within | prepared | [] | [] |
| explicit_attempt | F | complete_over | draft | [] | over |

Tuplardaki kısaltmalar authority_unverified/cost_unverified/cost_exceeds_budget'dır. Unpriced input=true bütün satırlar attempt_ready: A+none/partial → authority,cost; A+complete → authority; F+none/partial → cost; F+complete → []. Blockers hepsinde []. Complete/partial ayrımı tek nonnull kontrolüne indirgenemez.

Approval ack_authority iff authority risk; **ack_cost iff cost_policy=unpriced_accepted** (quote complete olsa da). Unpriced+tam kanıt satırında ack_authority=false, ack_cost=true. Gerekli true eksikse approval_required/4; gereksiz true invalid_request/2; saved approval yanlışlığı state_invalid/2. Draft approve edilemez, upload_plan_not_valid/2. Her iki policy approval alanı planla eşleşir; bütün yeni alanlar exact plan/binding digest'ine dahildir.

## İşlem kapıları ve current kanıt

| İşlem | V2 gate | Ret |
|---|---|---|
| prepare | local input/target + reducer + typed check; wire invalid ise plan üretmez | invalid_request/2, invalid_response/1, state_changed/2 |
| approve | prepared veya explicit attempt_ready; exact digest/current scope/age; ack tablosu | draft/expiry/binding → upload_plan_not_valid/2; eksik ack → approval_required/4 |
| new admit | approve gate + etkin approval + kapasite + current checks | aynı kodlar; stale credential/epoch → state_changed/2; mevcut namespace intent → operation_conflict/2 |
| existing admit | yerel aynı operation ID; yeni check/lease/claim/attempt yok | yerel bozuk kayıt → state_invalid/2 |
| arm | aynı initial write access/PID/owner/fence/lease, saved approval, predecessor, scope/input ve current check; draft yok | stale owner → operation_lease_lost/2; değişim → state_changed/2; diğer plan uyumsuzluğu → upload_plan_not_valid/2 |
| read/verified | aşağıdaki read matrisi + tam grafik + exact metadata | eksik grafik/proof → operation_uncertain/5; typed observation hataları aşağıda |

V1 new approve/admit/arm eski zayıf cost kanıtıyla açılamaz; historical prepared görünümü bu gate'i değiştirmez. V2 verified_only prepared-only; explicit prepared veya attempt_ready kabul eder. Null grant/cost yalnız reducer'ın izin verdiği attempt_ready durumunda geçerlidir; nonnull partial alanlar kendi scope/time/work validation'ını geçer.

**Fresh positive için seçenek A:** saved plan/status/risks/binding/approval değişmez. Current producer ayrı, private `UploadCurrentCheck` üretir: saved plan_id/digest/binding_digest, aynı work_digest ve scope, checked_at, nullable baseline_grant/baseline_cost_bound, nullable supplemental_grant/supplemental_cost_bound, typed AuthorizationCheck ve input sonucu. Bu snapshot plan yerine geçmez ve onayı yeniden yazmaz. Baseline alanları saved nonnull kanıtın aynı semantiğini (yalnız observation timestamps yenilenebilir) taşır; saved null ise baseline null kalır. Saved null/partial boyuta yeni pozitif tam kanıt yalnız ayrı supplemental alanında eklenebilir; yalnız gate'i daraltır, historical authority/risk özetini yükseltmez. Saved partial baseline da hâlâ geçerli olmalıdır; supplemental ona yapay yeni expiry vermez. Saved nonnull semantik kanıt değişirse (producer/source/version, permissions, work/category/period/amount dahil; yalnız observation timestamps hariç) upload_plan_not_valid/2. Saved full→expired/partial/missing ve saved partial→farklı nonnull semantic de ret; current mandatory probe başarısızlığı her zaman ret. Null→positive veya partial→aynı partial+ayrı full current kanıt durumları literal testlidir; partial'ı saved plan üzerinde full'e çevirmek yoktur. Yeni input/target/credential/epoch/clock farkı state_changed/2. V1 binding helper'ı değiştirilmez.

Arm deadline mevcut terimlerin min'idir: original monotonic total_end, plan expiry, approval expiry, güncel DB lease expiry, **var olan saved/baseline/supplemental grant ve cost expiry**, request cap (PUT 120 s, diğer effect 30 s); ilgili total/lease/authority/cost terimlerine 5 s sonuç payı uygulanır. Direct URL ayrıca expiry−5 s. Null term min'e katılmaz, sahte expiry/assert yoktur; pozitif kalan süre yoksa execution_timeout/2 ve sıfır port. Son intent COMMIT/permit ve revoke/reset sonrası geri alınamayan pencere değişmez.

## Tüketici profili, HTTP ve my-role

`not_exposed` yalnız kanonik olarak kayıtlı **evren-platform-observed-upload-v2 / policy_version=2** producer profilinin aşağıdaki dört action için doğrulanmış pre-authority oracle'ı sunmaması nedeniyle üretilebilir. Aynı profil complete pricing source da sunmaz; bu ayrı boyutta cost_bound=null kalır. Pricing source kayıtlıysa onun transport/malformed hatası da null fiyat diye yutulamaz. Bu profil genel principal/grant üretmez; P02-R1'e bağlı ready gate değildir. Yeni profil/sürüm kayıt ve contract review ister; kullanıcı config'inden veya başarısız endpoint'ten türetilemez. Public caller raw check/profile seçip izin genişletemez. İç AuthorizationCheck tam alanları: consumer_profile (bu kayıtlı literal), policy_version=2, action (dört UploadPermission literalından biri), scope:UploadScope, dataset_id:canonical UUID|null, producer_id/producer_version, checked_at, outcome=allowed|not_exposed|denied|unavailable|invalid, grant:UploadGrant|null, error_code:ErrorCode|null. Allowed mevcut action iznini taşıyan gerçek grant ve null error; not_exposed null grant/error; diğerleri null grant ve aşağıdaki exact error code ister. Scope current credential/store/epoch/clock'tur. Freshness en çok 30 s, arm öncesi yeniden kontrol; bu authority expiry değildir.

| Action | Bu profilin grant oracle'ı | Not_exposed'a ek mandatory gate |
|---|---|---|
| create_private_dataset | yok | Current exact owner/project/private context; known negative yok |
| link_project | yok | Aynı context ve accepted create/known dataset ID |
| upload_created_dataset | yok | Exact dataset/credential scope'ta taze my-role has_upload=true; presign/PUT/confirm predecessor/byte gate'leri |
| read_created_dataset | yok | Explicit read insan seçimi ve exact resource metadata şeması; verified read grant uydurulmaz |

My-role pozitif etiketi upload oracle'ı veya allowed grant yerine geçirilmez; profilin bilinen oracle yokluğu not_exposed kalırken ayrı UploadObservation gate'i geçer. Read metadata'nın başarılı olması da read grant üretmez. Aşağıdaki HTTP/schema negatifleri ise bu dar gözlem kapılarını kapatır; statik oracle yokluğuna düşürülemez.

Mandatory project/detail/my-role GET için kapalı eşleme:

| Sonuç | Check outcome | ErrorCode / exit |
|---|---|---|
| 401/403 veya typed açık permission reddi | denied | remote_access_denied / 3 |
| 404/405, 3xx veya beklenmeyen diğer 4xx | invalid | invalid_response / 1 |
| 429 | unavailable | remote_rate_limited / 1 |
| 5xx | unavailable | remote_failed / 1 |
| timeout | unavailable | transport_timeout / 1 |
| TLS/network/protocol | unavailable | transport_failed / 1 |
| 2xx logical false, malformed/missing/duplicate/nonfinite/oversize | invalid | invalid_response / 1 |
| önceden kayıtlı genel oracle yokluğu, endpoint çağrısı yapılmadan | not_exposed | null grant; yalnız explicit policy için izin verilen risk |

Salt okuma ADR-0017 gereği en çok iki fiziksel deneme/tek deadline'dır (yalnız tanımlı transient durumlar); effectful HTTP her status/exception'da tek denemedir. Tükenmiş retry sonucu yukarıdaki tabloya gider; 405/429/5xx hiçbir zaman not_exposed olmaz. Gerçek write 401/403 durable receipt/namespace'te kalır; yeni plan/flag/revision replay vermez. Prepare'daki read ret'i yeni çağrıda ancak aynı mandatory probe'un yeni başarısıyla aşılır; unavailable/empty/invalid ile değil. Ayrı kalıcı negatif cache eklenmez.

My-role endpoint **GET datasets/{exact_dataset_uuid}/my-role**. Root object veya success=true/data object envelope; varsa her consumed root success strict bool=true. Required `role: str` (1–64 control-free karakter), `permissions: list[str]` (≤32; her biri 1–64 control-free ASCII string); duplicate permission invalid_response, bilinmeyen label capability'ye çevrilmeden yok sayılır. Valid listede literal `upload` yoksa denied/remote_access_denied; missing/wrong type invalid. Raw tree strict JSON/secret/byte scan sonrası kullanılmayan metadata atılır; rol adı authority değildir. Exact dataset/credential/epoch/generation gözlem yaşı ≤30 s; stale veya yanlış bağ arm açmaz. Henüz dataset yoksa my-role sonucu uydurulmaz; create/link sonrası, presign/PUT/confirm öncesinde zorunludur. İç UploadObservation tam alanları consumer_profile/policy_version, scope, dataset_id, checked_at, has_upload:strict bool; role/permission listesi kalıcı grant'a çevrilmez. CurrentCheck'te bu nullable gözlem ayrı taşınır, ilgili upload arm'ında mevcut/taze/true olması gerekir.

## Read, terminal ve başarı grafiği

Terminal record acquire_read/reconcile/verified mutasyonunu **network ve lease öncesi** operation_conflict/2 ile reddeder; local list/show sonucu değişmez. Unknown yalnız workflow_latched=true için mümkündür. Lease'i bitmiş unlatched admission yerel CAS ile cancelled/lease_expired olur; read hatası admitted→unknown yaratamaz. Exact dataset ID kayıpsa ada göre lookup/re-create yoktur: local unknown/operation_uncertain/5 ve sıfır remote write. Lease halen etkinse başka aktör sahipliği alamaz; expiry sonrası bu yerel cleanup current credential veya read flag gerektirmeden fence/CAS ile kapanır. Aşağıdaki read matrisi latched ve ID'si bilinen **uzak okumayı** düzenler; hiç intent üretmemiş işin cancelled cleanup'ı ayrı, execution izni üretmeyen yerel yoldur.

| Policy/aktör | Current read grant | İnsan seçimi | Mod |
|---|---|---|---|
| v1 veya v2 verified_only | geçerli | unverified-read flag yok | verified_read |
| v1 veya verified_only | yok | flag yok | upload_plan_not_valid/2 |
| v1 veya verified_only | herhangi | unverified-read flag true | invalid_request/2; bypass yok |
| v2 explicit, initial write owner | geçerli | etkin initial approval | verified_read |
| v2 explicit, initial write owner | not_exposed | etkin approval + authority ack true | explicit_read_attempt |
| v2 explicit, initial write owner | not_exposed | authority ack false/approval expired/revoked | approval_required/4; coordinator delivery unknown ise aşağıdaki exit 5 |
| v2 explicit, restart/reconcile | geçerli | flag false veya true | verified_read; true yalnız fallback iznidir, grant sayılmaz |
| v2 explicit, restart/reconcile | not_exposed | accept-unverified-read true | explicit_read_attempt |
| v2 explicit, restart/reconcile | not_exposed | flag false | approval_required/4; ownership mutation/network yok |

İlgili read action check'inin denied/unavailable/invalid sonucu hiçbir satırda read attempt'e düşürülemez; ayrı upload action reddi metadata read izni diye de, genel read reddi diye de yeniden yorumlanmaz. Restart flag yeni write approval/permit değildir. Current read scope yeni gözlemin current credential/epoch/generation'ıdır; tarihsel admission/approval scope'u değişmez. Proof yazımında observed_at≤now ve yaş≤30 s, aynı nesilde son confirm receipt sonrası; reset sonrası güncel recovery floor uygulanır. Tarihsel proof ertesi gün freshness nedeniyle invalid olmaz.

Read 401/403→remote_access_denied/3; 429→remote_rate_limited/1; 5xx→remote_failed/1; transport_timeout/transport_failed→1; malformed/404/405→invalid_response/1. **Ayrı readonly reconcile çağrısı** bu güvenli kodu OperationError+operation ID ile döner; latched nonterminal kayıt unknown/read_unavailable ve recovery marker olur. Bu, genel exit-5 önceliğinin yalnız sıfır write yapan read çağrısı için açık istisnasıdır. **Aktif write start/coordinator** metadata teslimini kesinleştiremiyorsa operation_uncertain/5 + origin reason_code önceliğini korur. Read hatası remote execution failed veya terminal downgrade değildir.

Başarı için tam graph kümesi zorunludur: `{(create,null),(project_link,null)} ∪ {(presign,i),(put,i),(confirm,i):i=0..N−1}`. Cardinality tam **2+3N**, fazla/eksik/duplicate/index dışı intent yok; her biri tek accepted receipt; predecessor/intent/receipt chronology, expected dataset/project/opaque safe-key, PUT byte/hash, tam ordered metadata ad-digest/size/SHA/tekil item-ID eşliği geçer. Mevcut intent'lerin hepsi accepted olsa bile tek zorunlu intent eksikse **unknown**, metadata eşleşmesi onu üretmez. Eksik receipt veya create ID'si isim benzerliğiyle doldurulamaz. Başarı yazımı eksik graph veya tazelik nedeniyle operation_uncertain olursa, mümkün olan aynı-owner yerel marker kayıt durumunu unknown/request_uncertain yapar; mevcut lease yalnız salt okuma düzeltmesi için kalabilir, yeni arm açılamaz. Önceden commit edilmiş terminal sonuç korunur; owner/store kapısı marker yazımını engellerse belirsizlik ID ve güvenli reason_code ile döner.

Yeni nonterminal v2 metadata success, yukarıdaki tam graph'a ek accepted CreateReceiptV2 ve immutable full create-detail eşliği ister. Tarihsel terminal proof full validation'ına bu yeni şart koşulsuz eklenmez.

V2 control matrisi: metadata_verified yalnız succeeded+terminal+nonnull canonical v2 proof digest; read_unavailable yalnız unknown+recovery+null digest; diğer non-success reason'larda digest null. Succeeded/failed/cancelled terminal immutable; recovery aynı ayrılmış slotta semantic değişimi coalesce eder, terminal ayrı ikinci slot. Reset/takeover üreticisi operation sürümünü izler; v1/v2 mixed ret edilir. Full validation record/control/proof/revision/epoch ve rezerv eşliğini denetler.

## Public özet ve kabul

`DatasetUploadSummary v2`: schema_version=2, kind=dataset_upload_summary, plan_id, plan_digest, plan_status, admission_policy, cost_policy, risks, blockers, nullable operation_id/operation_status, verification_level=`none|metadata`, remote_bytes_verified=false, authority_verified (strict bool), nullable cost_bound (kapsamı yukarıdaki v2 tip), nullable budget_micros; cost_scope=`original_start_invocation|legacy_unknown` (source_plan_schema ile eş). DTO ≤16 KiB ve üst Result v1'dir. Yeni public upload yüzeyi daha önce yayımlanmadı; summary v2 ayrıca source_plan_schema=1|2 ve legacy_history_only:bool taşır. V1 history için cost_bound=null gösterilir, scope-only eski tutar yeni v2 garantiye çevrilmez; historical plan_status korunur ve yeni write gate'inin kapalı olduğu legacy_history_only ile görünür. V1 private list-entry/golden byte'ları ayrı korunur. List sayfa limiti en çok 100 ve encoded üst Result ≤1 MiB; byte tavanı önce dolarsa doğru keyset cursor ile daha kısa sayfa üretilir, kayıt atlanmaz. Authority true yalnız başarıya ulaşmış operasyonun başlangıcında tam grant vardı ve bütün arm'lar gerçek grant gate'ini geçtiyse tarihsel scoped durumdur; aksi false. Initial authority riski sonradan metadata/read grant ile yükseltilmez. Verification_level yalnız geçerli success proof'ta metadata'dır; read failure bu terminal sonucu değiştirmez. Eski plan/approval wire'ı summary'ye dönüştürülerek yeniden kaydedilmez.

Public show/list/prepare/approve/revoke/start/reconcile ve bütün output biçimleri internal repository view, receipt veya created_dataset serialize etmez; receipt'teki owner_id/org_id/name bu dar summary'ye eklenmez. Controller/public sentinel testleri stdout/stderr/JSON/NDJSON sınırını doğrular.

Kabul: ADR-0027 receipt/legacy/owner/CAS/raw-byte/public projection matrisi; 96 bağımsız literal matrix satırı; v2 plan/cost/approval/record/control/verification canonical byte/digest golden'ları; aynı scope farklı manifest/N/byte/root/storage/parameters/window/request-limit ve yalnız-transfer/unknown-storage negatifleri; fiyat tazeliği ve charge-period ayrımı; bool/float/overflow/category/type/period retleri; v1 history aynı kalırken yeni admit/arm sıfır permit. Null→current positive, partial→current full, full→expired, semantik source/amount değişimi ve immutable digest testleri. Approve/admit/arm/read hata/ack matrix'i; whole graph eksik ama kalan accepted+metadata eş fixture'ı; read failure/terminalimmutability; record/control mixed version/digest/iki-slot/coalescing/reset/takeover; max 128 file/16KiB record/2KiB control/128KiB proof ve gerçek rezerv tavanları. Aynı kaynak üç output/CLI/Python, process race, source-bound native/kurulum ve ayrı live/CI kabulü tamamlanmadan epik verified olmaz.
