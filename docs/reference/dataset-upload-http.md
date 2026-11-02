# Upload HTTP quota ve sayaç sözleşmesi

**Tarih:** 2026-11-03. **Durum:** P02-2n kanonik sözleşme; kayıtlı URI dilimi iki fresh turla yerel olarak kabul edildi. Rezervasyon ve gerçek HTTP quota bağlantısı henüz kabul edilmedi. [V2 work limitleri](dataset-upload-v2.md#işe-ve-döneme-bağlı-maliyet-kanıtı), [provider codec](platform-upload-consumer.md), [generic HTTP](http-transport.md) ve [storage](dataset-transfer.md#p02-2f-private-storage-port-sözleşmesi) sınırları korunur.

## Kayıtlı service URI provenance

Default HttpRequest endpoint/query literal politikası değişmez. Yalnız private upload composition, adlandırılmış kapalı `upload_endpoint` seçer. Bu seçim public config/CLI flag, caller header/body dict'i veya permission değildir. Seçim; exact evren-platform, resmi origin/API kökü, method/read_only/path/query biçimiyle kurucuda denetlenir. Başka hedef, yöntem, rota veya fazladan query bu muafiyeti kullanamaz.

| Endpoint kimliği | Method/path | Query ve dinamik literal değerler |
|---|---|---|
| me | GET auth/me | Query yok; URI sabit |
| project | GET projects/{uuid} | Query yok; canonical project UUID dinamik |
| create | POST datasets | Query yok; URI sabit; body codec ayrı zorunlu |
| project_link | POST projects/{uuid}/datasets | Query yok; project UUID dinamik |
| membership | GET projects/{uuid}/datasets | Query yok; project UUID dinamik |
| owned | GET datasets | page=1..128 canonical decimal, page_size=128, scope=owned; bu sayfa/protokol değerleri kapalı, fazladan/duplicate key yok |
| detail | GET datasets/{username}/{slug} | Query yok; iki bounded safe segment dinamik. UUID my-role rotası bu seçimden tahmin edilmez |
| role | GET datasets/{uuid}/my-role | Query yok; dataset UUID dinamik |
| presign | POST datasets/{uuid}/upload/presign | Query yok; dataset UUID dinamik |
| confirm | POST datasets/{uuid}/upload/confirm | Query yok; dataset UUID dinamik |
| items | GET datasets/{uuid}/items | limit=128 ve optional opaque cursor; dataset UUID ve cursor raw değerleri dinamik |

Seçili credential'ın literal kuralı yalnız dinamik URI girdilerine uygulanır; sabit route/query adları credential ile tesadüfen eşleştiği için ret üretmez. Dynamic segment denetimi URI prefix'i eklenmeden yapılır. Username/slug/UUID ve cursor tür/uzunluk/encoding kuralları provider referansındadır. Kaynak body/yerel alan literal denetimi bu URI seçiminden muaf olmaz. Kayıtlı çağrı aynı target'a bağlı X-API-Key credential ister; default generic tüketicilerin auth şekli değişmez.

## Rezervasyon ve tek çağrı bağı

Sayaç kapsamı, tek original `start` çağrısının ilk current/context HTTP isteğinden metadata/cleanup sonuna kadardır; pre-admission okumaları da aynı instance'a dahildir. Worker, helper, retry veya session fazı sayacı sıfırlamaz. Existing operation ve kalıcı namespace kontrolleri ağdan önce yereldir; existing-admit yeni probe/budget/claim açmaz. Prepare, approve, ayrı reconcile ve admission öncesi başarısız start'ın sonradan tekrar çağrılması ayrı bounded readonly invocation kapsamıdır. Bunların birikimli maliyeti original transfer quote'u veya plan ömrü toplam CR tavanı diye sunulmaz; eski bound yeni çağrıya taşınmaz. Bu, v2'deki workflow/retained-storage kapsamını açıklığa kavuşturur, account-geneli muhasebe eklemez.

Private UploadBudget yalnız strict saved UploadRequestLimits ve özgün monotonic end ile oluşur; son süre 900 s'yi aşamaz, prepared/read-only invocation daha dar olabilir. Clock/PID/thread/loop sahipliği korunur. Readonly budget hiç effect claim üretemez. Bütçe authority, approval veya DispatchPermit değildir; effectful çağrı ayrıca aynı durable intent ve tek permit ister.

Her mantıksal read ve etkili çağrı için private tek kullanımlık rezervasyon vardır. Effect count, JSON control request byte'ları, PUT'un declared source byte'ları ve response kapasitesi **intent'ten önce** ayrılır. Sayfa/read sayacı da HTTP'den önce ayrılır. İki worker'ın toplam pending response rezervi ile işlenmiş byte toplamı work sınırını aşamaz. Çağrı başlamadan bırakılmış rezervasyon ancak hiç physical attempt oluşmadığı doğrulanırsa geri verilebilir; başlamış effect/attempt byte slotu replay hakkına dönmez.

Low-level wrapper her fiziksel HTTP denemesini delegate/socket öncesinde sayar; read en çok iki attempt ile mevcut retry sahibini kullanır. Bir effect rezervasyonu bir fiziksel deneme açar; 429/5xx/connect refusal/timeout/cancel ikinci effect veya URL yenileme üretmez. Yanlış request/reservation/task veya ikinci kullanım HTTP'den önce ret edilir. Sayaç nesnesi DB, raw URL, body hash'i veya credential kopyası tutmaz; private pending call expectation yalnız çağrı ömründedir.

## Byte anlamı ve cleanup

Control request byte sayacı JSON body'nin gerçek byte uzunluğudur; query/header/TLS değildir. PUT upload byte sayacı source→transport'a teslim edilen gerçek chunk'ları sayar; sunucunun kabul ettiği byte veya uzak bütünlük değildir. Content-Length ve SHA-256 eşliği ayrıca storage portunda doğrulanır. Response sayacı client tüketimine teslim edilen raw body byte'larıdır; compressed içerik açılmaz. Limitte daha fazla body teslim edilmez, çağrı kontrollü kesilir. Socket/TLS/read-ahead buffer'ları veya provider'ın billable unit'i bu sayaçtan türetilmez; mevcut fiyat quote'unun ayrıca kendi tam kapsamı gerekir.

Response kapanınca kullanılmayan pending kapasite serbest bırakılır; tüketilmiş byte/attempt sayacı düşmez. Kısmi source/response, exception ve Task.cancel cleanup'ı aynı owner task'ta tamamlanır; yeni effect hakkı oluşmaz. Aynı session/client/pool toplam iki connection/slot sınırı korunur. Request/response/body/source özel değerleri log/repr/exception/receipt/Result'a çıkmaz; sayısal snapshot yalnız kapalı sayaç alanlarından oluşur. Progress daha sonra coordinator'da bu gerçek sayaçtan coalesce edilir; native RSS kabulü burada varsayılmaz.

## Hata ve kabul

Yeni `upload_limit_exceeded` / exit 2, yeni HTTP/intent öncesi work quota ayrılmadığında kullanılır; kaynak alt türü provider metni olarak yayımlanmaz. Süre için execution_timeout/2; response shape/byte ihlali invalid_response/1; transport kaynak hataları mevcut kapalı kodlardır. Aktif latched coordinator'ın belirsizliği operation_uncertain/5 + aynı ID önceliğini korur. Default store kapasite kodu upload_capacity_exceeded ile yeni HTTP quota kodu karıştırılmaz. Ayrı readonly source hata istisnası v2 read sözleşmesinde kalır.

Kabul, n'nin dar dilimlerinde ayrı kapanır: literal route/yanlış seçim/default uyumu; bool/float/nonfinite/limit boundary; pre-intent reservation rollback ve single-use; gerçek server attempt ve byte oracle; transient read iki deneme/etkili tek deneme; iki worker toplam kapasite, erken close/partial/timeout/cancel, slot/pool cleanup ve canary. Domain sayacının testi gerçek HTTP bağlandığını kanıtlamaz; n ancak URI, rezervasyon modeli ve gerçek wire bağlantısının ayrı ikişer fresh turuyla verified olur.
