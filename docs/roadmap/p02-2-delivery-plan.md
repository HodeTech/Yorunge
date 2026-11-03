# P02-2 — Private create ve doğrulanmış upload teslim planı

**Tarih:** 2026-11-02. **Güncellendi:** 2026-11-03. **Durum:** ADR-0024/0025/0026 Accepted; yerel d–t verified; gerçek ortak provider/API/CLI kodu yerel kabulü geçti, bütünleşik kurulum/native/son kaynak CI/kanıt/ayrı canlı kabul açık. **Dal:** `feat/p02-2-private-upload`, development `50d68b1` üzerinden; P02-1 kapanışı `973cec5` aynı daldadır. Kullanıcı P02-2a/b/c'yi tek nihai development PR'ında, adım başına commit ve iki fresh review turuyla istedi. Yeni ADR'ler onaylanmadan bağımlı ürün kodu başlamaz; ayrı hazırlık PR'ı açılmaz.

## Kullanıcı sonucu

Kullanıcı güncel yerel manifestle doğru owner/projede private dataset oluşturur; normal dosyaları hedef/yetki/byte sınırları içinde yükler ve neyin doğrulandığını görür. Cevap kaybında aynı operation ID'sine dönüp salt okuma ile durumu inceler; ikinci create/PUT üretmez. Gelişmiş etkili resume P02-3a'dır; ilk kesinti güvenliği ve read reconciliation bu pakettedir.

## Başlangıç kapıları

| Kapı | Mevcut kanıt / açılma koşulu | Bekleyen dilim |
|---|---|---|
| Karar | [ADR-0024](../decisions/0024-durable-dataset-transfers.md)/[0025](../decisions/0025-isolated-storage-streaming.md) Accepted — 2 Kasım kullanıcı yetkisi/review düzeltmeleri; yerel uygulama açıldı, gerçek otorite/wire kapıları ayrı | Yerel ve uzak bağımlı ürün kodu |
| Create/link authority ve wire | Kamu istemcisi `POST datasets` ve **ayrı** `POST projects/{id}/datasets` gösteriyor; API-key auth, owner/project ve current izin oracle'ı doğrulanmadı | Gerçek codec; verified_only için prepared, explicit_attempt için v2 risk/onay kapısı |
| Upload/verification wire | `my-role`, presign direct/proxy, `client_uid`, `skip_dedup`, item cursor alanları istemci kanıtı; exact strict response/expiry/header/object key güvenliği ve aynı hash farklı ad desteği açık | Gerçek adapter/pozitif aktarım |
| Live yetki | Mevcut private test projesi önceki discovery kabulündendir. Kullanıcı son yanıtında küçük denemeye ve 200 CR aşımına izin verdi; somut ilk pilot aşağıdaki tek dataset/üç küçük görselle sınırlıdır; ilk create 201, sonraki detail GET 405 ve kontrollü durma [kaydedildi](../research/p02-2-private-create-observations.md) | Canlı yazma kabulü |
| Fiyat ve kalacak kaynak | Kullanıcı başlangıçta **200 CR** tavanı belirledi, sonraki yanıtında bu tutarın aşılmasını kabul edip denemeyi istedi. İlk deneme tek private dataset/≤1 MiB üç görselle sınırlanır; create/storage/upload/okuma tarifesi ve provider hard-cap mekanizması hâlâ doğrulanmadı. Bu tercih ürün cost-bound/authority kanıtı değildir. Kaynak private kalır, otomatik silinmez | Canlı kabul |

Onaylanan mimariyle bağımsız local domain/journal/stream fixture işi bu dış kapıları beklemeden ilerleyebilir. Adapter endpoint'leri tahmin edilmez. Verified_only için gerçek tam grant/complete cost gerekir; ADR-0026 explicit_attempt yolu unknown yetki/fiyatı risk ve açık onayla taşır. Hiçbir mod wire/owner/private veya ürün/live kabul kapısını atlamaz. Dış gate kapanmazsa P02-2 partial/blocked nedeni ve somut açılma koşulu kaydedilir; kapsam kullanıcı kararı olmadan daraltılmaz. [Araştırma](../research/p02-2-readiness-review.md) bu kapıların kanonik kanıtıdır.

## Adımlar ve review döngüsü

