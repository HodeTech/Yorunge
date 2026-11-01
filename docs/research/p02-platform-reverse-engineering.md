# Platform discovery — tersine mühendislik ve gerçek consumer gözlemi

**Tarih:** 2026-11-01. **Durum:** Kullanıcı mevcut Platform anahtarıyla salt okunur tersine mühendisliği yetkilendirdi. Bu rapor yeni davranış kanıtını kaydeder; sağlayıcı garantisi, key grammar/auth doğrulaması veya P02-0 kapanışı değildir. Ürün kaynağı 2384a5c; [ADR-0020](../decisions/0020-service-bound-context-discovery.md)/[ADR-0021](../decisions/0021-platform-discovery-observations.md) Accepted kapıları halen bağlayıcıdır. [ADR-0022 önerisi](../decisions/0022-observed-platform-consumer-contract.md) bu raporun sınırlı tüketici sözleşmesi seçeneğini ayrı onaya sunar.

## Kapsam ve güven sınırı

Yalnız resmî yayımlanmış kamu istemcisi metin olarak incelendi ve kullanıcının önceden hazırladığı Platform key’iyle üç mevcut GET çağrısı yapıldı. JavaScript yürütülmedi; browser oturumu, JWT/cookie, özel hesap JSON’u veya başka hesabın kaynağı kullanılmadı. Yeni proje/anahtar oluşturma, anahtar rotasyonu, POST/PATCH/PUT/DELETE, upload/inference/şart kabulü yoktur. Discovery’nin normal yerel registry/clock gözlemi kendi mevcut store’unda çalıştı; yeni store veya migration oluşturulmadı. Kullanıcıdan secret değerini yeniden göndermesi istenmedi.

Araştırma için hazırlanan özel yürütücü; sayaç/slot kalıcılığı, atomik receipt/fsync/replace, setup/failure restorasyonu, ortak deadline/cleanup, doğru origin/path/header, kaynakta doğrulanmış HTTP/1.1 azami read boyutuyla önceden byte rezervi ve değer taşımayan descriptor açısından iki bağımsız preflight turundan geçti. 19 çevrimdışı test geçti. İlk turlardaki atomik kayıt/restorasyon/cleanup/config-proje ve read-ahead bulguları **hesap çağrısından önce** düzeltildi. Bu yardımcı ürün runtime’ına veya yeni kullanıcı backend seçeneğine eklenmedi.

## Denetlenebilir yürütücü ve test kaynağı

[Sürümlü kaynak arşivi](probes/platform-20261101/README.md), [özgün account_probe.py](probes/platform-20261101/account_probe.py) ve [özgün 19 vakalı test dosyasını](probes/platform-20261101/test_probe.py) içerir. Yürütücü receipt.probe_sha256 ile **bayt bayt aynı**dır; özgün receipt ve kaynak değiştirilmedi. Arşivdeki testler yeniden ağsız çalıştırıldı: **19 passed / 0,44 s**. Bu yeni yerel tekrar, önceki canlı koşunun veya tarihsel test koşusunun yeniden yapılmış olduğu iddiası değildir. Kaynakları burada sürümlemek sonraki reviewer’ın gerçek API çağrısını, sayaç/deadline’ı ve sanitization yöntemini okuyabilmesini sağlar; ağ olayına bağımsız attestasyon sağlamaz. Arşiv main() girişi canlı tekrar amacıyla çalıştırılmaz.

Bu rapordaki “tam ham ağaçta sır taraması” yalnız **seçili credential için mevcut literal-secret kuralıdır**: kısa UTF-8 değerde tam eşitlik, en az 8 byte değerde alt dize/tam eşitlik; açık sabit protokol anahtarı muafiyetleri yalnız seçilmiş şekildedir. Tüm sır türleri/başka credential veya dönüştürülmüş değerleri bulan genel sınıflandırma değildir. Metadata atımı bundan ve yapısal/boyut denetiminden sonra yapılır.

