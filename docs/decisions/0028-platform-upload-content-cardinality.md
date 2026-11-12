# ADR-0028 — Platform upload’ında tekrarlı içerik sınırı

**Durum:** Accepted — 4 Kasım kullanıcı review düzeltmeleri sonrası uygulamayı yetkilendirdi; revizyonlar iki farklı fresh turda temiz teyit edildi. Ürün/kabul geçişi aşağıdaki adımlarla uygulanır. **Tarih:** 2026-11-04. **İş:** P02-2 canlı kabulü. Öneri, [ADR-0024](0024-durable-dataset-transfers.md) ve [P02-2c kabul 8](../roadmap/tasks/p02-2c-upload-recovery-acceptance.md#kabul) içindeki aynı hash/farklı ad olumlu upload beklentisini daraltır. Manifest v1, geçmiş kayıtlar ve tam başarı grafiği değişmez.

**2026-11-06 kısmi değişiklik (Accepted):** [ADR-0031](0031-upload-continuation.md) yalnız **v3 continuation kayıtları** için başarı grafiğini “seçilen M dosyanın 3M accepted makbuzu + N dosyalık metadata kanıtı + kök operation’ın CreateReceiptV2 baseline eşliği” olarak tanımlar; v1/v2 kayıtları, golden’ları ve bu kararın diğer hükümleri değişmez.

## Bağlam ve kanıt sınırı

[r4 gerçek public koşusu](../research/p02-2-implementation-validation.md#4-kasım--r4-aynı-içerik-kardinalitesi-engeli), iki farklı içerik için accepted confirm üretti; üçüncü, farklı adlı fakat önceki dosyayla aynı SHA-256 içeriğinde created=0/batch_duplicates=1 döndü. İstek mevcut consumer’ın skip_dedup=true alanını taşıdı. Uygulama bunu accepted receipt veya başarıya çevirmedi; aynı operation unknown kaldı. Toplam 237 byte gönderildi; tekrar yapılmadı. Bu tek gözlem bütün hedef/sürüm/konfigürasyonlarda aynı davranışın kanıtı değildir; bugünkü yolun istenen pozitif kabulü karşılamadığını gösterir.

Sağlayıcının [güncel public istemci varlığında](https://evren.ssyz.org.tr/assets/DatasetDetailPage-CbVRFkdP.js) confirm JSON’unda skip_dedup görülür (4 Kasım, 293.478 byte, SHA-256 `767580ed265f555d416109d9a35cd0a883ba26085bc01bd214f187c04dace258`). Kaynak credentialsız indirildi, yürütülmedi. İstemci kodu sunucunun aynı içerikli adları koruduğunun garantisi değildir. Desteklenen alternatif henüz bilinmiyor; farklı flag/rota/yanlış hash veya batch davranışı tahmin edilerek yeni etki yapılmaz.

Bağımsız storage tanısında same-content.png confirm edildiğinde first.png henüz confirm edilmemişti; dataset’te yalnız farklı içerikli different.png vardı. O iki-slot başarısı aynı hash’in iki adla birlikte korunmasını sınamadı. Kural, r4’teki üçüncü-dosya vakasından daha geniş, iki dosyalı tekrar dahil her tekrarlı SHA-256’yı kapsayan bilinçli muhafazakâr sınırdır. Farklı hash de sağlayıcı tekilliği garantisi değildir; tam graph/metadata oracle’ı her işte korunur.

Kamu kaynağının kalıcı gözlem metadatası [ayrı receipt’te](../research/p02-2-public-source-20261104-receipt.json) tutulur. Gözlenen ifade skip_dedup:!m’dir: yerel m değerinin boolean tersi JSON’a yazılır; m’nin tüm UI durumları veya sunucu davranışı bundan türetilmez.

## Karar

P02-2’nin mevcut Platform producer’ı ilk teslimde yalnız **dosyaların SHA-256 değerleri birbirinden farklı** upload manifestlerini başlatır. Aynı hash taşıyan farklı adlar Manifest v1’de ayrı dosyalar olarak geçerli kalır; yerel inspect/verify bunları korur. Upload yolu dosyaları birleştirmez, atlamaz, yeniden adlandırmaz, içerik/hash değiştirmez veya kısmi teslimi tam başarı saymaz.

Yeni `upload_duplicate_content` kodu exit 2’dir. Kapalı mesaj: “Aynı içerikli farklı dosya adları bu Platform upload yolunda desteklenmiyor. Uzak istek yapılmadı. Manifestteki sha256 değerlerinden tekrarlayan adları bulun; istediğiniz dosyalar için ayrı bir klasör ve yeni manifest hazırlayın.” Yol/hash/provider metni eklenmez; CLI text/JSON/NDJSON ve Python aynı kod/mesajı kullanır. Kanonik katalog `src/yorunge/domain/errors.py`, hata referansı `docs/reference/dataset-transfer.md`’dir; public referansa ikinci katalog eklenmez. Mevcut hata zarfı korunur: operation_id null, mevcut details boş nesne; yeni details/sayaç alanı yoktur. Yerel manifest zaten ad/SHA alanlarını taşır; kullanıcı rehberindeki salt yerel örnek tekrarları bunlardan bulur. Kapalı sayaçlar hangi adların çakıştığını çözmeyeceği için bu düzeltmede DTO/inspect biçimi genişletilmez.

### Kapı yeri ve hata önceliği

Ortak saf `require_distinct_upload_content(manifest)` kontrolü yalnız mevcut Platform producer kompozisyonunda uygulanır; manifest/snapshot validator’ının veya repository full graph doğrulamasının yeni invariant’ı değildir.

| Giriş / tarihçe | Sıra ve sonuç |
|---|---|
| Yeni prepare | Mevcut argüman/policy/target/storage → `_bind`/secret → mevcut namespace/latch preflight → güncel capture/hash → namespace yeniden denetimi → duplicate kapısı → plan seal/HTTP/save. Gözlenen input_changed/limit/secret/namespace hataları önce gelir. Sıfır HTTP, plan/namespace business insert yok; mevcut credential bookkeeping/clock yazısı olabilir |
| Approve | `read_approval_input`: plan/status/digest/süre → ack → mevcut approval/operation conflict → saved manifest doğrulama → duplicate kapısı. Sonra deferred config/env/credential/capture/HTTP. Ret halinde registry ve upload business yazısı yok. Saved duplicate kapısı dosyaları yeniden açmadığından sonraki input_changed/config/env hatasından önce gelir |
| Start: plan için operation kaydı **yok** | `_initial`: plan/status → approval varlığı/status → plan/approval süreleri → saved manifest doğrulama → duplicate kapısı; ardından context loader/_bind/capture/HTTP/admission. Ret halinde registry/admission/lease/permit yok. Saved duplicate ret, sonradan gözlenebilecek input_changed/config/env hatasından önce gelir |
| Start: operation kaydı **var** | `_initial` önce mevcut operation’ı döndürür; config/env/source/hash/duplicate kontrolü yapılmaz. Mevcut same-ID terminal/unknown/conflict semantiği ve sıfır yeni write korunur |
| show/list/review/revoke/reconcile | Yeni uygunluk kapısının dışında; yerel inspection/revoke ve mevcut izinli salt okuma uzlaştırması korunur. Yeni workflow veya replay hakkı yoktur |
| Eski binary/önceden verilmiş permit | Geri çekildiği/rollback yapıldığı iddia edilmez; ADR-0016/0024 fencing sınırı korunur |
| Terminal/unknown tarihçe | Decode/full validation/digest/golden/status değiştirilmez; tarihçe yeni kurala göre geçersiz kılınmaz |
| Tekil hash’li yeni işte duplicate/eksik/yanlış metadata | Mevcut strict ret ve aynı-ID unknown; otomatik başka plan/flag/batch/istek veya cleanup yok |

Yukarıdaki business/registry yazı sınırları, store açma/migration/global clock bookkeeping’inin bütün disk yazılarını sıfırladığı iddiası değildir. Mevcut public argüman/state doğrulaması ve lifecycle hata öncelikleri korunur. Namespace preflight bugün zaten hash ve HTTP’den öncedir; yeni bir sıralama refaktörü gerekmez.

Başarı tam create/project-link ve her N dosyada presign/PUT/confirm grafiği, **2+3N accepted receipt** ve N tekil ad/item için exact size/SHA metadata eşliği ister. created=0 veya batch_duplicates>0 kabul edilmez. Authority/pricing/remote-byte iddiaları yükseltilmez. N=1 için 5, N=2 için 8, N=128 için 386 tam aşama gerekir; N=0 mevcut input_invalid kuralıyla reddedilir. V1/v2 plan/approval/receipt/proof sürümleri, DDL/checksum, limit/deadline ve Result envelope değişmez; hata kataloğuna yalnız yeni kod eklenir.

## Kısmi değişiklik ve onay sonrası geçiş

| Kaynak | Onay sonrası değişiklik |
|---|---|
| ADR-0024 ve karar indeksi | Özgün karar/kabul metni korunarak tarihli kısmi değişiklik notu ve indekste amendment işareti eklenir; aynı hash/farklı ad için yerel upload ret, Manifest koruması. Özgün olumlu çoklu-ad ihtiyacı [P02-R2](../roadmap/tasks/p02-r2-upload-content-cardinality.md) / datasets modülünde açık kalır |
| P02-2b bağımlılık/kabul 4 | Açık destek sınırı ve sıfır-HTTP negatif; eksik item yanlış success sayılmaz |
| P02-2c kabul 8, paket/live planı (tarihli amendment ile) | İki farklı içerikli PNG ile tam olumlu canlı yol; r4 kontrollü durması ve yerel preflight ret kabulü ayrı tutulur |
| P02-2u / tests/integration/test_upload_acceptance.py | 128 dosyanın tamamı farklı SHA-256; 128 distinct item ve **386 accepted aşama** korunur. Eski eş-hash olumlu kabul tarihsel kayıtta kalır; güncel uygunluk negatifi ayrı sıfır-HTTP testidir. batch_duplicates>0 codec reddi korunur |
| scripts/upload_live_acceptance.py / tests/integration/test_upload_live_acceptance.py | N=2/158 byte/8 graph; dosya/byte/receipt/item beklentileri N’den türetilir. Yeni private araştırma receipt’inde same_hash_different_names kaldırılır; olumlu işte kanıtlanmamış iddia yazılmaz |
| Frozen pilot.py, upload_storage_diagnostic.py, tarihsel receipt’ler | Üç PNG/237-byte tarihsel kaynak ve tamamlanmış üç-slot tanı değişmez. Yeni runner frozen fixtures() çıktısından literal ad/hash ile yalnız first.png/different.png seçer; frozen Pilot çalıştırılmaz |
| P02-2d/o ve capture_upload_input/Manifest | Yerel aynı-hash/hardlink dosya kimliği ve testleri korunur. Snapshot yakalama ayrı, yeni producer uygunluk kararı ayrıdır |
| tests/integration/test_upload_file_workflow.py ve onu tüketen çoklu-dosya pozitifleri | Yeni public/original writer olumlu fixture’ları tekil hash’e taşınır; historical/lower-level codec/receipt ve input-koruma testleri topluca değiştirilmez |
| Provider/prepare/public/transfer referansları, README/quickstart, current/faz/matris/changelog | Kullanıcı sınırı ve hata/sonraki adım; live/native/CI kapanmadan verified yazılmaz |

Bu geçişler Accepted geçişinde uygulanır; yeni davranış kod/test/live kabulü geçmeden uygulanmış veya verified sayılmaz. Önceki üç-item olumlu kabul **koşulu**nun r4’te sağlanmadığı korunur; r4 başarısızlığı pozitif kabul sayılmaz.

## Uygulama ve kabul planı

1. Ortak manifest uygunluk kapısı ve `upload_preparation.py`/`upload_original.py` prepare/approve/start kompozisyonu; yeni/eski-tarihçe ayrımı. Yeni ve eski duplicate plan için CLI/Python text/JSON/NDJSON kod/mesaj, sıfır HTTP/etki ve historical terminal/unknown/read-only regresyonları. Commit + iki fresh review turu.
2. Mevcut runner’a iki özgün, farklı hash’li PNG seçkisi (158 byte), **8 accepted intent/receipt** ve iki distinct item doğrulaması; private receipt’te yanlış same_hash_different_names iddiası yoktur. Eski üç-dosya frozen fixture/receipt’ler değişmez. Gerçek API/TLS success; duplicate-ret ise sıfır HTTP/TLS isteğiyle yerel preflight negatifidir, yeni canlı duplicate denemesi yapılmaz; commit + iki fresh tur. Yeni somut instance/istek/byte/süre/maliyet/stop koşulları çağrıdan önce live planına yazılır; mevcut genel kontrol yetkisi aşılmaz. ADR onayı kendi başına yeni canlı yetki değildir.
3. Olumlu canlı kabul sonrası **bir kez** son kaynak M5 serisi 03, üç ortam tam source CI/altı kurulum, Sonar ve kalıcı saklama; sonra PR #14 kullanıcı review’si. Eski başarısız koşular ve 01/02 referansları korunur.

## Alternatifler ve sonuçlar

- **Sağlayıcı çözümünü beklemek:** Özgün olumlu kabul korunur, P02-2 draft kalır; takvim dış sağlayıcıya bağlıdır.
- **Açık ret ile sınırlı ilk yolu teslim etmek (önerilen):** Farklı içerikli upload kullanılabilir; aynı içerikli ad ihtiyacı P02-R2’de açık ve görünürdür. Uygunluk kapısı gereksiz create/storage maliyetini önler.
- Sessiz dedup/skip, yanlış hash/eksik item ile başarı veya rastgele tekrar seçilmedi; dosya kimliğini/tek gönderimi ihlal eder veya kanıtsızdır.

Bu bir kapsam tercihidir; sağlayıcı davranışını düzelttiği iddia edilmez. Kullanıcının review düzeltmeleri sonrası uygulama yetkisi ve iki fresh revizyon teyidiyle Accepted’a geçildi; bağımlı uygulama yetkilidir.