Her uygulama adımı: **geliştir → ilgili gerçek kontroller → commit → fresh review R1 → doğrulanmış bulgu/fix/commit → farklı fresh reviewer R2 → doğrulanmış bulgu/fix/commit**. Reviewer'lar bulgu metni/yol/kodu untrusted veri sayar, current code ile doğrular; geçmiş yorum körlemesine uygulanmaz. İşin karmaşıklığına göre iki bağımsız eksen (state/güvenlik ve contract/UX/test) kullanılır. Önceki adım kabul/review bitmeden bağımlı sonraki kod adımına geçilmez. Sonuçsuz tercih yeni bug diye sunulmaz. Gerekli düzeltmenin doğrulaması aynı turda tamamlanır; iki tur tamamlandı diye açık bulgu bırakılmaz.

| Adım | Sahip | Tek review sonucu / başlama kapısı |
|---|---|---|
| 0 | Paket hazırlığı | Mevcut belge/kod ve güncel kamu sözleşmesi review'si, iki Proposed ADR, gerçek kartlar ve dış kapılar; iki fresh belge turu, kullanıcı ADR onayı |
| 1 | [P02-2d](tasks/p02-2d-upload-plan-contract.md) / P02-2a yerel | Exact public/private wire, immutable upload plan/manifest, strict model/oracle, digest approve/revoke ve ortak kullanım senaryosu; ADR onayı gerekir, remote permission uydurulmaz |
| 2 | [P02-2e](tasks/p02-2e-durable-transfer-journal.md) / P02-2a kalıcılık | 6→7 V2, quota/recovery rezervi, tekil niyet/intent/receipt, current credential/lease/clock, reset/preview/frontier ve eski restore yasağı; aynı kayıt üzerinde kill/race kabulü |
| 3 | P02-2a uzak | Kayıtlı v2 current producer, strict endpoint codec ve private create/proje bağı; verified_only ile açık explicit_attempt kapıları ayrıdır |
| 4 | [P02-2f](tasks/p02-2f-bounded-storage-port.md) temel / P02-2b adapter | Ayrı hedef politikası, bounded descriptor streaming ve presign/PUT/confirm; exact provider wire/allowlist ve önceki durable kayıt gerekir |
| 5 | P02-2c recovery | Show/reconcile, her etki/commit sınırında kill/cevap kaybı, aynı-ID read-only yol; ikinci create/presign/PUT/confirm sıfır |
| 6 | P02-2c deneyim/kabul | Ortak CLI/Python, text/JSON/NDJSON/error/cancel; gerçek TLS/kurulu upload bellek ve süre, sınır/yoğun state, altı temiz paket kurulumu, son kaynak M5 ve üç ortam CI |
| 7 | P02-2c live/teslim | Ayrı yetkili küçük canlı kabul, belge/current/matris/README gerçek durum, kanıt saklama, tek development PR ve kullanıcı review'si |

1 ve 2 yerel uygulama kabul birimleridir; P02-2a'nın remote kabulü ve kart verified'ı değildir. Upload planı hazırlığının local validation'ı 30 s, bütün remote akışın toplamı ayrı bütçedir. 128 dosya ilk istemci koruması açık bir ürün sınırıdır; P02-1 4.096 dosya kapsamı küçülmez. Her ölçümden önce kaynak/fixture/ortam/bütçe sabitlenir; başarısız ölçüm korunur, hedef sessizce artırılmaz.

## Canlı kabul hazırlığı

Kullanıcı **beş GET/10 attempt/5 MiB/30 s** salt okuma pilotunu açıkça onayladı: mevcut Platform target üzerinde auth/me, organizations, seçilmiş projects/{id}, projects/{id}/datasets ve datasets ilk sayfası (`page=1,page_size=5,scope=owned`). Bu kapsam billing/başka endpoint veya yanlış-key kontrolü içermez. Mevcut anahtar değeri sohbete/repoya girmez. Kamu bundle kaynak okuması ile auth'lu hesap çağrısı aynı kanıt sayılmaz. Bu plan tek başına hesap çağrısı yetkisi vermez.

