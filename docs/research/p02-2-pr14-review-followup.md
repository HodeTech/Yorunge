# PR #14 kullanıcı review takibi

**Tarih:** 2026-11-04. **Kaynak:** fd083a2 yerel /7e5675c uzak PR başı; development 50d68b1. **Durum:** Doğrulanmış düzeltmeler uygulanıyor; P02-2/a/b/c ve PR draft. Bu kayıt review iddialarını bağımsız kaynak denetimiyle sınıflar; bütün ajan iddiaları doğru kabul edilmez. Yeni source/test/script değişiklikleri nedeniyle 06 referansı artık önceki kaynağın tarihsel kabulüdür. Son bütün düzeltmeler/review ve gerekli karar kapanmadan yeni native seri veya source push yapılmaz.

## Uygulama sırası

1. **Ağ dayanıklılığı:** RST sonrası kaybolan peer metadata’sı, doğrulanmış DNS alternatifleri, 5 s keepalive ve owned TLS keylogging; aynı HTTP isteği/ortak deadline/peer/TLS sınırları korunur. Gerçek TLS ve bounded unit retleri; commit ve iki farklı fresh review turu.
2. **PUT receipt bütünlüğü:** Aynı anda biten veya cleanup sırasında tamamlanan başarılı task’ların tek publish denemesi; ilk hatadan sonra yeni arm/confirm yok, cancellation ve owner/lease kapıları korunur. Ayrı commit/iki fresh tur.
3. **Kullanıcı yolu ve anlamlı testler:** Onay/plan bayraklarının gerçek CLI negatifleri, v2 binding, populated migration/checksum, ctime recheck, consent/isolation, offline DNS/UDP koruması ve sinyal başlangıç koşulu; hız/süre/kota/hidden-file/unknown rehberi ve doğru hata mesajları. Yeni davranış uydurulmaz.
4. **Belge/kanıt ve teslim:** Aktif durum/head bilgileri, r5’in tarihsel kapsamı, yanlış original_commit ve gerçek proje literal’inin temizliği; gizlilik kararından sonra kişisiz çalışma kökünde bir son kaynak ölçüm serisi, üç ortam CI/altı kurulum/Sonar ve var olan bütün çıktının kalıcı saklanması.

Her kaynak dilimi commit → fresh R1 → doğrulanmış fix → farklı fresh R2 → fix teyidiyle kapanır. Önceden geçmiş bütün takımlar liste doldurmak için tekrarlanmaz; hedefli kontroller seçilir, tam takım final CI’ındır. Linux/macOS kapasite sorunu test veya workflow bypass’ıyla aşılmaz.

## Doğrulanan ürün kusurları

| Bulgu grubu | Bağımsız sonuç ve işlem |
|---|---|
| RST / peer=None | Doğrulanmış stream’in tamponlanmış cevabı okunmadan invalid_service_target verilebiliyor. Başlangıç TCP/TLS peer doğrulaması zorunlu; aynı stream’in sonradan kaybolan metadata’sı alttaki read/write sonucuna bırakılır. Görünen başka/bozuk IP yine reddedilir. |
| İlk DNS adresi | Bütün küme önceden doğrulanır; yalnız TCP kuruluş hatasında aynı tek çözümleme/ortak deadline altında sonraki numeric IP denenir. TLS/peer/HTTP hatasında fallback veya replay yoktur. |
| Keepalive | Guarded pool varsayılan None yerine mevcut hizmet yolu gibi 5 s ile sınırlanır. Bayat bağlantının her koşulda önlendiği iddia edilmez. |
| SSLKEYLOGFILE | Owned TLS context’lerinde keylogging kapatılır; sertifika/hostname/trust-store korunur. Context kurulumu header-only keylog dosyası açabilir; sıfır filesystem etkisi garantisi verilmez. |
| Eşzamanlı PUT | _drain ve _put_batch cleanup başarılı ayrı outcome’ları publish denemeden kaybedebiliyor. Her task en çok bir publish denemesi; publish sonrası belirsizlikte yeniden deneme yok. |
| Sınır/hız mesajları | 33,34 Mbit/s ve 120 s help/plan görünürlüğü ADR-0025 gereğidir. input_budget_exceeded yalnız 1 GiB dememeli; sayısal upload sınırları rehber/help’te açık olmalı. |

