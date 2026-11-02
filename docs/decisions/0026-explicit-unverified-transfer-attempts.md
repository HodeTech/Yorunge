# ADR-0026: Doğrulanmamış transfer denemesinde açık politika ve onay

**Durum:** Proposed — kullanıcı onayı bekleniyor; bağımlı ürün kodu başlamadı. **Tarih:** 2026-11-02. **İş:** P02-2a/b/c. [Accepted temel](0024-durable-dataset-transfers.md), [ilk create ve ayrı read gözlemleri](../research/p02-2-private-create-observations.md), [kanonik mevcut sözleşme](../reference/dataset-transfer.md), [paket planı](../roadmap/p02-2-delivery-plan.md).

## Bağlam

API key ile bir private create 201 döndü; doğru username/slug rotasında aynı kaydın detail ve my-role okumaları 200 oldu, `upload` etiketi gözlendi. İlk yanlış ID-detail rotasının 405 sonucu korunur. Project link/presign/PUT/confirm yapılmadı. Bu somut gözlemler genel create/link authority, principal anlamı, provider spending cap veya fiyat garantisi değildir. Kullanıcı küçük denemeyi ve ilk 200 CR'nin aşılmasını kabul etti; bu talimat ürünün bütün kullanıcılar için varsayılan politikasını değiştirmiş sayılmaz.

ADR-0024 mevcut public prepared yolunda tam güncel grant ve bounded cost ister. Sağlayıcı bu dar tüketici için complete create/link ön-yetki veya fiyat oracle'ı sunmadığında, gerçekten yapılabilecek bir işlemin deneme yolu da kapalıdır. Fixture grant/cost üretmek, rol etiketini doğrulanmış yetki saymak veya bilinmeyen ücreti sıfır yazmak doğru çözüm değildir. Bu karar yalnız açıkça seçilmiş deneme politikasını eklemeyi önerir.

## Karar

### Varsayılan ve açık alternatif

Varsayılan **`verified_only`** kalır: eksik authority veya cost kanıtı planı draft bırakır; onay/start bu koşulu aşamaz. Yeni **`explicit_attempt`**, insanın exact hedef/owner/proje/içerik/private etkilerini onaylayarak sağlayıcıya tek deneme göndermeyi seçmesidir. Provider'ın yetkisine ilişkin yerel bir proof değildir; bütün yazmalarda sağlayıcı son kararı verir. Public authority unknown kalabilir; `supported` veya `prepared` yetki garantisi üretilmez.

Bu alternatif capability cache'e olumlu kanıt yazmaz, P02-R1'i kapatmaz ve caller'dan raw grant/verified flag almaz. Görünürlük, kullanıcı ID'si, role veya `upload` string'i tek başına yetki değildir. Bilinen exact-scope 401/403, açık izin reddi, wrong-owner/project/private, input değişimi veya hedef uyuşmazlığı hiçbir acknowledgement ile aşılamaz. Yeni oluşturulan dataset için typed my-role okumasında `upload` bulunması ek bir dar önkoşuldur; bu gözlem yok/ret/bozuksa presign/PUT açılmaz. Pozitif etiket yine verified grant sayılmaz.

Trusted producer'ın iç `AuthorizationCheck` sonucu kapalıdır: `allowed`, `not_exposed`, `denied`, `unavailable`, `invalid`. `allowed` yalnız gerçek grant üretir; yalnız seçilmiş tüketici/policy sürümünün açıkça tanımladığı oracle yokluğu `not_exposed` olabilir. 401/403→denied (`remote_access_denied`/3), transport→unavailable (mevcut transport kodu/1), bozuk/eksik kontrol alanı→invalid (`invalid_response`/1); bunların hiçbiri exception yakalanıp null grant/not_exposed'a çevrilemez. Denied/unavailable/invalid prepare'ı veya henüz arm edilmemiş aşamayı durdurur; plan/permit üretilmez.

