# Upload input ve current hazırlık sözleşmesi

**Tarih:** 2026-11-03. **Durum:** P02-2o.1 input/revalidation iki fresh turla yerel olarak kapandı; o.2 readonly producer kodlandı, iki fresh tur bekliyor; o.3 henüz uygulama öncesi dar hedeftir. [Transfer](dataset-transfer.md#gönderilen-ve-doğrulanan-içerik), [v2 current gate](dataset-upload-v2.md), [provider](platform-upload-consumer.md) ve [HTTP bütçesi](dataset-upload-http.md) kanoniktir; public API henüz uygulanmış değildir.

## Yerel güncel içerik

Plan, approve ve original start'ın her biri manifestin tam dosya kümesini yeniden hash'ler; kaydedilmiş digest veya eski metadata tek başına inputs_verified değildir. Manifest parse ve kaynak hash no-follow/nonblocking descriptor, root/ancestor, ad/Unicode/üyelik ve hash öncesi/sonrası stat kurallarıyla P02-1 yolunu kullanır. Yerel validation kontrol noktaları en çok 30 s bütçedir; original total end daha erkense uygulanır. Upload alt kümesi 1–128 dosya, dosya başına 500.000.000 byte, toplam 1 GiB ve encoded manifest 256 KiB ile ayrıca sınırlıdır; boş envanter input_invalid, geçerli ama upload kotası üstü envanter input_budget_exceeded verir. Tam içerik eşliği yoksa input_changed; desteklenmeyen primitive ve özel dosya mevcut kontrollü input hatalarını korur.

Başarılı hash sonrasında private observation root anchor/device/inode, mutlak ancestor zinciri, bütün file stat/parent zincirleri ve dizin stat/üyelik kümelerini yakalar. FD tutulmadan immutable gözlem saklanabilir; her sonraki effect/current kapısında yeni descriptor'larla bütün bu metadata/üyelik ve root zinciri yeniden denetlenir. Yeniden açmada ENOENT/ELOOP/ENOTDIR gözlenmiş root/ancestor değişimi olarak input_changed verir; EACCES gibi gerçek okunabilirlik hataları file_unreadable kalır. İlk capture başlangıç hataları mevcut sınıflandırmasını korur. Bu ara recheck içerikleri yeniden hash'lemez ve yerel hash kontrolünün yerine geçmez. PUT kaynağı kendi güncel descriptor'ını açar ve gönderilen bütün byte/SHA-256/size eşliğini ayrıca doğrular. Gözlenmeyen değişimler/seri gözlem aralığı atomik snapshot veya düşmanca local sandbox değildir.

Private input observation PID/thread'e bağlıdır; aynı çağrının async/sync köprüsünde kullanılabilir. Kopyalanamaz/serialize edilmez, repr root/path/content dökmez. Recheck aynı immutable observation'ı taşır; yeni total end üretmez. Her kısa local recheck yeni dar I/O bütçesi alır, original total end'i genişletemez. Root/manifest/path dinamik değerleri seçili credential literal kuralıyla ağ/state/output öncesinde denetlenir.

## Warning üretmeyen request revalidation

Frozen/model_copy/model_construct kanıt değildir. Private request codec'i önce Python scalar/nested model verisini strict yeniden doğrular, sonra bounded canonical JSON model kontrolü yapar. Hatalı modeli warning yayımlayan serializer ile dışarı dökmez; warning-as-error ortamı ham UserWarning'e dönmez. Geçersiz girdinin repr'i, warning metni ve validation exception chain'i public hatada yer almaz. Ret invalid_request/2'dir; bilinen seçili literal kuralı ve fixed protocol key istisnaları değişmez.

## Provider ve kompozisyon dilimleri

O.2 zorunlu GET'leri aynı budget/session/credential üzerinden provider codec'ine bağlar; geçerli bildirilen context not_exposed üretir, grant/cost üretmez. Upload action'ında dataset bilindiğinde my-role upload etiketi zorunludur; read için upload izni varsayılmaz; read/metadata yetki kanıtı değildir. Exact hata/proof/freshness tablosu v2 referansında kalır.

O.3 private prepare/approve/revoke kullanım senaryolarını bu input/current gözlemlerine bağlar. Açık state init gerekir; captured scope/store/epoch/clock/credential son kısa transaction'da yeniden karşılaştırılır. Ağ veya tam hash boyunca SQLite store/deadline tutulmaz. Bu son iki dilimin tam internal imzaları kod başlamadan kendi reference maddeleriyle somutlaştırılır; burada henüz uygulanmış yüzey iddia edilmez.

## O.2 private current reader

ObservedUploadReader, exact scoped HttpCredential ve original UploadBudget'e bağlıdır; aynı UploadHttpxTransport üstünde yalnız GET yapar. Callback/fake grant veya cost kaynağı yoktur. Constructor scope/selected literal/official target'ı denetler. Her probe tek 30 s monotonic deadline alır (original total end daha erkense o); Pozitif/not_exposed checked_at ilk mandatory GET öncesindeki UTC'dir, HTTP sonunda yeniden yazılmaz. Yeni HTTP/schema negatifinin checked_at'ı o hatanın gözlendiği UTC'dir; eski pozitif kanıt yenilenmez. Böylece 30 s probe sonunda oluşan gerçek transport_timeout, eski pozitif snapshot tazeliğiyle upload_plan_not_valid'a maskelenmez; negatifin final transaction'daki 30 s kuralı ayrıca uygulanır. Return'de 30 s freshness ve yerel input metadata tekrar kontrol edilir. Final repository credential/epoch/clock/time transaction kapısı ayrıca kalır.

Private girişler: preparation(client)→AuthorizationCheck(create_private_dataset); current(client, plan, inputs, action, expected_dataset=None)→UploadCurrentCheck (create/link/upload write kapıları); read_authorization(client, expected_dataset, parameters)→AuthorizationCheck(read_created_dataset). Known dataset parametresi ancak gerçek strict create DTO'sundan veya onaylı durable baseline'dan gelir; güncel owned cevabı tarihsel expected yerine konmaz. Yeni receipt baseline formatı ADR-0027 Proposed/onay kapısındadır; bu reader onu yazmaz veya kendiliğinden üretmez.

| Action | Mandatory okumalar | Sonuç |
|---|---|---|
| preparation/create | auth/me + seçili project | exact bildirilen context; not_exposed |
| link | context + known ID owned lookup + exact username/slug detail | tam expected create DTO eşliği; not_exposed |
| upload | link okumaları + project membership + exact my-role | ilişki + has_upload gözlemi; not_exposed ve ayrı UploadObservation |
| read | context + known ID owned lookup + detail + membership | current exact metadata; not_exposed, upload grant/etiketi gerektirmez |

Owned lookup page=1..128/page_size=128/scope=owned; her sayfanın canonical ID'leri ve gözlenen sayfalar arasında duplicate ID reddedilir. ID bulununca yalnız o detail rotası kullanılır; kısa/boş sayfada veya tavan sonunda bulunamama invalid_response. Bu lookup liste tamlığı/snapshot kanıtı değildir. Bütün read/physical retry/response byte'ları aynı n bütçesinde sayılır.

Mandatory HTTP/schema/typed negative, v2 tablosundaki denied/unavailable/invalid Check'e eşlenir; yalnız bütün mandatory kapılar geçtiyse not_exposed. Local input, deadline veya quota hatası authority yokluğu gibi yutulmaz. Parametre/plan/current scope uyuşmazlığı HTTP öncesi kontrollü ret verir. Bu profil planın mevcut gerçek grant/cost baseline'ını yenileyemez; böyle bir saved plan için upload_plan_not_valid, sıfır HTTP.

CurrentCheck earliest checked_at'ı korur; controller aynı exact action/dataset/scope/input bağındaki ≤30 s gözlemi yeniden kullanabilir, her arm'da yeni local metadata recheck ve repository final freshness/CAS gerekir. Bu okuma cache'i grant üretmez ve tarihi yeni zamana kaydırmaz. Known negative görüldüğünde controller workflow'u durdurur; yeni call eski negative'i unavailable/not_exposed'a dönüştüremez.
