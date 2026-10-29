# ADR-0016: Kalıcı operation kabulü, tek gönderim ve sahiplik

**Durum:** Accepted — 2026-10-29 kullanıcı yetkisiyle, review bulgularının doğrulanmış revizyonu ve iki fresh review turu sonrası benimsendi. Tasarım kabulüdür; dört adımın yerel ürün kabulü bu dalda verified. Development merge ve canlı EVREN doğrulaması ayrı aşamalardır. **Tarih:** 2026-10-29. **İş:** P01-4b/4c. [Ön inceleme ve disposition](../research/p01-4-readiness-review.md), [teslim planı](../roadmap/p01-4-delivery-plan.md), [wire](../reference/operations.md).

## Bağlam

[ADR-0004](0004-local-durable-operation-state.md) ve [ADR-0011](0011-state-foundation-and-migrations.md) SQLite, yan etkiden önce kalıcı kayıt ve fencing seçimini yaptı. [ADR-0014](0014-execution-plan-validity-and-approval.md) immutable execution planı/onayı sağladı; fakat operation kardinalitesi, gönderim sınırı, lease zamanı, uzlaştırma kanıtı ve kaynak kotaları henüz tanımlı değil. Yerel fencing eski sürecin DB yazısını reddedebilir; son yerel kontrolden sonra durmuş sürecin dış çağrısını fiziksel olarak engellemez. Bu öneri ikinci sahibin ikinci gönderimini önleyen daha dar bir garanti kurar.

## Karar

### Kapsam ve uyumluluk

P01-4 iç koordinasyon portları ve public salt iş sorguları ekler. Ürün producer'ı draft/blocked kalır; public `run`, `admit`, `reconcile`, `watch`, `stop`, fixture backend veya gerçek HTTP/EVREN/araç adaptörü eklenmez. Pozitif yürütüm kanıtı yalnız testlerin seçtiği port ve sentetik ayrı süreçle oluşur. Offline v1, execution v2 gövdeleri/digest'leri ve genel Result v1 değiştirilmez.

Bu karar ADR-0011'in operation tüketicisini somutlaştırır; motor/journal/dayanıklılık ve bütçe seçimini değiştirmez. [ADR-0015](0015-checksummed-data-migrations.md) gereği şema 5→6 **SQL-only V2** migration olur; yeni tablolar boştur, eski plan/onaylar operation'a dönüştürülmez. Migration 1–5'in manifest/SQL/checksum ve donmuş handler baytları korunur.

### Kimlik ve atomik kabul

- Store başına her `plan_id` için ömür boyunca en çok bir operation vardır: `UNIQUE(plan_id)` ve plan FK `ON DELETE RESTRICT`. Terminal iş de aynı plandan yeniden gönderilmez. Bilinçli yeni çalıştırma yeni plan ve onay gerektirir; farklı plan ID'leri arasında anlamsal/global deduplikasyon iddiası yoktur.
- Operation UUIDv4; plan ID/digest, store/ilk identity epoch/clock generation ve kabuldeki approval ID, binding digest, onay zamanı/expiry snapshot'ı immutable'dır. Approval satırı replace/revoke edilince tarihsel kabul kanıtı değişmez; mutable approval satırına FK kurulmaz.
- Admission, pre-dispatch takeover ve final arm **aynı approval ID ve onay gövdesini** kullanır; bu kayıt hâlâ etkin olmalıdır. İdempotent approve aynı etkin kaydı döndürebilir. Revoke→reapprove veya expiry sonrası yeni approval ID, mevcut admitted operation'ı canlandırmaz/yeniden bağlamaz; yeni yürütme niyeti yeni plan/onay ister. Böylece tek kalıcı onay snapshot'ı arm yetkisinin de kesin kanıtıdır.
- İç admission aynı çağrıda trusted execution validator, descriptor input ve tek credential snapshot'ıyla güncel doğrulama yapar. Caller'ın eski `valid=true`, digest veya `approved=true` değeri kabul bileti değildir. P01-4'te local-only dahil etkin digest onayı zorunludur.
- Admission, gönderim öncesi takeover ve final arm'ın **her birinin kendi son BEGIN IMMEDIATE transaction'ında**, kullanılan her credential için güncel `credential_id`, `credential_revision`, `identity_epoch`, `service_id`, origin ve API base path tekrar okunup aynı çağrının private snapshot'ıyla tam karşılaştırılır. Yeni bir registry revision sayacı yoktur. B revision 2'yi kaydettikten sonra A revision 1'le commit edemez: state_changed, sıfır port çağrısı, otomatik env yeniden çözümlemesi yoktur. Planın sabit baytları, aynı etkin approval, store/epoch/clock generation ve bütün validity aralıkları da son transaction'da tekrar denetlenir; operation + ilk attempt + ilk lease + geçiş kaydı birlikte yazılır. Ağ/uzun hash transaction dışında kalır.
- Mevcut operation aynı plan için tekrar admission'da yalnız bulunur; yeni attempt, lease veya gönderim bileti üretilmez. İki yarışmacı tek kayda yakınsar. Kayıt ID'sini bilmek execution yetkisi değildir.
- Kabul/sonuç commit'i belirsizse aynı kayıt incelenir; otomatik yeni operation/admission/start yoktur. Commit edilmiş kabulün son süre kontrolü başarısızsa ID hata zarfındaki operation_id alanında korunur, dış port çağrılmaz.

