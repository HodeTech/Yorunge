# ADR-0021: Platform için doğrulanmamış, tipli keşif gözlemi

**Durum:** Proposed — kullanıcı onayı bekleniyor; bağımlı ürün kodu uygulanmadı. **Tarih:** 2026-10-31. **İş:** P02-0d / P02-0b. Bu öneri [ADR-0020](0020-service-bound-context-discovery.md)’nin yalnız Platform adaptörüne başlama kapısını ve tüketilmeyen raw metadata politikasını kısmen değiştirir. ADR-0020 halen Accepted ve yürürlüktedir. [Gözlem kaydı](../research/p02-platform-discovery-observations.md), [önerilen public sözleşme](../reference/context-discovery.md#önerilen-platform-gözlem-varyantı), [iş kartı](../roadmap/tasks/p02-0d-platform-context-discovery.md).

## Bağlam ve gerçek dış kapı

ADR-0020 raw minimum şema, key kabulü ve pagination kapatılmadan Platform adaptörünü draft tutar. Yeni yetkili salt okuma araştırmasında aynı Platform hedefinde auth/me, organizations ve projects HTTP200 verdi. Me zarfında success=true; organizasyon cevabında items ve total; proje cevabında boş dizi gözlendi. Bu üç gözlem çağrısı aynı 30 s bütçe içinde 0,193 s sürdü. Key-auth sözleşmesi, principal/account anlamı ve liste tamlığı bu sonuçlardan kanıtlanmadı. Kullanıcının project ID bilmemesi ilk liste okumalarını engellemedi.

Me cevabı kullanıcı sunum ve kişisel veri alanları da taşıyor. Bunları public modele almak veya her metadata alanını kimlik kararının parçası yapmak gerekmiyor. Bilinmeyen wire’ı generic dict olarak dışarı vermek de uygun değil. Bugünkü tam-provider-schema kapısı, belirsizliği açıkça koruyan dar bir okuma sonucunu dahi engelliyor.

## Karar önerisi

### 1. Uygulamaya başlama ve kapanış ayrı kapılardır

Onay sonrası P02-0d’de yalnız **unverified Platform observation** uygulanabilir. Mevcut public discover komutunun Platform seçimi, kod/test/kullanıcı belgesi tamamlandıktan sonra bu kapalı tipli varyanta bağlanır. Yeni debug/backend komutu veya kullanıcıdan kanıt enjekte etme seçeneği eklenmez. Bu ADR kabul edilene kadar mevcut unsupported_combination davranışı sürer.

Bu karar **P02-0d/P02-0b/P02-0 verified koşulunu kaldırmaz**. ADR-0020 kabul 6’daki Platform key kimlik sözleşmesi ve gerçek hizmet kabulü kapısı aynen kalır. Kod ve yerel testler bitse de açık dış koşullar kartta/raporda kalır; bunlar kapanmadan kart verified veya paket tamamlandı sayılmaz. Ayrı PR açılmaz, var olan tek P02-0 paket planı korunur. Böylece kodun ilerlemesi eksik yetki kanıtını saklamaz.

### 2. Raw veriden açıkça sınırlı projeksiyon

Platform normalizer’ı yalnız [referanstaki](../reference/context-discovery.md#önerilen-platform-gözlem-varyantı) alanları tüketir. Bu **Yörünge’nin kabul ettiği projeksiyon** sözleşmesidir; sağlayıcının eksiksiz OpenAPI’si veya bütün alanlarının kararlılık garantisi değildir.

- Ortak HTTP, deadline, byte/header/chunk, strict UTF-8/JSON, duplicate/nonfinite ve depth/node sınırları aynen uygulanır.
- Önce **tüm parse edilmiş raw ağacın** dinamik string değerleri ve tüketilmeyen metadata anahtarları mevcut literal-secret kuralıyla denetlenir. Tüketilmeyen alanlar bu taramadan kaçamaz. Sabit, açıkça tanımlı protokol anahtarları anahtarın kaynağı sayılmaz; serbest metadata anahtarları muaf değildir.
- Her endpoint’in root object’inde success varsa tüketilen kontrol alanıdır; strict bool=true zorunludur. False/non-bool, geçerli id veya items/total yanında da projeksiyondan önce invalid_response olur; bu bayrak metadata diye atılmaz. Endpoint root tür kuralı ayrıca korunur.
- Sonra yalnız tüketilen alanlar seçilir, strict ve extra=forbid iç/public modellere doğrulanır. Tüketilen alandaki yanlış tip, eksik zorunlu alan veya tutarsız ID controlled invalid_response olur. Bilinmeyen metadata çıktı, hata, log, cache veya diske aktarılmadan atılır.
- Bu dar adaptör sınırı, ortak decode_response veya diğer hizmet modellerini extra=ignore yapmaz. Diğer consumer’ların closed-codec davranışı korunur. Tüm PII/role/admin_permissions değerleri public sonuç dışında kalır.

Tüketilmeyen raw metadata’nın tek başına ret sebebi olmaması, ADR-0020/P02-0d’nin tüm raw unknown alanları reddetme beklentisine bu consumer için açık istisnadır. Public wire kapalı kalır. Kısmi veya yanlış kullanılan alan sessizce düşürülmez.

### 3. Gözlenen ID, doğrulanmış principal değildir

Platform sonucu her hedefte authentication=unknown, validation=unverified, authorization_scope=null ve consistency=not_guaranteed taşır. Provider principal/account/org/project alanları null; identity_status=unverified olur. Me yanıtından gelen üç ID yalnız ayrı reported_identity nesnesinde **hangi wire alanından geldiği belirli opak bildirimler** olarak sunulur. Bunlar principal, kullanıcı üyeliği, aktif hesap veya yürütme yetkisi diye adlandırılmaz.

Profil account/project tercihleri ve açık project seçimi selected altında tercih olarak korunur. Account ID’nin user mı organizasyon mu olduğu varsayılmaz. İlk organizasyon/proje, tek kayıt olsa bile otomatik seçilmez; config yazılmaz. Me listesindeki ID, profil seçiminin yerine geçirilmez. LLM varyantı, selected=null ve eski Context/config/Plan/Result anlamları değişmez.

### 4. Liste, seçim ve hata sonucu

Organizasyon/proje listeleri en çok 128 öğeyle tipli ID referanslarıdır. Provider total değeri yalnız reported_total olarak gösterilir. total=len(items) tamlık kanıtı değildir; completeness en iyi unknown olur. Bilinen total daha büyükse incomplete olur. Proje dizisinin boşluğu, hizmette hiç proje olmadığı veya erişim reddi anlamına gelmez. Sırf gözlemi zenginleştirmek için bilinmeyen pagination parametresi tahmin edilmez; cursor/Link takip edilmez.

Seçili project varsa dördüncü GET yalnız o açık ID içindir. Detail404 seçimin gözlenemediği sonucudur; silinmiş/izinsiz diye kesin hüküm verilmez. Detail200’de dönen ID istenen ID ile eşleşmelidir; başka ID invalid_response olur. Parent alanı doğrulanmış hesap anlamına bağlanmaz. Hiç project seçilmemişse boş/tek/çok listede selection_required nedeni korunur.

401/403 remote_access_denied,429 remote_rate_limited; liste/me404 invalid_response ve2xx logical failure invalid_response aynen kalır. Ham sağlayıcı mesajı kullanıcı hatasına taşınmaz. Hata bir listeyi sessizce boş başarıya çevirmez.

### 5. Yetki ve kaynak sınırları

Normal 3 GET, açık project detail ile en çok 4 GET/8 attempt, toplam 30 s, her response≤1 MiB/toplam≤4 MiB ve public output≤256 KiB değişmez. Herhangi bir limit aşımı kontrollü ret olur; sessiz kırpma yoktur. Same owned session, tek hizmet/env snapshot, no-init store, ağ sırasında kapalı transaction/lock ve son credential/epoch/clock/deadline kapısı ADR-0020 ile aynıdır. Yeni DB/cache/schema/secret backend eklenmez.

Bilinen biçimde negatif kontrol yoksa auth unknown kalır; bu öneri key sözdizimi uydurmaz veya normal discover içine negatif istek eklemez. Uzak yazma, proje/hesap oluşturma, upload/inference, şart kabulü, key oluşturma veya browser JWT/cookie fallback’i yoktur. Discovery hâlâ operation/admission/authorization producer değildir.

## Kabul ve uygulama sırası

Aynı araştırmanın HTTP sonrası analiz/parse hatası da çağrı slotunu tüketir; helper’ı değiştirmek sayaç/deadline bütçesini sıfırlamaz. Takip account probe’u ancak baştan tek yürütücüde tanımlı toplam bütçeyle yapılır; başarısız kayıt silinmez veya kabul koşusuna dönüştürülmez.

1. Kullanıcı bu ADR’yi onaylar; Platform referansının Proposed bölümü karar ve kartla birlikte uygulama sözleşmesine dönüşür. Onay öncesi ürün kodu yoktur.
2. Kapalı Platform public model, salt projeksiyon normalizer’ı, mevcut state/final kapısıyla ortak core; sonra CLI/API/text/JSON/NDJSON aynı kullanıma bağlanır. Büyük iş iki kod adımına ayrılır; her adım commit ve iki farklı fresh review turu içerir.
3. Bağımsız fixture’lar: me PII/role/serbest metadata atımı; yok/yanlış/duplicate/nonfinite/oversize tüketilen alan; **atılacak metadata içindeki secret**; kısa secret/protokol sabiti ayrımı; bool/int ve nullable/missing parent farkı. Geçerli organizations items/total yanında success=false,success=0 ve success="true" ayrı invalid_response fixture’larıdır.
4. Boş/tek/çok/duplicate128/129 liste, total<len/=/>, profile tercih/explicit project/detail404/yanlış detail ID; eksik parent, yeni metadata ve değişen sayfa/üyelikte unverified/tamlık sınırı korunur. Mevcut canlı boş proje örneği, dolu/selected-project canlı kabulü diye gösterilmez.
5. TLS gerçek request sınırı, tek env/hedef, no-init, iki süreç credential/reset/clock yarışı, timeout/retry/cleanup/SIGINT/pipe ve UTF-8/NDJSON; eski LLM ve offline v1 regresyonları.
6. Kaynak değiştiğinde tam test/statik/iki clean install ve yeni kaynak bağlı M5 startup/jobs yapılır; önceki LLM referansı güncel ürün kabulü yerine kullanılmaz. P02-0d’nin eksik auth/principal/pagination ve dolu/seçili proje live kabulü ayrı açık kalır. Yeni kullanım senaryoları bu gözlemden izin üretmez.

## Alternatifler ve sonuç

- Tam sözleşme gelene kadar bütün Platform kodlamasını bekletmek: ADR-0020’nin mevcut davranışı; onay verilmezse korunur.
- Ham dict veya sağlayıcının bütün profil/PII alanlarını yayınlamak: seçilmedi.
- 2xx/tek organizasyon/boş proje ile kimliği ve listeyi verified yapmak: seçilmedi.
- Bu öneriyle P02-0 kabulünü de daraltıp paketi verified saymak: seçilmedi; ayrı kullanıcı kararı olmadan kabul kapısı değişmez.

Öneri güven iddiasını büyütmeden çalışan bir gözlem diliminin kodlanmasını açar. Karşılığı, tam provider schema yerine tüketilen alan projeksiyonunun açıkça sahiplenilmesi ve eksik dış kabullerin görünür tutulmasıdır. Bu karar henüz Accepted değildir ve uygulanmış özellik sayılmaz.
