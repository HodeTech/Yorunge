# ContextDiscovery v1 sözleşmesi

**Tarih:** 2026-10-31. **Güncellendi:** 2026-11-01. **Durum:** Accepted ADR-0020/0021 ve [ADR-0022](../decisions/0022-observed-platform-consumer-contract.md) kapalı referansı. LLM terms ve Platform’un sınırlı unverified gözlem yolu çalışma dalında uygulanmıştır; iki hizmetin ayrı canlı consumer kabulleri kayıtlıdır. Platform için aşağıdaki strict tüketilen alan/metadata atımı nihai read-only sözleşmedir; ayrı whole-raw katı decoder veya formal auth/principal/pagination kapısı yoktur. Doğrulanmış kimlik/bağ ihtiyacı [P02-R1](../roadmap/tasks/p02-r1-verified-context-binding.md) kapsamındadır. Son kaynak/PR/CI durumu [paket ve hizmet kartlarında](../roadmap/p02-0-delivery-plan.md) tutulur.

## Giriş ve state

CLI `context discover --service evren-platform|evren-llm [--config PATH] [--profile NAME] [--project ID] [--state-dir PATH] [--output text|json|ndjson]`. Bugünkü Python uygulaması `api.discover_context(service_id: ServiceId, *, config: Path|None=None, profile: str|None=None, project: str|None=None, state_dir: Path|None=None) -> Result[ContextDiscovery] | Result[PlatformContextDiscovery]`; literal hizmet çağrıları dar DTO dönüşünü korur. İki-varyant overload ve renderer sözleşmesi [ayrı bölümde](#önerilen-python-api-ve-renderer-tip-sözleşmesi) tanımlıdır ve çalışma dalında uygulanmıştır. ServiceId mevcut iki değerdir; bilinmeyen/bool/tür hatası invalid_request. Ortak CLI seçenekleri önce/sonra geçerlidir; tekil discovery seçeneklerinin yinelenmesi reddedilir. Yeni --account yok; account tercihi yalnız profilden gelir.

LLM’de açık project/--project `invalid_request` ile I/O öncesi reddedilir. Ortak profilin account_id/project_id alanları çağrıyı engellemez ancak LLM selected alanına kopyalanmaz. Platform unverified gözlem yolu ADR-0022 ile nihai dar tüketici sözleşmesidir; gerçek liste/seçili-detail ve son kaynak/review/kurulum/M5/PR CI kabulü tamamdır. P02-0 çalışma dalında verified, PR #12 kullanıcı review/merge bekler; bu durum public validation=unverified sabitini yükseltmez.

Discovery yalnız önceden **açık state init** ile oluşturulmuş güncel store’u açar. Varsayılan mevcut state kökü veya açık CLI/Python state-dir aynı davranır; yok/bozuk/uyumsuz şemada `state_invalid` / exit2, sıfır env/ağ ve yeni dizin/DB/key yoktur. İzin/intent/key/lock/SQLite/platform hataları mevcut kontrollü state sözleşmesini korur. Örtük bootstrap/migration ve default store’a fallback yoktur. Registry/clock gözlemi mevcut store’da yerel yazı yapabilir. Eski context identity/open_store auto-init davranışı bu yeni çağrı tarafından değiştirilmez.

## Kapalı public LLM varyantı

Her alan zorunludur; nullable alan eksik bırakılamaz. Tüm nesneler extra=forbid/strict/frozen, string’ler strict UTF-8; duplicate JSON key/nonfinite/bool sürüm veya sayaç reddedilir. Mevcut Identifier 1–128 ASCII biçimi, UUIDv4 ve positive-int64 türleri aynen kullanılır. Public toplam encoded UTF-8 JSON ≤256 KiB; UTC zaman tam `YYYY-MM-DDTHH:MM:SS.ffffffZ` biçimidir. Yeni user/provider serbest açıklaması veya generic dict yoktur.

| ContextDiscovery tam alanı | LLM v1 tür/değer |
|---|---|
| schema_version | Strict int literal1 |
| service_id | Literal evren-llm |
| profile | Identifier |
| target | Tam service_origin/api_base_path; normalize edilmiş binding v1 hedefi |
| binding | Tam store_id:UUIDv4, identity_epoch:UUIDv4, clock_generation:positive-int64, credential_id:UUIDv4, credential_revision:positive-int64 |
| profile_preference | Tam account_id:Identifier veya null, project_id:Identifier veya null, service_scope:unknown veya not_applicable; alanlardan biri doluysa unknown, ikisi null ise not_applicable |
| selected | Tam account_id:null, project_id:null; Platform tercihleri LLM seçimi olmaz |
| provider | Tam principal_id:null, account_id:null, organization_id:null, project_id:null, identity_status:not_exposed |
| authorization_scope | Yalnız null; bu keşif yazma/çıkarım izni üretmez |
| organizations, projects | Her biri null; sunulmayan liste boş/doğrulanmış liste olmaz |
| list_completeness | Literal not_exposed |
| terms | Tam accepted:strict bool, current_version:strict int 0…2^63−1, is_material:strict bool |
| observed_from, observed_until, validated_at | Kanonik UTC; invocation başlangıcı ≤ endpoint aralığı ≤ observed_until ≤ yerel validated_at |
| observations | JSON array, tam1 TermsEndpointObservation öğesi; Python’da tek öğeli tuple; aşağıdaki kapalı alanlar |
| consistency | Literal not_guaranteed; atomik uzak snapshot veya üyelik garantisi yok |
| validation | Literal unverified; Result completed keşif tamamlanmasıdır, context verified değildir |
| reasons | Sıralı/tekrarsız kapalı neden dizisi; aşağıdaki deterministik kural |

TermsEndpointObservation tam `endpoint_id:llm_terms_status`, `started_at:UTC`, `completed_at:UTC`, `authentication:unknown` taşır. İlk uygulama için key-auth/principal doğrulaması yeterli kanıtla kapanmadığından authentication her hedefte unknown kalır; custom host’tan gelen2xx hiçbir zaman verified olmaz. Pilotun tarihli bir davranış gözlemi bu public alanı kalıcı yetkiye yükseltmez. Gelecekte accepted raw/auth sözleşmesiyle verified varyantı gerekiyorsa hedef/parametre kapsamı ve producer sürümü aynı referans ve testte açık genişletilir; public flag/config/önceki cache kaydı kanıt enjekte edemez.

Neden kümesi her zaman `authorization_not_verified`, `identity_not_exposed`, `remote_snapshot_not_guaranteed` içerir; profile_preference.service_scope=unknown ise `profile_scope_unknown`, terms.accepted=false ise ayrıca **`terms_not_accepted`** eklenir. ASCII sözlük sırasıyla verilir. Böylece terms reddi, auth unknown ve identity not_exposed ayrı gözlenir; accepted=true diğer nedenleri silmez. raw doc_path public sonuçta yer almaz.

Platform varyantı LLM alanlarına provider ID uydurmaz; aşağıdaki ayrı kapalı varyantta selected tercih, reported ID ve unknown provider anlamı tanımlıdır. Doğrulanmış principal/bağ ihtiyacı P02-R1’de ayrıca takip edilir. Mevcut v1 Context/config/Plan/Result/capability scope değiştirilmez.

## Raw terms adaptörü ve hata

Yalnız seçili LLM hedefindeki **GET terms/status** kullanılır; query/body boş, read_only=true. Kimlik header’ı Authorization/Bearer seçilen LLM snapshot’ıdır; Accept-Encoding ve diğer taşıma header’ları ayrı kalır. HTTPX/SDK nesnesi public modele girmez. Session-owned Runner’ın loop/thread/PID/reentrancy kontrolü env/DB/ağdan önce yapılır.

200 gövdesi **tam** accepted:bool, current_version:int64≥0, is_material:bool, doc_path:string alanlarını taşır. doc_path1–2048 Unicode code point, ≤8192 UTF-8 byte, C0/DEL/C1/surrogate yok; URL’ye çevrilmez/takip edilmez ve public’e kopyalanmaz. strict JSON + closed typed decode + P01 literal secret denetimi raw modelde yapılır; bilinmeyen alan/envelope/logical failure/yanlış tür/boş gövde invalid_response. Provider’ın version/tip genişlemesi sessizce kabul edilmez. Tüm2xx’ler aynı gövde şemasına tabidir.

| HTTP / sınır | Discovery sonucu |
|---|---|
| terms/status, auth/me, organizations veya projects list404 | Adaptör HttpStatusFailure.status_code üzerinden invalid_response üretir; generic remote_failed olarak kaçmaz |
| projects/{id}404 | ADR-0020’de kavramsal selection_unverified + selected_project_not_found; [önerilen wire eşlemesi](#seçim-kavramları-ve-kapalı-wire-eşlemesi); “silinmiş/erişim yok” kesin hükmü yok |
| 401/403 | remote_access_denied / exit3; auth/principal doğrulaması veya global unsupported değil |
| 429 | remote_rate_limited / exit1; mevcut bounded read retry politikası geçerli |
| Diğer non2xx | Mevcut HttpStatusFailure kodu; body/path/headers public’e kopyalanmaz |
| Geç/encoding/JSON/type/secret/oversize | Mevcut transport_timeout/invalid_response; eski başarılı observation/cache fallback yok |
| Eksik store / uyumsuz şema | state_invalid / exit2; env/ağ/init yok |
| Credential/epoch/clock-generation değişimi | state_changed / exit2; env yeniden okunmaz, gözlem otomatik tekrarlanmaz |

Discovery, operation ReadPort değildir. Yukarıdaki endpoint eşlemesi generic HTTP taşımasının status politikasını veya operation404→not_found gözlemini değiştirmez. Body bir hata gövdesinden okunup public mesaja dönüştürülmez. Normal parser/API hatası traceback/ham exception zinciri içermez.

## Zaman ve yerel final kapısı

Sonuç **gözlem aralığıdır**, tek uzak atomik snapshot değildir. İstekler seri olabilir; endpoint/sayfa snapshot revision garantisi yoksa consistency=not_guaranteed kalır. Uzak üyelik/sayfa değişimi yerel credential CAS ile saptanmış sayılamaz; birleşik context verified verilmez. Yerel validated_at store/epoch/clock/credential/monotonic final denetiminin zamanıdır; uzak kayıtları aynı zamana yeniden damgalamaz.

Invocation config/env/registry/network/decode/final denetim dahil30 s monotonic bütçe taşır. Ağ kısa SQL transaction dışında, aynı private credential snapshot ile yapılır. Her state açma/işlem bütçesi ≤5 s ve lock ≤1 s, invocation’ın daha dar kalan süresiyle uygulanır; 30 s ağ beklemesi store deadline’ını30 s yapmaz. Snapshot + response arasındaki boşlukta store lock’u açık tutulmaz; final tekrar mevcut store’u açar ve aynı store_id/identity_epoch/clock_generation/credential ID/revision’ı son transaction’da denetler. Yalnız clock generation değişiminde de state_changed gerekir; saat anomaly aktifken unverified sonucu dahi eski bağla yayımlanmaz.

Kök/ancestor/lstat denetimleri state bütçesi başlamadan yapılmaz; kontrol geri döndüğünde deadline tekrar sınanır. Aynı invocation toplamı içinde final/clock cleanup için en çok 5 s ayrılır; kısa iç test bütçesinde kalan sürenin en çok üçte biri kullanılır. Ağ deadline’ı bu rezervi tüketmez; toplam 30 s uzatılmaz. Başarılı cevap kadar HTTP/schema/timeout ve cleanup/iptal hata yolları da alınmış snapshot’ın clock/frontier denetimini kaynaklar kapandıktan sonra dener; yeni env/request yoktur. Beklenen state_changed ile kalıcı invalidation tamamlanınca birincil read hatası/iptal korunur. Cleanup’ın gerçek state I/O/bütçe hatası normal read hatasından önceliklidir; mevcut exit5 belirsizliği/operation ID ve BaseException kontrol akışı gölgelenmez. Dayanıklılık I/O’su başarısızken invalidation başarıyla saklandı iddiası yoktur. Ortak cache’in kendi final bütçe kodu capability_expired dışarı sızmaz; discovery’de state_busy olur.

UTC geriye dönüşü ve global expiry frontier mevcut StateCache zaman kapısıyla kalıcılaştırılır; normal business ret bu invalidation’ı geri alamaz. Final commit ve owned-session cleanup sonrasında publish öncesi deadline/store binding tekrar kontrol edilir; bilinen değişim eski sonucu yayımlamaz. Kontrol noktasından sonraki eşzamanlı dış değişimi durdurma, sonraki caller anına yetki veya bloke sistem I/O’suna katı duvar saati garantisi yoktur.

## Bütçe ve pilot kapsamı

Normal discovery ve ayrı auth araştırması farklıdır. Aşağıdaki contract pilotları yalnız ayrıca yetkili ve grameri kapatılmış opsiyonel araştırmadır; Accepted ADR-0022 kapsamında dar Platform gözlem tesliminin verified önkoşulu değildir. Normal discover negatif kontrol üretmez, public authentication unknown kalır.

| Sınır | Normal Platform | Normal LLM | Ayrı Platform contract pilotu | Ayrı LLM contract pilotu |
|---|---:|---:|---:|---:|
| Mantıksal GET tavanı | 4 | 1 | 4 pozitif +4 negatif =8 | 1 pozitif +1 negatif =2 |
| Attempt tavanı | 8 | 2 | 8 pozitif +4 negatif =12 | 2 pozitif +1 negatif =3 |
| Toplam gövde | 4 MiB | 1 MiB | 4 MiB | 1 MiB |
| Toplam süre | 30 s | 30 s | 30 s | 30 s |

Her response≤1 MiB, chunk≤32 KiB; listede≤128 kayıt, çıktı≤256 KiB; mevcut strict depth/node/header ve toplam byte politikası ayrıca geçerli. Normal read-only retry en çok 2, negatif kontrol retry0; public consumer’a veri başladıktan sonra retry yok. Sessiz kırpma yok; sınır aşımı invalid_response. Tamlığı kanıtlanmayan kabul edilebilir liste unverified/incomplete kalır; takılan cursor veya değişen üyelik/sayfa verified üretmez.

Auth kanıtı normalize service/origin/API kökü, method/endpoint ve ilgili query/path parametre kapsamıyla karşılaştırılır. Farklı custom host/API kökü/endpoint/proje parametresine aynı kanıt taşınmaz; çok hedefli provider sözleşmesi ancak açık kapsam kanıtıyla geçerlidir. Kanıt türü/tarihi ve raw parser sürümü aynı kayıtta yer alır. Kaynak/pilot sonucu yalnız kontrol edilen davranışı kanıtlar; genel sunucu otoritesi veya permission değildir.

Ayrı bir auth davranışı iddiası araştırılacaksa yetkili sözleşme yokken her endpoint/parametre için iyi biçimli kontrol gerekir; bu normal gözlem consumer’ının kabul önkoşulu değildir. Teyitli syntax/length/prefix yoksa kontrol üretilmez ve auth unknown kalır. Kontrol değeri fresh kriptografik random, sağlayıcıdan alınmamış, gerçek key’den farklıdır; gerçek key’in yalnız bir karakterini değiştirme kullanılmaz. Tercih401; 403 ancak kaynakla anlamı kapanmış invalid-key reason ise kabul, terms/permission/unknown403 veya iki2xx auth kapısını kapatmaz. Malformed-key reddi yeterli değildir. Kontrol yalnız önceden yetkili ayrı pilotta yapılır, registry’ye yazılmaz ve normal discover içine eklenmez. Scope/biçim/iki status/neden/no-registry outcome maskeli kayda girer; key değeri/full body/PII girmez. [Hazırlık yönergesi](../p02-account-setup.md) ürün env politikasına alternatif secret backend değildir.

## Platform gözlem varyantı

**Accepted nihai dar gözlem sözleşmesi.** [ADR-0021](../decisions/0021-platform-discovery-observations.md) wire/başlangıcı, [ADR-0022](../decisions/0022-observed-platform-consumer-contract.md) nihai tüketici ve kabul sınırını tanımlar. Platform discover artık bu tipli gözlem varyantına bağlanır. LLM ContextDiscovery sınıfı/wire’ı aynı kalır; yeni PlatformContextDiscovery kardeş modeli aynı service-bound API’nin Platform sonucudur. Eski LLM çağrısının dönüş tipi ve mevcut sınıf adı korunur; generic ServiceId çağrısı **iki Result örneği tipinin union’ıdır**; Result’ın invariant tür parametresi değiştirilmez. schema_version iki varyantta da1; wire discriminator data.service_id alanıdır.

### Tam public alan kümesi ve tipler

Platform varyantının bütün alanları zorunludur; nullable alan eksik bırakılamaz. Tam alan kümesi: schema_version,service_id,profile,target,binding,profile_preference,selected,provider,reported_identity,authorization_scope,organizations,projects,list_completeness,terms,observed_from,observed_until,validated_at,observations,consistency,validation,reasons. Tüm public nesneler strict/frozen/extra=forbid; mevcut Identifier, DiscoveryBinding ve canonical UTC kuralları aynen geçerlidir. JSON dizileri Python’da tuple’dır; output≤256 KiB.

| Alan | Platform v1 |
|---|---|
| schema_version / service_id | Strict int literal1 / Literal evren-platform |
| profile,target,binding | Mevcut ortak türler; target canonical, binding store/epoch/clock/credential public kimliklerini taşır |
| profile_preference | Değiştirilmemiş profil account_id/project_id ve mevcut unknown/not_applicable scope kuralı; explicit project buraya kopyalanmaz |
| selected | Tam account_id:Identifier veya null,project_id:Identifier veya null; account yalnız profilden, project açık override varsa ondan, yoksa profilden; tercih kanıt değildir |
| provider | Tam principal_id/account_id/organization_id/project_id:null; identity_status:unverified |
| reported_identity | Tam me_id:Identifier,organization_id:Identifier veya null,personal_organization_id:Identifier veya null,organization_id_state/personal_organization_id_state:reported_id veya reported_null veya not_exposed |
| authorization_scope / terms | Yalnız null / yalnız null |
| organizations | Tam items:OrganizationRef dizisi,reported_total:strict nonnegative-int64 |
| projects | Tam items:ProjectRef dizisi,selection:ProjectSelection |
| list_completeness | Tam organizations:unknown veya incomplete,projects:unknown; complete yok |
| observations | Sıralı3 veya4 EndpointObservation; aşağıdaki kapalı sıra |
| observed_from / observed_until / validated_at | Mevcut canonical UTC; local final gate zamanı provider zamanı yerine geçmez |
| consistency / validation | Yalnız not_guaranteed / yalnız unverified |
| reasons | Aşağıdaki kapalı kuralla üretilen tekil, ASCII sözlük sırasında reason dizisi |

OrganizationRef tam id:Identifier taşır. ProjectRef tam id:Identifier,organization_id:Identifier veya null,organization_id_state:reported_id veya reported_null veya not_exposed taşır. Aynı listedeki duplicate ID invalid_response; en çok 128 item, sessiz sıralama/dedup/kırpma yoktur. OrganizationRef.owner_id ve tüketilmeyen ad/slug/ham role/profil alanları yayımlanmaz. Yayımlanan me/organizasyon/proje ID’leri kişiye bağlanabilir; bu sözleşme tüm kişisel veriyi ayıkladığını iddia etmez. Public wire, kullanıcının CLI/Python çıktısıdır; ortak log/PR/artefakta aktarmadan önce bu tanımlayıcılar gerektiğinde maskelenir veya çıkarılır. Identifier yalnız sözdizimini doğrular, kişisel veri sınıflandırmaz.

Çözümlenen selected.project_id açık CLI/Python override’ı veya profil tercihinden gelebilir; **ikisi de detail GET’ini tetikler**. profile_preference değiştirilmemiş profili korur, selected açık override varsa onu kullanır. project=None override değildir; boş string invalid_request olur. Seçili project yoksa 3 GET/3 observation, varsa 4 GET/4 observation vardır.

ProjectSelection tam state:not_selected veya observed veya not_found,project:ProjectRef veya null taşır. selected.project_id=null ise not_selected/null; detail404 ise not_found/null; detail200’de observed/ProjectRef ve dönen id=seçilen id olmalıdır. Bu observed yalnız ID eşitliği ve alınan alanları anlatır; kimlik, membership, parent veya execution izni doğrulanmış olmaz. Listeye seçili kayıt otomatik eklenmez. Tek proje/organizasyon da otomatik seçilmez.

Reported_identity.me_id yalnız auth/me.data.id’nin opak bildirimidir. Diğer iki ID yalnız aynı nesnenin organization_id/personal_org_id alanından gelir. Kaynak alan yoksa not_exposed/null, açık null ise reported_null/null, Identifier ise reported_id/değer; başka tip invalid_response. Bu alanlar provider principal/account alanlarına veya capability scope’a kopyalanmaz. Raw profil ve explicit tercih aynı config snapshot’ından ayrılır; config/env tekrar okunmaz.

EndpointObservation tam endpoint_id,resource_id,started_at,completed_at,authentication,outcome taşır. İlk üç endpoint_id sırası platform_me/platform_organizations/platform_projects, resource_id=null, outcome=observed; selected.project_id açık override veya profil kaynaklı doluysa dördüncü platform_project_detail,resource_id=seçilen ID,outcome=observed veya not_found olur. Authentication her zaman unknown. Aralıklar seri sırada ve observed_from≤ilk başlangıç≤bitiş≤sonraki başlangıç≤son bitiş≤observed_until≤validated_at olmalıdır. Clock rollback’in mevcut kalıcı generation/final kapısı atlanmaz.

Reasons tekil ve ASCII sözlük sırasındadır; verilen reason dizisi tam hesaplanan kümeyle bu sırada eşleşmelidir. Reasons her zaman account_semantics_unknown,authorization_not_verified,identity_not_verified,list_completeness_unknown,remote_snapshot_not_guaranteed içerir. Profile_preference scope unknown ise profile_scope_unknown; project seçilmemişse project_selection_required; detail404 ise selected_project_not_found; organizations completeness incomplete ise provider_listing_incomplete eklenir. Başka keyfi reason veya ErrorCode yoktur. Text görünümü gözlem/tercih ve doğrulanmamış auth/kimlik/tamlık sınırını açıklar; ham provider açıklaması/metadata basmaz. Result completed ve context_not_verified uyarısı korunur.

### Raw projeksiyonun tam tüketim sınırı

Bu tablo Yörünge’nin kabul edeceği tüketim şeklidir; provider’ın tam schema garantisi değildir. Tüketilen alanlar strict doğrulanır. Auth/me’de success ve data zorunludur; ortak “varsa” kuralı bu zorunluluğu kaldırmaz. Organizations root success’i opsiyoneldir; detail’de bare object veya zorunlu success/data zarfı ayrılır. Her endpoint’in root object’inde success anahtarı varsa **tüketilen kontrol metadata’sıdır**: strict bool ve true zorunludur; false/non-bool, geçerli items/total/id yanında olsa da projeksiyondan önce invalid_response olur. Root success asla atılacak metadata değildir. Endpoint’in root tür kuralı ayrıca korunur; bu denetim projects dizisi yerine keyfi zarf kabulü açmaz. Diğer metadata, **tam raw-tree JSON/sır taramasından sonra** atılır; ortak decode_response/closed-codec gevşetilmez. Raw verinin hiçbir generic dict’i public sonuca girmez. Metadata’daki bilinen secret veya malformed JSON da invalid_response olur.

| Endpoint | Kabul edilecek tüketilen yapı |
|---|---|
| auth/me | Root object; success anahtarının varlığı, strict bool=true ve data object zorunlu; data.id zorunlu Identifier,organization_id/personal_org_id isteğe bağlı Identifier/null. logical false veya yanlış/eksik id invalid_response |
| organizations | Root object; success varsa strict bool=true ön denetimi, items object dizisi ve total strict nonnegative-int64 zorunlu; her item.id zorunlu Identifier. total<len(items) invalid_response; total>len(items) incomplete; eşitlik unknown |
| projects | Root object değil JSON dizisi; her item.id zorunlu Identifier,org_id isteğe bağlı Identifier/null. Public parent state missing/null/id ayrımını korur; owner_id veya ad/slug yorumlanmaz |
| projects/{selected_id} | HTTP 200’de bare project object veya success=true/data project object. success anahtarı varsa strict bool ve data object zorunlu; yanlış tip/false/eksik data ret. Project tüketimi listeyle aynı, id=selected_id olmalı.404 not_found; diğer hatalar mevcut kurala göre hata |

Arrays 129+, wrong ID/type/total veya output sınırı ret; overflow incomplete adıyla gizlenmez. Boş projects dizisi geçerli gözlemdir; hiç proje olmadığı/izin bulunmadığı veya seçimin geçerli olduğu sonucu değildir. Pagination parametresi/cursor/Link tahmin edilmez ve takip edilmez; diğer metadata’nın bilinmemesi zaten unknown tamlıkla gösterilir.

No-init/tek credential/state final kapısı, normal en çok 4 GET (proje yoksa 3)/8 attempt/30 s/4 MiB, response ≤1 MiB ve mevcut HTTP/hata/iptal/UTF-8 kuralları korunur. ADR-0022 ile bu sınırlı tüketici politikası nihai sözleşmedir: consumed alan/control strict, tüm raw yapısal/byte ve aşağıdaki seçili literal denetimi sonrası kullanılmayan metadata atılır. Ayrı bütün-raw unknown-ret decoder adımı yoktur. Public unknown/unverified, null authority ve not_guaranteed sabitleri auth/principal/pagination doğrulaması sayılmaz. [Gerçek üç uç](../research/p02-platform-reverse-engineering.md) ve [ayrı seçili-proje consumer kabulü](../research/p02-platform-selected-project-observations.json) Identifier/total/ID-route predikatlarıyla kayıtlıdır; ilk yalnız tür receipt’i bu sonraki kanıtla geriye dönük değiştirilmez. Son kaynak/review/PR/CI kabulü korunur.

### Mevcut literal-secret denetiminin sınırı

Ham ağacın taranması, yalnız **seçili credential’ın mevcut literal-secret kuralıyla** tüm dinamik string değerlerinde ve muaf olmayan metadata anahtarlarında aranmasıdır. UTF-8 uzunluğu 8 byte’tan küçük değerde tam eşitlik; en az 8 byte değerde tam eşitlik veya alt dize eşleşmesi reddedilir. Muafiyet yalnız seçilmiş endpoint/bare-zarf şeklinin açık sabit protokol anahtarları içindir; serbest alt metadata veya seçilmemiş şekil anahtarlarına taşınmaz. Bu, bütün sır türlerini/başka credential’ları veya Base64/hash/URL-encoding gibi türetilmiş değerleri genel olarak tespit eden DLP değildir. JSON kaçışlarının strict parser’da normal çözümlenmesi aynı kalır. Tüm PII’nin otomatik sınıflandırıldığı iddia edilmez.

Mevcut fixture bağı: [Platform contract testleri](../../tests/contracts/test_platform_discovery.py) kısa secret/tam eşitlik ve sabit protokol anahtarını, uzun literal’in metadata değer/anahtarında reddini ve detail şekline ait olmayan anahtarın muaf kalmamasını sınar. [Özgün araştırma kaynak/test arşivi](../research/probes/platform-20261101/README.md) ayrı sayaç/deadline/çıktı yöntemini ağsız incelemeye açar; bu testler genel sır tespiti kanıtı değildir.

### Seçim kavramları ve kapalı wire eşlemesi

ADR-0020’deki genel seçim terimleri henüz uygulanmış Platform enum’ları değildir. Accepted ADR-0021 ile aşağıdaki eşleme geçerlidir; selection_required,selection_unverified,mismatch yeni wire’da ek alan, state veya reason değildir. Bu sözleşme Platform için kesin wire/error eşlemesini sahiplenir; ADR-0020’ye gizli bir state eklemez.

| Genel kavram / durum | Kesin sonuç |
|---|---|
| selection_required; çözümlenen project yok | projects.selection.state=not_selected,project=null; reason project_selection_required; validation=unverified;3 GET |
| selection_unverified; detail404 | projects.selection.state=not_found,project=null; reason selected_project_not_found; validation=unverified;4 GET |
| unverified; detail200/ID eşit | projects.selection.state=observed ve ProjectRef; validation=unverified, authorization_not_verified/account_semantics_unknown korunur;4 GET |
| mismatch; detail ID istenen ID’den farklı | invalid_response / exit1; Result veya discovery payload yayımlanmaz |
| Profil account-parent veya list/detail parent farkı | Normal unverified gözlem; doğrulanmış parent anlamı yok. Listedeki org_id ile detail org_id farklıysa iki kaynak ayrı korunur; consistency=not_guaranteed ve account_semantics_unknown/remote_snapshot_not_guaranteed korunur. Bunlar invalid_response veya membership hükmü değildir |

Profil-only project için de selected.project_id doludur; son satır dışındaki4 GET kuralı explicit override ile aynıdır. Profil-only/dördüncü GET/selected/profile_preference/state tek fixture’da birlikte sınanır. Örneğin profilde A ve override B varsa profile_preference A,selected B kalır ve yalnız B detail’i istenir. Tüketilen parent yanlış tipse normalizer invalid_response verir; eksik/null/ID veya endpoint’ler arasında değişmesi farklı durumlardır.

### Önerilen Python API ve renderer tip sözleşmesi

**Accepted ve çalışma dalında uygulanmış sözleşme.** Overload’lar aşağıdaki gibidir. Generic çağrının dönüşü `Result[ContextDiscovery] | Result[PlatformContextDiscovery]`’dir. `Result[ContextDiscovery | PlatformContextDiscovery]` dar literal overload’larla aynı şey değildir: mevcut invariant Result ile izole strict-mypy deneyi implementation-return uyumsuzluğunu doğruladı. Result’ın variance’ı veya Result v1 wire’ı bu iş için değiştirilmez.

```python
@overload
def discover_context(
    service_id: Literal["evren-llm"], *, config: Path | None = None,
    profile: str | None = None, project: str | None = None,
    state_dir: Path | None = None,
) -> Result[ContextDiscovery]: ...

@overload
def discover_context(
    service_id: Literal["evren-platform"], *, config: Path | None = None,
    profile: str | None = None, project: str | None = None,
    state_dir: Path | None = None,
) -> Result[PlatformContextDiscovery]: ...

@overload
def discover_context(
    service_id: ServiceId, *, config: Path | None = None,
    profile: str | None = None, project: str | None = None,
    state_dir: Path | None = None,
) -> Result[ContextDiscovery] | Result[PlatformContextDiscovery]: ...
```

Python literal-service caller dar Result tipini alır; generic caller result.data.service_id ile data varyantını daraltır. JSON’da discriminator data.service_id, NDJSON result event’inde payload.data.service_id’dir; tek başına schema_version=1 varyant seçmez. Her DTO’nun service_id literal’ı sabittir; yanlış model/service eşleşmesi kabul edilmez. Mevcut LLM sınıf adı ve wire’ı korunur.

CLI discovery_text_result iki doğrulanmış DTO sınıfına dispatch eder; yalnız eski ContextDiscovery isinstance kontrolüyle Platform’u TypeError’a düşürmez. Platform text gözlem/tercih/unknown auth-kimlik-tamlık sınırını, LLM text mevcut terms sınırını gösterir. Provider dict veya metadata renderer’a girmez; JSON/NDJSON seçilen DTO’yu aynı Result zarfında serileştirir. Testler iki literal ve generic dönüş/narrowing, iki text varyantı, JSON ve NDJSON eşliğini kapsar. Public kod adımı önceki Platform unsupported davranışını bu tipli varyanta çevirdi; onay tek başına implementasyon sayılmadı.

### Detail404 için tam sentetik Result örneği

Aşağıdaki bütün ID/zaman/değerler sentetiktir; canlı kanıt veya gerçek hesap bilgisi değildir. Profil-only seçilen project detail404 verdiğinde 4 observation ve tam JSON aşağıdaki şekildedir. selection_unverified ek bir alan/değer değildir; üst validation=unverified ile not_found + selected_project_not_found bu kavramı ifade eder. NDJSON result event’inin payload alanı bu aynı Result’tur.

```json
{
  "schema_version": 1,
  "operation_id": null,
  "status": "completed",
  "data": {
    "schema_version": 1,
    "service_id": "evren-platform",
    "profile": "synthetic",
    "target": {
      "service_origin": "https://api.ssyz.org.tr",
      "api_base_path": "/api/v1"
    },
    "binding": {
      "store_id": "11111111-1111-4111-8111-111111111111",
      "identity_epoch": "22222222-2222-4222-8222-222222222222",
      "clock_generation": 1,
      "credential_id": "44444444-4444-4444-8444-444444444444",
      "credential_revision": 1
    },
    "profile_preference": {
      "account_id": null,
      "project_id": "33333333-3333-4333-8333-333333333333",
      "service_scope": "unknown"
    },
    "selected": {
      "account_id": null,
      "project_id": "33333333-3333-4333-8333-333333333333"
    },
    "provider": {
      "principal_id": null,
      "account_id": null,
      "organization_id": null,
      "project_id": null,
      "identity_status": "unverified"
    },
    "reported_identity": {
      "me_id": "synthetic-me-id",
      "organization_id": null,
      "personal_organization_id": null,
      "organization_id_state": "not_exposed",
      "personal_organization_id_state": "not_exposed"
    },
    "authorization_scope": null,
    "organizations": {
      "items": [],
      "reported_total": 0
    },
    "projects": {
      "items": [],
      "selection": {
        "state": "not_found",
        "project": null
      }
    },
    "list_completeness": {
      "organizations": "unknown",
      "projects": "unknown"
    },
    "terms": null,
    "observed_from": "2026-11-01T12:00:00.000000Z",
    "observed_until": "2026-11-01T12:00:00.850000Z",
    "validated_at": "2026-11-01T12:00:00.900000Z",
    "observations": [
      {
        "endpoint_id": "platform_me",
        "resource_id": null,
        "started_at": "2026-11-01T12:00:00.100000Z",
        "completed_at": "2026-11-01T12:00:00.200000Z",
        "authentication": "unknown",
        "outcome": "observed"
      },
      {
        "endpoint_id": "platform_organizations",
        "resource_id": null,
        "started_at": "2026-11-01T12:00:00.300000Z",
        "completed_at": "2026-11-01T12:00:00.400000Z",
        "authentication": "unknown",
        "outcome": "observed"
      },
      {
        "endpoint_id": "platform_projects",
        "resource_id": null,
        "started_at": "2026-11-01T12:00:00.500000Z",
        "completed_at": "2026-11-01T12:00:00.600000Z",
        "authentication": "unknown",
        "outcome": "observed"
      },
      {
        "endpoint_id": "platform_project_detail",
        "resource_id": "33333333-3333-4333-8333-333333333333",
        "started_at": "2026-11-01T12:00:00.700000Z",
        "completed_at": "2026-11-01T12:00:00.800000Z",
        "authentication": "unknown",
        "outcome": "not_found"
      }
    ],
    "consistency": "not_guaranteed",
    "validation": "unverified",
    "reasons": [
      "account_semantics_unknown",
      "authorization_not_verified",
      "identity_not_verified",
      "list_completeness_unknown",
      "profile_scope_unknown",
      "remote_snapshot_not_guaranteed",
      "selected_project_not_found"
    ]
  },
  "warnings": [
    "context_not_verified"
  ]
}
```