## Mevcut kararlar ve yanlış genişletilmiş bulgular

- **M5/Linux:** 06 M5 cache 147,0188 ms geçti; Linux 348,0745/208,4823 ms diagnostic_budget_exceeded tarihsel olarak saklanır. Birincisi ikincisinin performans başarısı değildir; H-1’in bunları aynı kapı sayması yanlıştır.
- **Discovery hedefi:** ADR-0017/0022 açık custom target’ı destekler. Credential/service/origin/API-root ve prepared wire eşliği zaten denetlenir; official-origin pin eklemek ayrı uyumluluk değişikliği olur. Transfer’in public-IP politikası normal discovery’ye sessizce taşınmaz.
- **Kalıcı kota:** ADR-0024, 128 plan/operation, 4.096 dosya ve 16 MiB rezervi birlikte uygular; tavanların hepsine aynı anda ulaşma garantisi yoktur. Otomatik geçmiş silmeme kabul edilmiştir. Forget/prune bu bugfix’e eklenmez; kapasite ve doluluk yolu görünür anlatılır.
- **Ayrı ad/hedef:** Exact namespace kilidi bilinçlidir; başka adla bilinçli ayrı iş ADR-0024’te mümkündür. Unknown işi yeni ad/store ile retry etmeyi uygulama önermez; hesap genelinde content kilidi eklenmez.
- **ID’siz unknown:** Ad tahminiyle yeni dataset ID/baseline üretilmez. Aynı yerel ID korunur; olası Platform kalıntısı ve otomatik kurtarmanın yokluğu açıklanır. Silme veya yeniden gönderim önerisi yoktur.
- **120/900 s:** Süreler, 5 s sonuç payı ve geç-start sınırlaması Accepted kararlardır. Yeni minimum throughput/admission veya daha uzun timeout seçilmez; mevcut sınırlar kullanıcıya açıklanır.
- **Proof sonrası hata / SQLite busy:** Geç çağrı hata verebilirken commit edilmiş başarı korunur; bu testle sabittir. SQLite’ın 1.000 ms busy beklemesi ve commit öncesi kayıpta same-ID uncertainty ADR-0011/0027 sınırıdır. Bunlar _drain’in publish’i hiç denememesiyle karıştırılmaz.
- **V1 golden:** write_access_digest, 37cbc6e’de ADR-0026 kabulünden önce eklendi. 37cbc6e, e58ea85 kabulü ve fd083a2’de journal-v1 golden SHA-256 aynıdır: c9e739fec4dcbd7c643ca375742a39de5531d5b190577238cafc29915f310091. Freeze sonrası byte değişimi yoktur; tarihsel decode/sürüm aileleri kaldırılmaz.
- **Ctime / fork:** Metadata imzası ctime_ns içerir; eksik olan captured recheck negatifidir. Xattr toleransı eklenmez. Ebeveyn permit’inin child’a miras kaldığı testi fork gerektirir; toplu spawn dönüşümü oracle’ı değiştirir. Diğer iki kill testinde deadlock kanıtı yoktur.
- **Probe consent:** Operatörün bounded pilot yetkisi ürün risk onayına çevrilir; TOS endpoint’i veya şart kabulü yoktur. storage --confirm ek confirm etkisini açar; presign/PUT izni ayrı accept-storage-probe bayrağıdır. Frozen kaynaklar düzenlenmez; tarihsel transport/exit sınırı README’de açıklanır.
- **Yeni özellik önerileri:** Filename-list DTO, forget/prune, content-wide kilit, write resume, yeni timeout/admission politikası, v1 aile silme ve paket bölme bu incelemenin doğruladığı bugfix’ler değildir. Mevcut sözleşmeyi değiştirmeden gerekli görünürlük sağlanır.

## Test ve kanıt boşlukları

Gerçek CLI approve/plan negatifleri ve yedi ek v2 binding predicate; migration 7 literal checksum ve dolu schema-6 geçmişinin byte koruması; ayrı consent/isolation negatifleri; production resolver/port/Unix/header sınırı; gerçek literal-secret dump assertion; current recheck ctime-only farkı; hata testlerinde exact kod/istek sayısı tamamlanır. Mevcut olan testler yok sayılmaz ve aynı aşama tekrar tekrar geniş koşulmaz.