### Attempt ve tek kullanımlık gönderim sınırı

Attempt **bir execution başlatma adayıdır**; heartbeat veya reconcile çağrısı değildir. İlk attempt `claimed` olur. Gönderim sınırına gelmemiş lease devrinde eski attempt `abandoned`, yeni attempt sıradaki numarayla `claimed` olabilir. Numara operation içinde 1'den artar; terk edilen attempt gönderilmiş sayılmaz. Gönderim sınırından sonra yeni attempt yoktur; yeni sahip aynı attempt'i yalnız uzlaştırır.

1. Gönderimden hemen önce aynı çağrının güncel execution validation/onay/credential snapshot'ı yeniden denetlenir. Final transaction bütün credential ID/revision/hedef bağlarını tekrar okur; current owner/fence, lease/epoch/generation ve süreleri kontrol eder. Geçerli lease aynı owner/fence ile arm sırasında yenilenebilir; bu kontrolün yerine geçmez.
2. Operation'ın bir kez atanabilen `dispatch_attempt_id` bağı ve attempt `submitted` durumu **dış çağrıdan önce** birlikte commit edilir. `submitted`, sağlayıcının kabul ettiğini değil, gönderimin yapılmış olabileceğini anlatır. Bu bağ hiçbir reset, lease devri, expiry, hata veya yeni onayla temizlenmez.
3. Yalnız bu başarılı commit'in ilk sahibi için composition içinde tüketilen tek kullanımlık izin oluşur. Permit oluşturulduğu PID'ye bağlıdır; consume anında mevcut PID tekrar okunur, fork kopyası reddedilir; copy/pickle/serialize ve repository'den sonradan yeniden üretme yoktur. Aynı süreçte consume thread-safe tek kullanımdır. Coordinator portun start metodunu en çok bir kez çağırır; otomatik retry/idempotency replay yoktur. Trusted composition'ın coordinator'ı bypass edip portu doğrudan çağırması güven sınırı dışındadır. Correlation anahtarı porttan önce kalıcılaştırılır; sağlayıcı desteği iddia edilmez.
4. Commit sonrası son UTC/monotonic/ownership kontrolü başarısızsa port çağrılmaz. Hâlâ yetkili CAS mümkünse iş unknown'a taşınır; lease/owner/generation kaybedilmişse eski süreç hiçbir business mutasyonu yapmaz, son atomik submitted/running korunur ve sonraki yetkili takeover unknown'a taşır. Bu son kontrol ile dış çağrı arasındaki scheduler duraklaması tamamen kapatılamaz. Lease kaybı/reset/revoke önceden alınmış izni dış sistemden geri çekmez; başka sahip **ikinci** `start` yapamaz. Uzak exactly-once veya tam iptal garantisi verilmez.
5. Port başladıktan sonraki timeout, kesinti, bozuk/eksik yanıt veya sonuç yazma belirsizliği unknown olarak ele alınır. P01-4'te ayrı trusted not_sent kanıtı/replay yolu yoktur; connection-refused gibi transient hata bile latch'i temizlemez. Kesin terminal observation varsa failed/succeeded/cancelled kaydı oluşabilir; ham exception terminal kanıt değildir. Kalıcılaştırma da başarısızsa son atomik submitted/running korunur; takeover bunu unknown'a taşır. Bellekteki başarı kalıcı başarı diye sunulmaz.

