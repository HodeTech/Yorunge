# ADR-0021: Platform için doğrulanmamış, tipli keşif gözlemi

**Durum:** Accepted — kullanıcı revize kararı 2026-11-01 tarihinde onayladı ve uygulamayı yetkilendirdi; bu onay commit’inde bağımlı ürün kodu henüz uygulanmadı. **Tarih:** 2026-10-31. **Güncellendi:** 2026-11-01. **İş:** P02-0d / P02-0b. Bu öneri [ADR-0020](0020-service-bound-context-discovery.md)’nin Platform adaptörünün ara gözlem aşamasına başlama kapısını ve o aşamanın tüketilmeyen raw metadata politikasını kısmen değiştirir; Platform seçim kavramlarının kapalı wire/error eşlemesini de açıkça belirler. ADR-0020 halen Accepted ve yürürlüktedir. [Gözlem kaydı](../research/p02-platform-discovery-observations.md), [önerilen public sözleşme](../reference/context-discovery.md#platform-gözlem-varyantı), [iş kartı](../roadmap/tasks/p02-0d-platform-context-discovery.md).

**2026-11-01 ileri karar notu:** [Accepted ADR-0022](0022-observed-platform-consumer-contract.md), yalnız Platform read-only keşfinin nihai tüketici sözleşmesi ve kabul kapsamını kısmen değiştirir. Tüketilen alanlar strict, seçili credential literal denetimi ve yapısal/boyut sınırları korunur; tüketilmeyen metadata atılır. Ayrı whole-raw unknown-ret decoder ve resmî auth/principal/pagination bilgisi bu dar gözlem tesliminin önkoşulu değildir. Public sonuç unverified/unknown kalır, yetki üretmez; doğrulanmış kimlik/bağ ihtiyacı P02-R1’de takip edilir. Aşağıdaki önceki karar metni tarihsel kapsamıyla korunur; bu maddelerde güncel kural ADR-0022’dir.

## Bağlam ve gerçek dış kapı

ADR-0020 raw minimum şema, key kabulü ve pagination kapatılmadan Platform adaptörünü draft tutar. Yeni yetkili salt okuma araştırmasında aynı Platform hedefinde auth/me, organizations ve projects HTTP200 verdi. Me zarfında success=true; organizasyon cevabında items ve total; proje cevabında boş dizi gözlendi. Bu üç gözlem çağrısı aynı 30 s bütçe içinde 0,193 s sürdü. Key-auth sözleşmesi, principal/account anlamı ve liste tamlığı bu sonuçlardan kanıtlanmadı. Kullanıcının project ID bilmemesi ilk liste okumalarını engellemedi.

**Kanıt sınırı:** Devam araştırması toplam **5 mantıksal GET girişimi** içerdi; ADR-0020 contract pilotunun 4 pozitif GET/30 s tavanını karşılamadı. 0,193011 s yalnız son üç-GET survey’in süresidir. Gerçek attempt sayısı ölçülmedi; son survey’in tavanı 3 GET/6 attempt/3 MiB/30 s idi, ürünün 4 GET/8 attempt/4 MiB bütçesiyle aynı değildir. Birikimli sapma contract kabulü sayılmaz; önceki başarısız/dar kayıtlar korunur.

Receipt yalnız şekil/tür gözlemidir: organization id’nin Identifier koşulunu, total’ın nonnegative-int64 aralığını veya total≥len(items) eşitsizliğini geçtiği kaydedilmedi. Dolayısıyla **önerilen parser’ın mevcut canlı örneği kabul edeceği henüz gösterilmedi**. Dolu proje ve detail yanıtı da canlıda sınanmadı. İleride uygun scope ile gerçek değerleri saklamadan bu predicate’lerin bool sonuçları kaydedilebilir; mevcut receipt’e geriye dönük başarılı sonuç eklenmez.

Me cevabı kullanıcı sunum ve kişisel veri alanları da taşıyor. Bunları public modele almak veya her metadata alanını kimlik kararının parçası yapmak gerekmiyor. Bilinmeyen wire’ı generic dict olarak dışarı vermek de uygun değil. Bugünkü tam-provider-schema kapısı, belirsizliği açıkça koruyan dar bir okuma sonucunu dahi engelliyor.

## Karar

### 1. Uygulamaya başlama ve kapanış ayrı kapılardır

Onay sonrası P02-0d’de yalnız **unverified Platform observation** uygulanabilir. Mevcut public discover komutunun Platform seçimi, kod/test/kullanıcı belgesi tamamlandıktan sonra bu kapalı tipli varyanta bağlanır. Yeni debug/backend komutu veya kullanıcıdan kanıt enjekte etme seçeneği eklenmez. Bu ADR kabul edilene kadar mevcut unsupported_combination davranışı sürer.

Bu karar **nihai auth/principal/pagination/live ve paket kabul kapılarını kaldırmaz**. Ancak ara gözlem aşamasının raw alan kabulü değişir; “hiçbir kabul davranışı değişmiyor” denemez. [P02-0d](../roadmap/tasks/p02-0d-platform-context-discovery.md) kabul 1 bu iki aşamayı ayrı tanımlar:

- **Ara unverified uygulama:** tüketilen alan/control yanlışsa ret; tüketilmeyen metadata tüm raw-tree JSON/sır taramasından sonra atılır. Bu aşama başlamaya ve anlamlı kod/test ilerlemesine izin verir, kartı verified yapmaz.
- **Nihai verified teslim:** provider-version/endpoint kapsamı kapanınca **ek ürün kodu değişikliği** gerekir. Üretim CLI/Python yolundaki projeksiyon-only raw kabul sınırı, sağlayıcı sözleşmesine bağlı katı decoder ile değiştirilir; raw unknown alanlar kontrollü reddedilir. Katı decoder başarısızken ara projeksiyona fallback yoktur; yalnız kabul helper’ının katı olması yetmez. Katı raw model PII alanlarını doğrulasa da public projeksiyon aynı dar alanları yayımlar.

Sonraki katı decoder işi bu P02-0d paketinin açık kapanış adımıdır, bitmiş işten sonraya saklanan bir cleanup değildir. Nihai teslim için ayrıca ADR-0020’deki kimlik/auth/tamlık ve tüm canlı kabul koşulları gerekir. İş kartının verified teslim durumu ile public validation farklıdır: bu önerinin public validation alanı daima unverified kalır; kimliği doğrulanmış yeni public wire bu ara önerinin kapsamı değildir. Kod/yerel test veya katı parser tek başına paket kapanışı değildir. Ayrı PR açılmaz; tek P02-0 planı korunur.

### 2. Raw veriden açıkça sınırlı projeksiyon

Platform normalizer’ı yalnız [referanstaki](../reference/context-discovery.md#platform-gözlem-varyantı) alanları tüketir. Bu **Yörünge’nin kabul ettiği projeksiyon** sözleşmesidir; sağlayıcının eksiksiz OpenAPI’si veya bütün alanlarının kararlılık garantisi değildir.

- Ortak HTTP, deadline, byte/header/chunk, strict UTF-8/JSON, duplicate/nonfinite ve depth/node sınırları aynen uygulanır.
- Önce **tüm parse edilmiş raw ağacın** dinamik string değerleri ve tüketilmeyen metadata anahtarları mevcut literal-secret kuralıyla denetlenir. Tüketilmeyen alanlar bu taramadan kaçamaz. Sabit, açıkça tanımlı protokol anahtarları anahtarın kaynağı sayılmaz; serbest metadata anahtarları muaf değildir.
- Her endpoint’in root object’inde success varsa tüketilen kontrol alanıdır; strict bool=true zorunludur. False/non-bool, geçerli id veya items/total yanında da projeksiyondan önce invalid_response olur; bu bayrak metadata diye atılmaz. Bu ortak “varsa” denetimi auth/me’deki zorunlu success alanını opsiyonel yapmaz: me için success/data zorunlu; organizations için success opsiyonel, varsa strict true; detail için bare veya zorunlu success/data zarfı ayrı şekillerdir. Endpoint root tür kuralı ayrıca korunur.
- Sonra yalnız tüketilen alanlar seçilir, strict ve extra=forbid iç/public modellere doğrulanır. Tüketilen alandaki yanlış tip, eksik zorunlu alan veya tutarsız ID controlled invalid_response olur. Bilinmeyen metadata çıktı, hata, log, cache veya diske aktarılmadan atılır.
- Bu dar adaptör sınırı, ortak decode_response veya diğer hizmet modellerini extra=ignore yapmaz. Diğer consumer’ların closed-codec davranışı korunur. Tüketilmeyen ad, e-posta, telefon, kimlik numarası ve diğer profil alanları ile ham role/admin_permissions değerleri public sonuç dışında kalır. Bu bir “tüm kişisel veri ayıklandı” garantisi değildir; bilinçli olarak yayımlanan opak ID’ler kişiye bağlanabilir.

Tüketilmeyen raw metadata’nın tek başına ret sebebi olmaması, ADR-0020/P02-0d’nin tüm raw unknown alanları reddetme beklentisine **yalnız ara unverified aşama için** açık istisnadır; nihai verified aşamanın katı raw decoder zorunluluğunu değiştirmez. Public wire kapalı kalır. Kısmi veya yanlış kullanılan alan sessizce düşürülmez.

### 3. Gözlenen ID, doğrulanmış principal değildir

Platform sonucu her hedefte authentication=unknown, validation=unverified, authorization_scope=null ve consistency=not_guaranteed taşır. Provider principal/account/org/project alanları null; identity_status=unverified olur. Me yanıtındaki en çok üç ID alanı yalnız ayrı reported_identity nesnesinde **hangi wire alanından geldiği belirli opak bildirimler** olarak sunulur. Bunlar principal, kullanıcı üyeliği, aktif hesap veya yürütme yetkisi diye adlandırılmaz. “Public”, CLI/Python çıktı şemasını anlatır; aleni yayın yapıldığı anlamına gelmez. Bu ID’ler kişiye bağlanabilir tanımlayıcılardır; çıktıyı paylaşan/tutan kullanıcı onları kimlik verisi olarak ele alır, ortak log/PR/artefakta aktarmadan önce gerekirse maskeler veya çıkarır. Identifier doğrulaması bir PII sınıflandırıcısı değildir.

Profil account/project tercihleri selected altında korunur; project için açık CLI/Python override varsa o kullanılır. **Çözümlenen selected.project_id, açık override veya profil kaynaklı olmasına bakılmadan detail GET’i tetikler.** Profil-only seçim de 4 çağrı üretir; project=null ise 3 çağrı olur. profile_preference aynı config snapshot’ındaki değiştirilmemiş profil tercihidir. Account ID’nin user mı organizasyon mu olduğu varsayılmaz. İlk organizasyon/proje, tek kayıt olsa bile otomatik seçilmez; config yazılmaz. Me yanıtındaki ID, profil seçiminin yerine geçirilmez. LLM varyantı, selected=null ve eski Context/config/Plan/Result anlamları değişmez.

### 4. Liste, seçim ve hata sonucu

Organizasyon/proje listeleri en çok 128 öğeyle tipli ID referanslarıdır. Provider total değeri yalnız reported_total olarak gösterilir. total=len(items) tamlık kanıtı değildir; completeness en iyi unknown olur. Bilinen total daha büyükse incomplete olur. Proje dizisinin boşluğu, hizmette hiç proje olmadığı veya erişim reddi anlamına gelmez. Sırf gözlemi zenginleştirmek için bilinmeyen pagination parametresi tahmin edilmez; cursor/Link takip edilmez.

Çözümlenen selected.project_id null değilse dördüncü GET yalnız o ID içindir; profil-only seçim de bu kurala dahildir. Detail404 seçimin gözlenemediği sonucudur; silinmiş/izinsiz diye kesin hüküm verilmez. Detail200’de dönen ID istenen ID ile eşleşmelidir; başka ID invalid_response olur. Parent alanı doğrulanmış hesap anlamına bağlanmaz. Hiç project seçilmemişse boş/tek/çok listede tek wire reason **project_selection_required** olur. ADR-0020’nin selection_required/selection_unverified/unverified/mismatch anlatımları genel seçim kavramlarıdır; Platform için kapalı eşleme [referanstadır](../reference/context-discovery.md#seçim-kavramları-ve-kapalı-wire-eşlemesi). Detail404, validation=unverified + projects.selection.state=not_found + selected_project_not_found reason’ıdır; selection_unverified adında ek alan/değer üretilmez. Detail ID’nin istenen ID’den farklı olması invalid_response’dur; bu dar ID-route uyuşmazlığı eşlemesi burada açıkça belirlenir.

Aynı project ID’sinin listede org_id=A, sonraki detail’de org_id=B olması tek snapshot garantisi bulunmadığı için ret değildir: iki kaynak ayrı korunur, validation=unverified/consistency=not_guaranteed kalır, account_semantics_unknown ve remote_snapshot_not_guaranteed nedenleri vardır. Profil account_id ile parent ID karşılaştırmasından üyelik/mismatch veya izin sonucu çıkarılmaz. Eksik/null parent ayrımı korunur.

401/403 remote_access_denied,429 remote_rate_limited; liste/me404 invalid_response ve2xx logical failure invalid_response aynen kalır. Ham sağlayıcı mesajı kullanıcı hatasına taşınmaz. Hata bir listeyi sessizce boş başarıya çevirmez.

### 5. Yetki ve kaynak sınırları

Project seçilmemişse3 GET; açık override veya profil kaynaklı selected.project_id varsa 4 GET/en çok 8 attempt, toplam 30 s, her response≤1 MiB/toplam≤4 MiB ve public output≤256 KiB değişmez. Herhangi bir limit aşımı kontrollü ret olur; sessiz kırpma yoktur. Same owned session, tek hizmet/env snapshot, no-init store, ağ sırasında kapalı transaction/lock ve son credential/epoch/clock/deadline kapısı ADR-0020 ile aynıdır. Yeni DB/cache/schema/secret backend eklenmez.

Bilinen biçimde negatif kontrol yoksa auth unknown kalır; bu öneri key sözdizimi uydurmaz veya normal discover içine negatif istek eklemez. Uzak yazma, proje/hesap oluşturma, upload/inference, şart kabulü, key oluşturma veya browser JWT/cookie fallback’i yoktur. Discovery hâlâ operation/admission/authorization producer değildir.

## Kabul ve uygulama sırası

Aynı araştırmanın HTTP sonrası analiz/parse hatası da çağrı slotunu tüketir; helper’ı değiştirmek sayaç/deadline bütçesini sıfırlamaz. Takip account probe’u ancak baştan tek yürütücüde tanımlı toplam bütçeyle yapılır; başarısız kayıt silinmez veya kabul koşusuna dönüştürülmez.

1. Kullanıcı bu ADR’yi onaylar; [onay commit’i geçiş listesi](#onay-commitinde-belge-geçişi) koddan önce uygulanır. Onay öncesi ürün kodu yoktur. Ara gözlem koduna başlama ile nihai verified/live kabul ayrı tutulur.
2. Kapalı Platform public model, salt projeksiyon normalizer’ı, mevcut state/final kapısıyla ortak core; sonra CLI/API/text/JSON/NDJSON aynı kullanıma bağlanır. Ara uygulama iki kod adımına ayrılır; dış sözleşme kapanınca üçüncü zorunlu adım üretim katı decoder ve nihai kabulü tamamlar. Her kod adımı commit ve iki farklı fresh review turu içerir. API overload’ları, invariant Result için union-of-results ve varyant renderer [referansta](../reference/context-discovery.md#önerilen-python-api-ve-renderer-tip-sözleşmesi) koddan önce kapatılır.
3. Bağımsız fixture’lar: me PII/role/serbest metadata atımı; yok/yanlış/duplicate/nonfinite/oversize tüketilen alan; **atılacak metadata içindeki secret**; kısa secret/protokol sabiti ayrımı; bool/int ve nullable/missing parent farkı. Auth/me için success yok,false,0,1,"true" ve data yok/yanlış tip ayrı invalid_response fixture’larıdır. Organizations items/total yanında success=false,0,1,"true" ret; success yokken geçerli object kabul. Detail’de bare object kabul; zarf varsa success/data zorunlu, false/0/1/"true"/eksik data ret. Root kontrol politikası tüketilmeyen metadata istisnasından önce sınanır.
4. Boş/tek/çok/duplicate 128/129 liste, total<len/=/>, profil-only project (4 GET), boş profil (3 GET), explicit override (4 GET)/detail404/yanlış detail ID; eksik parent, yeni metadata ve değişen sayfa/üyelikte unverified/tamlık sınırı korunur. Liste/detail parent farkı ve profil account-parent farkında unverified sonuç; yanlış detail ID’de invalid_response ayrı oracle’dır. Tam reason dizisi ASCII sözlük sırası/tekillik ile assert edilir; selection_required/selection_unverified/mismatch wire reason’ları reddedilir. Mevcut canlı boş proje örneği veya tür receipt’i, parser uyum/dolu/seçilmiş proje canlı kabulü diye gösterilmez.
5. TLS gerçek request sınırı, tek env/hedef, no-init, iki süreç credential/reset/clock yarışı, timeout/retry/cleanup/SIGINT/pipe ve UTF-8/NDJSON; eski LLM ve offline v1 regresyonları.
6. Kaynak değiştiğinde tam test/statik/iki clean install ve yeni kaynak bağlı M5 startup/jobs yapılır; önceki LLM referansı güncel ürün kabulü yerine kullanılmaz. Nihai kabul öncesi üretim katı decoder değişikliği ve bütün ilgili regresyonlar yeniden doğrulanır. P02-0d’nin eksik auth/principal/pagination ve dolu/seçili proje live kabulü ayrı açık kalır. Yetkili yeni kontrolde değerleri saklamadan Identifier/strict nonnegative-int64/total≥len predicate sonuçları kaydedilebilir; mevcut receipt bu sonuçları kanıtlamaz. Yeni kullanım senaryoları bu gözlemden izin üretmez.

## Onay commit’inde belge geçişi

Kullanıcının 2026-11-01 tarihli açık onayıyla bu geçişler ürün kodundan **önce aynı commit’te** uygulandı. ADR-0021 Accepted; ADR-0020 yalnız belirtilen ara başlangıç/metadata/wire sınırlarında kısmen değiştirilmiştir. P02-0d ara uygulamaya ready, üst teslim draft kalır.

| Belge | Onay sonrası değişiklik |
|---|---|
| ADR-0021 ve decisions/README | Gerçek onay tarihiyle Accepted; implementation henüz yok; ADR-0020’ye dar amendment ilişkisi |
| ADR-0020 forward notu | Başlangıç/ara metadata/Platform wire eşlemesinde ADR-0021’e yönlendir; nihai auth/live ve raw unknown ret kapısı korunur. ADR-0020 bütünü Superseded yapılmaz |
| ContextDiscovery referansı | Platform bölümünü Accepted tasarım/uygulanmadı olarak işaretle; overload/renderer/eşleme sözleşmesi korunur. Mevcut ürün imzası ve unsupported durumu kod gelene kadar ayrı anlatılır |
| P02-0d kartı | Ara gözlem başlangıcı ready olabilir; kabul 1’in ara projeksiyon/nihai katı parser ayrımı ve detay/reason eşlemesi korunur. Verified/live dış kapısı kaldırılmaz |
| P02-0b üst kartı | Alt işin başlangıç kapısı ile üst verified kapısını ayır; aggregate draft kalır, ara unverified kodu üst işi bitirmez |
| P02-0 planı adım5 | 5.1 core/projeksiyon,5.2 API/CLI;5.3 dış sözleşme kapanınca üretim katı decoder+nihai kabul. Her kod adımında iki fresh review |
| current ve tasks/README | Eski yalnız-raw kapanınca başlama ifadesini yeni dar başlangıçla hizala; kimlik/live/kart/PR/CI durumunu ilerlemiş gösterme |

## Alternatifler ve sonuç

- Tam sözleşme gelene kadar bütün Platform kodlamasını bekletmek: ADR-0020’nin mevcut davranışı; onay verilmezse korunur.
- Ham dict veya sağlayıcının bütün profil/PII alanlarını yayınlamak: seçilmedi.
- 2xx/tek organizasyon/boş proje ile kimliği ve listeyi verified yapmak: seçilmedi.
- Bu öneriyle P02-0 kabulünü de daraltıp paketi verified saymak: seçilmedi; ayrı kullanıcı kararı olmadan kabul kapısı değişmez.

Öneri güven iddiasını büyütmeden bir ara gözlem diliminin kodlanmasını açmayı amaçlar; uygulanabilirlik, parser’ın canlı örneği kabulü veya çalışan ürün henüz kanıtlanmış değildir. Karşılığı, tam provider schema yerine tüketilen alan projeksiyonunun açıkça sahiplenilmesi ve eksik dış kabullerin ve nihai üretim katı decoder işinin görünür tutulmasıdır. Bu karar Accepted’dır; onay tek başına uygulanmış özellik veya nihai kabul sayılmaz.


## Uygulama durum notu — 2026-11-01

Onay commit’i9fae321’den sonra iki ara kod adımı, her birinde commit ve iki farklı fresh review turuyla uygulandı. [Ara yerel kabul](../research/p02-0-implementation-validation.md#platform-ara-yerel-kabul-kapanışı) tam test/iki temiz kurulum ve yeni kaynak bağlı M5 kanıtını taşır. Bu, karar anındaki uygulanmadı ifadelerinin sonraki durumudur. Parser’ın gerçek canlı örneğe uyumu, nihai üretim katı decoder ve auth/principal/pagination/dolu-seçili proje canlı kabulü henüz kanıtlanmış değildir; P02-0d/P02-0b/P02-0 verified ilan edilmez.


## Sonraki araştırma notu — 2026-11-01

**Tarihsel, ADR-0022 onayı öncesi:** Kullanıcının ayrı salt okuma yetkisiyle [yeni davranış koşusu](../research/p02-platform-reverse-engineering.md) mevcut üç endpoint cevabının gerçek ürün parser’ı ve Identifier/total predikatlarını geçtiğini gösterdi; yukarıdaki daha önceki kanıt eksikliği bu dar kapsamda giderildi. Seçili/dolu proje ve auth/principal/pagination garantileri halen açık. [ADR-0022](0022-observed-platform-consumer-contract.md) read-only consumer için nihai raw/kapanış kapısına kısmi değişiklik önerdi; bu not yazıldığında Proposed idi. ADR-0022 daha sonra 2026-11-01 tarihinde açık kullanıcı onayıyla Accepted oldu; güncel kural yukarıdaki ileri karar notundadır.