Paylaşılan başarısız tam test günlüğünde SIGINT testleri ready bariyerini geçmiş; ayrıca in-process raise_signal(SIGINT) da beklenen istisnayı üretmemiştir. Bunu yalnız yük veya sıra bağımlılığına bağlamak kanıtlı değildir. Ignored/blocked başlangıç sinyaliyle uyumludur; hangisi ve nereden geldiği kaydedilmemiştir. Test launcher’ı foreground sinyal baseline’ını bir kez açık kurup önceki durumu geri yüklemeli; ürün çağrıları baseline’ı değiştirmemeli. Per-test kör reset veya timeout büyütme yapılmaz.

R5 ca0d29c/runtime07’de iki 79-byte dosyayı kapsar. Sonraki 128 KiB okuma/codec değişiklikleri TLS/native/CI ile çevrimdışı doğrulandı; yeni canlı kaynak kabulü diye sunulmaz. Public r5 receipt runner’ın exact private proof kontrollerinin sonucunu/sayaçlarını kaydeder; arşiv verifier’ı tek başına private exact metadata eşliğini yeniden hesaplatmaz. Ham receipt’e sonradan alan uydurulmaz.

## Gizlilik kararı

Belgelemenin kişisel yol yasağı ile orijinal kanıt baytlarını koruma kuralı çakışıyor. 442 arşivde bilinen yerel hesap yolu ve yayımlanmış Git author e-posta literal’lerinin dar taraması 90 eşleşen arşiv buldu: 87 yerel yol, 8 e-posta (örtüşür). Bu genel PII/secret veya gömülü ZIP taraması değildir; değerler yeni belgeye kopyalanmaz. İlk gizlilik/retention önerisi ayrı [ADR-0029](../decisions/0029-evidence-provenance-privacy.md) olarak kullanıcı onayına sunulmuştu; aşağıdaki revizyon/kabul kaydı günceldir. Bağımsız ürün kusurları bu kararı beklemedi. Secret sızıntısı bulunduğu iddia edilmez; tarihsel gzip/history yeniden yazılmaz.

## Dilim 1 ilk doğrulama

Yeni bounded/fallback/peer/idle/keylog ve mevcut network unit seçkisi **84 passed**. Gerçek guarded 8 MiB PUT/RST’nin tam cevabı ve eksik cevap taşıma hatası ayrı sınandı. İlk iki test son resource assertion’ında olmayan closed özelliğine baktı; ürün beklentileri geçmişti. Test gerçek descriptor alanlarına düzeltildi, dar iki case geçti; ardından storage/gerçek TLS cancel/normal HTTP regresyonu **76 passed /41,99 s**. Bu iki son seçki ayrıdır. Strict mypy 144 ve değişen dosyalarda Ruff geçti. Kaynak review turları henüz beklenir; native/CI veya hesap çağrısı yapılmadı.


Dilim 1 /9815f70, R1 Astra/high contract + Sol/high safety ve farklı fresh R2 Sol/high contract + Astra/high safety tarafından bulgusuz kapandı. Reviewer’lar geçen testleri/ölçümleri tekrar çalıştırmadı. Literal socket-options iterator ve TLS-failure fallback için ek test fikri opsiyonel kapsam olarak kaydedildi; mevcut kod kusuru bulunmadı. İkinci kod dilimi artık receipt toplama bütünlüğüne geçebilir. Proposed ADR-0029 yalnız gizlilik/retention politikasını bekletir; ağ düzeltmesinin onay kapısı değildir.


ADR-0029 önerisi ve 90 kayıtlı dar envanter, d5f04c5 kaynağında fresh R1 Sol/high ve farklı fresh R2 Astra/high tarafından bulgusuz incelendi. Karar Proposed; bağımlı privacy/retention kodu yoktur. Kullanıcıya somut onay sorusu sunulur; bağımsız receipt ve kullanıcı/test düzeltmeleri sürer.


## Dilim 2 ilk doğrulama

PUT task’larının tek publish-attempt kümesi, başarıları worker hatasından önce toplar; sonraki current/prepare/arm hatasında cleanup da henüz denenmemiş başarılı sonucu işler. İşaret publish’den öncedir; commit cevabı kaybı tekrar deneme üretmez. Cleanup her kaynağı kapatmayı dener ve gerçek cancellation önceliğini korur.