Onay/yetki için linearization noktası gönderim niyetinin commit'idir. Önceki revoke/reset/kimlik değişimi gönderimi engeller; sonraki değişim yeni izinleri engeller, başlamış olabilecek işi iptal ettiğini söylemez. Bu sınır yarış testleri ve kullanıcı bakım metninde açık tutulur.

### Lease, fencing ve saat

Lease TTL **30 saniye**; yenileme aynı owner/fence ile now < lease_expires_at iken now + 30 s'ye yapılır. Alan modeli kapalıdır:

| Alan | Tür / anlam / değişim |
|---|---|
| admission_identity_epoch / admission_clock_generation | UUIDv4 / positive int64; kabulün değişmez tarihsel store bağları |
| owner_id | UUIDv4 veya null; acquire/takeover rastgele yeni owner; reset/terminal null |
| fence | 0…2^63−1; ilk claim 1, her acquire/takeover +1; heartbeat/reset'te sabit; terminalde korunur |
| ownership_identity_epoch / ownership_clock_generation | UUIDv4 / positive int64 veya ikisi null; acquire anındaki **güncel** state_meta.identity_epoch ve cache_clock.clock_generation; renew değiştirmez |
| lease_expires_at | canonical UTC veya null; owner ile birlikte bulunur; renew değiştirir, reset/terminal temizler |
| revision | positive int64; ownership/recovery/business/result değişiminde +1, heartbeat'te sabit; bakım semantic fingerprint girdisi |
| recovery_required / recovery_reason | bool / kapalı OperationReason veya null; yalnız bounded güncel recovery kontrol özeti; terminalde temizlenir |

Ayrı ownership_generation sayacı yoktur; artan owner sürümü fence'dir. Sahip token'ı tam `(operation_id, owner_id, fence, ownership_identity_epoch, ownership_clock_generation)` olur. Son iki alan **mevcut store** epoch/generation ile ve token ile eşleşmeli, clock anomaly olmamalı, UTC lease süresi geçmemiş olmalıdır. Stale token business/renew/result yazamaz. Admission/acquire/takeover ve exclusive reset kendi transaction predikatıyla son row revision/fence'i CAS eder; eski token'a izin vermez. Reset epoch'u değiştirip owner/lease tuple'ını null yapar; fence'i artırmak gerekmez. Fence taşması yeni acquire'ı operation_fence_exhausted ile reddeder; credential reset'i buna bağlı değildir.

Kalıcı UTC lease aralığı ortak durable clock/generation kapısına tabidir; monotonic yalnız çağrı içi süre farkıdır, reboot otoritesi değildir. operations(lease_expires_at,operation_id) indeksi güncel owner'ı bulunan en çok 1.024 lease'i global frontier'e ekler: şema 6'da **13.312 expiry, 13.313 kontrol sınırı ve dört indeks araması**. Önceki şema 5'in 12.288/12.289/üç hesabı tarihsel kalır. Renew/replacement/terminal eski etkin expiry'yi değiştirir; gözlenmiş expiry watermark kanıtı kaybolmaz. Capability türev tablosuna lease satırı yazılmaz. Başka stateful çağrının gözlediği lease expiry geri saatte dirilemez. Clock anomaly business rollback'inden bağımsız kalıcılaşır; eski generation sahibi yazamaz/yenileyemez.

**İleri saat credential reset'ini kilitlemez.** Değişmez event geçmişi kendi gerçek UTC gözlem zamanını ve o andaki identity epoch/clock generation'ı taşır; business sırasının otoritesi artan event sequence ve revision'dır. Reset eski event timestamp'ini yeniden yazmaz; yeni epoch'ta güncel UTC ile kontrol invalidation'ı kaydeder. Güncel updated_at/outcome recorded_at yeni gözlemin gerçek UTC'sidir; epoch/generation değişiminde created_at'ten eski olabilir. Sticky clock_anomaly flag'i bu durumu gösterir; max(old,now) ile sahte gözlem zamanı üretilmez. Aynı clock alanında normal business UTC gerilemesi ortak kapıda reddedilir. Reset, gelecekteki nonterminal işi arşivi korunmuş recovery karantinasına alır; yeni epoch'ta read reconciliation hemen yapılabilir, 1 yıl beklemek gerekmez. Kalıcı dispatch latch'i değişmez. Tam wire ve sıra invariantları operations referansındadır.