## Kamu istemcisinden doğrulanan yapı

Web okuyucusu hedefleri açamadığından dosyalar doğrudan credentialsız HTTPS ile alındı. 10 GET/978.276 byte; baştan 12 GET/4 MiB/30 s tavanı. Kaynak URL/byte/SHA kimlikleri [kaynak kaydında](evidence-register.md#1-kasım-platform-tersine-mühendislik-kaynakları). Kaynak, sağlayıcının kendi yayınladığı web istemcisidir; sunucunun bütün alanlarının kararlılık veya key-auth garantisi değildir.

| İstemci gözlemi | Çıkarılabilecek sonuç | Çıkarılamayacak sonuç |
|---|---|---|
| Ana API client baseURL api.ssyz.org.tr/api/v1; browser token’ını Authorization Bearer’a ekliyor | Web arayüzünün HTTP kökü ve kendi auth yolu | Aynı uçların API key semantiği veya browser JWT fallback gereği |
| GET wrapper success/data varsa data’yı açıyor, yoksa doğrudan gövdeyi döndürüyor | Bare ve zarf biçimleri istemcide birlikte mevcut | Her endpoint için tek evrensel envelope |
| Proje listesi search parametresi kullanıyor; list/detail Zod şeması id UUID ve nullable/optional org_id tanımlıyor | Proje tüketiminin alanları, route ve arama parametresi için kaynak var | Liste tamlığı veya API key’le aynı davranışın garantisi |
| Organization UI array veya items kabul ediyor | İstemci org listelerini bu iki şekille okuyabiliyor | total’ın anlamı, cursor/offset/end-of-list veya bütün üyelikler |
| API key oluşturma UI’sı kind=platform/llm_inference/model_inference ve credit_org_id kullanıyor | Key amaç ayrımı ve faturalama organizasyonu alanı istemcide var | VIEW adlı read scope’u, key grameri veya credit_org_id’nin etkin context olduğu |
| SyncAuthMe organization_id/personal_org_id/admin_permissions alanlarını UI store’una taşıyor | Alanlar web istemcisinde nasıl kullanılıyor görülebilir | Principal/account anlamının veya permission otoritesinin bağımsız kanıtı |

Orbit kamu API keşfi de denendi; dönen 5 adayın hiçbiri EVREN endpoint’i değildi. Başka sağlayıcının benzer adlı projects endpoint’i kullanılmadı. Bu arama sonucu resmî sözleşmenin başka yerde bulunmadığı iddiası değildir.

## Tek sınırlı hesap koşusu

İlk pozitifler gerçek **api.discover_context evren-platform** yolunu; owned session/state capture/final gate ve üretim projeksiyon decoder’ını çalıştırdı. Araştırma kompozisyonu yalnız retry’ı daha dar tek denemeye düşürdü ve sayaç/descriptor topladı. Sonra aynı endpoint’lere hiç auth header’ı olmadan birer kontrol GET’i yapıldı. Biçimi tahmin edilmiş veya rastgele key üretilmedi. Bütün istekler aynı sayaç ve başlangıçtan 30 s deadline’a bağlıydı; helper veya session değişimi bütçeyi sıfırlamadı.

| Endpoint | Seçili key | Anahtar yok | Gerçek tüketici / predicate |
|---|---:|---:|---|
| auth/me | 200 | 401 | Public DTO döndü; me ID Identifier koşulunu geçti |
| organizations | 200 | 401 | 1 item; tüm ID’ler geçerli; total nonnegative-int64, total≥count ve total=count doğru |
| projects | 200 | 401 | Boş dizi; mevcut decoder kabul etti |
| projects/{id} | Çağrılmadı | Çağrılmadı | Profil/scope’ta seçili proje ve listede kayıt yok; ID tahmin edilmedi |

**Gerçek toplam:** 6 mantıksal GET, 6 wire attempt, 0 retry, 1.397 tüketilmiş raw-body byte, 0,616151 s. İlan edilen tavan 8 GET/8 attempt/4 MiB/30 s idi. Byte ölçümü tüketilen gövde chunk’larıdır; TCP/TLS paketleri veya tüketilmeyen hata gövdesi toplamı değildir. İleri okuma için 64 KiB rezerv ve kapanış için 1 s rezerv, sınırda daha erken kontrollü durmayı seçer. Bloke sistem I/O’suna fiziksel kesin süre garantisi verilmez. Probe yeniden çalıştırılmadı; özgün kayıt korunur.

[Değer taşımayan receipt](p02-platform-reverse-observations.json) field-name/type descriptor, sayaç, status ve bool predicate içerir; raw yanıt, gerçek ID, email/telefon/ad/TC kimlik değeri, key/env adı/tag/K, Cookie/Authorization veya imzalı URL içermez. Kaydedilen bilinen alan adları daha önceki descriptor ve yayımlanmış consumer kaynaklarıyla sınırlıdır; yeni serbest metadata anahtarları yayımlanmaz. Source/probe hash’i ve tamamlanan dosyanın UTC mtime’ı kaydedilir; mtime bağımsız ağ/zaman attestasyonu değildir.

## Kapanan belirsizlikler ve sınırlar

- Üç uç için **mevcut ürün parser’ının gerçek cevapları kabul ettiği** artık kanıtlandı. Önceki metadata receipt’inde eksik olan Identifier/total predikatları bu yeni koşuda gerçek decoder’dan geçti. Eski 31 Ekim receipt’ine sonuç eklenmedi veya geçmiş başarısız/sınırı aşan araştırma kabul koşusuna çevrilmedi.
- Aynı hedef/endpoint/default parametrelerde seçili key’le 200 ve header yokken 401 gözlendi. Böylece tamamen anahtarsız aynı başarının elde edildiği ihtimali bu koşuda görülmedi. **Bu, key değerinin doğru doğrulandığını kanıtlamaz:** yalnız header varlığını kontrol eden bir sunucu da aynı farkı üretebilir. İyi biçimli invalid-key kontrolü yapılmadı; auth unknown kalır.
- total=count gözlemi sağlayıcının bütün listeyi döndürdüğünü kanıtlamaz. İstemcide pagination kontrolü görmemek de pagination olmadığı anlamına gelmez. Tamlık unknown ve uzak snapshot not_guaranteed kalır.
- Provider principal/account semantiği belirlenmedi. Reported ID’ler provider principal/account alanlarına taşınmadı; izin veya yetkili execution üretildiği iddia edilmez.
- Proje listesi bu key’le boştur. Gerçekte hiç proje yok, key scope’u farklı veya filtreleme var çıkarımlarından biri seçilmedi. Dolu proje/detail gerçek kabulü açık kalır. Kullanıcıya arayüzde mevcut proje bulunup bulunmadığı soruldu; otomatik kaynak oluşturulmadı.

## Devam seçeneği

Tersine mühendislik bu dar, doğrulanmamış tüketici için somut bilgi ve gerçek çalışma kanıtı sağladı. Bütün sağlayıcı şemasını veya key/principal/pagination semantiğini evrensel olarak kanıtlamaz. Mevcut Accepted ADR-0021’in nihai whole-raw unknown-ret ve güçlü dış kabul kapısı bu gözlemle kendiliğinden kapanmaz.

[ADR-0022](../decisions/0022-observed-platform-consumer-contract.md), bu dört read-only endpoint için **kanıta dayalı sınırlı tüketici sözleşmesini** nihai ürün sınırı yapmayı önerir: tüketilen alanlar/control’lar strict; tam raw-tree JSON/sır/byte sınırı; tüketilmeyen metadata atımı; public auth/identity/tamlık belirsizliği korunur. Bu, mevcut kapanış koşulunun açık kapsam değişikliğidir, geriye dönük başarılı kabul etiketi değildir. Yeni ADR onayı gelmeden bağımlı ürün/kart kapanışı yapılmaz. Seçili/dolu proje canlı kabulü öneride de ayrı açık tutulur.

## Birinci fresh belge ve kanıt review turu

bcb3ede için iki yeni ajan adr22_r1_contract / adr22_r1_evidence karar/tüketici sınırını ve kanıt/gizlilik zincirini bağımsız inceledi; yeni doğrulanmış bulgu yok. Proposed/onay kapısı, dar kabul kapsamı değişikliği, no-authority wire, key/no-key kanıtının sınırı ve dolu/seçili proje canlı kapısı tutarlı. Receipt yalnız 35 bilinen profil alanının tipleri ve diğer güvenli metadata/predikatları taşır; gerçek ID/key/PII değeri yoktur. Probe hash’i,10 kamu dosyası URL/byte/SHA eşliği ve 978.276 byte toplamı karşılaştırıldı.

142 belge/6 skill/16 kart,155 arşiv ve iki mevcut current-source M5 verifier geçti; runtime/test/script/workflow kaynakları değişmedi. Özgün private receipt hash/mtime veya ağ olayının bağımsız attestasyonu iddia edilmedi. Review sırasında credentials/scope/state/key okunmadı, probe/ağ veya yeni performans çalıştırılmadı. İkinci tur farklı fresh ajanlarla bu kayıt commit’inden sonra yapılır.

## İkinci fresh belge ve kanıt review turu

6863041 üzerinde farklı yeni ajanlar adr22_r2_contract / adr22_r2_evidence cumulative araştırma/karar/kanıt değişikliğini bağımsız inceledi; yeni doğrulanmış bulgu yok. ADR-0022’nin hangi nihai kabul kapısını değiştirdiği ve Proposed/onay sınırı açık; strict tüketilen alan, tam raw-tree sır taraması, unknown/unverified/no-authority ve dolu/seçili canlı proje şartı tutarlı.

6 GET/6 attempt/key 200-no-key 401/1.397byte/1 org–0 proje ve gerçek API/projeksiyon predikatları receipt ile eşleşti. 10 kamu source URL/byte/SHA’sı ve 978.276 byte toplamı, helper SHA ve 19 parametrik preflight vakasının helper kapsamı karşılaştırıldı.142 belge/155 arşiv ve mevcut iki current-source M5 referansı geçti; runtime/test/script/workflow kaynakları değişmedi. Credentials/scope/state/key veya özel hesap receipt’i okunmadı; probe/ağ/ürün testi/benchmark tekrarlanmadı. Ağ olayı veya private receipt mtime/hash’i bağımsız attestasyon sayılmadı. Karar kullanıcı onayına hazırdır; mevcut Accepted kapılar ve blocked/draft/partial statüler henüz değişmedi.


## Proje hazırlığına ilişkin sonraki kullanıcı yanıtı

Kullanıcı mevcut projesi olmadığını bildirdi; ardından boş private test projesinin sayfa URL’sini paylaştı. Gerçek ID burada yayımlanmaz. Bu yeni test kaynağı ayrı amaç/sayaç/deadline ile hazırlanacak seçili-proje salt okuma kabulünde kullanılabilir; önceki 6 GET koşusuna çağrı eklemek veya onun tavanını/deadline’ını yeniden başlatmak değildir. Bu not proje endpoint’inin kabulü veya ADR-0022 onayı sayılmaz; henüz bu proje için yeni çağrı yapılmadı.

## Kullanıcı ADR-0022 review bulgularının revizyonu

Özgün doğrulanmış kimlik/bağ ihtiyacı [P02-R1](../roadmap/tasks/p02-r1-verified-context-binding.md) ve backlog B14 altında P02 identity-context sahibine bağlandı. Nihai gözlem sözleşmesi önerisi bu ihtiyacı tamamlanmış saymaz. Özgün probe ve 19 vakalı test kaynağı receipt hash’i korunarak sürümlendi; literal-secret denetiminin seçili credential, kısa/uzun değer ve protokol anahtarı sınırı kanonik referansta açıklığa kavuştu. ADR’ye kullanıcı sonucu ve kabul madde bazlı kaldırılır/yeniden yazılır/korunur eşlemesi ile tüm onay sonrası dosya/anchor geçiş listesi eklendi. 35 toplam/3 tüketilen/32 atılan alan hesabı, kanonik ürün adı, güncel indeks tarihleri ve ADR-0021 Accepted kaydı düzeltildi.

Aktif P02-0b/d kabul kapıları onay gelmeden değiştirilmedi. Bu, review bulgusunun atlanması değildir: somut değişiklik ADR’de onaylanabilir biçimde yazıldı; henüz kabul edilmemiş öneri mevcut Accepted kararı geçersiz kılamaz. Ürün davranışı, source-bound kapsam ve geçmiş receipt’ler değişmedi. Mevcut 93 tüketici ve 19 arşiv test vakası birlikte **112 passed**; docs/skill/kart kontrolleri geçti.

[Seçili-proje kabul yürütücüsü ve testleri](probes/platform-project-20261101/README.md) ayrı araştırma kaynağıdır. Gerçek API/final-state yoluna sayaç ekler; özgün helper’ın doğrulanan aynı baytlarını çalıştırır. Bir kez 4 pozitif GET ve yalnız yeni detail için 1 missing-key GET, toplam en çok 5 GET/5 attempt/4 MiB/30 s; önceki koşu veya formal pilot sayacıyla birleştirilmez. Sentetik MockTransport/SQLite ile **10 test** geçti. İlk test denemesindeki buffered-response fixture hatası ve düzeltmesi kaynak açıklamasında korunur. Canlı çalıştırma öncesinde iki farklı fresh review turu yapılır; bu hazırlık canlı başarı değildir.

## Kullanıcı review revizyonu — birinci fresh tur

70e60f8 üzerinde iki yeni ajan adr22_revision_r1_contract ve adr22_revision_r1_probe madde eşlemesi/özgün ihtiyaç/literal kapsamı ile yürütücü/hash/bütçe/gizliliği ayrı inceledi; yeni doğrulanmış bulgu yok. Ana incelemede son session cleanup dönüşünde toplam deadline’ın ayrıca karşılaştırılması eklendi; sentetik geç kapanış artık transport_timeout olur ve kabul sayılmaz. Yeni yürütücü **10 vaka**, değişmez arşiv **19 vaka**, mevcut tüketici **93 vaka** kapsamındadır.

155 arşiv ve iki güncel kaynak bağlı M5 verifier geçti; bunlar yeni performans koşusu değildir. 70e60f8 paket build’i wheel **66**, sdist **412** izinli üyeyle geçti; altı probe/README kaynağı sdist’te, özel hazırlık/bytecode/raw arşivleri dışarıdadır. Ek üyelik kontrolünün ilk iki yardımcı denemesi build dizinindeki arşiv olmayan dosyayı seçme ve inspect_archive’ın zaten kökü ayıran dönüş tipini yanlış yorumlama nedeniyle reddedildi; artifact allowlist kontrolleri ve düzeltilmiş üyelik kontrolü geçti. İki nested README ayrıca H1/fence/local-link kontrolünden geçti; ana docs checker’ın flat kapsamına dahil oldukları iddia edilmez. Yeni runtime/full-suite/temiz kurulum veya benchmark bu belge/research değişikliğinde tekrarlanmadı; mevcut runtime kanıtı aynı kaynak baytlarına bağlıdır.

Canlı proje çağrısı henüz yapılmadı. İkinci fresh tur farklı ajanlarla bu kapanış ve deadline düzeltmesi commit edildikten sonra yapılır. ADR-0022 Proposed ve aktif Accepted kabul kapıları değişmedi.
