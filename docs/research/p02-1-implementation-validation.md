# P02-1 hazırlık ve uygulama kaydı

**Durum:** P02-1a verified; ADR-0023 Accepted, P02-1b implementasyonu başladı; ürün epik kabulü yapılmadı. **Tarih:** 2026-11-01. **Dal:** `feat/p02-1-local-manifest`, taban `9f30fd2`. P02-0 merge kapanışı önceki `139ab91` commit’inde korunur. [Teslim planı](../roadmap/p02-1-delivery-plan.md), [ADR-0023](../decisions/0023-local-dataset-manifests.md), [manifest referansı](../reference/dataset-manifest.md).

## Belge ve mevcut kod incelemesi

Roadmap/faz/modül ve ilgili mimari/standart/referanslar planın inceleme listesiyle karşılaştırıldı. `DescriptorInputs` en çok 128 explicit execution referansını hash’ler; recursive envanter/manifest parser/atomik dataset artifact’ı yoktur. Yeni tasarım mevcut execution biçimini veya gerçek yetki kapısını genişletmez. CLI’daki planlanan `datasets` ailesi seçildi; P03 LLM içerik araçlarını sahiplenen `data` ailesi kullanılmaz.

Bağımsız hazırlık incelemeleri dosya güvenliği ve kanıt kapasitesini ayrı değerlendirdi. Dosya kolu; final üyelik/dosya imza kontrolü, aynı hash farklı ad, Unicode/case directory çakışması, root dışı çıktı, timestamp/root’u içerik digest’inden ayırma ve açık kaynak tavanları önerdi. Bunlar ADR-0023/ref/kartlara aktarıldı. Mevcut P01 binder’ında bu inceleme kapsamında doğrulanmış yeni kusur saptanmadı; yeni özellik eksikleri mevcut destekmiş gibi sunulmadı.

2026-11-01 B15 salt okunur sayımı: **247/256 kayıt**, manifest **369.514 byte**, indeks **235.437 byte**, toplam gzip **2.106.036 byte**, açılmış özgün içerik **16.303.574 byte**. En büyük gzip **50.467 byte**, en büyük özgün rapor **872.182 byte**. Mevcut verifier 247 arşivi geçti; bu yeni performans veya ürün kabulü değildir. Aynı v1 biçimiyle bounded büyüme, bölümleme/migration’a göre daha dar değişikliktir. Seçilen tavanlar/kabul P02-1a’da; eski başarısız ölçümler ve kaynak referansları korunur.

Resmî Python os/Unicode ve Linux link/fsync belgeleri ADR’nin teknik dayanak bölümüne tarih/sınırla bağlandı. Enumeration atomikliği, bütün platformlarda aynı Unicode kabulü veya fiziksel sync garantisi uydurulmadı. Canlı EVREN veya kullanıcı anahtarı okunmadı; bu yerel iş bunlara ihtiyaç duymaz.

## Hazırlık review ve onay kapısı

ADR-0023 ve bağlı taslaklar kullanıcı onayı bekler. İlk fresh belge turunda iki bağımsız reviewer üç P2 ve bir P3 doğruladı: kritik link çağrısı içindeki iptal belirsizliği, dayanıklı API başarısı sonrası renderer exit önceliği, native bellek L/U/G kabulü ve güncel NDJSON tavanı. Bulgular mevcut config/stream/performance sözleşmesiyle doğrulanıp ADR/ref/plan/kartlarda kapatıldı. İkinci fresh belge turunda bir reviewer yeni bulgu bulmadı; diğer reviewer kontrol karakterli uzun artifact ankrajının JSON escaping ile ≤16 KiB özeti aşabildiğini bağımsız fixture’la doğruladı (2.997 byte yol → 17.680 byte Result). Ankraj/leaf kontrol-bidi politikası ve publication öncesi exact encoded özet preflight’ı ADR/ref/kartta netleştirildi. Bu son düzeltme ayrıca iki fresh kod reviewer’ı tarafından hedefli teyit edildi; yeni doğrulanmış belge bulgusu çıkmadı. Hazırlık kontrolleri runtime testinin yerine geçmez. Yeni ürün kodu ve manifest/scan/CLI uygulaması henüz başlamadı.

