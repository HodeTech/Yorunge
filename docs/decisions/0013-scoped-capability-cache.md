# ADR-0013: Kapsamlı capability cache, kanıt ve tazelik

**Durum:** Accepted — 2026-10-27 kullanıcı onayıyla benimsendi; uygulama/kabul ayrı kaydedilir. **Tarih:** 2026-10-27. **İş:** P01-3a. [Ön inceleme](../research/p01-3-readiness-review.md), [teslim planı](../roadmap/p01-3-delivery-plan.md).

## Bağlam

[ADR-0005](0005-capabilities-and-contracts.md) dört destek durumunu ve kapsam/kanıt/zaman bağını kabul eder; cache yenileme ve eski kanıt davranışını açık bırakır. P01-2 artık kalıcı credential kimliği/nesli sağlar. Bu gözlem uzak yetki kanıtı değildir. Bugünkü `Scope`, `Capability` ve `Plan` yalnız offline v1 alt kümesini kabul eder; bunları genişletmek eski dosya ve digest anlamını değiştirebilir.

Bu öneri SQLite, HMAC, hedef normalleştirme veya dosya dayanıklılığı seçimini yeniden açmaz. [ADR-0011](0011-state-foundation-and-migrations.md), [ADR-0012](0012-credential-identity-and-change-detection.md) ve [binding v1](../reference/credential-binding-v1.md) geçerlidir.

## Önerilen karar

### Ayrı kayıt ve tam kapsam

Yeni `CapabilityRecord` biçimi `schema_version=2` olur; mevcut offline v1 modelleri/çıktısı/digest'i değişmez. Yeni kayıtta `capability_id`, `task`, `scope`, dört durumlu `support`, sınırlı reason/message, tipli constraints, kanıtlar, `checked_at` ve `expires_at` bulunur. Bilinmeyen alan/sürüm, duplicate JSON key, NaN/Infinity ve yanlış tür reddedilir.

Yeni scope şu bağların tamamını taşır:

| Bağ | Anlam |
|---|---|
| `store_id`, `identity_epoch`, `clock_generation` | Yerel store, etkin kimlik alanı ve kalıcı saat geçersizleştirme nesli; local-only kayıtlar da bağlıdır |
| Hizmet/hedef | `service_id`, `service_origin`, `api_base_path`; uzak hedef binding v1 ile karşılaştırılır |
| Hesap/proje | Seçilen `account_id`, `project_id`; seçim tek başına doğrulanmış uzak kimlik değildir |
| Credential | Opak `credential_id`, pozitif `credential_revision`; referans adı, tag veya sır yoktur |
| `authorization_scope` | Doğrulanmış global izinler ve kaynak başına izin kayıtları; bilinmiyorsa null |
| Model | Kaynak/kimlik, seçilmiş revision ve varsa doğrulanmış içerik digest'i; bilinmeyen bağ null |
| Araç | Kimlik, doğrulanmış sürüm, executable ve environment digest'leri; yoksa null |
| Execution | Backend, doğrulanmış runtime kimliği/sürümü; bilinmeyen bağ null |

Kapalı alan/tür/nullability, alt nesne, Unicode/sıralama, toplam limit ve local/remote değişmezlerinin **tek normatif kaynağı** bağlı [CapabilityScopeV2 wire sözleşmesidir](../reference/capability-scope-v2.md). Bu belge de aynı kullanıcı onayıyla benimsenmiştir; uygulamaya bırakılmış serbest `dict` veya producer'a göre değişen alan adları yoktur.

Null **wildcard değildir**; yalnız aynı null alanla eşleşir ve doğrulama yerine geçmez. İzin ve kaynak listeleri sınırlı, sıralı ve tekrarsızdır; kaynak kaydı namespace/type/id ile kendi izinlerini birlikte taşır. Boş doğrulanmış izin kümesi ile bilinmeyen izin ayrıdır. Gerekli olmayan bağ null olabilir; görev için gerekli fakat bilinmeyen bağ execution desteğini engeller. Adapter hangi bağların gerekli olduğunu kendi tipli görev sözleşmesinde bildirir; caller bu gereksinimleri azaltamaz.

