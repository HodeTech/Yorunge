# ADR-0016: Kalıcı operation kabulü, tek gönderim ve sahiplik

**Durum:** Proposed — kullanıcı onayı bekleniyor; ürün kodu uygulanmadı. **Tarih:** 2026-10-28. **İş:** P01-4b/4c. [Ön inceleme](../research/p01-4-readiness-review.md), [teslim planı](../roadmap/p01-4-delivery-plan.md), [önerilen wire](../reference/operations.md).

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
- Son kısa `BEGIN IMMEDIATE` transaction'ında planın sabit baytları, güncel etkin approval, store/epoch/clock generation, registry revision ve bütün validity aralıkları tekrar denetlenir; operation + ilk attempt + ilk lease + geçiş kaydı birlikte yazılır. Ağ/uzun hash transaction dışında kalır.
- Mevcut operation aynı plan için tekrar admission'da yalnız bulunur; yeni attempt, lease veya gönderim bileti üretilmez. İki yarışmacı tek kayda yakınsar. Kayıt ID'sini bilmek execution yetkisi değildir.
- Kabul/sonuç commit'i belirsizse aynı kayıt incelenir; otomatik yeni operation/admission/start yoktur. Commit edilmiş kabulün son süre kontrolü başarısızsa ID hata ayrıntısında korunur, dış port çağrılmaz.

### Attempt ve tek kullanımlık gönderim sınırı

Attempt **bir execution başlatma adayıdır**; heartbeat veya reconcile çağrısı değildir. İlk attempt `claimed` olur. Gönderim sınırına gelmemiş lease devrinde eski attempt `abandoned`, yeni attempt sıradaki numarayla `claimed` olabilir. Numara operation içinde 1'den artar; terk edilen attempt gönderilmiş sayılmaz. Gönderim sınırından sonra yeni attempt yoktur; yeni sahip aynı attempt'i yalnız uzlaştırır.

1. Gönderimden hemen önce aynı çağrının güncel execution validation/onay/credential snapshot'ı yeniden denetlenir. Final transaction current owner/fence, lease/epoch/generation ve süreleri kontrol eder.
2. Operation'ın bir kez atanabilen `dispatch_attempt_id` bağı ve attempt `submitted` durumu **dış çağrıdan önce** birlikte commit edilir. `submitted`, sağlayıcının kabul ettiğini değil, gönderimin yapılmış olabileceğini anlatır. Bu bağ hiçbir reset, lease devri, expiry, hata veya yeni onayla temizlenmez.
3. Yalnız bu başarılı commit'in ilk sahibi için composition içinde tüketilen, serialize/yeniden yükleme yüzeyi olmayan tek kullanımlık izin oluşur. Repository'den sonradan permit üretilemez. Coordinator portun `start` metodunu en çok bir kez çağırır; otomatik retry/idempotency replay yoktur. Correlation anahtarı porttan önce kalıcılaştırılır; sağlayıcı desteği iddia edilmez.
4. Commit sonrası son UTC/monotonic/ownership kontrolü başarısızsa port çağrılmaz. Hâlâ yetkili CAS mümkünse iş unknown'a taşınır; lease/owner/generation kaybedilmişse eski süreç hiçbir business mutasyonu yapmaz, son atomik submitted/running korunur ve sonraki yetkili takeover unknown'a taşır. Bu son kontrol ile dış çağrı arasındaki scheduler duraklaması tamamen kapatılamaz. Lease kaybı/reset/revoke önceden alınmış izni dış sistemden geri çekmez; başka sahip **ikinci** `start` yapamaz. Uzak exactly-once veya tam iptal garantisi verilmez.
5. Port başladıktan sonraki timeout, kesinti, bozuk/eksik yanıt veya sonuç yazma belirsizliği `unknown` olarak ele alınır. Kalıcılaştırma da başarısızsa son atomik `submitted/running` kaydı korunur; takeover bunu unknown'a taşır. Bellekteki başarı kalıcı başarı diye sunulmaz.

