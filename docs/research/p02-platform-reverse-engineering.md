# Platform discovery — tersine mühendislik ve gerçek consumer gözlemi

**Tarih:** 2026-11-01. **Durum:** Kullanıcı mevcut Platform anahtarıyla salt okunur tersine mühendisliği yetkilendirdi. Bu rapor yeni davranış kanıtını kaydeder; sağlayıcı garantisi, key grammar/auth doğrulaması veya P02-0 kapanışı değildir. Ürün kaynağı2384a5c; [ADR-0020](../decisions/0020-service-bound-context-discovery.md)/[ADR-0021](../decisions/0021-platform-discovery-observations.md) Accepted kapıları halen bağlayıcıdır. [ADR-0022 önerisi](../decisions/0022-observed-platform-consumer-contract.md) bu raporun sınırlı tüketici sözleşmesi seçeneğini ayrı onaya sunar.

## Kapsam ve güven sınırı

Yalnız resmî yayımlanmış kamu istemcisi metin olarak incelendi ve kullanıcının önceden hazırladığı Platform key’iyle üç mevcut GET çağrısı yapıldı. JavaScript yürütülmedi; browser oturumu, JWT/cookie, özel hesap JSON’u veya başka hesabın kaynağı kullanılmadı. Yeni proje/anahtar oluşturma, anahtar rotasyonu, POST/PATCH/PUT/DELETE, upload/inference/şart kabulü yoktur. Discovery’nin normal yerel registry/clock gözlemi kendi mevcut store’unda çalıştı; yeni store veya migration oluşturulmadı. Kullanıcıdan secret değerini yeniden göndermesi istenmedi.

Araştırma için hazırlanan özel yürütücü; sayaç/slot kalıcılığı, atomik receipt/fsync/replace, setup/failure restorasyonu, ortak deadline/cleanup, doğru origin/path/header, kaynakta doğrulanmış HTTP/1.1 azami read boyutuyla önceden byte rezervi ve değer taşımayan descriptor açısından iki bağımsız preflight turundan geçti.19 çevrimdışı test geçti. İlk turlardaki atomik kayıt/restorasyon/cleanup/config-proje ve read-ahead bulguları **hesap çağrısından önce** düzeltildi. Bu yardımcı ürün runtime’ına veya yeni kullanıcı backend seçeneğine eklenmedi.

## Kamu istemcisinden doğrulanan yapı