Cache anahtarı `capability_id`, `task` ve scope'un **tamamının** kanonik JSON baytlarının SHA-256'sıdır. Kodlama `sort_keys=True`, `separators=(",", ":")`, `ensure_ascii=True`, `allow_nan=False`, UTF-8; BOM/newline yoktur. Kayıtlı tam anahtar baytları da okunurken karşılaştırılır; digest tek başına eşitlik veya güven kanıtı değildir. Profil adı, env adı veya ham secret/hash anahtar değildir. Kaynak/politika sürümü değişmiş kayıt yeni kararın yerine kullanılamaz.

### Kanıtın yetkisi

Kanıt türleri `local_policy`, `documentation`, `synthetic_test`, `live_account`, `not_verified` olarak ayrılır; her kanıt producer kimliği/sürümü ve sınırlı provenance taşır. Genel şema/kılavuz hesabın erişimini; sentetik test gerçek EVREN'i; yerel credential gözlemi uzak auth/izni kanıtlamaz. `supported` yalnız capability'nin iddia ettiği düzeyde yeterli kanıtla üretilebilir. Çelişkili güncel kanıtlar görünür gerekçeyle `unknown` olur; son yazan kazanır politikası uygulanmaz. 401/403 tek başına global `unsupported` veya kesin `requires_access` değildir.

Uygulama tipli bir producer portunu çağırır; üretici seçimi composition katmanındadır. Public CLI/Python yüzeyi producer, kanıt JSON'u, `supported`, yetki listesi veya doğrulanmışlık bayrağı kabul ederek kayıt yetkilendirmez. Python nesnesinin tipli olması provenance kanıtı değildir. Aynı process/UID içindeki keyfî Python koduna karşı sandbox veya imza güvencesi iddia edilmez.

P01-3 ürün üreticisi yalnız mevcut yerel politika ve `not_verified` sonuçlarını verir. Uzak discovery/araç adaptörü yokken `unknown`/mevcut uyumsuzluk sonucu korunur. Pozitif hesap ve yürütme senaryoları yalnız test fixture producer'larında doğrulanır; ürün görev listesine test backend'i eklenmez. Gerçek hesap üreticileri P02/P03, HTTP taşıması P01-5 kapsamındadır.

### Discovery yapmadan kayıt bulma

`--cached` etkin lookup için aynı çağrının bağımsız trusted resolver'ının sağlayabildiği kapsamı kullanır; DB kaydı kendi authorization scope'unu doğrulayamaz. Resolver bu çağrıda güncel kapsamı doğrulayamıyorsa `authorization_scope=null` ile **tam eşitlik** aranır. Persist edilmiş izinler, önceki process'in bilgisi veya caller parametresi bu null'ı doldurmaz. P01-3'te uzak resolver yoktur; cache içindeki eski `live_account/supported` satırı tek başına güncel hesap desteği olamaz.

Etkin exact lookup yoksa tarihsel gösterim için ayrı, sınırlı aday sorgusu yapılabilir: yalnız authorization_scope alanı çıkarılmış anahtar projeksiyonu ile, diğer **bütün** scope alanları tam eşleşen en çok dört kayıt seçilir (`checked_at` azalan, tam cache key artan). Bu projection yalnız `historical_candidates` içindir; etkin key/eşitlik kuralını değiştirmez. Adaydaki izinler gösterilir fakat effective support `unknown`, neden `authorization_scope_unverified` olur. Diğer bağlardan biri de bilinmiyorsa onun null'ı dolu değerle aday eşleşmesi sağlamaz. Satırın kendi TTL'sinin dolmamış olması bu bağımsız doğrulama eksikliğini gidermez.

Restart sonrası scope bilinmiyorsa miss/unknown veya tarihsel aday döner. Güncel kapsam bağımsız doğrulanmışsa yalnız o tam scope'un kaydı etkinlik adayıdır; değişmiş kapsam eski key'i kullanamaz. `--cached` discovery başlatmaz; çözüm için gereken dış yenileme ayrı açık `--refresh` yoludur, gerçek üreticisi sonraki fazda gelir. Böylece eski scope'u cache'ten okuyup yeniden kendisiyle eşleştirme yoluyla yetki kurulmaz.

### Tazelik ve saat