Onay/yetki için linearization noktası gönderim niyetinin commit'idir. Önceki revoke/reset/kimlik değişimi gönderimi engeller; sonraki değişim yeni izinleri engeller, başlamış olabilecek işi iptal ettiğini söylemez. Bu sınır yarış testleri ve kullanıcı bakım metninde açık tutulur.

### Lease, fencing ve saat

Lease TTL **30 saniye**; yenileme aynı owner/fence ile `now < lease_expires_at` iken en çok `now + 30 s`'ye yapılır. Owner rastgele UUIDv4; fence pozitif signed-64 int, her acquire/takeover'da +1, heartbeat'te sabittir. Mevcut sahibin bütün business yazıları operation ID + owner + fence + ownership epoch/generation CAS koşulu ve geçerli lease gerektirir. Admission/acquire/takeover ve açık exclusive bakım bu mevcut-owner kuralının ayrı transaction sahipleridir; eski token'ı geçerli saymadan ilgili satırın son sürümünü denetleyip atomik değiştirir. Süresi bitmiş token diriltilmez; sayı taşması `operation_fence_exhausted` ile yazmadan reddedilir.

Kalıcı UTC lease aralığı, mevcut ortak durable clock/generation kapısına tabidir; monotonic yalnız çağrı içi süre farkıdır, DB/reboot otoritesi değildir. Etkin lease expiry'leri indeksli global frontier'e ve onun bounded döngü hesabına eklenir. Başka cache/plan çağrısının gözlediği expiry, saat geri dönünce lease'i diriltemez. Clock anomaly business rollback'inden bağımsız kalıcılaşır; eski generation sahibi yazamaz/yenileyemez. İleri sıçrama erken lease kaybına yol açabilir; tek gönderim bağı buna rağmen korunur.

Operation'ın gerçek UTC business zamanı geri yazılmaz. Current UTC ilgili operation'ın son business zamanından küçükse acquisition/renew/reconcile/business yazımı `state_changed` ile reddedilir; ortak clock anomaly kaydı yine kendi kalıcı kapısını kullanır. Reset yeni clock epoch'u açsa da arşiv operation için bu karşılaştırma kalkmaz. Reset preview/apply, değiştireceği nonterminal operation'lardan biri gelecekte görünüyorsa aynı şekilde atomik reddedilir; terminal geçmiş okunabilir ve değişmez. Sonuç olarak yanlış ileri ayardan sonra saati geri düzeltmek, ilgili işin uzlaştırma/reset'ini gerçek UTC son kayıt zamanına yetişene kadar bekletebilir. Gerçek zamanı ileri uydurmak veya eski timestamp'i yeniden yazmak yerine bu açık güvenli ret seçilir.

Lease devri başlamış işi yeniden çalıştırmaz. Gönderim öncesinde güncel plan/onayla yeni aday alınabilir. Gönderim sonrası takeover önce nonterminal kaydı unknown yapar; aynı attempt için yeni owner/fence yalnız read-only reconciliation izni alır. Tarihsel admission epoch'u ile güncel reconciliation ownership epoch'u ayrı tutulur; reset sonrası eski işin sorgulanması mümkün, yeniden gönderimi yasaktır. Terminal işte lease tutulmaz.

### Durumlar, kanıt ve sonuç

Operation durumları `admitted|submitted|running|unknown|succeeded|failed|cancelled`; attempt durumları bunlardan `admitted` yerine `claimed` ve ayrıca `abandoned` taşır. İzinli operation geçişleri:

| Kaynak | Hedef / gerekçe |
|---|---|
| admitted | submitted; veya gönderim öncesi kesin ret/yerel vazgeçmede failed/cancelled |
| submitted | running; senkron doğrulanmış sonuçla succeeded/failed/cancelled; belirsizlikte unknown |
| running | succeeded/failed/cancelled; belirsizlikte unknown |
| unknown | Aynı işin trusted kanıtıyla running/succeeded/failed/cancelled; belirsiz gözlemde unknown |
| succeeded/failed/cancelled | Değişmez; yeni deneme veya yeniden açılma yok |