Saf scheduler/reply-loss/cancel senaryoları ve gerçek SQLite/TLS fixture’ında bir başarılı PUT + bir 503, kalıcı **7 intent/6 accepted receipt**, tek accepted PUT index0, unknown/no lease/no verification ve sıfır confirm ile geçti; aynı-ID local lookup yeni ağ açmadı. İlk ek cleanup-cancel testinde gather’ın opsiyonel cancel mesajını koruduğu varsayılmıştı; Python bu mesajı düşürebildiğinden contract oracle’ı gerçek CancelledError tipi, receipt ve bütün close sonuçlarına düzeltildi. Daha dar ilk grupta 10 passed/1 bu test-oracle hatası vardı. Son scheduler/file-workflow/gerçek kill seçkisi **29 passed /30,58 s**. Yeni kod strict mypy ve Ruff’la denetlenir; R1/R2 kaynak review henüz beklenir. Genel tam suite/ölçüm veya hesap çağrısı yapılmadı.


Dilim 2 /a9b1ffb, iki farklı fresh R1 (Astra/high contract, Sol/high safety) ve R2 (Sol/high contract, Astra/high safety) tarafından bulgusuz kapandı. Reviewer’lar testleri yeniden çalıştırmadı. Başarılı ayrı PUT sonucunun tek publish denemesi, cancellation ve release sırası doğrulandı.


## ADR-0029 kullanıcı bulguları sonrası revizyon

Kullanıcı, doğrulanmış bulgular kapatıldıktan sonra Accepted’a taşıyıp devam etmemizi yetkilendirdi. Bağımsız dar audit: üst düzey 82 gerçek kişisel yol + 8 yayımlanmış e-posta arşivi; önceki 5 runner/e-posta kesişimi kişisel yol değildir. Beş adlandırılmış base64/sıkıştırılmış tanı ekinde size/SHA/strict decode sonrası gerçek kişisel yol doğrulandı. Hash’li envanter 95 kayda revize edildi (87 gerçek yol, 8 e-posta); özgün byte’lar değişmedi. İlk 90 kayıt review’sü bu yeni kapsamın doğrulaması diye sunulmaz.

Yeni karar kontrolü hem Git hem CI artefakt upload öncesine, gerçek runtime/interpreter/temp kaynaklarını kapsayan zorunlu özel üretim bağlamına ve bounded kodlanmış ek doğrulamasına bağlar. Eksik beyan veya çözülemeyen ek temiz sayılmaz; privacy reddi public yayımı durdurur ve somut kalıcı saklama kapanmadan kabul/merge önerisi verilmez. Katalog original_commit için ilk exact-byte Git blob’u kuralı netleşir; 28 daha geç commit ve bir olmayan yol kaydı metadata olarak düzeltilecektir. Yeni politika uygulaması revize belgenin fresh teyidinden sonradır.


## Dilim 3 ilk doğrulama

Onay önerisi risk bayraklarını komuta hazır eklemez; ayrı insan seçimi anlatılır. Text unknown/error aynı-ID show ve koşullu salt okuma yolunu, eksik ID’nin olası uzak private kaynağını açıklar. JSON/NDJSON zarfı ve iş kuralları değişmez. Help/review/rehber 128 dosya, 500.000.000 byte, 1 GiB, 120 s/33,34 Mbit/s, 900 s, kalıcı kota/hidden-file/revoke sınırlarını taşır. Girdi bütçesi mesajı yalnız 1 GiB demez.

Gerçek CLI eksik iki acknowledgement ve yanlış digest negatifleri sıfır yeni HTTP/onay/operation ile; default verified-only + numeric bütçenin draft kalması; yedi ek bağımsız geçerli approval binding negatifi; schema-7 literal checksum; dolu schema-6 plan/approval/operation/attempt/event/outcome byte koruması; captured ctime recheck; gerçek seçili synthetic credential dump yokluğu; dört probun ayrı consent/isolation retleri ve exact PUT hata/istek oracles’ı tamamlandı.

