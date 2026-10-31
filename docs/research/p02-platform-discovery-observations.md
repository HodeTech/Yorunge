# Platform discovery — sınırlı şema gözlemleri

**Tarih:** 2026-10-31. **Durum:** Yetkili raw-schema araştırması; ürün, auth veya P02-0d kabulü değildir. [ADR-0020](../decisions/0020-service-bound-context-discovery.md) yürürlükte; [ADR-0021](../decisions/0021-platform-discovery-observations.md) Proposed. Sağlayıcının tam sözleşmesi veya yeni bir permission kaynağı oluşturulmadı.

## Kapsam ve yöntem

Kullanıcının daha önce hazırladığı seçili Platform key’i yalnız yerel çocuk süreçte okundu. Hedef sabit https://api.ssyz.org.tr/api/v1; yalnız GET auth/me, organizations, projects. Ortak P01 owned HttpSession/HTTPX, doğrulanmış HTTPS, redirect/cookie/proxy/log sınırı ve strict JSON kullanıldı. Hiçbir uzak kaynak oluşturulmadı, şart kabul edilmedi; browser oturumu kullanılmadı. Araştırma registry’ye yeni credential veya negatif key yazmadı.

Bu raw-schema incelemesi, normal discovery veya şeması önceden bilinen contract kabulü değildir. Devam serisinde iki tek-endpoint girişimi ve üç-endpoint survey olmak üzere **toplam 5 mantıksal GET başlatıldı**; ilk girişim analiz hatasıyla bitti. Bu birikimli seri ADR-0020 contract pilotunun 4 pozitif GET/30 s tavanını karşılamadı; bu sapma kabul başarısı sayılmaz. Tavanlar yalnız son üç-GET survey için ayrıca ölçüldü. Bundan sonra bu araştırmada yeni hesap çağrısı yapılmadı; önceki başarısız/dar kayıtlar korundu. Yalnız alan adı/türleri, dizi sayıları, HTTP status, logical success ve pagination-header varlığı toplandı. Raw kullanıcı değerleri, ID’ler, email/telefon/diğer kişisel alan değerleri, key/header veya ham gövde saklanmadı/yayımlanmadı. Şema descriptor’ü payload değerlerinin yerine geçmez; sağlayıcı garantisi değildir.

İlk tek-endpoint özetleyicide SecretValue yerine str bekleyen helper’a yanlış tip verilmesi analiz hatasına yol açtı. Başarısız receipt korundu, kabul kanıtı sayılmadı. Düzeltme ağsız sentetik secret/PII/type/boyut örnekleriyle doğrulandı; sonraki dar me gözlemi200/success=true verdi. Ardından ayrı, baştan limitli survey çalıştırıldı. Başarısız veya dar probe, birleşik survey’in 30 s ölçümüne eklenmiş ya da eksiksiz contract kabulü diye gösterilmedi.

Birleşik survey 31 Ekim 23:27:23 Europe/Istanbul’da üç mantıksal GET’i **0,193011 s** içinde tamamladı. İlan edilen tavan3 GET/6 attempt/3 MiB/30 s; kullanılan response gövdesi toplam **1.350 byte**. Retry sahibi ortak taşıma, her read-only GET en çok2 attempt; gerçek attempt sayısı ayrıca ölçülmedi, üç attempt yapıldığı iddia edilmez. Aşağıdaki sonuçlar yalnız varsayılan parametre kapsamındadır; başka hedef/query/project’e taşınmaz.

## Gözlem tablosu

| Endpoint | Sonuç | Gözlenen dar yapı | İddia sınırı |
|---|---|---|---|
| GET /api/v1/auth/me | HTTP200,1.036 byte; success=true | success/data/message/meta zarfı; data35 alanlı object. id,organization_id,personal_org_id string; önceki dar gözlemde UUID metin biçimi | Raw ID’lerin principal/account anlamı veya API-key auth sözleşmesi doğrulanmış değil |
| GET /api/v1/organizations | HTTP200,312 byte | items dizisi1 kayıt; total integer. Öğede id/owner_id string ve başka metadata | Bir kayıt gözlenmesi veya total alanının varlığı tam liste/üyelik/yazma izni değildir |
| GET /api/v1/projects | HTTP200,2 byte | Boş JSON dizisi | Bu anahtarlı isteğin cevabıdır; Platform’da hiç proje olmadığı veya erişim olmadığı sonucu çıkarılmaz. Dolu proje/detail şeması canlıda sınanmadı |

Üç response’ta Link/X-Total-Count/X-Has-Next/X-Next-Cursor/Content-Range gözlenmedi. Header yokluğu pagination’ın bulunmadığını veya listenin tamam olduğunu kanıtlamaz. Proje seçimi/config yazımı yapılmadı; account/project ID’nin önceden girilmemesi bu ilk okumaları engellemedi.

## Açık kanıt ve ürün kararı