Check; action, exact normalized target, owner/project, varsa dataset UUID, credential ID/revision, store/epoch/clock, producer/policy sürümü ve checked_at ile bağlanır. Create/link genel authority oracle'ı olmayabilir; mandatory owner/project context okumaları ve var olan my-role endpoint'i yine yapılır, başarısızlıkları oracle yokluğu sayılmaz. Yeni prepare ve her effect arm güncel check ister; my-role upload gözlemi aynı exact dataset/credential/epoch için en çok 30 s yaştadır, gerekiyorsa transaction dışında yenilenir. Bu observation freshness'tir; uydurma authority-expiry veya 120 s PUT garantisi değildir. Bir güncel ret aynı işlemde sonraki boş/başarısız okumayla unknown'a düşürülemez. Yeni çağrıda mandatory probe yeniden yapılır; önceki read reddi ancak aynı scope'ta yeni başarılı probe ile aşılabilir, unavailable/invalid ile değil. Bu karar ayrı kalıcı negatif cache eklemez. Gerçek write 401/403'ü zaten durable intent/receipt ve kalıcı namespace bağında saklanır; yeni plan/reset/revision veya politika o niyet için ikinci write vermez. Credential değişiminde eski pozitif/negatif snapshot yeni kimliğe taşınmaz; yeni check zorunludur.

### Ücret ve bütçe seçimi

Numeric `--budget-cr` verildiğinde provider kaynaklı güncel `UploadCostBound` hâlâ zorunludur. Unknown fiyat bu tutarın altında varsayılamaz; bilinen bound bütçeyi aşarsa draft/ret kalır. Bu kural explicit_attempt'ta da değişmez.

Yalnız explicit_attempt ile ayrı **`--unpriced`** seçilebilir: `budget_micros=null`, `cost_policy=unpriced_accepted`. Caller tarafından seçilmiş sayısal CR tavanı uygulanmaz; provider hard-cap ayrıca doğrulanmadıysa var sayılamaz. Fiyat bilinmiyorsa başlık/özet/onayda “ücret ve kalıcı depolama maliyeti bilinmiyor; tutar üst sınırı uygulanmıyor” görünür. Bilinen fiyat/bound varsa bunun yerine gerçek bound ve “kullanıcı CR tavanı seçmedi” gösterilir; bilinen değer unknown diye sunulmaz. 200 CR gibi önceki rakam enforced limit olarak gösterilmez. Başlangıçta fiyat bilinmiyorsa garantili ücretsiz diye yeniden adlandırılmaz; yalnız tanımlı dosya/byte/request/time kapsamına tek denemedir. Bilinen bound yeni bir sayısal kullanıcı tavanı yaratmaz.

`--budget-cr` ile `--unpriced` birlikte veya ikisi de yoksa `invalid_request`/exit 2; verified_only + unpriced da aynı şekilde etkiden önce reddedilir. Para decimal string → integer microcredit olarak strict/finite/nonnegative çözümlenir; float/bool, precision kaybı veya taşma kabul edilmez. Yeni politikada da file/byte/adet/süre ve kalıcı store kapasitesi değişmez.

### Kapalı v2 plan ve onay

Yeni public producer **DatasetUploadPlan v2** üretir; kind `dataset_upload_plan`, schema_version=2, policy_version=2. V1 alanları ve bound scope/root/manifest/storage/parameters korunur; aşağıdaki farklar tamdır:

| Alan | V2 tipi ve kural |
|---|---|
| `admission_policy` | `verified_only` veya `explicit_attempt`; default yalnız kullanıcı argümanında verified_only, persisted JSON'da zorunlu |
| `cost_policy` | `bounded_required` veya `unpriced_accepted`; numeric budget ile ilk, unpriced ile ikinci |
| `budget_micros` | strict nonnegative int64 veya null; yalnız unpriced_accepted'ta null |
| `risks` | en çok iki, tekil ASCII sıralı kapalı tuple: `authority_unverified`, `cost_unverified`; grant yok veya required dört permission tam değilse ilk, cost_bound yoksa ikinci; caller istediği için boşaltılamaz |
| `blockers` | V1 kapalı katalog; seçilmiş politika altında gerçekten engelleyen koşullar, risklerle aynı şey değildir |
| `status` | `draft`, `prepared`, `attempt_ready`; aşağıdaki reducer'a tam eşit |
| Diğer alanlar | V1'deki tip/limit/digest/scope/tazelik ve `executable=false`; raw secret/env/tag/K/URL yok |