Offline guard standart DNS/reverse-DNS/datagram yollarını kapatır; TLS fixture yalnız explicit loopback reverse bilgisini üretir. Bu native-extension sandbox’ı değildir. Foreground test işi inherited ignored/blocked SIGINT’i bir kez normalleştirip çıkışta eski durumu döndürür; testler arası kontrol reset yapmadan sızıntıyı assert eder. İki nested launcher modu gerçek HTTP session/CLI publication/known-ID iptal testlerini geçti.

İlk seçki 358 passed/6 test-oracle hatası verdi: dört binding vektörü yanlışlıkla standalone strict DTO listesine konmuştu; wrong-arm kodu invalid_request ve post-stream hash retinde bir HTTP doğru beklentilerdir. Bunlar düzeltildi; ilgili 22 test geçti. Sonraki dar text/CLI kontrolleri 7, dolu terminal migration/mesaj kontrolleri 4 test geçti (kümeler örtüşür, toplam olarak toplanmaz). Ruff ve dört değişen source dosyasında strict mypy geçti. Son leak/counter assertion’ları ayrıca dar koşulur; fresh review beklenir. Tam suite veya native/live çağrı çalıştırılmadı.


ADR-0029 /f331d7e revizyonu fresh R1 Sol/high ve farklı fresh R2 Astra/high tarafından bulgusuz teyit edildi. Kullanıcının koşullu kabul talimatıyla Accepted’a taşındı; 95 hash’li kayıt sınırı sabittir. Bu, yeni kontrolün veya son nötr native kabulünün uygulandığı anlamına gelmez. Standart/ADR-0019 forward bağları aynı kabul commit’inde güncellenir; araç/workflow ve metadata düzeltmesi dilim 4’te kapanacaktır.


Dilim 3 /cd3473a R1: Sol/high safety bulgusuz; Astra/high contract bir P2 test izolasyonu buldu. Admission-policy vektörü cost/ack’i de değiştirdiği için tuple yerine önce risk mismatch ile kapanıyordu. Tam kanıtlı bounded planda yalnız policy’yi değiştiren geçerli DTO’ya taşındı; tam binding mismatch zorunlu, 11 ilgili test geçti. Mevcut cost_policy vektörü DTO/ack bağı gereği risk retini de sınar; bağımsız yalnız cost predicate iddiası kurulmaz. Son leak/counter seçkisi 7 passed; Ruff temiz. Farklı fresh R2 beklenir.


Dilim 3 /6787300, farklı fresh R2 Sol/high contract ve Astra/high safety tarafından bulgusuz kapandı. Admission-policy izolasyonu, bütün yeni test oracle’ları ve text-only ürün rehberi kaynak üzerinden teyit edildi; reviewer’lar test/native/live/raw tekrar etmedi. Dilim 4 artık Accepted ADR-0029 araç/CI kapısı ve kalan belge/katalog düzeltmelerine geçer.


## Dilim 4 ilk doğrulama

Accepted ADR-0029 için zorunlu private üretim bağlamı, known-provenance byte/string kontrolü, bounded strict base64/gzip/stored-deflate ZIP ve opaque profil/text ayrımı eklendi. Unsupported/bozuk/denetlenemeyen ek temiz sayılmaz; encoded nesnenin text/string içinde saklanması da ret verir. Dosya/FIFO/dizin/symlink kapısı descriptor’ları kapatır. Git archive ve CI artefakt upload önce aynı kontrolü kullanır; CI önce actual kaynak/interpreter/temp/child köklerini beyan eder, son always adımı bütün seçilmiş özgünleri denetleyip hash eşliğiyle ayrı staging’e kopyalar. Rette upload yok, güvenli job özetinde açık retention ve geçici runner kaybı riski görünür. Measurement/test başarısızlığı başarıya çevrilmez.

İlk birleşik seçki 502 passed/93 failed verdi: yeni privacy yükleyicisinin benchmark-only runpy test seam’iyle çakışması ve artık yayımlanamayan bozuk tanı beklentisi. Privacy yükleyicisi benchmark seam’inden ayrıldı; malformed özgünler private kalıp açık takipte ret edilir, geçerli tanı byte-kayıpsız pozitif olarak ayrıca korunur. İlgili dar tekrar 208 passed; devam eden gerçek source-map/CI/yeni boundary seçkisi 328, son source-map/CI alt seçkisi 118 passed (örtüşür; toplanmaz). Bounded gzip/ZIP ve special-file testinin yakaladığı directory fdopen sınıflandırması fstat-before-wrap/finally-close ile düzeltildi; son privacy seçkisi 56 passed. Ruff tüm src/tests/scripts, strict mypy 145 dosya ve actionlint geçti. Yeni kontrol gerçek native/CI kabulü sayılmaz.