Provider tarafından tanımlı key syntax/length/prefix bütünü henüz yok; tahmini negatif key üretilmedi. Üç pozitif2xx auth doğrulaması değildir, authentication unknown kalır. Me id’sinin account veya organization yerine kullanılacağı varsayılmaz. Kamu kılavuzundaki dataset cursor kuralı bu listelere aktarılmaz.

[ADR-0021](../decisions/0021-platform-discovery-observations.md), kapalı public wire ve tüm raw ağaçta sır/JSON sınırlarıyla **unverified projeksiyon** kodlamasını önerir. Bu, mevcut hard raw/key başlangıç kapısını kısmen değiştirir ve kullanıcı onayı ister; kabul/verified kapısını değiştirmez. Onaysız ürün kodu veya yeni Platform success yüzeyi eklenmedi. [Hazır provider bilgi talebi](../p02-account-setup.md#platform-sözleşme-kapısını-açmak) hâlâ geçerlidir.

## Platform chatbot cevabının kontrolü

Kullanıcı, Platform chatbot’unun sözleşme açıklamasını paylaştı. Bu metin bir arama ipucudur; sürüm/hash veya doğrudan OpenAPI dosyası olmadan normatif provider sözleşmesi sayılmaz. Yeni account çağrısı yapılmadan mevcut metadata receipt’i ve güncel resmî yayımlanmış istemci/kılavuz karşılaştırıldı.

| Chatbot iddiası | Doğrulama | Kullanım kararı |
|---|---|---|
| Base URL ve X-API-Key | Kamu kılavuzu ve yapılan sorguyla uyumlu | Genel hedef/header bilgisi olarak yararlı; endpoint/key-auth garantisi değil |
| auth/me minimum user_id | Receipt data.id gösteriyor, user_id yok | user_id’ye göre parser yazılamaz; id’nin principal/account anlamı ayrıca açık |
| organizations org_id/display_name/role | Gözlenen item alanları id/name; belirtilen üç alan yok | Gözlenen items/total şekli esas alınır; role veya membership uydurulmaz |
| projects ve detail minimum project_id | Güncel resmî web istemcisinin list/detail şemaları id UUID bekliyor | project_id ile uyuşmuyor; dolu/seçili proje live kabulü hâlâ yapılmadı |
| organizations limit/offset, genellikle10 veya20 | Teyitli endpoint parametre/tamlık tanımı bulunamadı | Parametre veya varsayılan sayfa boyutu tahmin edilmez |
| Guide’da tam Swagger/OpenAPI | Erişilebilen güncel Guide asset’inde OpenAPI/Swagger ifadesi veya doğrudan şema bağlantısı bulunamadı | Başka/oturumlu doküman olmadığı iddia edilmez; gerçek dosya URL’si gerekir |
| evren_plt_ + alfa-numerik biçim; VIEW scope;401/403 ayrımı | Metin kesin uzunluk/karakter grameri veya yetkili endpoint scope/hata şeması vermiyor | Negatif kontrol key’i veya permission/auth çıkarımı için yeterli değil |

Önceki kullanıcı özetinde geçen total=1 değeri receipt’te kayıtlı değildir. Kanıtlanan şey **1 gözlenen item ve total’ın integer türü**dür; total’ın sayısal değeri bu kayıtla doğrulanamaz. Tablo veya kabul fixture’ı bu değeri canlı gözlem diye sabitlemez. Ayrıca total=len(items) gözlense bile tamlık kanıtı sayılmaz.

Yeni [kamu kaynak kimlikleri](evidence-register.md#31-ekim-platform-chatbot-sözleşme-kontrolü) kod/hesap kanıtından ayrıdır. Kılavuz normal dataset kullanımını açıklar; provider contract veya chatbot’tan aktarılan açıklama birbirine dönüştürülmez. Doğrudan çalışan OpenAPI JSON/YAML URL’si ve endpoint response schema referansı gelirse Accepted ADR-0020’nin mevcut kanıt yolu yeniden değerlendirilir.

## Doğrulamanın sınırı

Sentetik probe kontrolleri sadece özetleyicinin değer yayımlamama ve limit davranışını denetler; ürün regresyon takımı değildir. Kaydedilen metadata bir davranış gözlemidir, doğrulanmış provider OpenAPI veya tam nonempty-project oracle’ı değildir. Ürün kodu/test/ölçüm/workflow kaynakları değişmedi; yeni performans ölçümü yapılması gerekmiyor. Önceki LLM yerel kapanışı bu Platform araştırmasıyla yeniden etiketlenmez.

Küçük [metadata receipt’i](p02-platform-discovery-observations.json) özgün baytlarıyla sürümlendi; SHA256 `bdb18c7aabc66ca3a5c8ae3b2e14f7a38a05ae71d34788980dfd68589d1aae1b`. Yalnız descriptor/request metadata’sı içerir; ham hesap cevabı değildir. Hash içerik eşliğidir, bağımsız ağ veya kimlik doğrulama kanıtı değildir. Performans/gzip arşiv kataloğundaki 152 kayıt bu dosyayı kapsamaz.