## Uygulama ve nihai kabul

P02-1a ilk uygulaması, aynı evidence v1 isim/byte yapısını koruyarak 4.096 kayıt ve 128/512 MiB toplam bütçeyi, yazı öncesi tam eski katalog/indeks doğrulamasını ve yeni metadata byte preflight’ını ekledi. 71 odaklı test ve gerçek 247 arşiv geçti. İlk kod turunda iki fresh reviewer 71 testi ve eski 247 arşivi ayrıca doğruladı. Bir P2: GzipFile.read(1) gerçekte 8.192 decoded byte üretiyordu; kalan gerçek decode bütçesi + tek sentinel sözleşmesi için read1 döngüsü ve gerçek _GzipReader tüketimini sayan regresyon eklendi. İkinci fresh kod turunda bir reviewer yeni bulgu bulmadı; diğer reviewer aynı prefetch riskini compressed dosya okumasında gerçek verify yoluyla doğruladı (kalan 1 byte + sentinel 1 yerine FileIO 4.096 byte okudu). Tamponlamasız FileIO ve ortak bounded kısa-okuma döngüsü eklendi; gerçek ham tüketim 0/1/17/4.096/8.192 bütçelerinde, decoded tüketim ayrı sabit negatiflerde test edilir. Geçerli kısa okumaların tamamlanması da sınanır. Son ec40164 düzeltmesi iki yeni bağımsız reviewer ile hedefli statik teyitten geçti; yeni doğrulanmış bulgu çıkmadı. Bu son tur sırasında seri profil alındığı için reviewer’lar test/benchmark koşturmadı; çalışma ağacını değiştirmedi. Strict mypy mevcut 74 runtime kaynak dosyasında geçti; araştırma scriptinin bu mypy kapsamına dahil olduğu iddia edilmez. Kaynak map’i script/test değişikliği nedeniyle değişti; eski M5 referansı yeni kaynak kabulü değildir, final P02-1d’de fresh ölçüm zorunludur.

Her adımın uygulama commit’i, iki fresh review turu, doğrulanmış bulgu/fix commit’i ve gerçek kontrol kanıtı burada tutulacak. Nihai startup/jobs/dosya ölçümleri, paket ve PR/CI yapılmadan P02-1 ürün epik kabulü veya verified durumu yazılmaz; aşağıdaki bağımsız P02-1a bakım kabulü ayrıdır.

## P02-1a kapanışı — yerel ve bağımsız bakım