Web okuyucusu hedefleri açamadığından dosyalar doğrudan credentialsız HTTPS ile alındı.10 GET/978.276 byte; baştan12 GET/4 MiB/30 s tavanı. Kaynak URL/byte/SHA kimlikleri [kaynak kaydında](evidence-register.md#1-kasım-platform-tersine-mühendislik-kaynakları). Kaynak, sağlayıcının kendi yayınladığı web istemcisidir; sunucunun bütün alanlarının kararlılık veya key-auth garantisi değildir.

| İstemci gözlemi | Çıkarılabilecek sonuç | Çıkarılamayacak sonuç |
|---|---|---|
| Ana API client baseURL api.ssyz.org.tr/api/v1; browser token’ını Authorization Bearer’a ekliyor | Web arayüzünün HTTP kökü ve kendi auth yolu | Aynı uçların API key semantiği veya browser JWT fallback gereği |
| GET wrapper success/data varsa data’yı açıyor, yoksa doğrudan gövdeyi döndürüyor | Bare ve zarf biçimleri istemcide birlikte mevcut | Her endpoint için tek evrensel envelope |
| Proje listesi search parametresi kullanıyor; list/detail Zod şeması id UUID ve nullable/optional org_id tanımlıyor | Proje tüketiminin alanları, route ve arama parametresi için kaynak var | Liste tamlığı veya API key’le aynı davranışın garantisi |
| Organization UI array veya items kabul ediyor | İstemci org listelerini bu iki şekille okuyabiliyor | total’ın anlamı, cursor/offset/end-of-list veya bütün üyelikler |
| API key oluşturma UI’sı kind=platform/llm_inference/model_inference ve credit_org_id kullanıyor | Key amaç ayrımı ve faturalama organizasyonu alanı istemcide var | VIEW adlı read scope’u, key grameri veya credit_org_id’nin etkin context olduğu |
| SyncAuthMe organization_id/personal_org_id/admin_permissions alanlarını UI store’una taşıyor | Alanlar web istemcisinde nasıl kullanılıyor görülebilir | Principal/account anlamının veya permission otoritesinin bağımsız kanıtı |

Orbit kamu API keşfi de denendi; dönen5 adayın hiçbiri EVREN endpoint’i değildi. Başka sağlayıcının benzer adlı projects endpoint’i kullanılmadı. Bu arama sonucu resmî sözleşmenin başka yerde bulunmadığı iddiası değildir.

## Tek sınırlı hesap koşusu

İlk pozitifler gerçek **api.discover_context evren-platform** yolunu; owned session/state capture/final gate ve üretim projeksiyon decoder’ını çalıştırdı. Araştırma kompozisyonu yalnız retry’ı daha dar tek denemeye düşürdü ve sayaç/descriptor topladı. Sonra aynı endpoint’lere hiç auth header’ı olmadan birer kontrol GET’i yapıldı. Biçimi tahmin edilmiş veya rastgele key üretilmedi. Bütün istekler aynı sayaç ve başlangıçtan30 s deadline’a bağlıydı; helper veya session değişimi bütçeyi sıfırlamadı.

| Endpoint | Seçili key | Anahtar yok | Gerçek tüketici / predicate |
|---|---:|---:|---|
| auth/me | 200 | 401 | Public DTO döndü; me ID Identifier koşulunu geçti |
| organizations | 200 | 401 |1 item; tüm ID’ler geçerli; total nonnegative-int64, total≥count ve total=count doğru |
| projects | 200 | 401 | Boş dizi; mevcut decoder kabul etti |
| projects/{id} | Çağrılmadı | Çağrılmadı | Profil/scope’ta seçili proje ve listede kayıt yok; ID tahmin edilmedi |

**Gerçek toplam:**6 mantıksal GET,6 wire attempt,0 retry,1.397 tüketilmiş raw-body byte,0,616151 s. İlan edilen tavan8 GET/8 attempt/4 MiB/30 s idi. Byte ölçümü tüketilen gövde chunk’larıdır; TCP/TLS paketleri veya tüketilmeyen hata gövdesi toplamı değildir. İleri okuma için64 KiB rezerv ve kapanış için1 s rezerv, sınırda daha erken kontrollü durmayı seçer. Bloke sistem I/O’suna fiziksel kesin süre garantisi verilmez. Probe yeniden çalıştırılmadı; özgün kayıt korunur.

[Değer taşımayan receipt](p02-platform-reverse-observations.json) field-name/type descriptor, sayaç, status ve bool predicate içerir; raw yanıt, gerçek ID, email/telefon/ad/TC kimlik değeri, key/env adı/tag/K, Cookie/Authorization veya imzalı URL içermez. Kaydedilen bilinen alan adları daha önceki descriptor ve yayımlanmış consumer kaynaklarıyla sınırlıdır; yeni serbest metadata anahtarları yayımlanmaz. Source/probe hash’i ve tamamlanan dosyanın UTC mtime’ı kaydedilir; mtime bağımsız ağ/zaman attestasyonu değildir.

## Kapanan belirsizlikler ve sınırlar

- Üç uç için **mevcut ürün parser’ının gerçek cevapları kabul ettiği** artık kanıtlandı. Önceki metadata receipt’inde eksik olan Identifier/total predikatları bu yeni koşuda gerçek decoder’dan geçti. Eski31 Ekim receipt’ine sonuç eklenmedi veya geçmiş başarısız/sınırı aşan araştırma kabul koşusuna çevrilmedi.
- Aynı hedef/endpoint/default parametrelerde seçili key’le200 ve header yokken401 gözlendi. Böylece tamamen anahtarsız aynı başarının elde edildiği ihtimali bu koşuda görülmedi. **Bu, key değerinin doğru doğrulandığını kanıtlamaz:** yalnız header varlığını kontrol eden bir sunucu da aynı farkı üretebilir. İyi biçimli invalid-key kontrolü yapılmadı; auth unknown kalır.
- total=count gözlemi sağlayıcının bütün listeyi döndürdüğünü kanıtlamaz. İstemcide pagination kontrolü görmemek de pagination olmadığı anlamına gelmez. Tamlık unknown ve uzak snapshot not_guaranteed kalır.
- Provider principal/account semantiği belirlenmedi. Reported ID’ler provider principal/account alanlarına taşınmadı; izin veya yetkili execution üretildiği iddia edilmez.
- Proje listesi bu key’le boştur. Gerçekte hiç proje yok, key scope’u farklı veya filtreleme var çıkarımlarından biri seçilmedi. Dolu proje/detail gerçek kabulü açık kalır. Kullanıcıya arayüzde mevcut proje bulunup bulunmadığı soruldu; otomatik kaynak oluşturulmadı.

## Devam seçeneği

Tersine mühendislik bu dar, doğrulanmamış tüketici için somut bilgi ve gerçek çalışma kanıtı sağladı. Bütün sağlayıcı şemasını veya key/principal/pagination semantiğini evrensel olarak kanıtlamaz. Mevcut Accepted ADR-0021’in nihai whole-raw unknown-ret ve güçlü dış kabul kapısı bu gözlemle kendiliğinden kapanmaz.

[ADR-0022](../decisions/0022-observed-platform-consumer-contract.md), bu dört read-only endpoint için **kanıta dayalı sınırlı tüketici sözleşmesini** nihai ürün sınırı yapmayı önerir: tüketilen alanlar/control’lar strict; tam raw-tree JSON/sır/byte sınırı; tüketilmeyen metadata atımı; public auth/identity/tamlık belirsizliği korunur. Bu, mevcut kapanış koşulunun açık kapsam değişikliğidir, geriye dönük başarılı kabul etiketi değildir. Yeni ADR onayı gelmeden bağımlı ürün/kart kapanışı yapılmaz. Seçili/dolu proje canlı kabulü öneride de ayrı açık tutulur.