Yeni zamanlar kanonik UTC, altı basamak mikrosaniye ve `Z` ile yazılır. Taze koşulu `checked_at <= now < expires_at` olur; tam expiry anı stale'dir. Policy üst sınırları `supported`/`unsupported` için 300, `requires_access` için 60, `unknown` için 30 saniyedir. Producer daha kısa süre seçebilir; uzatamaz. Birleşik kayıtta en erken expiry kullanılır. Bunlar hizmet garantisi değil, ilk Yörünge politikasıdır.

Enjekte edilen saat UTC kayıt ile süreç içi monotonic deadline/yaş denetimini ayırır. Açık stateful cache/plan kullanımında kısa transaction, epoch'a bağlı kalıcı UTC high-watermark'ı ileri taşır. Clock metadata ayrıca pozitif signed-64 `clock_generation` ve `anomaly_active` taşır. `now` önceki watermark'tan geriye ilk düştüğünde aynı transaction generation'ı bir artırır ve anomaly işaretini kalıcılaştırır. Aynı geri-saat olayı sürdükçe generation yeniden artırılmaz; saat watermark'a yetişince anomaly kapanır. Taşma kontrollü hata olur, sayaç sarmaz veya otomatik reset olmaz.

Cache, plan ve onay etkinliği **güncel clock generation** ile de eşleşmelidir. Anomali öncesi kayıtlar saat yetiştikten veya süreç yeniden açıldıktan sonra canlanmaz. Yeni refresh de anomaly sürerken kritik geçerlilik vermez. İleri sıçrayıp süresi bitmiş kayıtların saat geri dönünce canlanması aynı kapıyla engellenir. Gelecekteki veya bozuk producer zamanı kabul edilmez. Clock generation'ın ilerletilmesi, kullanım senaryosunun sonraki hata/ret nedeniyle rollback ettiği bir transaction içinde kaybolamaz; ret öncesi ayrı kısa kalıcı saat denetimi tamamlanır. Son cache/plan/onay commit'i bu neslin değişmediğini tekrar doğrular.

Güvenilir dış saat yokken gözlenmeyen saat geri dönüşünü veya DB+K+clock metadata'sının birlikte eskiye alınmasını tam saptama iddiası yoktur. Persist edilmiş monotonic sayaç restart otoritesi olarak kullanılmaz. Cache tazeliği **yan etki yetkisi değildir**: kritik execution/approval geçerliliği [ADR-0014](0014-execution-plan-validity-and-approval.md) uyarınca güncel trusted producer doğrulaması ister.

Normal stateful sorgu miss/stale/clock-anomaly durumunu açık gösterir; eski `supported` yalnız tarihsel kayıt olarak sunulur, etkin karar `unknown` olur. `--refresh` hatası eski başarıyı güncellemez veya geçerli kılmaz; kontrollü hata ve güvenli önceki kayıt korunur. `--cached` discovery yapmaz. Hiçbir yol sınırsız/otomatik refresh döngüsü açmaz.

### Transaction ve saklama

Cache yazımı/etkin okuması son kısa transaction'da store/epoch/clock generation ve kullanılan bütün credential ID/revision bağlarını tekrar denetler. Arada gözlem değişmişse `state_changed` olur; eski snapshot tekrar observe edilmez, env ikinci kez okunmaz ve otomatik retry yoktur. Ağ/hash işlemi SQL write transaction'ı dışında kalır. Açık cache kullanımının toplam bütçesi 5 saniye, lock/busy beklemesi en çok 1 saniyedir; disk I/O için katı duvar saati garantisi iddia edilmez.

**Son süre kapısı:** SQL kilidi alındıktan sonra ve etkin karar/yazım kesinleşmeden hemen önce UTC ve monotonic zaman yeniden örneklenir. Her gerekli kanıt ve kaydın `checked_at <= now < expires_at` koşulu, toplam deadline, etkin clock generation/anomaly ve bütün bağlar birlikte doğrulanır. Eski örnek zaman veya aynı generation yeterli değildir. Kilit/producer bekleyişinde tam expiry'ye ulaşılmışsa kayıt etkin sonuç vermez; stale tarihsel gösterilebilir. Producer'ın özgün zaman/expiry'si yeni örnekle ileri damgalanmaz. Son örnekte anomali görülürse business yazımı yapılmaz; clock invalidation ret/rollback'ten bağımsız kalıcılaşır.