İç coordinator'ın açık recover/takeover çağrısı lease kaybını işler; daemon/startup sweep veya jobs sorgusunda otomatik takeover yoktur. Gönderim öncesinde geçerli aynı plan/onayla yeni aday alınabilir. Sahibi expired/invalid olmuş, dispatch latch'i boş işte, onayın revoke/expiry/ID değişimi, plan expiry/epoch veya credential revision değişimi DB'den kesin doğrulanırsa **cleanup takeover** mevcut claimed attempt'i failed yapar; yeni attempt, execution izni veya port çağrısı üretmez. Attempt kotası da böyle kesin yerel retle kapatılabilir. Geçici validator/ağ hatası kesin ret değildir. Terminal slotu bu cleanup için açıktır.

Gönderim sonrası takeover aynı attempt'i recovery_required=true ile unknown karantinasına alır; yeni owner/fence yalnız read-only reconciliation içindir. Restore/reset/generation sonrası yeni owner güncel read credential'ını kullanır; admission credential'ını execution için yeniden yetkilendirmez. Terminal işte lease yoktur. Jobs yalnız son kayıtlı tarihi durumu gösterir; submitted/running kaydının stale olabileceği metin ve warnings'de açık belirtilir.

### Durumlar, kanıt ve sonuç

Operation durumları `admitted|submitted|running|unknown|succeeded|failed|cancelled`; attempt durumları bunlardan `admitted` yerine `claimed` ve ayrıca `abandoned` taşır. İzinli operation geçişleri:

| Kaynak | Hedef / gerekçe |
|---|---|
| admitted | submitted; veya gönderim öncesi kesin ret/yerel vazgeçmede failed/cancelled |
| submitted | running; senkron doğrulanmış sonuçla succeeded/failed/cancelled; belirsizlikte unknown |
| running | succeeded/failed/cancelled; belirsizlikte unknown |
| unknown | Aynı işin trusted kanıtıyla submitted/running/succeeded/failed/cancelled; belirsiz gözlemde unknown |
| succeeded/failed/cancelled | Değişmez; yeni deneme veya yeniden açılma yok |

Execution/delivery ayrı enum'lardır; bütün geçerli çiftler tek saf reducer ile operations referansındaki tabloya eşlenir. Succeeded+pending **running**, succeeded+unknown **unknown**, succeeded+complete/not_required **succeeded**, succeeded+failed **failed** olur; çift aynı anda iki toplam duruma eşlenmez. Not_started'ın admitted/failed/cancelled ayrımı yalnız kesin yerel terminal nedeni ile yapılır. Kalıcı OperationOutcome yalnız terminal sonuçtur; nonterminal'de null, güncel eksenler summary/attempt'tedir. Teslim gereksinimi trusted saved plan görev/effect politikasından admission'da sabitlenir; caller veya port not_required diyerek gereği düşüremez. P01-4 artefakt adaptörü teslim etmez.

Reconciliation yalnız composition'ın seçtiği trusted portun tipli observation'ını kabul eder; public kullanıcıdan provider JSON'u/verified flag almaz. Operation'ın saved hizmet/hedef/account/project ve kalıcı run ID veya kesin correlation bağı eşleşmelidir; güncel read yetkisi ayrıca doğrulanır. Eski plan/onay expiry'si geçmiş işi okumaya tek başına engel değildir ve yeni execution yetkisi vermez. Uzak okuma portu `start/cancel/fetch` çağırmaz.

`not_found`, timeout, 401/403, iptal isteği kabulü, yerel watcher kapanması ve benzer isim/zamandaki iş terminal kanıt değildir. Yanlış/çelişkili bağ veya yetersiz observation unknown'u korur. Provider run ID ilk güvenilir bağlamadan sonra değiştirilemez. Ham durum/exit code yalnız bounded alanlarda saklanır; ham body, log, argv, env, prompt, signed URL veya secret yazılmaz. Sonuç, görev/teslim durumlarının küçük tipli özeti olur; tam artefakt/metric portu değildir.

### Kaynak ve tarihçe sınırı

| Sınır | Seçim |
|---|---|
| Store | En çok 1.024 operation; her biri mevcut en çok 1.024 plandan birini bağlar |
| Operation | En çok 16 attempt ve 256 sıralı business geçişi; son bir geçiş slotu terminal sonuç için ayrılır |
| Kalıcı payload | Operation kabul metadata'sı ≤8 KiB; attempt ≤4 KiB; sonuç ≤4 KiB; geçiş ≤1 KiB UTF-8 |
| Public show | En çok 256 KiB encoded data; ham geçmiş yerine plan + attempt'ler + güncel outcome; geçişler public export edilmez |
| İşlem | Mevcut 1 s busy / 5 s store ve input/current validation dahil 30 s coordinator deadline'ı; kontrol noktalarında uygulanır |