Önceki iki Linux CI artefaktı, sentetik CI bağlamıyla yalnız format/limit uyumu için okundu; scanner 166 ve 33 üye işledi (nested dahil). Bu bir yeni CI veya kişisel veri attestasyonu değildir. Final marker eklemesi sonrası aynı dar format uyumu da teyit edildi. Metadata [düzeltme kaydı](p02-2-evidence-catalog-corrections.json) 28 ilk exact-byte commit’i ve bir null düzeltmesini taşır; 442 gzip/content hash’i değişmeden katalog/indeks doğrulandı. Aktif eski durum metinleri ve gerçek proje UUID’li test örnekleri düzeltildi; frozen source/test byte’ları değiştirilmedi.

07 startup/jobs/datasets/upload referans adları ilk ölçümden önce workflow/test/standartta sabitlendi; raw da aynı seri workspace’inde üretilecektir. Yeni kaynak kontrolü kaynak haritasında Python dosyalarıyla birlikte artifact allowlist metnini de kapsar. Henüz 07 ölçümü, yeni kaynak CI, paket kabulü veya yeni canlı çağrı yapılmadı. R1/R2 beklenir.


Dilim 4 /2438a86 R1: Astra/high contract iki P2 (eşleşen Git blob’u varken None erken dönüşü; CI failure-retain yoluna context env aktarımının eksikliği), Sol/high safety bir P2 (ZIP directory adı altında sıkıştırılmış veri atlama) doğruladı. None artık ilk exact-byte commit’ini otomatik türetir; gerçek archive metadata’sı bunu taşır. Shallow repo ilk kayıt iddiası üretemez; resolver reddeder ve CI candidate tam Git geçmişi alır. Baseline pinned içeriği değişmez. Workflow actual context yolunu GITHUB_ENV’e aktarır; o gerçek export satırından automatic failure-retain entegrasyonu geçti. Nonempty ZIP directory reddedilir, adlar taranır ve boş directory de global üye kotasını tüketir. CI’de generic home yanında kişisel interpreter/child/temp yolu kabul edilmez; local account varsayımı yapılmaz. Opaque encoded-marker kontrolü lineer satır/quoted-key sınıfına daraltıldı. Son privacy/CI seçkisi 122 passed; ilgili archive/regresyon seçkisi 266 passed (örtüşür). Ruff/mypy145/actionlint temiz. Farklı fresh R2 beklenir; 07 veya yeni CI/live çağrı yoktur.


Dilim 4 /7617bd0 R2: Sol/high contract bulgusuz; Astra/high safety bir P2 doğruladı. ZIP’te local/central açık boyut ve CRC sıfırlanarak metadata’ya güvenen ZipExtFile’ın gerçek deflate yükünü boş döndürmesi mümkündü; directory düzeltmesi tek başına yetmedi. Guard artık PKWARE alan düzenine göre dar ZIP subset’inde EOCD/central/local kayıtlarını, contiguous byte aralıklarını ve tam directory kapsamını doğrular. Gerçek compressed yük metadata boyutuna güvenmeden bounded raw-deflate ile açılır; EOF/tam tüketim/actual-size/CRC eşliği zorunludur. ZIP64/descriptor/extra/comment/prefix/gap desteklenmez ve ret edilir. Bu ürün upload ZIP import desteği değildir.

Directory ve regular forged-size/CRC/compressed-size saldırıları, deflate trailing/truncated/gap, unsupported biçimler ve stored/deflate ASCII/UTF-8/CP437 pozitifleri eklendi. Son privacy/CI seçkisi 142 passed; Ruff336/mypy145 ve belge200/6skill45 kontrolleri geçti. Fix’in dar bağımsız teyidi beklenir; 07 hâlâ ölçülmedi. Önceki 56/122/142 sayıları farklı source/test dilimleridir ve toplam olarak toplanmaz.