Geçerlilik denetimi bir zaman noktasına aittir; çıktı kontrol zamanını ve `valid_until` sınırını taşır. Commit/çıktı hazırlığı sırasında süre geçtiği ayrıca gözlenirse taze/etkin karar sunulmaz. Fsync'in ne kadar süreceği veya sonraki caller anı için süreyi durdurma garantisi yoktur; sonraki tüketici kendi güncel süre kapısını uygular.

### Eşzamanlı refresh ve çelişki

Refresh, producer çağrısından önce aynı tam key'in mevcut kayıt sürümünü okur; yokluk da snapshot token'ına dahildir. Token store/epoch içinde monoton ilerleyen cache mutation sürümünden gelir; silme/eviction/yeniden ekleme eski sürümü tekrar kullanmaz. Taşma kontrollü ret, otomatik reset yoktur. Producer/network SQL transaction'ı dışında çalışır.

Son `BEGIN IMMEDIATE` içinde güncel kayıt, token ve taze kanıtlar tekrar okunur; süre/bağ kapıları önce uygulanır. Token aynıysa yeni tam producer snapshot'ı yalnız **kendi producer kimliği/sürümüne** ait eski gözlemleri yenileyebilir; başka producer'ın taze kanıtını silemez. Token farklıysa kör overwrite veya producer retry yoktur: güncel ve gelen taze gözlemler aynı transaction'da deterministik birleştirilir. Aynı producer'dan eşzamanlı farklı sonuçlar da korunur ve çelişki `unknown` olur. Sonraki, bu çelişki sürümünü görerek başlamış yeni tam snapshot yalnız kendi producer kanıtını yenileyebilir.

Aynı producer/sürüm ve aynı semantik karar/constraints/provenance için eşdeğer gözlemler tekilleştirilir; en yeni gerçek producer gözlemi tutulur, eşit zamanda kanonik bayt sırası tie-break'tir. Farklı semantik kararlar tekilleştirilmez. Etkin karar birleştirilmiş kanıtlardan yeniden türetilir; özgün süreler korunur, en erken expiry ve unknown için en çok 30 saniye uygulanır. Idempotent erken dönüş dahi son süre/bağ kapısını atlayamaz.

**Karar TTL'si kanıt saklama süresi değildir.** Normal (overflow olmayan) çelişkide aggregate unknown 30 saniyede stale olsa da her kanıt kendi özgün expiry'sine kadar merge girdisi olarak tutulur. Aggregate `expires_at` tek başına taze karşı kanıtı sildirmez. Temizlik yalnız gerçekten süresi geçmiş bireysel kanıtları budar; cache-only okuma bu budamayı yeni producer kontrolü gibi gösterip aggregate TTL'yi uzatamaz. Çelişki taşıyan satır, karşı kanıtlar bireysel olarak expire olmadan veya yukarıdaki exact-token kendi-producer yenilemesiyle çözülmeden quota eviction'a aday değildir. Yer yetmiyorsa yeni yazım kontrollü reddedilir; mevcut çelişki kaybedilip supported dönülmez. Örneğin T+300'e kadar taze iki karşı kanıtın T+30'daki unknown TTL'si veya erken kota baskısı, T+31'de tek producer'ın eski karşı kanıtı unutmasını sağlamaz.

Birleşim sekiz kanıt/32 KiB sınırına sığmıyorsa kanıtı sessiz kırpmak veya önceki supported'ı bırakmak yerine bounded `evidence_overflow` blocker yazılır: effective karar unknown, ayrıca kaybolan kanıtların en geç **özgün** expiry'sine kadar `conflict_until` tutulur. Bu tarih unknown kaydının TTL'sini uzatmaz; TTL bittikten sonra dahi blocker yeni pozitif kararı engeller. Tek producer refresh'i bu marker'ı erken silemez. Aynı key'deki blocker güncellenirken tarih geriye çekilmez; aynı store/epoch/generation içinde bu tarihten önce quota eviction ile atılmaz. Marker da kayıt/boyut kotasına dahildir; kota güvenli tutulamıyorsa yeni refresh kontrollü reddedilir ve etkin başarı dönmez. Epoch/generation değişmiş blocker güvenli biçimde emekliye ayrılabilir. Normal taze çelişkide iki provenance korunur; overflow'da eksik ayrıntı açıkça etiketlenir, tam kanıt korunmuş iddiası yoktur.

