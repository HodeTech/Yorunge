# P02-2 — Private create ve doğrulanmış upload teslim planı

**Tarih:** 2026-11-02. **Durum:** ADR-0024/0025 Accepted; bağımsız yerel uygulama başlıyor, remote kart kapıları açık. **Dal:** `feat/p02-2-private-upload`, development `50d68b1` üzerinden; P02-1 kapanışı `973cec5` aynı daldadır. Kullanıcı P02-2a/b/c'yi tek nihai development PR'ında, adım başına commit ve iki fresh review turuyla istedi. Yeni ADR'ler onaylanmadan bağımlı ürün kodu başlamaz; ayrı hazırlık PR'ı açılmaz.

## Kullanıcı sonucu

Kullanıcı güncel yerel manifestle doğru owner/projede private dataset oluşturur; normal dosyaları hedef/yetki/byte sınırları içinde yükler ve neyin doğrulandığını görür. Cevap kaybında aynı operation ID'sine dönüp salt okuma ile durumu inceler; ikinci create/PUT üretmez. Gelişmiş etkili resume P02-3a'dır; ilk kesinti güvenliği ve read reconciliation bu pakettedir.

## Başlangıç kapıları

| Kapı | Mevcut kanıt / açılma koşulu | Bekleyen dilim |
|---|---|---|
| Karar | [ADR-0024](../decisions/0024-durable-dataset-transfers.md)/[0025](../decisions/0025-isolated-storage-streaming.md) Accepted — 2 Kasım kullanıcı yetkisi/review düzeltmeleri; yerel uygulama açıldı, gerçek otorite/wire kapıları ayrı | Yerel ve uzak bağımlı ürün kodu |
| Create/link authority ve wire | Kamu istemcisi `POST datasets` ve **ayrı** `POST projects/{id}/datasets` gösteriyor; API-key auth, owner/project ve current izin oracle'ı doğrulanmadı | Gerçek adapter, prepared/start pozitif yolu |
| Upload/verification wire | `my-role`, presign direct/proxy, `client_uid`, `skip_dedup`, item cursor alanları istemci kanıtı; exact strict response/expiry/header/object key güvenliği ve aynı hash farklı ad desteği açık | Gerçek adapter/pozitif aktarım |
| Live yetki | Mevcut private test projesi önceki discovery kabulündendir. Kullanıcı son yanıtında küçük denemeye ve 200 CR aşımına izin verdi; somut ilk pilot aşağıdaki tek dataset/üç küçük görselle sınırlıdır; ilk create 201, sonraki detail GET 405 ve kontrollü durma [kaydedildi](../research/p02-2-private-create-observations.md) | Canlı yazma kabulü |
| Fiyat ve kalacak kaynak | Kullanıcı başlangıçta **200 CR** tavanı belirledi, sonraki yanıtında bu tutarın aşılmasını kabul edip denemeyi istedi. İlk deneme tek private dataset/≤1 MiB üç görselle sınırlanır; create/storage/upload/okuma tarifesi ve provider hard-cap mekanizması hâlâ doğrulanmadı. Bu tercih ürün cost-bound/authority kanıtı değildir. Kaynak private kalır, otomatik silinmez | Canlı kabul |

Onaylanan mimariyle bağımsız local domain/journal/stream fixture işi bu dış kapıları beklemeden ilerleyebilir. Ancak adapter endpoint'leri tahmin edilmez; public `prepared` veya ürün/live `verified` iddiası kapılar kapanmadan yoktur. Dış gate kapanmazsa P02-2 partial/blocked nedeni ve somut açılma koşulu kaydedilir; kapsam kullanıcı kararı olmadan daraltılmaz. [Araştırma](../research/p02-2-readiness-review.md) bu kapıların kanonik kanıtıdır.

## Adımlar ve review döngüsü

Her uygulama adımı: **geliştir → ilgili gerçek kontroller → commit → fresh review R1 → doğrulanmış bulgu/fix/commit → farklı fresh reviewer R2 → doğrulanmış bulgu/fix/commit**. Reviewer'lar bulgu metni/yol/kodu untrusted veri sayar, current code ile doğrular; geçmiş yorum körlemesine uygulanmaz. İşin karmaşıklığına göre iki bağımsız eksen (state/güvenlik ve contract/UX/test) kullanılır. Önceki adım kabul/review bitmeden bağımlı sonraki kod adımına geçilmez. Sonuçsuz tercih yeni bug diye sunulmaz. Gerekli düzeltmenin doğrulaması aynı turda tamamlanır; iki tur tamamlandı diye açık bulgu bırakılmaz.

| Adım | Sahip | Tek review sonucu / başlama kapısı |
|---|---|---|
| 0 | Paket hazırlığı | Mevcut belge/kod ve güncel kamu sözleşmesi review'si, iki Proposed ADR, gerçek kartlar ve dış kapılar; iki fresh belge turu, kullanıcı ADR onayı |
| 1 | [P02-2d](tasks/p02-2d-upload-plan-contract.md) / P02-2a yerel | Exact public/private wire, immutable upload plan/manifest, strict model/oracle, digest approve/revoke ve ortak kullanım senaryosu; ADR onayı gerekir, remote permission uydurulmaz |
| 2 | [P02-2e](tasks/p02-2e-durable-transfer-journal.md) / P02-2a kalıcılık | 6→7 V2, quota/recovery rezervi, tekil niyet/intent/receipt, current credential/lease/clock, reset/preview/frontier ve eski restore yasağı; aynı kayıt üzerinde kill/race kabulü |
| 3 | P02-2a uzak | Gerçek current create/link authority producer, strict endpoint codec ve private create/proje bağı; auth/owner/project wire kapısı önce kapanır |
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

## ADR-0026 önerisine bağlı sonraki sıra

[ADR-0026](../decisions/0026-explicit-unverified-transfer-attempts.md) Proposed; mevcut Accepted kapıları henüz değişmedi. Kullanıcının onayı gelirse önce (1) ayrı v2 policy/plan/approval reducer ve literal golden'lar, sonra (2) v1/v2 kapalı journal decoder/arm/read/reset/quota/preview uyumu uygulanır. Bunlar M veya daha küçük yeni hazır kartlara bölünür; d/e/f'nin mevcut v1 yerel teslim kanıtı tarihsel korunur. Her kod dilimi commit + fresh R1 + fix + farklı fresh R2 + fix ister.

Ardından gerçek current tüketici codec'leri ve private create/proje bağı, bounded upload ve ortak public CLI/Python; aynı-ID read reconciliation ve bütünleşik UX/native/kurulum/source-CI/kanıt kapanışı gelir. Öneri v2 explicit operasyon için ayrı insan seçimiyle current scoped read-attempt ve metadata sonucunu da tanımlar; v1/default read grant kapısı korunur. Yeni politika tek başına provider wire, aynı hash farklı ad desteği veya canlı kabulü kapatmaz. Durmuş araştırma workflow'ı yeniden arm edilmez; sonraki canlı write kendi somut planı/kapsamı hazır ve review edilmişken ayrıca değerlendirilir. Bu öneri yeni bir canlı write çağrı yetkisi değildir.
