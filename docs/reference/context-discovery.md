# ContextDiscovery v1 sözleşmesi

**Tarih:** 2026-10-31. **Durum:** [Accepted ADR-0020](../decisions/0020-service-bound-context-discovery.md) uygulama öncesi kapalı referansı. LLM terms kolunun wire’ı aşağıda kesinleştirildi; ürün uygulaması henüz başlamadı. Platform raw kimlik/envelope/pagination/key kabulü açık; bu belgede tanımlanmamış Platform yanıtı generic dict ile dışarı verilmez. [Paket ve hizmet kartları](../roadmap/p02-0-delivery-plan.md) uygulama/canlı kabul durumunun sahibidir.

## Giriş ve state

CLI `context discover --service evren-platform|evren-llm [--config PATH] [--profile NAME] [--project ID] [--state-dir PATH] [--output text|json|ndjson]`. Python `api.discover_context(service_id: ServiceId, *, config: Path|None=None, profile: str|None=None, project: str|None=None, state_dir: Path|None=None) -> Result[ContextDiscovery]`. ServiceId mevcut iki değerdir; bilinmeyen/bool/tür hatası invalid_request. Ortak CLI seçenekleri önce/sonra geçerlidir; tekil discovery seçeneklerinin yinelenmesi reddedilir. Yeni --account yok; account tercihi yalnız profilden gelir.

LLM’de açık project/--project `invalid_request` ile I/O öncesi reddedilir. Ortak profilin account_id/project_id alanları çağrıyı engellemez ancak LLM selected alanına kopyalanmaz. Platform alt kartı raw sözleşmesi kapanmadığı sürece public çağrı I/O öncesi `unsupported_combination` verir; sahte observation veya adapter yoktur. LLM’nin uygulanması Platform’ın verified olduğu anlamına gelmez.

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

Platform varyantı bu LLM alanlarına provider ID uydurarak oluşturulmaz. İlgili kart hazır olmadan principal/account/org anlamı, liste/detay/envelope/pagination ve seçilmiş account/project eşliği kendi kapalı varyantında tanımlanır. Mevcut v1 Context/config/Plan/Result/capability scope değiştirilmez.

## Raw terms adaptörü ve hata

Yalnız seçili LLM hedefindeki **GET terms/status** kullanılır; query/body boş, read_only=true. Kimlik header’ı Authorization/Bearer seçilen LLM snapshot’ıdır; Accept-Encoding ve diğer taşıma header’ları ayrı kalır. HTTPX/SDK nesnesi public modele girmez. Session-owned Runner’ın loop/thread/PID/reentrancy kontrolü env/DB/ağdan önce yapılır.

200 gövdesi **tam** accepted:bool, current_version:int64≥0, is_material:bool, doc_path:string alanlarını taşır. doc_path1–2048 Unicode code point, ≤8192 UTF-8 byte, C0/DEL/C1/surrogate yok; URL’ye çevrilmez/takip edilmez ve public’e kopyalanmaz. strict JSON + closed typed decode + P01 literal secret denetimi raw modelde yapılır; bilinmeyen alan/envelope/logical failure/yanlış tür/boş gövde invalid_response. Provider’ın version/tip genişlemesi sessizce kabul edilmez. Tüm2xx’ler aynı gövde şemasına tabidir.

| HTTP / sınır | Discovery sonucu |
|---|---|
| terms/status, auth/me, organizations veya projects list404 | Adaptör HttpStatusFailure.status_code üzerinden invalid_response üretir; generic remote_failed olarak kaçmaz |
| projects/{id}404 | Platform varyantında selection_unverified + selected_project_not_found observation; “silinmiş/erişim yok” kesin hükmü yok |
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

UTC geriye dönüşü ve global expiry frontier mevcut StateCache zaman kapısıyla kalıcılaştırılır; normal business ret bu invalidation’ı geri alamaz. Final commit ve owned-session cleanup sonrasında publish öncesi deadline/store binding tekrar kontrol edilir; bilinen değişim eski sonucu yayımlamaz. Kontrol noktasından sonraki eşzamanlı dış değişimi durdurma, sonraki caller anına yetki veya bloke sistem I/O’suna katı duvar saati garantisi yoktur.

## Bütçe ve pilot kapsamı

| Sınır | Normal Platform | Normal LLM | Ayrı Platform contract pilotu | Ayrı LLM contract pilotu |
|---|---:|---:|---:|---:|
| Mantıksal GET tavanı | 4 | 1 | 4 pozitif +4 negatif =8 | 1 pozitif +1 negatif =2 |
| Attempt tavanı | 8 | 2 | 8 pozitif +4 negatif =12 | 2 pozitif +1 negatif =3 |
| Toplam gövde | 4 MiB | 1 MiB | 4 MiB | 1 MiB |
| Toplam süre | 30 s | 30 s | 30 s | 30 s |

Her response≤1 MiB, chunk≤32 KiB; listede≤128 kayıt, çıktı≤256 KiB; mevcut strict depth/node/header ve toplam byte politikası ayrıca geçerli. Normal read-only retry en çok2, negatif kontrol retry0; public consumer’a veri başladıktan sonra retry yok. Sessiz kırpma yok; sınır aşımı invalid_response. Tamlığı kanıtlanmayan kabul edilebilir liste unverified/incomplete kalır; takılan cursor veya değişen üyelik/sayfa verified üretmez.

Auth kanıtı normalize service/origin/API kökü, method/endpoint ve ilgili query/path parametre kapsamıyla karşılaştırılır. Farklı custom host/API kökü/endpoint/proje parametresine aynı kanıt taşınmaz; çok hedefli provider sözleşmesi ancak açık kapsam kanıtıyla geçerlidir. Kanıt türü/tarihi ve raw parser sürümü aynı kayıtta yer alır. Kaynak/pilot sonucu yalnız kontrol edilen davranışı kanıtlar; genel sunucu otoritesi veya permission değildir.

Yetkili auth sözleşmesi yokken, her kullanılan endpoint/parametre için iyi biçimli kontrol gerekir. Teyitli syntax/length/prefix yoksa kontrol üretilmez ve auth unknown kalır. Kontrol değeri fresh kriptografik random, sağlayıcıdan alınmamış, gerçek key’den farklıdır; gerçek key’in yalnız bir karakterini değiştirme kullanılmaz. Tercih401; 403 ancak kaynakla anlamı kapanmış invalid-key reason ise kabul, terms/permission/unknown403 veya iki2xx auth kapısını kapatmaz. Malformed-key reddi yeterli değildir. Kontrol yalnız önceden yetkili ayrı pilotta yapılır, registry’ye yazılmaz ve normal discover içine eklenmez. Scope/biçim/iki status/neden/no-registry outcome maskeli kayda girer; key değeri/full body/PII girmez. [Hazırlık yönergesi](../p02-account-setup.md) ürün env politikasına alternatif secret backend değildir.