Sonra yazma pilotu somutlaştırılır: bir private dataset ve bir proje bağlantısı; toplam ≤1 MiB üç sentetik normal görsel (iki farklı ad aynı içerik, üçüncü farklı içerik); create≤1/link≤1, presign≤3/PUT≤3/confirm≤3, read≤10 ve isteğe bağlı bağımsız byte doğrulama≤3; effectful retry=0, read max2 attempt, toplam≤120 s. İlk sürüm dosya başına presign/confirm yapar; batch istisnası yoktur, tavan hedef değildir. Kullanıcı ilk salt okuma tamamlandıktan sonra “deneyebiliriz” ve “200’ü geçerse de sorun yok” yanıtıyla bu küçük denemeyi açtı; yeni kapsamlı/tekrarlı harcama akışı çıkarılmaz. İlk create 201 sonrasında detail GET 405 ile duruldu; link/presign/PUT/confirm yapılmadı ve görseller gönderilmedi. Bu koşu upload kabulü değildir; yeni create veya otomatik yeniden yürütme yoktur. Kesin byte toplamı, izinli storage origin, format, sayısal fiyat/hard-cap bulunamadığı ve gerideki kaynağın sahibi **pilot öncesi** kaydedilir. Şart kabulü, wrong parent, schema, secret, sınır veya ilk belirsizlikte durulur; cleanup adıyla DELETE yoktur. Bu dar araştırma yetkisi ürünün güncel authority/cost-bound kapısının yerine geçmez.

## Teslim kaydı

İlk hazırlık aşamasında ürün geliştirmesi/testi/native veya hesap çağrısı yoktu. Güncel durumda [P02-2d yerel plan uygulaması](../research/p02-2-implementation-validation.md) ve ayrıca yetkili beş GET şekil araştırması yapıldı; gerçek upload/native/live yazma kabulü yoktur. İki hazırlık ajanı salt okunur mevcut kod/belge sınırlarını doğruladı. İlk hazırlık 2655c2b, doğrulanmış R1 düzeltmeleri 5e185a0 ile commit edildi. İki fresh belge turu tamamlandı; R2'de yeni doğrulanmış bulgu yok. Gerçek belge/rehber/arşiv ve mevcut kaynak bağlı referans sonuçları [hazırlık kaydındadır](../research/p02-2-readiness-review.md#fresh-belge-review-r2-ve-onay-öncesi-kapanış). Kullanıcı review düzeltmeleri sonrası ADR-0024/0025 Accepted; kod/local kabul ve dış kapılar izleniyor. Önceki P02-1 kapanışı bu paketin ürün kabulü yerine geçmez.

## Bağımsız yerel kart sırası

P02-2d/e/f yerel temel kartları, a/b/c üst teslim ID/kabulünü yeniden numaralandırmadan daraltır. d tamamlandıktan sonra e, ardından f uygulanır; her kart commit+iki fresh tur ister. Remote adım 3 dış otorite/wire kapısında beklerse f temelini bekletmez; f gerçek adapter/ücretli/live kabulü değildir. a/b/c, ilgili yerel temelleri kendi gerçek remote/UX/live kabulleriyle birlikte kapatır.

P02-2f iki kod dilimine ayrılır: **4.1** kapalı hedef/request politikası ve gerçek descriptor byte kaynağı; **4.2** public-IP pin/peer backend, aynı client/pool storage entegrasyonu ve iki gerçek TLS origin negatifleri. Her dilim kendi commit'i ve iki farklı fresh review turuyla kapanır; f ancak ikisi tamamlanınca verified olur. Native bütünleşik ve gerçek provider codec/kabulü yine b/c kapsamındadır.

## ADR-0026 sonrası sıra

[ADR-0026](../decisions/0026-explicit-unverified-transfer-attempts.md) kullanıcı review revizyonu ve iki fresh tur sonrası Accepted; kanonik v2 sözleşmesi geçerlidir. Önce (1) ayrı v2 policy/plan/approval reducer ve literal golden'lar, sonra (2) v1/v2 kapalı journal decoder/arm/read/reset/quota/preview uyumu uygulanır. Bunlar M veya daha küçük yeni hazır kartlara bölünür; d/e/f'nin mevcut v1 yerel teslim kanıtı tarihsel korunur. Her kod dilimi commit + fresh R1 + fix + farklı fresh R2 + fix ister.

Ardından gerçek current tüketici codec'leri ve private create/proje bağı, bounded upload ve ortak public CLI/Python; aynı-ID read reconciliation ve bütünleşik UX/native/kurulum/source-CI/kanıt kapanışı gelir. Öneri v2 explicit operasyon için ayrı insan seçimiyle current scoped read-attempt ve metadata sonucunu da tanımlar; v1/default read grant kapısı korunur. Yeni politika tek başına provider wire, aynı hash farklı ad desteği veya canlı kabulü kapatmaz. Durmuş araştırma workflow'ı yeniden arm edilmez; sonraki canlı write kendi somut planı/kapsamı hazır ve review edilmişken ayrıca değerlendirilir. Bu öneri yeni bir canlı write çağrı yetkisi değildir.

