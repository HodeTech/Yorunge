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

İlk koşu durdu ve 180 saniyelik penceresi sona erdi. Aşağıdaki ayrı kapsam henüz yetkilendirilmemiştir. Amacı, yeni oluşturulan exact dataset’in owned-list/detail consumer’ında niçin reddedildiğini değer saklamadan ayırmaktır. Operation’ı uzlaştırmaz veya değiştirmez; yeni yazma/create hakkı üretmez.

[Dar tanı aracı](../../scripts/upload_owned_diagnostic.py), aynı hazırlıktaki canonical Platform key’i ve yalnız mevcut accepted CreateReceiptV2 baseline’ını kullanır. İlk çağrı `GET datasets?page=1&page_size=128&scope=owned`; yalnız exact dataset satırı mevcut strict consumer’dan geçerse ikinci çağrı aynı satırın doğrulanmış username/slug detail rotasıdır. Başka sayfa/rota/host veya my-role çağrısı yoktur. İlk hata sonrasında ikinci GET yapılmaz. En çok **2 GET /4 fiziksel deneme /4 MiB yanıt /30 s ortak deadline**; iki GET’in her biri mevcut 1 MiB response sınırındadır. Başlık/framing bu gövde sayacı değildir. Hiç POST/PUT/DELETE, start veya reconcile çağrısı yoktur.

Özel yeni output dizini ilk GET’ten önce no-clobber oluşturulur. Yayınlanabilir receipt yalnız HTTP status veya güvenli hata kodu, byte/counter, root/envelope türü, satır sayısı, exact ID bulunma sayısı, sabit alanların varlık/türleri ve create eşliği bool’larını taşır. Raw gövde, kimlik/owner/org/name, kullanıcı adı/slug, URL veya credential değeri saklanmaz. Kaynak önce/sonra eşliği ayrıca denetlenir; sonuç yeni metadata success/auth kanıtı sayılmaz. Kaynak/test review’si ve somut kullanıcı onayı kapanmadan ağ çağrısı yapılmaz.

**Hazırlık kapısı kapandı:** 2c710d4’e kadar iki fresh contract/safety turu tamamlandı. R1’in private preflight lookup ve marker alias bulguları kapatıldı; farklı R2 ajanları temiz sonuç verdi. Yedi core tür/sır/locator case’i ile altı ayrı CLI/preflight negatifi geçti; gerçek hesap çağrısı yapılmadı. Önerilen tek output `.local/p02-pilot/p02-2-owned-diagnostic-20261104/receipt.json`, girdisi yalnız önceki `p02-2-final-20261104` özel workspace’idir. Bu bölüm somut ayrı kullanıcı onayını bekler.