- PR/commit: ilk uygulama [694a7b7](https://github.com/HodeTech/Yorunge/commit/694a7b7), decoded prefetch düzeltmesi [b301682](https://github.com/HodeTech/Yorunge/commit/b301682), raw prefetch/short-read düzeltmesi [ec40164](https://github.com/HodeTech/Yorunge/commit/ec40164). Aynı nihai P02-1 PR’ına girecek; henüz PR/merge/yayın yoktur.
- Birinci fresh kod turu: iki reviewer, 71 odaklı test/247 arşiv; bir decoded-prefetch P2 kapatıldı. İkinci fresh kod turu: iki farklı reviewer, 76 odaklı test/247 arşiv; bir raw-prefetch P2 kapatıldı. İki ek fresh hedefli teyitte yeni doğrulanmış bulgu yok. Mevcut code/test/standard aynı bütçe anlamını taşır.
- Son kaynakta **425 ilgili evidence/installation/jobs/stream/startup/baseline/diagnostic testi**, Ruff format/lint ve strict mypy (74 runtime dosyası) geçti. Tam ürün takımı/build/temiz kurulum veya yeni startup/jobs performansı bu bağımsız adımda yeniden koşulmadı; P02-1d final kabulüdür.
- Tarihsel byte eşliği **139ab91** P02-0 kapanış commit’indeki 247 entry ve gzip SHA-256’sıyla birebir karşılaştırıldı; eski indeks bu entry’lerden byte-identical yeniden üretilir, anchor/ilk-kayıt linkleri değişmedi. Katalog yeni profil kaydıyla **248/4.096** oldu; gzip/manifest/indeks gerçek verifier’dan geçti.
- İki eski M5 referans adı bulunmaya devam eder; doğru biçimde `complete current source bytes` uyuşmazlığıyla reddedilir. Bu beklenen kaynak kapısıdır; yeni script/test baytları eski başarılı ölçüme eşitlenmedi. Fresh kaynak bağlı referanslar P02-1d’de zorunlu kalır.

[Yoğun katalog ham profili](evidence.md#p02-1a-evidence-catalog-profile), ec40164 kaynak commit’i ve script/test before/after SHA eşliğiyle kayıpsız arşivlendi. Apple M5 Max/arm64, macOS 27.0.1, CPython 3.11.18; disk türü **unknown** olarak kaydedildi. Her satır üç bağımsız seri yeni süreçtir, bütün örnekler saklanır. `time -l` Darwin native **lifetime peak byte** sayacı kullanıldı; fark/anlık baseline veya referans performans kabulü iddia edilmez. Contract satırları pytest başlangıcı, dosya fixture kurulumu ve bütün assert/verify işlerini içerir; yalnız verifier RSS’i değildir. Fiziksel duvar saati hedefi veya en iyi örnek seçimi yoktur.

| Profil | Üç wall ölçümü (ms) | En büyük native lifetime RSS (byte) |
|---|---|---:|
| Mevcut 247 arşiv verifier | 752,030 / 743,581 / 750,128 | 48.709.632 |
| Gerçek 256→257 kayıt contract yolculuğu | 423,559 / 375,170 / 439,195 | 79.495.168 |
| Gerçek 4.096 kayıt ve sonraki yazıda no-mutation ret | 1.123,990 / 1.156,655 / 1.142,848 | 107.642.880 |

B15 kapanışı aynı evidence v1 biçiminde kapasite ve bounded tüketim bakımını tamamlar; ürünün 64 MiB ek RSS veya startup/jobs hedefinin geçtiği anlamına gelmez. P02-1 ürün manifest/scan/CLI kodu henüz yoktur; ADR-0023 Proposed ve açık kullanıcı onayı bekler. Epik partial’dır, verified değildir.

## Kullanıcı ADR review’si ve Accepted geçişi

Kullanıcı 2026-11-01 tarihinde aşağıdaki bulguların giderilmesinden sonra ADR’yi Accepted yapmayı ve uygulamayı açıkça yetkilendirdi. Önceki Proposed/onay bekleme cümleleri tarihsel hazırlık aşamasıdır.

- Gerçek CancelledError yayılımı geçerli P2: public dataset API senkron; async entry/Task.cancel ile thread durdurma vaadi yok. Alt çağrıdan gelen CancelledError cleanup sonrası aynen yayılır; kritik publication başlamışsa yalnız sabit uncertainty exception note’u eklenir. CLI KeyboardInterrupt/exit normalizasyonu ayrı kalır; ADR-0018 değişmez.
- Ortak input mesajları geçerli P2: kod/exit’i koruyup hem execution hem dataset için doğru yerel dosya/kök sonraki adımı söyleyecek biçimde güncellenir; text/JSON/NDJSON mesaj regression’ı final CLI kabulündedir.
- Belirsiz “kontrol dizinleri”, hardlink cümlesi, tam encoded Result/DTO/NDJSON payload boyutu ve B15 çapraz referansı netleştirildi. Mismatch sayaçları kod başlamadan missing_file_count/unexpected_file_count/changed_file_count olarak adlandırıldı.
- Son geçiş ikinci içerik hash’i değildir; device/inode/mode/size/mtime_ns/ctime_ns metadata, dizin üyeliği ve root zinciri yeniden denetlenir. Primitive destek kapısı manifest okuması ve tarama dahil filesystem I/O öncesindedir. unicode_version kaynağı unicodedata.unidata_version’dır.
- Verify sonucuna opsiyonel manifest_path eklenmedi: caller manifest yolunu zaten açık verir, taşınabilir manifest_digest kesin içerik kimliğidir; yeni gereksiz alan kapalı wire’a eklenmez. CLI hata tablosunu kopyalamadan kanonik manifest referansına bağlar.
- Başlık değişikliği tercih notu olarak uygulanmadı; “sınırlı” sayısal bounded kaynak politikasını ifade eder. L/U/G negatifleri ve boş dizin farkı kabulde korunur. Root içindeki manifest örneğinin mismatch olduğu yorumu geçerli değil: mevcut sözleşme otomatik ignore etmez ve root içi artifact’ı taramadan önce input_invalid ile reddeder. UCD sürümü aynı dosyada saklanmadığı için uydurma “version mismatch” teşhisi eklenmez; gerçek runtime sürümü sonuçta ve Unicode çakışma sınırı yardımda açık kalır.

Yeni ADR veya yeniden kullanıcı seçimi gerektiren temel kapsam değişikliği yapılmadı. Bütünlük/hash/dosya politikası ve limitler onaylı biçimde korunur. Bundan sonraki adımlar önceki planın commit ve iki fresh review döngüsüyle sürer.

## P02-1b — manifest modeli ve parser kapanışı

Yerel uygulama 67ea66f, type-before-copy düzeltmesi de366c2, bağımsız aggregate oracle’ı 787fc7c ve duplicate-key oracle’ı fc16ca1 commit’lerindedir. DatasetManifest/DatasetFile strict/frozen/closed model, exact canonical byte/digest, portable path/inferred directory quota ve 8 MiB/depth8/node50.000 parser kapıları uygulanmıştır. Golden fixture’ın canonical gövdesi literal olarak yazıldı; digest üretici fonksiyonu kullanılmadan shasum ile sabitlendi. Ortak input hata mesajları execution planı üretmeyen kullanıcıya da doğru yerel denetim adımını verir; kod/exit korunur.

R1 iki fresh reviewer: ürün kusuru yok; yanlış digest’in aggregate/sıralama/duplicate path retlerini maskeleyebildiği bir test kabul açığı doğrulandı. Geçerli independently re-signed bozuk gövdelerle kapatıldı. R2 iki yeni fresh reviewer: ürün kusuru yok; eksik şemalı duplicate-key örneklerinin guard regresyonunu yakalamadığı bir kabul açığı doğrulandı. Tam golden wire’a root/dosya seviyesinde same-value duplicate eklenerek kapatıldı. İzole guard çıkarma deneyi bu iki yeni oracle’ın duyarlılığını doğruladı; ürün kaynağı değiştirilmedi.

Son kaynakta **124 manifest + 216 core boundary = 340 test**, Ruff format/lint ve **75** runtime kaynağında strict mypy geçti. Yeni feature modeli eski context/help import yoluna yüklenmiyor. İlk lint satır uzunluğu ve test mesajındaki case-sensitive assertion düzeltilip kontrol yeniden geçti; başarısız ara koşu son kabul diye sunulmadı. Filesystem/FD/race, gerçek public API/CLI ve performans bu kartın teslim iddiası değildir. P02-1b verified; P02-1c başladı, P02-1d final kabulü açık kalır.

## P02-1c — descriptor envanteri ve verify çekirdeği

İlk uygulama 5695c62: no-follow recursive normal-file scan, bounded bir-worker hash, tüm dosya/dizin metadata/üyelik ve kök zinciri son denetimi; root dışı bounded manifest read, strict decode, monotonic budget ve kapalı mismatch sayı/digest çekirdeği. Same hash/hardlink adları ayrı tutulur, boş dizinler güvenlik/kota kontrolünde sayılır, içerik kimliğinde yoktur. Public API/CLI veya artifact yayını henüz bu adımda açılmadı.

R1 iki fresh reviewer tek P2 kökü doğruladı: paylaşılan directory_chain/relative_file helper’ları parent close hatasında child/leaf FD’sini kaybedebiliyor ve cleanup hatası gerçek CancelledError’ı maskeleyebiliyordu. b489516 sahiplik devrini child açılır açılmaz kaydeder; başarısız leaf devri kapatılır ve belirsiz close tekrar edilmez. R2 iki yeni fresh reviewer bir P2 doğruladı: sys.exception çağıranın ilgisiz except bağlamını da gördüğünden normal close EIO’su yutulabiliyordu. 06223b9 explicit primary argument ve yalnız kendi işleminin istisnasını yakalayan owned context ile kapattı. İki ek fresh hedefli teyitte yeni bulgu yok; kaynak sahipliği/iptal ve legacy uyumu ayrıca incelendi.

Son geniş küme **901 test**: dataset filesystem/manifest, legacy input, core, stream/model/codec/limits/CLI output, execution planı ve onayı. Ek config/secret/state guard’ı 1/1 geçti. Dataset+legacy input alt kümesi 112/112 idi (son guard sonrası 113 test); 77 runtime dosyasında strict mypy ve Ruff geçti. Gerçek 4.096-file ve root dahil 4.096-directory kapasitesinin −1/exact/+1 retleri, maksimum 32 bileşen ve ≤64 owned FD, raw same-size/root/ancestor/leaf/FIFO/manifest-read yarışları ve exact byte/no-sentinel hash sınırı sınandı. Gerçek socket/FIFO kullanıldı; character-device ve farklı device sınırı stat metadata enjeksiyonudur. İlk Unix socket fixture’ında macOS pathname limiti aşıldı; relative socket bind ile fixture düzeltilip tekrar geçti, ürün ret nedeni gibi sunulmadı.

Bu kaynak kabulü fiziksel güç kesintisi, gerçek Windows/EVREN, büyük dosyanın native RSS/duvar saati veya bütün ağacın atomik snapshot ispatı değildir. Kurulu artifact/API/CLI ve 16/256/1.024 MiB native bellek kabulleri P02-1d’de zorunlu kalır. P02-1c verified; P02-1d başladı.


## P02-1d adım 4 — yayın ve public yüzey uygulaması

Çalışma dalında `api.inspect_dataset/verify_dataset` aynı application bütçe/parser/scan/karşılaştırma yoluna bağlandı. CLI yalnız local datasets seçeneklerini kabul eder; relative iki argüman tek CWD gözlemine bağlanır, unsupported platform bütün I/O’dan önce reddedilir. DTO/Result/NDJSON payload encoded preflight yayından önce yapılır. 0600 aynı-parent stage, bounded kısa-write döngüsü, full-sync, exclusive link, kimliği koruyan stage cleanup ve parent/final kaynak/hedef kontrolleri başarı kapısıdır. Link denemesi sonrası bütün context close/deadline hataları API dönüşüne kadar uncertainty kapısındadır. Gerçek CancelledError aynı nesne ve yalnız sabit note ile yayılır; KeyboardInterrupt CLI 6/5 sınırını korur. Dayanıklı API dönüşünden sonraki çıktı hataları 6/1/6’dır.

İlk 69 uçtan uca test geçti. Ek negatiflerde 11 test fixture/oracle hatası düzeltildi: os.open double’ı primitive destek kümesine eklenmediği için yanlış unsupported yolu, hata retryable alanının envelope yerine nesneden okunması ve eksik test import’u. Ürün başarısızlığı diye sayılmadı. Ardından 87 test geçti; ek gerçek CLI SIGINT/pipe kabulleri son komitle kontrol edilir. Parent’ın son pre-link kontrolünden sonra değişmesi gözlem aralığı sınırıdır; eski held parent’ta tam hedef oluşursa başarı verilmez, uncertainty/5 olur ve replacement parent’a dosya yazılmaz. Bu same-UID saldırgan için sandbox veya atomik snapshot iddiası değildir.

README sentetik yolculuğu, modül ve CLI/reference durumu güncellendi. M5/native kaynak ölçümü, iki temiz kurulum, tam takım ve PR/CI bu adımın başarısı gibi sunulmaz; adım 5’te zorunludur. İlk kod commit’i sonrası iki fresh review turu kaydı buraya eklenecek.