## V2 dar kartları

P02-2g exact-work cost → P02-2h policy/plan/approval → P02-2i union/full graph → P02-2j durable write gates → P02-2k read/reset/metadata. Review revizyonu ve iki fresh tur kapandı; ADR-0026 Accepted. G/h/i/j/k/l/m/n/o çalışma dalında verified; her biri iki fresh kod review turu ve doğrulanmış düzeltmeleriyle kapandı. I aşaması yeni v2 writer açmaz; j geçişi yeni v1 write yasağıyla v2 write testlerini atomik tamamlar. D/e/f mevcut v1 kabulü tarihsel kalır; yeni public writer yalnız j/k kabulünden sonra tüketilir. Ardından a/b/c gerçek producer/API/CLI/codec ve nihai native/kurulum/CI/live kapsamı devam eder.


## Gerçek tüketiciye geçiş

[P02-2l](tasks/p02-2l-platform-control-codecs.md), a üst kartının context/create/link strict codec dilimidir; [kanonik tüketici referansı](../reference/platform-upload-consumer.md) ürün kodundan önce yazıldı. Ardından upload codec/storage descriptor, gerçek HTTP read/attempt/body bütçe sayacı, ortak koordinatör ve CLI/Python yüzeyi ayrı S/M commit/review dilimleri olarak somutlaştırılır. Bu teknik ayırma epik kapsamını daraltmaz; her dilim iki fresh turla kapanır, üst a/b/c ancak kendi bütünleşik ve live kabulüyle verified olur. Profil grant/fiyat uydurmaz; yeni canlı write, exact planı ve kapsamı hazırlanıp incelendikten sonra ayrı yetki ister.

P02-2l control codec kabulü tamamlandı; sıradaki [P02-2m](tasks/p02-2m-platform-upload-codecs.md) proxy descriptor/presign/confirm/items codec birimidir. Gerçek direct provider wire henüz yoktur; generic port kabulü onu açmaz. M öncesi kaynak/handle sınırı hazırlanır; onaylanmış politika değiştirilmeden seçilen authenticated proxy consumer daraltılır.

3 Kasım: m codec iki fresh tur ve fix teyidiyle verified. Sıradaki [P02-2n](tasks/p02-2n-upload-http-budgets.md) üç kod dilimidir: (n.1) kayıtlı service URI literal provenance; (n.2) pre-intent kota rezervasyonu; (n.3) aynı owned client üzerinde gerçek physical-attempt/body/source sayacı ve TLS/cleanup. Her dilim kendi commit/iki fresh turuyla kapanır. Ardından gerçek current producer ve prepare/approve, start/reconcile koordinatörü, ortak CLI/Python ve c bütünleşik kabulü kalan kapsamdır.

N üç dar dilim/ikişer fresh tur ve düzeltme teyidiyle yerel verified oldu. Sonraki dar kart; güncel input snapshot, gerçek current provider ve prepare/approve kompozisyonunu ayrı dilimlere böler. Start/reconcile controller, ortak public API/CLI ve c kabulü henüz tamamlanmadı.

[P02-2o](tasks/p02-2o-current-upload-preparation.md) üç ayrı commit/review dilimidir: (o.1) current local input observation ve warning üretmeyen revalidation; (o.2) gerçek current/read producer; (o.3) private prepare/approve/revoke kompozisyonu. Ardından etkili controller ve public yüzey, son olarak c bütünleşik kabulü gelir.

O.2 hazırlık incelemesi, unconditional create/detail owner_id+org_id eşliği için eski receipt'te tarihsel baseline eksikliğini doğruladı. [ADR-0027](../decisions/0027-durable-created-dataset-context.md) Accepted: 3 Kasım kullanıcı koşullu yetkisi, bulgu düzeltmeleri ve iki fresh belge turu kapandı. [P02-2p](tasks/p02-2p-created-dataset-context.md) önce DTO/union/history, sonra writer/legacy mutation/proof gate iki ayrı commit/iki fresh tur dilimidir.