DB alt adımları aynı kalan toplam bütçeyi kullanır; her SQL/port çağrısında süre sıfırlanmaz. Port deadline'ı `min(call_remaining, lease_remaining) − 5 s` olur; pozitif pay yoksa port çağrılmaz. Sonuç yazımı için 5 s pay ayrılır, arka plan heartbeat/thread/daemon eklenmez. Cooperative port deadline'ı izlemelidir; bloke olmuş sistem I/O'su, fsync, scheduler veya uyumsuz port Python'da zorla kesilebilir varsayılmaz. Kontrol döndüğünde deadline/lease tekrar denetlenir; geç sonuç yetkiyi diriltmez ve unknown olabilir. Bunlar katı fiziksel duvar saati garantisi değil, kontrol deadline'ı ve referans ortamda ölçülebilir pozitif kabul hedefidir. Uzak job ömrü/planın 300 s geçerliliğiyle karıştırılmaz; gerçek backend deadline P01-5/P03 tüketicisinde tamamlanır.

Admission/dispatch için gereken normal attempt/geçiş/sonuç slotları porttan önce ayrılır. Heartbeat, acquire/recovery ownership ve reset invalidation **normal business geçiş slotu tüketmez**; operation başına tek bounded güncel kontrol kaydı, fence ve semantic revision ile izlenir. Önceki kontrol özetleri sınırsız append edilmez; eski normal event'ler korunur. 255 normal slot dolunca yeni dispatch/normal business geçişi capacity hatasıdır, fakat recovery takeover ve read-only reconcile portu çalışabilir. Nonterminal observation için yeni slot yoksa güncel recovery marker unknown/capacity_exceeded olarak kalır; terminal kanıtı **yeni yetkili recovery sahibi de** ayrılmış 256. slota yazabilir. Latch boş orphan cleanup veya reset cancellation da son terminal slotunu kullanır. Armed reset yalnız kontrol karantinası oluşturur; kota doluluğu reset'i kilitlemez. Terminal satır immutable'dır, yeni attempt gerektirmez. Kotalar transaction içinde uygulanır ve full validation'da denetlenir.

Operation/attempt/sonuç/anti-duplicate geçmişi otomatik veya public forget ile silinmez. **1.024 lifetime operation bütün 1.024 plan slotunu bağladıysa terminal işler dahil yeni plan hazırlanamaz**; P01-4 sınırsız üretim store'u değildir. Bu bilinçli kaynak sınırı user docs ve kapasite hatasında anlatılır; mevcut history/reset/recovery okunabilir ve çalışır. Yeni state dizini eski unknown işi tekrar gönderme çözümü değildir. Seçili plan forget'te yalnız doğrulanmış operation FK bağı plan_in_use; yabancı/bozuk FK state_invalid olur. Arşiv/tombstone/retention sonraki gerçek tüketici kararıdır.

### Reset, restore ve public jobs

Reset önizlemesi v3; operation/attempt/nonterminal/unknown sayıları ve ID/semantic revision/status/sonuç/owner-fence fingerprint'ini onaya bağlar. Heartbeat-only expiry/zaman değişimi onayı bozmaz; ownership/business/result değişimi bozar. Preview sayıları kayıtlı durumlardan hesaplanır, canlı provider durumu değildir.

Reset tek transaction'da yeni epoch/K ile owner tuple'larını temizler; eski normal event/plan/approval snapshot/terminal sonuç korunur. Latch olmayan aktif iş cancelled (identity_reset), latch olan aktif iş slot gerektirmeyen recovery karantinasıyla unknown olur; terminal sonuç değişmez. Kontrol revision/clock anomaly flag'i ve preview fingerprint'i güncellenir. Geç gelen eski sonuç CAS'ten geçemez. Dispatch bağı silinmez; önceden arm edilmiş dış çağrının geri çekildiği iddia edilmez. Future UTC veya 255 normal slot reset'i kilitlemez. Preview v3 tam wire/fingerprint'i local-state referansında tanımlıdır.