Grant/cost varsa eski exact scope, producer, süre ve maksimum tutar koşulları korunur. Authority/cost bilgisi bulunmadığı için null kalır; yanlış pozitif observation veya kullanıcı acknowledgement bu alanlara yazılmaz. Positive full grant ve cost kanıtı numeric budget içinde ise prepared; hiç proof olmayan deneme yalnız attempt_ready olabilir. Geçersiz input, known over-budget veya bağ uyuşmazlığı her durumda engeldir.

| Politika ve kanıt | Sonuç |
|---|---|
| verified_only; numeric budget; tam grant/cost ve input | prepared |
| verified_only; eksik grant veya cost | draft; eski blockers korunur |
| explicit_attempt; numeric budget; cost yok veya bütçe üstünde | draft; consent hard-cap yerine geçmez |
| explicit_attempt; numeric budget; cost yeterli; grant unknown; input geçerli | attempt_ready; authority_unverified riski |
| explicit_attempt; unpriced; grant/cost unknown; input geçerli | attempt_ready; iki risk |
| explicit_attempt; unpriced; tam grant mevcut, cost unknown; input geçerli | attempt_ready; cost_unverified riski |
| explicit_attempt; unpriced; cost biliniyor | Bilinen bound gösterilir; numeric tavan iddia edilmez. Grant eksikse attempt_ready; insanın unpriced seçimi korunur |

`prepared` yalnız numeric bütçeli tam doğrulanmış yoldur. Unpriced seçiminde bütün snapshot'lar olumlu olsa da status attempt_ready kalır; üst sınırın kullanıcıca seçilmediği görünür. Unknown şartı sonradan yeni bilgiyle sessizce farklı admission politikasına çevrilmez; saved plan değişmez. Güncel yeni negatif/expiry/change denetimleri her arm'da geçerlidir.

**DatasetUploadApproval v2** bütün V1 alanlarını (`approval_id`, plan/binding digest, store/epoch/generation, zaman ve revoke dahil) korur; schema_version=2 olur ve `admission_policy`, `acknowledge_unverified_authority: bool`, `acknowledge_unpriced_cost: bool` ekler. İlk bool, plan risks içinde authority_unverified varsa tam true; ikinci bool cost_unverified varsa tam true olmalıdır. Gerekmeyen bool false kalır. Unpriced seçim bilinen cost ile kullanılıyorsa sayısal tavan olmadığı plan digest'ine bağlıdır; approve özeti bunu ayrıca gösterir. Bu bool'lar caller acknowledgement'dır, provider grant/cost kanıtı değildir. Yeni plan alanlarının tamamı canonical plan/binding digest girdisidir; observation zamanı gibi dışlanan alanlara eklenmez.

Eksik acknowledgement `approval_required`/exit 4; geçersiz argüman `invalid_request`/2; bozuk saved JSON/type/digest state_invalid/2; süresi/bağı değişmiş plan upload_plan_not_valid/2. Bilinen operation üzerindeki belirsizlikte mevcut operation ID/exit 5 önceliği korunur. Yeni bir açık uçlu `force`, keyfî reason veya error dict'i yoktur. Text/JSON/NDJSON/Python aynı reducer ve onay koşulunu kullanır.

### Yüzey, yaşam döngüsü ve son kapılar

Plan komutu mevcut owner/project/root/manifest argümanlarına `--admission-policy verified-only|explicit-attempt` ve zorunlu bütçe seçimi `(--budget-cr DECIMAL | --unpriced)` ekler. Approve, gerektiğinde `--accept-unverified-authority` ve `--accept-unpriced-cost` ister. Python aynı keyword-only seçimleri/defaultları taşır; user'dan producer/client/SQL/proof enjeksiyonu almaz. Bilinen hiçbir risk boş/örtük flag ile kabul edilmiş sayılmaz; config/env bu flags'i otomatik üretmez.

Saved approval, policy/risks ve exact plan digest'ine bağlıdır. Admission ve her arm; aynı credential ID/revision/hedef, store/epoch/clock, owner/fence/lease, input ve önceki receipt kapılarını korur. Explicit unknown authority'de uydurma authority expiry oluşturulmaz; port deadline hesabında o mevcut olmayan terim kullanılmaz. Gerçek bounded grant/cost varsa kendi süreleri hâlâ kısıtlar. Total/lease/URL için 5 s pay, 900/150/120 s, PID-bound write access ve tek kullanımlık permit aynen kalır. Intent COMMIT sonrası revoke/reset'in geri alamadığı pencere değişmez.

