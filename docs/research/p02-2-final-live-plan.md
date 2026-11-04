# P02-2 nihai canlı kabul planı

**Tarih:** 2026-11-04. **Durum:** Kullanıcı bu somut kapsamı onayladı; tek deneme b9f3101 kaynağında create sonrasında `operation_uncertain` ile durdu. 1 create, 10 GET, 0 upload; accepted CreateReceiptV2 aynı unknown operation’da korunuyor. Yazma yetkisi tüketildi; yeni create veya devam denemesi yapılmaz. [Kabul kaydı](p02-2-implementation-validation.md) başarısız özgün receipt’in kanonik sahibidir. Sahip [P02-2c kabul 8](../roadmap/tasks/p02-2c-upload-recovery-acceptance.md#kabul). Önceki [partial pilot](p02-2-private-create-observations.md) de tüketilmiş araştırma yetkisidir.

## Tek denemenin kapsamı

Mevcut hazırlıktaki Platform anahtarı ve kullanıcının önceden oluşturduğu private test projesi açıkça seçilir. İlk GET yalnız o projenin dar owner/org/private alanlarını okur; bildirilen owner seçimi sonraki public prepare tarafından auth/me/proje bağlamıyla tekrar kontrol edilir. Bu seçim doğrulanmış yetki değildir. Yeni private dataset aynı owner/projeye bağlanır; remote kaynak kullanıcı hesabında kalır ve otomatik silinmez.

Üç sabit normal PNG kullanılır: `first.png`, `same-content.png`, `different.png`; her biri 79 byte, toplam **237 byte**. İlk iki ad aynı SHA-256 içeriğini, üçüncü farklı içeriği taşır. Önceki frozen pilotun görsel üreticisi değiştirilmeden/hash’i denetlenerek yeniden kullanılır; testler ayrı literal hash vektörünü kontrol eder. Kaynak dosyalar, özel state, create baseline/owner/org/name ve yerel operation/dataset ID dosyaları repoya veya genel artefakta alınmaz.

| Sınır | Tek koşunun toplam tavanı |
|---|---|
| Salt okuma | 40 mantıksal GET / 80 fiziksel deneme; hedef değildir |
| Yan etki | Create 1, proje link 1, presign 3, PUT 3, confirm 3; toplam 11, her biri tek fiziksel deneme |
| Kaynak | Üç sabit PNG / 237 byte; koruma üst sınırı 1 MiB |
| Kontrol gövdeleri | İstek toplam 64 KiB; yanıt toplam 16 MiB; HTTP başlıkları/alt katman framing bu sayaç değildir |
| Süre | Dört çağrı boyunca ortak monotonic 180 s; production’ın daha dar 30/120 s/final pay kapıları korunur; fiziksel I/O süre garantisi değildir |
| Hedef | Yalnız canonical Platform API; mevcut strict proxy consumer; yeni direct origin/fallback yok |
| Maliyet | `explicit_attempt` + `unpriced`; yetki/fiyat ve süreğen depolama maliyeti unknown, sayısal CR tavanı uygulanmaz |

Normal hızlı üç-dosya yolunda ilk GET + prepare 2 + approve 2 + original start/proof 18 = **23 GET**, ardından 11 etki beklenir. Ek freshness okumaları ancak toplam 40 GET içinde kalabilir. Eski pilotun 10 GET/120 s tavanı bu nihai public akış için kullanılmaz; yeni sınırlar ayrı onaya sunulur. Başlangıçtaki 200 CR tercihi maliyet üst sınırı kanıtı değildir. Kullanıcı fiyat belirsizliğini ve kalacak kaynağı ayrıca onaylamadan çalıştırılmaz.

## Uygulama ve kanıt

[Runner](../../scripts/upload_live_acceptance.py) izole runtime-only wheel kökenini, tam ürün/metadata/lock ve ölçüm kaynağını mevcut araçlarla denetler. Gerçek public prepare→digest approve→start çağrıları kullanılır; grant, fiyat veya receipt/proof enjekte edilmez. [Ek pilot koruması](../../scripts/upload_pilot_guard.py), mevcut UploadBudget/Reservation metotlarına delege ederek bütün çağrıların toplamını daraltır; hedef/auth/peer/TLS/tek gönderim/owner/fence/final kapıları değiştirmez. Muhafazakâr claim sayaçları ile gerçek production byte/attempt sayaçları ayrı raporlanır. Response pending rezervi ve tüketilen byte aynı toplam tavana dahildir.

Uzak çağrıdan önce yeni özel workspace exclusive oluşturulur ve başlangıç kaydı fsync edilir. Aynı workspace ikinci defa kullanılamaz; yeniden çalışma yeni plan/create/PUT üretmez. İlk ret, schema/private/owner/secret/limit/iptal/belirsizlikte durulur. TOS, DELETE, export, bağımsız indirme, eğitim, mevcut partial create’e devam veya otomatik reconcile yoktur. İlk start’ın aynı operation üzerinde yaptığı salt okuma proof’u kabulün read doğrulamasıdır; canlı restart deneyi diye sunulmaz. Gerçek kill/restart kapsamı önceki çevrimdışı testlerdedir.

Başarı için tam 11 accepted intent/receipt grafiği, üç ayrı remote item, her dosyanın path digest/size/SHA eşliği ve durable metadata sonucu gerekir. Kaynak/wheel/runtime before-after eşliği ve final açık rezerv sıfır olmalıdır. Public receipt yalnız sınır, sayaç ve predicate taşır; ham hesap/yanıt, owner/org/name, key veya signed URL içermez. Başarısız koşu receipt’i `incomplete` kalır; özgün özel workspace ve aynı operation kimliği korunur. Kaynak commit ve araç/testler sürümlenmiştir; küçük güvenli receipt ve kabul raporu yayımlanabilir. **Metadata başarısı remote byte indirme, yetki, fiyat veya sonraki hesap çağrıları için izin değildir.**

Örnek yalnız onay sonrası, yer tutucular gerçek yerel yollarla doldurulur:

```sh
RUNTIME/bin/python -I scripts/upload_live_acceptance.py \
  --wheel CANDIDATE.whl --workspace NEW_PRIVATE_WORKSPACE \
  --config .local/p02-pilot/config.toml \
  --credentials .local/p02-pilot/credentials.json \
  --project SELECTED_TEST_PROJECT_UUID --accept-live-unpriced-write
```

Bu komut örneği kendi başına hesap çağrısı yetkisi vermez. Onay sorusunda gerçek test projesi/yeni workspace ve aynı sayısal sınırlar belirtilir. Fixture veya kurulu sentetik başarı, canlı kabul yerine yazılmaz; insan UX deneyi ayrıca yapılmadıysa belirtilir.

## Durma sonrası salt okuma tanısı — öneri

İlk koşu durdu ve 180 saniyelik penceresi sona erdi. Aşağıdaki ayrı kapsam kullanıcı tarafından onaylandı ve 06c2650 kaynağında bir kez çalıştırıldı; yetkisi tüketildi. Amacı, yeni oluşturulan exact dataset’in owned-list/detail consumer’ında niçin reddedildiğini değer saklamadan ayırmaktır. Operation’ı uzlaştırmaz veya değiştirmez; yeni yazma/create hakkı üretmez.

[Dar tanı aracı](../../scripts/upload_owned_diagnostic.py), aynı hazırlıktaki canonical Platform key’i ve yalnız mevcut accepted CreateReceiptV2 baseline’ını kullanır. İlk çağrı `GET datasets?page=1&page_size=128&scope=owned`; yalnız exact dataset satırı mevcut strict consumer’dan geçerse ikinci çağrı aynı satırın doğrulanmış username/slug detail rotasıdır. Başka sayfa/rota/host veya my-role çağrısı yoktur. İlk hata sonrasında ikinci GET yapılmaz. En çok **2 GET /4 fiziksel deneme /4 MiB yanıt /30 s ortak deadline**; iki GET’in her biri mevcut 1 MiB response sınırındadır. Başlık/framing bu gövde sayacı değildir. Hiç POST/PUT/DELETE, start veya reconcile çağrısı yoktur.

Özel yeni output dizini ilk GET’ten önce no-clobber oluşturulur. Yayınlanabilir receipt yalnız HTTP status veya güvenli hata kodu, byte/counter, root/envelope türü, satır sayısı, exact ID bulunma sayısı, sabit alanların varlık/türleri ve create eşliği bool’larını taşır. Raw gövde, kimlik/owner/org/name, kullanıcı adı/slug, URL veya credential değeri saklanmaz. Kaynak önce/sonra eşliği ayrıca denetlenir; sonuç yeni metadata success/auth kanıtı sayılmaz. Kaynak/test review’si ve somut kullanıcı onayı kapanmadan ağ çağrısı yapılmaz.

**Hazırlık kapısı kapandı:** 2c710d4’e kadar iki fresh contract/safety turu tamamlandı. R1’in private preflight lookup ve marker alias bulguları kapatıldı; farklı R2 ajanları temiz sonuç verdi. Yedi core tür/sır/locator case’i ile altı ayrı CLI/preflight negatifi geçti; gerçek hesap çağrısı yapılmadı. Önerilen tek output `.local/p02-pilot/p02-2-owned-diagnostic-20261104/receipt.json`, girdisi yalnız önceki `p02-2-final-20261104` özel workspace’idir. Onay sonrası ilk owned GET `remote_failed` ile durdu; detail çağrısı yapılmadı. Gerçek HTTP status alanı araçta yakalanmadığından receipt’te null kaldı. Sıfır okunan body byte, uzak gövdenin boş olduğunu kanıtlamaz. Özgün receipt değiştirilmeden [başarısız tanı arşivine](evidence.md#p02-2-owned-diagnostic-20261104-incomplete) alındı; bu sonuç consumer veya canlı kabul başarısı değildir.


## Sorgu ve locator ayrıştırma tanısı — öneri

Önceki onayın 30 saniyelik penceresi kapandı. Bu yeni kapsam kullanıcı tarafından onaylandı ve 70e787c kaynağında bir kez çalıştırıldı; önceki kullanılmayan GET slotları yeni çağrı hakkı sayılmaz. Aynı accepted CreateReceiptV2, aynı unknown operation ve canonical Platform hedefi kullanılır. Yeni output `.local/p02-pilot/p02-2-owned-diagnostic-20261104-r2/receipt.json` exclusive oluşturulur; operation veya özel baseline değiştirilmez.

Herkese açık [Platform istemci varlığında](https://evren.ssyz.org.tr/assets/datasetApi-DZyifXpy.js) 4 Kasım’da `page_size=20` varsayılanı görüldü (7.005 byte, SHA-256 `79387e65f48caa5aa9fea9e4e583e2bb781c1ff44aab32cb0ed5c1cfeda0a16b`). Bu yalnız istemci varsayılanıdır; sunucu azami sayfa boyutunu veya önceki ret nedenini kanıtlamaz. İndirme credentialsız yapıldı, JavaScript yürütülmedi.

1. `GET datasets?page=1&page_size=20&scope=owned`.
2. Yalnız ilk yanıtın gerçek HTTP durumu **422** ise, önceden gözlenen `page_size=5` ile aynı ilk sayfa bir kez okunur. Diğer hata veya ret durumunda durulur; 401/403, 429 veya 5xx bu dalı açmaz.
3. Strict JSON/literal-credential taraması, bütün satırların geçerli/benzersiz ID’leri, exact dataset ID ve güvenli username/slug zorunludur. Satırdaki mevcut create alanları tür ve değer olarak baseline ile aynı olmalıdır; eksik alanlar doldurulmaz. Bu dar locator kapısı geçerse aynı dataset’in username/slug detail GET’i yapılır. Detail mevcut tam strict consumer ile accepted create baseline’ına karşı karşılaştırılır.

Bu araştırmada yalnız locator için kullanılan kapı, üretim owned consumer’ının kabulü değildir. Receipt ayrıca `owned_consumer_accepted`, `detail_matches_create` ve her iki yanıttaki alan türü/eşlik bool’larını ayrı kaydeder. Bilinen private/owner/metadata uyuşmazlığı detail çağrısını durdurur; eksik metadata yalnız eksik diye raporlanır. Üretim parser’ı ve literal sorgu registry’si değiştirilmez.

Toplam tavan **3 mantıksal GET /6 fiziksel deneme /6 MiB yanıt /30 s ortak deadline**; her response/attempt için mevcut 1 MiB sınırı korunur. Ortak P01 salt okuma `HttpSession` ve gerçek public DNS/peer korumalı HTTPX backend kullanılır; credential yalnız aynı canonical Platform hedefine gider. Redirect/cookie/environment proxy kapalıdır. Receipt `physical_attempts_upper_bound` ile muhafazakâr deneme üst sınırını ve yalnız başarıyla alınan `returned_body_bytes` değerini bildirir; bunlar gözlenmiş toplam fiziksel deneme/hat byte sayısı diye sunulmaz. HTTP ret kodu `HttpStatusFailure.status_code` üzerinden kaydedilir; ham hata gövdesi saklanmaz.

POST/PUT/DELETE, create, proje bağlantısı, start/reconcile, yeni permit veya operation değişikliği yoktur. Ham yanıt, kimlik, owner/org/name, kullanıcı adı/slug, URL veya anahtar değeri saklanmaz. `evidence_collected` yalnız araştırmanın tamamlandığını belirtir; workflow, yetki veya fiyat başarısı değildir. Araç/testler ile iki farklı fresh contract/safety review turu bc74509/0e06b9b üzerinde temiz kapandı. Sonraki açık kullanıcı onayıyla yalnız iki GET çalıştı: owned20 HTTP 200/1.403 byte ve detail HTTP 200/993 byte. 422 dalı kullanılmadı. Liste contribution alanı eksikti, tam detail create baseline’ıyla eşleşti. Üretim consumer’ının ret sonucu ve bu alanların predicate’leri [özgün kayıtta](evidence.md#p02-2-owned-diagnostic-20261104-r2) korunur; kaynak/op değişmedi. Araştırma tamamlandı; yazma hakkı üretmez.


## Yeni tam kabul denemesi — öneri

İlk tam deneme ve iki ayrı tanı tarihsel kayıtlardır; eski unknown operation yeniden arm edilmez. Gözlenen liste/detail wire farkı düzeltildikten ve iki fresh kod review turu kapandıktan sonra yeni tam kabul için **ayrı** bir somut deneme önerilir. Kullanıcı bu kapsamı “ihtiyacın olan tüm kontrolleri yapabilirsin” yanıtıyla onayladı; 59ff11a kaynağındaki tek koşu link aşamasında durdu. Bu tüketilmiş koşu yeniden çalıştırılmaz.

- Aynı hazırlanmış Platform key’i ve `yorunge-discovery-test` projesi (`01a19492-2404-7701-afee-d45c26561062`).
- Yeni exclusive workspace `.local/p02-pilot/p02-2-final-20261104-r2`; yeni private dataset `yorunge-acceptance-p02-2-final-20261104-r2`. Önceki kaynaklar hesabında kalır; DELETE/cleanup yoktur.
- Aynı üç sentetik PNG, toplam 237 byte; iki ayrı ad aynı hash. En fazla 1 create/1 project link/3 presign/3 PUT/3 confirm; her etki tek deneme, durma sonrası otomatik devam yoktur.
- Toplam en fazla 40 GET/80 okuma denemesi, 16 MiB response body, 64 KiB control request body ve ortak 180 s. Product’ın daha dar request/lease/current/deadline sınırları korunur.
- `explicit_attempt` + `unpriced`, yetki/fiyat ve süreğen depolama maliyeti unknown; **sayısal CR tavanı uygulanmaz**. Şart kabulü, eğitim, export/indirme veya başka kaynak değişikliği yoktur.

Mevcut aynı runner yeni runtime-only wheel’den çalışır; provenance, source/wheel önce-sonra eşliği ve accepted grafiği değiştirilmez. İlk beklenmeyen hata/belirsizlikte durur; aynı ID üzerindeki original salt okuma proof’u bu tek koşuya dahildir. İki aynı hash/farklı adın üç ayrı item’ı ve exact manifest metadata’sı zorunludur. Bu deneme gerekli kaynak ölçümlerinden önce yapılır; aksi halde yeni doğrulanmış wire farkı bütün M5 referanslarını gereksiz yere tekrar ettirebilir. Yeni source/native/CI kabulü, canlı başarının ardından ayrı ve birer kez kapanır.


**Uygulama hazırlığı tamam:** c279e4f düzeltmesi iki farklı fresh contract/safety turunda temiz kapandı; 372 odaklı test ve ayrıca 1 gerçek API/TLS runner success case’i geçti. Yeni runtime-only wheel’in gerçek `-I` provenance kapısı doğrulandı; bu yeni canlı çağrı değildir. Somut yeni create/upload onayı beklenir.


## Tek-link sözleşme tanısı

4 Kasım’daki genel kontrol yetkisi kapsamında, aynı test projesi/anahtarı ve **ilk** `p02-2-final-20261104` koşusunun accepted create baseline’ı kullanılır. Bu kayıtta yalnız create intent/receipt’i bulunmalıdır; herhangi bir link intent’i, aktif lease, başka proje/hedef veya test dışı ad HTTP’den önce reddedilir. İkinci koşunun belirsiz link’i yeniden gönderilmez; eski operation değiştirilmez. Bu bağımsız, tek kullanımlık araştırma slotu ürün restart/recovery yolu değildir.

[Link tanısı](../../scripts/upload_link_diagnostic.py) önce auth/me, exact project, owned ilk 20, exact username/slug detail ve project membership okur. Me/project/owner/private ve tam immutable create-detail eşliği zorunludur. Kaynak zaten bağlıysa POST yapılmaz. Değilse aynı project endpoint’ine yalnız dataset_id taşıyan **tek POST** yapılır. HTTP 2xx sonrası strict JSON/literal taraması ve varsa dataset_id/project_id eşliği korunur; logical false, malformed/secret/binding veya HTTP hatasında durulur. Bilinmeyen ama bu temel kapılardan geçen 2xx acknowledgement, araştırmanın hedefidir: eski typed decoder sonucu kaydedilir ve yalnız membership sonrası bir GET ile actual bağ kontrol edilir. Bu gözlem accepted receipt veya product success yazmaz.

Tavan: **6 GET + 1 POST / 13 fiziksel deneme / 13 MiB response body / 128 byte POST body / ortak 30 s**; response/attempt başına 1 MiB, read en çok 2 ve POST tek deneme. Yeni create, presign, PUT, confirm, silme, eğitim, şart kabulü veya byte indirme yoktur. Fiyat unknown, sayısal CR tavanı yoktur; private kaynak hesabında kalır. Yeni exclusive workspace `.local/p02-pilot/p02-2-link-contract-20261104`, fsync edilmiş start marker’ıyla HTTP’den önce kalıcılaşır; ikinci çalışma reddedilir.

[Ortak control izi](../../scripts/upload_control_trace.py), gelecekteki mevcut runner’da create/link/presign/confirm gövdelerinin yalnız kapalı alan türlerini, sayıları ve exact expected/literal eşlik bool’larını decoder’dan önce kaydeder. Ham gövde, serbest anahtar/metin, kimlik, owner/org/name, object key, URL veya credential değeri tutulmaz. HTTP hata kodu typed exception’dan kaydedilir; `_outcome`a ulaşılmışsa yalnız transport 2xx kabulü bilinir, gerçek 2xx status icat edilmez. Bütün origin/secret/permit/budget/decoder davranışları delegate edilir. Yeni script/test dilimi 5ebec93’e kadar iki farklı fresh contract/safety turuyla kapandı; kaynak review’si ve dar fix teyidi temizdir. Önceden tanımlanan tek slot genel kullanıcı kontrol yetkisi kapsamında bir kez çalıştırılır.


**Tek-link sonuç:** f843e6f üzerinde 6 GET/1 POST tamamlandı; link HTTP 201, exact project/dataset çiftli bare nesne, öncesinde yok/sonrasında membership true. Ham yanıt/kimlik saklanmadı; eski operation değişmedi. Slot tüketildi ve yeniden kullanılmaz. Kaynak-bound decoder uyumu bu kayda dayanır; kaynak/provenance kapanış hatası araştırma receipt’ini incomplete bırakır.

## Sonraki public tam kontrol

Genel kullanıcı kontrol yetkisinde, yukarıdaki aynı kapalı full-runner/sayısal sınırlarda bir yeni private instance planlanır: `.local/p02-pilot/p02-2-final-20261104-r3`, dataset `yorunge-acceptance-p02-2-final-20261104-r3`. Aynı test projesi/anahtar, toplam 237 byte olan üç PNG ve iki aynı hash/farklı ad korunur. Tam one-shot private create/link/3 presign/3 PUT/3 confirm; 40 GET/80 read attempt/16 MiB response/64 KiB control/180 s, unknown/unpriced maliyet ve sayısal CR tavanı yokluğu değişmez. İlk hata/belirsizlikte durur; eski işler veya nonce’lar yeniden kullanılmaz. Root/data/bare-link wire uyumu iki fresh kaynak turu ve yeni runtime-only wheel provenance kapısından sonra çalışır. Ek kaynak/hesap değişikliği, cleanup/silme/şart kabulü veya indirme/eğitim içermez.


**r3 kaynak kapısı:** 821e155 exact ilişki decoder uyumu ve finalization, iki farklı fresh contract/safety turunda temiz kapandı. Önceki koşular yeniden gönderilmez; yalnız r3 exclusive workspace aynı sabit sayısal kapsamda bir defa kullanılır.


## Storage sözleşmesi — üç dosyalık bağımsız tanı

Genel kontrol yetkisinde, aynı ilk sentetik dataset/proje/anahtar kullanılır; r3’ün unknown işi veya onun presign/PUT istekleri yeniden gönderilmez. [Storage tanısı](../../scripts/upload_storage_diagnostic.py) yalnız orijinal Manifest’teki üç sabit PNG’yi ve literal hash’lerini kabul eder. Dosya başına tek exclusive slot vardır: `.local/p02-pilot/p02-2-storage-contract-20261104/first`, `different`, `same-content`. İlk `first.png` yalnız presign/PUT cevabını inceler; sonraki dosyalarda `--confirm`, yalnız mevcut typed PUT kabulünden sonra confirm’i açabilir. Üç slot toplam en fazla 3 presign/3 PUT/3 confirm/237 byte gönderir; yeni create/link, eski operation mutation, silme/şart/eğitim/indirme yoktur.

Her slotta azami 8 GET (me/project/owned20/exact detail/membership/my-role/items-before/after), 1 presign POST, 1 PUT ve isteğe bağlı 1 confirm POST; **19 fiziksel deneme /5 MiB response /4 KiB control request /79 byte upload /30 s ortak deadline**. Kontrol yanıtı/attempt 256 KiB, PUT response 64 KiB; GET en çok 2, POST/PUT tek denemedir. Fiyat/storage unknown ve sayısal CR tavanı yoktur; kaynak private kalır.

Önce sadece-create-intent/accepted-v2/unknown/no-active-lease/exact historical context kapısı korunur. Gerçek dosyalar tamamen yeniden hash’lenir; root/manifest eşliği gerekir. Fresh me/project/owner/private/detail/membership ve my-role literal upload etiketi zorunludur; etiket grant değildir. Items yalnız üç bilinen dosya ve exact hash/size ile tutarlı, küçük ve terminal tek sayfa olmalıdır. Seçilen dosya zaten metadata’da varsa effect sıfırdır. Her yeni effect öncesi uygun input observation recheck, gönderimde gerçek descriptor byte/SHA ve source complete eşliği korunur.

Presign descriptor’ı mevcut strict proxy decoder’ından geçer; direct origin/fallback veya redirect açılmaz. Signed URL/provider key yalnız aynı çağrının volatile descriptor’ında kalır. PUT yanıtında mevcut typed ack’in kabul/ret sonucu ve kapalı şekil/eşlik bool’ları kaydedilir; ret sonrasında confirm yoktur. Confirm araştırmasında mevcut toplam sayacı beklentisi ile singleton count=1 iki ayrı **decoder predicate’i** olarak kaydedilir; bunlar product policy veya receipt değildir. Logical-negative/malformed/binding/secret/byte HTTP hatasında başka write yoktur. En az bir kapalı singleton confirm oracle’ı geçerse yalnız items-after okunur; total/name/size/hash karşılaştırması metadata gözlemidir, remote byte doğrulaması değildir.

Nonce/dizin fsync ve kaynak önce/sonra eşliği HTTP’den önce/sonra uygulanır. Response type/alan adı/sayı/literal/expected bool dışında serbest metin, kimlik, object key, URL veya credential saklanmaz. Mevcut public runner’da PUT için de task-context’e bağlı kapalı iz eklenmiştir: iki worker’ın satırları karışmaz; original ownership/permit/source/decoder/cleanup aynen delegate edilir. Wrapper’a giriş, fiziksel deneme diye sunulmaz; actual sayaç ayrı kalır. Script/test dilimi 1bb9041/51f4d34 üzerinde iki farklı fresh contract/safety turu ve dar fix teyidiyle kapandı. İlk first.png slotu confirm kapalı olarak genel kullanıcı kontrol yetkisiyle bir kez çalışır; kalan slotlar observed wire uyumu ve input/typed kapılarından sonra seçilir.


**İlk storage slotu tüketildi:** 00658df’de first.png için 7 GET/1 presign/1 PUT; PUT 200/79 sent byte/hash eşliği true, root ok=true/size 79, eski typed ack ret. Confirm yoktur. Yeni decoder bu bağlamı destekledikten ve iki fresh tur/provenance kapandıktan sonra `different.png --confirm`, ardından `same-content.png --confirm` ayrı birer slotta çalışabilir. İlk dosya tekrar gönderilmez. Bu sıra yeni dataset veya eski operation’a devam değildir; singleton/current confirm predicate’i ile sonraki metadata wire’ını araştırır.