Operation-capable runtime'da **restore/recover kapalı kalır**: operation sayısı sıfır, snapshot eski/boş, hedef eksik veya eski intent/stage/live tamamlanmış olsa dahi `state_restore_unsupported`. Runtime allowlist genişletilmez; bu yeni yasak değil ADR-0012/0014'ün mevcut sınırıdır. Eski desteklenen runtime'ın yarım bakım işi o runtime'da tamamlanmadan yükseltilmez; otomatik intent silme/stage yükseltme kaçışı yoktur. Migration snapshot'ları inceleme için korunur, yeni runtime'da restore vaadi verilmez.

Public `jobs list/show` ve Python karşılıkları [operations referansındaki](../reference/operations.md) bounded salt sorgudur. Genel Result v1 `status=completed`, `operation_id=null` kalır; işin durumu data içindedir. Unknown/failed işi başarıyla okumak exit 0'dır. Normal prepare job yaratmaz; ağ/config/env/input içeriği sorgulanmaz. Açık store erişimi gerektiğinde mevcut migration/SQLite hot-journal recovery yapabilir; fiziksel olarak hiç DB yazılmaz garantisi değildir.

### Kontrollü hatalar

OperationError, YorungeError'ın kapalı alt sınıfıdır; genel eski hata/Result zarfı değiştirilmez. Yeni kodların kesin tetik/exit ve details şekli operations referansındadır; public tablo uygulama adımında CLI referansına taşınır. İş biliniyorsa üst operation_id canonical UUID'dir. Details tam `{reason_code: ErrorCode, capacity_kind: store|attempt|transition|null}`; neden provider metni veya OperationReason değildir. Retryable=false. Dispatch öncesi kontrollü hata mevcut exit 2/4 anlamını korur; arm sonrası belirsiz dış etki operation_uncertain/5'tir. State I/O/bütçe/şema/platform eşlemeleri mevcut karardır; ham traceback/path/secret sızmaz.

## Alternatifler

- Yalnız lease süresine güvenip tekrar göndermek, eski sahibin geç devam etmesinde çift etki yaratır; reddedildi.
- Provider idempotency varmış gibi start replay yapmak henüz kanıtlanmamış dış sözleşmeye dayanır; P01-4'e alınmadı.
- Public run veya demo backend açmak mevcut blocked producer sınırını aşar; sentetik fixture yalnız testtedir.
- Persist edilmiş monotonic değeri reboot kimliği saymak ve WAL'a performans gerekçesi olmadan geçmek seçilmedi.
- Otomatik history silmek anti-duplicate kanıtını kaybettirir; bounded kontrollü ret seçildi.

## Sonuçlar ve kabul

Güvenli tercih, gerçekten gönderilmemiş işin de crash sonrası unknown kalabilmesidir. Operatörün belirsizliği otomatik tekrar gönderime çevrilmez; P01-4 gerçek backend sağlamadığı için public jobs çoğu yeni kurulumda boş olacaktır. Terminal sonuç yalnız trusted kanıtla oluşur. Reset/revoke'un önceden arm edilmiş uzak etkiyi durduramaması ve dolu store'un ret davranışı kullanıcıya açık anlatılır.

Kabul iki iş kartında tutulur: [P01-4b](../roadmap/tasks/p01-4b-operation-coordination.md), [P01-4c](../roadmap/tasks/p01-4c-local-jobs.md). Ayrı süreçte tek gözlenebilir sentetik etki, bütün crash sınırları, geç eski sahip, saat/epoch, revoke/reset/forget yarışları, kanıt/teslim negatifleri, gerçek operation şemasıyla bakım retleri ve yoğun kaynak ölçümleri zorunludur. Her uygulama adımı commit ve iki fresh review turuyla kapanır. Süreç öldürme fiziksel güç kesintisi veya canlı EVREN kabulü değildir.

Resmî dayanaklar (erişim 2026-10-28): [SQLite transaction/snapshot ve hata davranışı](https://www.sqlite.org/lang_transaction.html), [SQLite atomic commit/donanım sınırı](https://www.sqlite.org/atomiccommit.html), [Python 3.11 monotonic saati](https://docs.python.org/3.11/library/time.html#time.monotonic), [Python sqlite3 transaction ve bağlantı yaşam döngüsü](https://docs.python.org/3.11/library/sqlite3.html#transaction-control). SQLite'ın yerel atomikliği dış etkiyle atomik commit sağlamaz; tek gönderim protokolü bu proje için seçilen tasarımdır.