Bir kez kalıcılaşmış create/intent bağı yeni politika/onay/plan ile replay edilemez. İlk araştırmada oluşturulan dataset read-only incelenir; bu karar o durmuş workflow'a yeni write permit vermez. Yeni canlı yazma kabulü kendi review'den geçmiş somut planı, scope'u ve yetkisiyle değerlendirilir; kullanıcının önceki dar denemesinden sınırsız yeni create/harcama çıkarılmaz.

### Aynı kayıt üzerinde açık salt okuma ve metadata sonucu

V1 ve verified_only operasyonların mevcut current `read_created_dataset` grant kapısı korunur. **Yalnız v2 explicit_attempt** için aynı hedef/owner/proje/dataset'e bound bir read-attempt yolu eklenir; bu da read grant üretmez. İlk workflow'ın aynı etkin owner'ı kendi onayındaki authority acknowledgement ile final metadata okumasını yapabilir. Restart/reconcile çağrısında current user ayrıca `--accept-unverified-read` / Python `acknowledge_unverified_read=True` seçer; mevcut etkin write approval gerekmez. Eksik flag approval_required/4'tür; v1/verified_only'de flag bir bypass değildir. Caller bu flag ile yeni hedef/dataset veya write aşaması seçemez. Config/env bunu otomatik üretmez.

Read takeover yine yalnız read lease/CAS/fence alır; write access/attempt/permit üretilmez. Güncel credential/store/epoch/clock ile historical exact resource bağı korunur; reset sonrası yeni kimlik yalnız bu kaydı okur. Bilinen read 401/403, unavailable veya malformed gözlem başarı/failed execution sayılmaz; operasyon unknown ve v2 kapalı `read_unavailable` reason'ıyla kalır, mevcut güvenli hata/operation ID zarfı döner. List/show her durumda yerel/etkisizdir.

**TransferVerification v2** schema_version=2; v1 `dataset_id`, `project_id`, `observed_at`, ordered `files` alanlarını korur, `scope: UploadScope`, `authorization_policy=verified_read|explicit_read_attempt`, `grant: UploadGrant|null` taşır. Verified_read aynı scope'ta current read grant ister; explicit_read_attempt yalnız v2 explicit operation ve yukarıdaki insan seçimiyle null grant kullanabilir. Scope'ta current credential/identity/clock ve değişmeyen exact owner/project/target/store bağları son transaction'da karşılaştırılır. Kaydın aynı clock/epoch business floor'u veya reset sonrası güncel recovery control floor'u korunur; final kayıt transaction'ında observed_at gelecekte veya 30 s'den eski olamaz. Bu tazelik gate'i yalnız yeni proof yazımı içindir; tarihsel başarı kaydı ertesi gün full validation'da bu nedenle bozulmaz. Files yine tam sıra/ad-digest/size/SHA/tekil item-ID oracle'ına eşit olur; raw body/signed URL saklanmaz.

V2 success yalnız **bütün eski stage intent'lerinin geçerli accepted receipt'i** ve tam metadata karşılaştırması varsa mümkündür; kayıp receipt salt liste gözlemiyle yeniden üretilmez, yoksa unknown kalır. Success reason `metadata_verified`; public özet `verification_level=metadata`, `remote_bytes_verified=false` ve gerçek authority durumunu ayrı gösterir. Bu metadata teslim sonucudur; yetki/principal, atomik uzak snapshot veya indirilmiş byte doğrulaması değildir. Unknown authority ile yapılmış bir deneme successful metadata sonucuna ulaşabilir ama capability supported/verified grant yazamaz. V1 `verified` reason/DTO semantiği değiştirilmez.

V2 özette `authority_verified`, yalnız mevcut metadata okuması başarılı diye true olmaz. Plan başlangıçta authority_unverified riski taşıdıysa bu operation'ın özeti false kalır; başlangıçta/arm sırasında gerçekten doğrulanmış yetki varsa kendi scope ve zamanına ilişkin tarihsel durum ayrı gösterilir. Read grant veya metadata kanıtı geçmiş write yetkisine dönüştürülmez.

### Uyumluluk ve onay sonrası geçiş