O.1/o.2/o.3 her dilimde iki fresh tur ve bulgu/fix teyitleriyle yerel verified oldu. Bağımsız prepare/approve/revoke kompozisyonu kapandı; sıradaki kalıcı create baseline ADR-0027/P02-2p ile uygulanır; restart/controller onu tüketir. Sonra ortak public yüzey ve c kabulü gelir. Bu sıralama yeni canlı write yetkisi veya epik kapanışı değildir.

P02-2p iki kod dilimi ve her birinde iki fresh review/fix teyidiyle yerel verified oldu. Gerçek HTTP effect/metadata portu, original start ve salt okuma controller'ı, ortak public summary/API/CLI ve c nihai kabulü kalan somut işlerdir. P kartı schema/golden/history ve no-new-rights kabulüdür; remote upload veya epik kapanışı değildir.

[P02-2q](tasks/p02-2q-platform-effect-port.md) gerçek HTTP portunu üç kod/review dilimine ayırır: q.1 immutable arm-result ve ortak semantic digest; q.2 pre-intent call/quota ve control effect'ler; q.3 bounded PUT ve item metadata. Yeni [kanonik port referansı](../reference/dataset-upload-port.md) implementation öncesidir. Sonra original-start/read-only controller, public summary/API/CLI ve c nihai kabulü gelir; generic status definitive rejected receipt'e dönüştürülmez.

Q portu üç ana dilim ve ortak owner guard takip düzeltmesinde iki fresh turla yerel verified oldu. [P02-2r](tasks/p02-2r-original-upload-workflow.md) original koordinatörü üç kod dilimine ayırır: r.1 invocation/environment/admission/create-link iki fresh turla yerel kapandı; r.2 bütün presign ve bounded PUT/seri confirm iki fresh tur/fix teyidiyle kapandı; r.3 initial-owner read/proof ve original workflow/kill/unknown iki fresh tur/test delta teyidiyle kapandı; r kartı yerel verified. [Koordinatör referansı](../reference/dataset-upload-workflow.md) bu dar akışın kanonik sahibidir. Ayrı read-reconcile controller, public summary/API/CLI ve c nihai kabulü sonra gelir; bütün a/b/c/epik kapsamı korunur.


R üç kod dilimi ve ikişer fresh tur/fix teyidiyle yerel verified. [P02-2s](tasks/p02-2s-readonly-upload-reconciliation.md) ayrı readonly invocation, ağsız preflight, current credential/metadata ve read-only lease/proof/hata kompozisyonunu daraltır. [Uzlaştırma referansı](../reference/dataset-upload-reconciliation.md) iki eksenli temiz preflight sonrası s.1 local/current probe iki fresh tur/fix teyidiyle kapandı; s.2 read lease/items/proof ve gerçek kesinti regresyonları iki fresh kod turuyla kapandı; s yerel verified. Orijinal write devam ettirilmez. Ardından public summary/API/CLI ve c bütünleşik kabulü sürer.


[P02-2t](tasks/p02-2t-public-upload-workflows.md) public yüzeyi üç kod dilimine ayırır: t.1 tipli summary/yerel list-show-requested review; t.2 gerçek prepare/approve/start/reconcile API; t.3 CLI/render/TTY ilerleme. [Public sözleşme](../reference/dataset-upload-public.md) üç kod diliminde ikişer fresh review/fix teyidiyle uygulandı; t yerel verified. Provider baseline özel kalır, kullanıcıya istediği niyet onay öncesi ayrı gösterilir. Ardından üst c native/kurulum/source CI/kanıt/ayrı live kabulü sürer.


Son bütünleşik kabul iki dar kod kartına ayrılır: [P02-2u](tasks/p02-2u-offline-upload-acceptance.md) public süreç/ID kurtarma, azami128 dosya ve test sınırlarını; [P02-2v](tasks/p02-2v-installed-upload-measurement.md) gerçek kurulu upload native ölçüm araçları ve bağımsız rapor doğrulamasını sahiplenir. U t verified sonrası başlar; [w kaynak bakım kartı](tasks/p02-2w-upload-maintainability.md) u sonrası, v de w sonrası başlar; her kod dilimi kendi commit/iki fresh turunu alır. [Ölçüm planı](../research/p02-2-upload-measurement-plan.md) ölçümden önce sabitlenir. Altı kurulum/son kaynak M5/üç ortam CI/kanıt saklama, ayrı somut live yetkisi/kabulü ve nihai belge/PR üst c’de kalır. Bu ayırma üst kabulü daraltmaz veya yeni hesap çağrısına yetki vermez.
