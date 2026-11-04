# ADR-0028 — Platform upload’ında içerik çokluğu sınırı

**Durum:** Proposed — kullanıcı kararı bekleniyor; aşağıdaki değişiklikler henüz uygulanmaz. **Tarih:** 2026-11-04. **İş:** P02-2 canlı kabulü. Öneri, [ADR-0024](0024-durable-dataset-transfers.md) ve [P02-2c kabul 8](../roadmap/tasks/p02-2c-upload-recovery-acceptance.md#kabul) içindeki aynı hash/farklı ad olumlu upload beklentisini daraltır. Manifest v1, geçmiş kayıtlar ve tam başarı grafiği değişmez.

## Bağlam ve kanıt sınırı

[r4 gerçek public koşusu](../research/p02-2-implementation-validation.md#4-kasım--r4-aynı-içerik-kardinalitesi-engeli), iki farklı içerik için accepted confirm üretti; üçüncü, farklı adlı fakat önceki dosyayla aynı SHA-256 içeriğinde created=0/batch_duplicates=1 döndü. İstek mevcut consumer’ın skip_dedup=true alanını taşıdı. Uygulama bunu accepted receipt veya başarıya çevirmedi; aynı operation unknown kaldı. Toplam 237 byte gönderildi; tekrar yapılmadı. Bu tek gözlem bütün hedef/sürüm/konfigürasyonlarda aynı davranışın kanıtı değildir; bugünkü yolun istenen pozitif kabulü karşılamadığını gösterir.

Sağlayıcının [güncel public istemci varlığında](https://evren.ssyz.org.tr/assets/DatasetDetailPage-CbVRFkdP.js) confirm JSON’unda skip_dedup görülür (4 Kasım, 293.478 byte, SHA-256 `767580ed265f555d416109d9a35cd0a883ba26085bc01bd214f187c04dace258`). Kaynak credentialsız indirildi, yürütülmedi. İstemci kodu sunucunun aynı içerikli adları koruduğunun garantisi değildir. Desteklenen alternatif henüz bilinmiyor; farklı flag/rota/yanlış hash veya batch davranışı tahmin edilerek yeni etki yapılmaz.

## Önerilen karar

P02-2’nin mevcut Platform producer’ı ilk teslimde yalnız **dosyaların SHA-256 değerleri birbirinden farklı** upload manifestlerini başlatır. Aynı hash taşıyan farklı adlar Manifest v1’de ayrı dosyalar olarak geçerli kalır; yerel inspect/verify bunları korur. Upload yolu dosyaları birleştirmez, atlamaz, yeniden adlandırmaz, içerik/hash değiştirmez veya kısmi teslimi tam başarı saymaz.

Yeni `upload_duplicate_content` kodu exit 2’dir. Kapalı mesaj: “Aynı içerikli farklı dosya adları bu Platform upload yolunda desteklenmiyor. Manifesti koruyun; uyumlu bir dosya kümesini ayrı bir kökten açıkça seçin.” Yol/hash/provider metni eklenmez; CLI text/JSON/NDJSON ve Python aynı kod/mesajı kullanır.

| Giriş / tarihçe | Önerilen davranış |
|---|---|
| Yeni prepare, tekrarlı hash | Yerel manifest/hash doğrulamasından sonra, ilk HTTP ve plan business insert’inden önce ret; uzak etki sıfır. Credential bookkeeping’i sıfır yerel yazı diye sunulmaz |
| Eski planın approve veya henüz admission yapılmamış start’ı, tekrarlı hash | Yerel input/manifest kapısı ardından HTTP/approval/admission/permit öncesi aynı ret; kayıt yeniden yazılmaz |
| Mevcut operation için start/show/list/reconcile | Tarihsel davranış korunur: yeni workflow/write hakkı yok; aynı ID bulunur veya mevcut kuralla salt okunur. Eski işi yeni create/PUT’a açmaz |
| Eski binary/önceden verilmiş permit | Geri çekildiği/rollback yapıldığı iddia edilmez; ADR-0016/0024 fencing sınırı korunur |
| Terminal/unknown tarihçe | Decode/full validation/digest/golden/status değiştirilmez; yeni kural historical graph invariant’ı yapılmaz |
| Tekil hash’li yeni işte duplicate/eksik/yanlış metadata | Mevcut strict ret ve aynı-ID unknown; otomatik başka plan/flag/batch/istek veya cleanup yok |

Başarı tam create/project-link ve her N dosyada presign/PUT/confirm grafiği, **2+3N accepted receipt** ve N tekil ad/item için exact size/SHA metadata eşliği ister. created=0 veya batch_duplicates>0 kabul edilmez. Authority/pricing/remote-byte iddiaları yükseltilmez. V1/v2 plan/approval/receipt/proof sürümleri, DDL/checksum, limit/deadline ve Result envelope değişmez; hata kataloğuna yalnız yeni kod eklenir.

## Kısmi değişiklik ve onay sonrası geçiş

| Kaynak | Onay sonrası değişiklik |
|---|---|
| ADR-0024 kabulü | Aynı hash/farklı ad için yerel upload ret; Manifest koruması. Özgün olumlu çoklu-ad ihtiyacı [P02-R2](../roadmap/tasks/p02-r2-upload-content-cardinality.md) / datasets modülünde açık kalır |
| P02-2b bağımlılık/kabul 4 | Açık destek sınırı ve sıfır-HTTP negatif; eksik item yanlış success sayılmaz |
| P02-2c kabul 8, paket/live planı | İki farklı içerikli PNG ile tam olumlu canlı yol; r4 kontrollü durması ve yerel preflight ret kabulü ayrı tutulur |
| Provider/prepare/public/transfer referansları, README/quickstart, current/faz/matris/changelog | Kullanıcı sınırı ve hata/sonraki adım; live/native/CI kapanmadan verified yazılmaz |

Bu geçişler şu an **öneridir**. Accepted ADR’ler ve mevcut üç-item olumlu kabul onaydan önce yürürlüktedir; r4 başarısızlığı pozitif kabul sayılmaz.

## Uygulama ve kabul planı

1. Ortak manifest uygunluk kapısı ve prepare/approve/start kompozisyonu; yeni/eski-tarihçe ayrımı. Yeni ve eski duplicate plan için CLI/Python text/JSON/NDJSON kod/mesaj, sıfır HTTP/etki ve historical terminal/unknown/read-only regresyonları. Commit + iki fresh review turu.
2. Mevcut runner’a iki özgün, farklı hash’li PNG seçkisi (158 byte), **8 accepted intent/receipt** ve iki distinct item doğrulaması. Eski üç-dosya frozen fixture/receipt’ler değişmez. Gerçek API/TLS success ve duplicate-ret negatifleri; commit + iki fresh tur. Yeni somut instance/istek/byte/süre/maliyet/stop koşulları çağrıdan önce live planına yazılır; mevcut genel kontrol yetkisi aşılmaz. ADR onayı kendi başına yeni canlı yetki değildir.
3. Olumlu canlı kabul sonrası **bir kez** son kaynak M5 serisi 03, üç ortam tam source CI/altı kurulum, Sonar ve kalıcı saklama; sonra PR #14 kullanıcı review’si. Eski başarısız koşular ve 01/02 referansları korunur.

## Alternatifler ve sonuçlar

- **Sağlayıcı çözümünü beklemek:** Özgün olumlu kabul korunur, P02-2 draft kalır; takvim dış sağlayıcıya bağlıdır.
- **Açık ret ile sınırlı ilk yolu teslim etmek (önerilen):** Farklı içerikli upload kullanılabilir; aynı içerikli ad ihtiyacı P02-R2’de açık ve görünürdür. Uygunluk kapısı gereksiz create/storage maliyetini önler.
- Sessiz dedup/skip, yanlış hash/eksik item ile başarı veya rastgele tekrar seçilmedi; dosya kimliğini/tek gönderimi ihlal eder veya kanıtsızdır.

Bu bir kapsam tercihidir; sağlayıcı davranışını düzelttiği iddia edilmez. Kullanıcı onayı olmadan bağımlı ürün kodu veya kabul daraltması yapılmaz.