Bir kanonik cache kaydı en çok 32 KiB, en çok sekiz kanıt ve wire sözleşmesindeki toplam 128 izin/kaynak öğesi taşır. Etkin credential binding/nesil başına 128, store genelinde 1.024 kayıt sınırı vardır; credential'sız local kayıtlar epoch'a bağlı tek kota grubudur. Upsert transaction'ı önce eski epoch/nesil/clock-generation kayıtlarını, sonra bireysel proof expiry'sini temizler; korunmuş çelişki/blocker dışındaki kota adaylarını en eski doğrulama zamanı/anahtar sırasıyla çıkarır. Hiç aday yoksa kontrollü kota reddi vardır; pinlenmiş çelişki gizlice silinmez. Eski nesil kayıtları aktif cache'te birikmez. Bu yalnız türetilmiş cache'e uygulanır; identity geçmişi, plan, onay, operation veya backup silinmez. Sınır mantıksal payload/satır sınırıdır; SQLite dosyasını küçültmek için otomatik VACUUM yapılmaz.

Gerçek tüketiciyle yeni immutable SQL migration eklenir; eski migration/checksum değiştirilmez. Şema sürümüne duyarlı full validation, backup ve sıcak tek-kayıt doğrulaması yeni payload/değişmezleri kapsar. Reset/restore yeni epoch kurunca cache etkinliğini yitirir. Restore/recover genişlemesinin sınırı ADR-0014'tedir.

### Public yüzey ve uyumluluk

Mevcut `capabilities` varsayılanı ve `api.inspect_capabilities` offline/stateless kalır. Açık `capabilities --cached|--refresh [--state-dir PATH]` yeni cache sorgusunu seçer; seçenekler birbirini dışlar. Python karşılığı ayrı `api.query_capabilities(..., refresh=False, state_dir=None)` kullanım senaryosudur. Açık yol private state/clock metadata yazabilir, uzak görevde yalnız seçili hizmet env'sini bir kez gözleyebilir; uzak discovery bu sürümde yoktur. `--refresh` ağ bağlantısı varmış gibi anlatılmaz.

JSON sonucu cache hit/miss, freshness, etkin karar ve varsa tarihsel kaydı ayırır. Sorgunun `unknown` dönmesi başarılı sorgu olabilir; malformed istek/state/binding çatışması kontrollü hatadır. Yeni public alanların ayrıntısı onay sonrası capability/CLI referansında tek yerde sabitlenir; eski offline JSON'a bu alanlar eklenmez.

## Değerlendirilen alternatifler

- **v1'i yerinde genişletmek:** Eski offline dosyanın anlamını ve yeniden hesaplama kuralını bulanıklaştırır; ayrı v2 seçildi.
- **Caller JSON'u veya doğrudan cache import:** Kanıt ile iddiayı karıştırır; production admission yolu değildir.
- **TTL'siz/sınırsız cache veya revision'sız anahtar:** Eski yetki ve sınırsız büyüme riski; reddedildi.
- **Her komutta bütün endpointleri taramak:** P01 kapsamını ve kaynak bütçesini aşar. Açık, görev kapsamlı producer çağrısı seçildi.
- **Sadece UTC veya sadece monotonic:** İlki gözlenen saat geri dönüşünde kayıt canlandırabilir; ikincisi restart için güvenilir kalıcı zaman değildir. Sınırlı birleşik yaklaşım ve kritik yeniden doğrulama seçildi.

## Sonuçlar

Onay; ayrı v2 kayıt, kaynak güven sınırı, sayısal cache/TTL politikası ve açık stateful sorguyu kapsar. Canlı hesap desteği, yeni bağımlılık veya yan etki yetkisi vermez. Ürün kabulü [P01-3a kartında](../roadmap/tasks/p01-3a-scoped-capability-cache.md); bu öneri kabul/test kanıtı değildir.