V1 canonical plan/approval ve digest golden'ları değişmez. V7 SQL tabloları payload version'ını zaten taşır; DDL/checksum 1–7 yeniden yazılmaz. Yeni decoder V1 ve V2'yi kapalı discriminated union olarak okur. Yeni planın **TransferRecord v2** kaydı schema_version=2 ve içte DatasetUploadApproval v2 taşır; diğer operation alanları/limitleri korunur, kapalı reason kataloğuna `metadata_verified`/`read_unavailable` eklenir. StageIntent/Receipt/lease wire'ı aynı kalır. V1 verified-only semantiği korunur, v1 belirsiz kayıt v2'ye çevrilip arm edilemez. Eski binary'nin v2 payload'ı kontrollü reddetmesi veri kaybı/otomatik downgrade doğurmaz. Payload ve rezerv kotaları mevcut üst sınırda kalır; yeni tip aynı byte sınırına sığmalıdır.

**TransferControl v2** schema_version=2, diğer v1 control alanları ve 2 KiB sınırını korur. V2 record/control reason kataloğu eski non-success nedenler + `metadata_verified`/`read_unavailable` olur; v1 `verified` string'i v2'de kullanılmaz. `metadata_verified` yalnız terminal control ve nonnull `verification_digest` ile; `read_unavailable` yalnız recovery control ve null digest ile geçerlidir. Diğer nedenlerde digest null'dır. Digest canonical TransferVerification v2 byte'larını bağlar; v1 digest algoritması/golden'ı değiştirilmez. Her v2 operation yalnız v2 approval/control/verification, v1 operation yalnız kendi v1 tipleriyle doğrulanır; karma sürüm ret edilir. Reset, read takeover ve terminal/recovery upsert operation sürümüne uygun control üretir. Mevcut iki recovery/terminal rezervi ve coalescing kuralı korunur; yeni sınırsız history yoktur.

Onay commit'inde ADR-0024'e partial amendment forward link, karar indeksi, transfer referansının v2 tam alan/kural/örnekleri, P02-2a/b/c ve d/e uyum alt adımları, paket planı/current/matris güncellenir. Provider codec/actual upload/live/native/paket/CI kapıları kaldırılmaz. D/e mevcut v1 yerel kabulü tarihsel korunur; v2 değişiklikleri kendi commit ve iki fresh review turuyla yeniden kabul edilir. P02-2 scope'u yalnız observer'a düşürülmez.

## Alternatifler

- Yalnız verified_only ve provider oracle beklemek: güvenli mevcut seçenek; kullanıcı açıkça denemek istediğinde dar feature ilerlemesini dış desteğe bağlar.
- Fixture grant, role → verified veya unknown cost → 0: yanlış iddia; seçilmedi.
- Varsayılanı unknown-attempt yapmak veya tek `--force` flag'i: bilinmeyen harcama/yetkiyi gizler; seçilmedi.
- Yalnız bu hesaba hardcoded istisna: ortak ürün sözleşmesini/testi bozar; seçilmedi.

## Sonuçlar ve kabul

Öneri, doğrulanmış ön-yetki/fiyat zorunluluğunu yalnız açık alternatifte değiştirir; bilinmeyeni dürüst gösterir ve insan kararına bağlar. Uzak exactly-once, permission guarantee, spending cap veya yeniden başlatılabilir upload vaat etmez. Tek bir tüketici gözlemiyle kapsamlı capability açılmaz.

Kabul: literal v1/v2 JSON/digest/approval/verification fixture'ları; yukarıdaki tüm policy×proof×budget matrisi; kısa/uzun secret ve dinamik yerel alanlar; eksik/yanlış bool acknowledgement; known negative→yeni plan, negative→unavailable/empty, credential/epoch değişimi ve stale/wrong-dataset upload gözlemi; over-budget/no-body/schema/expiry; iki süreçte revoke/rotation/reset ve intent öncesi/sonrası ayrımı; restart'ta sıfır write, explicit read flag/current scope ve unknown authority ile metadata sonucu; kayıp receipt'in success'e çevrilememesi; eski v1 okuma/checksum/kapasite/frontier/preview eşliği; ortak CLI/Python ve üç çıktı biçiminde açık risk özeti. Aynı hash farklı ad, real proxy/direct sınırı, source/remote metadata ayrımı ve actual provider success oracle'ları P02-2b'de korunur. Son kaynaklı native/kurulu/CI ve ayrı yetkili live kabul olmadan epik verified olmaz.