`execution_status=not_started|submitted|running|unknown|succeeded|failed|cancelled`, `delivery_status=not_required|pending|complete|failed|unknown` ayrı tutulur. Execution succeeded ve delivery pending/unknown iken operation succeeded olamaz; toplam durum running/unknown'dır. Delivery kesin başarısızsa toplam failed olabilir, execution succeeded korunur. Teslim gereksinimi saved planın trusted görev/effect politikasından türetilir; caller veya port `not_required` diyerek gereği düşüremez. P01-4 artefakt indirme/doğrulama adaptörü teslim etmez.

Reconciliation yalnız composition'ın seçtiği trusted portun tipli observation'ını kabul eder; public kullanıcıdan provider JSON'u/verified flag almaz. Operation'ın saved hizmet/hedef/account/project ve kalıcı run ID veya kesin correlation bağı eşleşmelidir; güncel read yetkisi ayrıca doğrulanır. Eski plan/onay expiry'si geçmiş işi okumaya tek başına engel değildir ve yeni execution yetkisi vermez. Uzak okuma portu `start/cancel/fetch` çağırmaz.

`not_found`, timeout, 401/403, iptal isteği kabulü, yerel watcher kapanması ve benzer isim/zamandaki iş terminal kanıt değildir. Yanlış/çelişkili bağ veya yetersiz observation unknown'u korur. Provider run ID ilk güvenilir bağlamadan sonra değiştirilemez. Ham durum/exit code yalnız bounded alanlarda saklanır; ham body, log, argv, env, prompt, signed URL veya secret yazılmaz. Sonuç, görev/teslim durumlarının küçük tipli özeti olur; tam artefakt/metric portu değildir.

### Kaynak ve tarihçe sınırı

| Sınır | Seçim |
|---|---|
| Store | En çok 1.024 operation; her biri mevcut en çok 1.024 plandan birini bağlar |
| Operation | En çok 16 attempt ve 256 sıralı business geçişi; son bir geçiş slotu terminal sonuç için ayrılır |
| Kalıcı payload | Operation kabul metadata'sı ≤8 KiB; attempt ≤4 KiB; sonuç ≤4 KiB; geçiş ≤1 KiB UTF-8 |
| Public show | En çok 256 KiB encoded data; ham geçmiş yerine plan + attempt'ler + güncel outcome; geçişler public export edilmez |
| İşlem | Mevcut 1 s busy / 5 s store bütçesi; input/current validation dahil coordinator çağrısı toplam en çok mevcut 30 s execution bütçesi |

Koordinatörün DB alt adımları aynı kalan toplam bütçeyi kullanır; her SQL çağrısında süre sıfırlanmaz. Dış portun çağrı deadline'ı kalan bütçeyi aşamaz. Bu süreler uzak job ömrü değildir; execution v2'nin 300 s plan geçerliliği job timeout'u yapılmaz. Gerçek backend/iş deadline politikası P01-5/P03'te gerçek tüketicisiyle tamamlanır.

Admission/claim/gönderim için gereken attempt/geçiş/sonuç slotları porttan önce ayrılır. Heartbeat ve aynı observation'ın tekrarı tarihçe satırı eklemez; anlamlı durum/owner/run-ID/sonuç değişimleri sıralı kayda girer. 255 normal geçiş dolunca yeni normal mutasyon ve port çağrısı `operation_capacity_exceeded` ile reddedilir; mevcut geçerli sahibin doğrulanmış terminal sonucu ayrılmış son slota yazılabilir. Bu sınır reset/takeover'ı da kontrollü reddedebilir; dolu geçmiş silinmez. Sonuç satırı güncellemesi yeni attempt slotu gerektirmez. Kotalar SQLite transaction içinde uygulanır ve full validation'da denetlenir.

Operation/attempt/sonuç/anti-duplicate geçmişi otomatik veya public forget ile silinmez. Dolu store güvenli ret ve mevcut jobs okuması sağlar; yeni state dizini eski unknown işi yeniden gönderme çözümü diye önerilmez. Seçili plan forget operation bağı varsa `plan_in_use` verir. İleride arşiv/tombstone/retention tasarımı ayrı gerçek kullanım kararıdır; sınırsız kullanım veya mevcut temizleme komutu iddiası yoktur.

### Reset, restore ve public jobs

Reset önizlemesi v3; operation/attempt/nonterminal/unknown sayıları ve ID/semantic revision/status/sonuç/owner-fence fingerprint'ini onaya bağlar. Heartbeat-only expiry/zaman değişimi onayı bozmaz; ownership/business/result değişimi bozar. Preview sayıları kayıtlı durumlardan hesaplanır, canlı provider durumu değildir.

Reset tek transaction'da yeni epoch/K ile eski sahipliği etkisizleştirir; plan, approval snapshot, attempt, geçiş ve sonuç geçmişi korunur. Gönderim bağı olmayan aktif iş cancelled (`identity_reset`), bağı olan aktif iş unknown olur; terminal sonuç değişmez. Bu değişimler tarihçeye girer ve kota/taşma hatasında reset atomik reddedilir. Geç gelen eski sonuç CAS'ten geçemez. Kalıcı gönderim bağı silinmez; önceden arm edilmiş dış çağrının geri çekildiği iddia edilmez.

Operation-capable runtime'da **restore/recover kapalı kalır**: operation sayısı sıfır, snapshot eski/boş, hedef eksik veya eski intent/stage/live tamamlanmış olsa dahi `state_restore_unsupported`. Runtime allowlist genişletilmez; bu yeni yasak değil ADR-0012/0014'ün mevcut sınırıdır. Eski desteklenen runtime'ın yarım bakım işi o runtime'da tamamlanmadan yükseltilmez; otomatik intent silme/stage yükseltme kaçışı yoktur. Migration snapshot'ları inceleme için korunur, yeni runtime'da restore vaadi verilmez.

Public `jobs list/show` ve Python karşılıkları [operations referansındaki](../reference/operations.md) bounded salt sorgudur. Genel Result v1 `status=completed`, `operation_id=null` kalır; işin durumu data içindedir. Unknown/failed işi başarıyla okumak exit 0'dır. Normal prepare job yaratmaz; ağ/config/env/input içeriği sorgulanmaz. Açık store erişimi gerektiğinde mevcut migration/SQLite hot-journal recovery yapabilir; fiziksel olarak hiç DB yazılmaz garantisi değildir.

### Kontrollü hatalar

Yeni kararlı kodlar `operation_not_found`, `operation_conflict`, `operation_lease_lost`, `operation_fence_exhausted`, `operation_capacity_exceeded`, `plan_in_use` çıkış 2; `operation_uncertain` çıkış 5'tir. Sonuncu yalnız iç yan etkili çağrının gönderim sınırı/sonucu belirsizken kullanılır; jobs okumasını exit 5 yapmaz. İş biliniyorsa hata zarfındaki operation ID korunur; `details` tam `{reason_code}` olur ve bu neden yalnız mevcut+yeni kapalı `ErrorCode` kataloğundandır, provider metni değildir. Tümü retryable=false. Admission sonrası port çağrılmadan oluşan kontrollü hatada bilinen ID korunur, fakat dış etki belirsizliği yoksa exit 2/4 gibi mevcut anlam değiştirilmez. Kalıcı attempt/outcome nedenleri ayrı [OperationReason v1 kataloğudur](../reference/operations.md#durum-ve-neden-invariantları). Foreign key/projection/payload bozukluğu state_invalid, SQLite hata/bütçe/platform eşlemeleri mevcut sözleşmedir; ham traceback/path/secret sızmaz.

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
