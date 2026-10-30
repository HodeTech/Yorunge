# P02 — Veri, katalog ve çıkarım

**Güncellendi:** 2026-10-30. **Durum:** Başlangıç hazırlığı tamamlandı; [P02-0a araştırma kartı](tasks/p02-0a-contract-sdk-pilot.md) `ready`, ürün uygulaması ve hesap pilotu başlamadı. P01 [PR #11 / bc9532c](../research/p01-remaining-implementation-validation.md#development-merge-kapanışı) ile development’a teslim edildi. **Yetenekler:** C01/C02 uzak alt küme, C03–C07, C11 okuma, C12/C13 entegrasyon. [Hazırlık review’si](../research/p02-readiness-review.md) kapsam ve kod karşılaştırmasını kaydeder.

## Kullanıcı sonucu ve kapsam

Veri sorumlusu doğru hesap/projede küçük klasörü private veri setine aktarır; kesintiden sonra aynı işi uzlaştırır, indirir ve doğrulama seviyesini görür. Uygulama geliştirici uygun model/görevle metin, stream, embedding/rerank veya görsel çıkarım sonucu ve bilinen kullanım bilgisini alır. Bu akışlar ForgeLM, Torch veya eğitim kurulumu gerektirmez.

Public görünürlük, silme, rezervasyon yazma, model warmup/benchmark gibi ek ücretli etkiler, görsel eğitim, OCR/ses, tool calling sonucu araç yürütme, notebook execution ve kullanıcı modeli serving bu fazın gizli kapsamı değildir. ZIP import/otomatik arşiv açma ilk normal-dosya yoluna eklenmez; gerekiyorsa ayrı kapsam/limit/kabul kararı gerekir. Mevcut CLI komutları bu hedeflerin uygulanmış yüzeyi sayılmaz; yeni komut/API adları ilgili kart ve referansta kesinleşir.

## Epikler ve bağımlılıklar

| ID | Teslim sınırı | Önkoşul | Kabulün sahibi | Durum |
|---|---|---|---|---|
| P02-0 | Sözleşme ve gerçek hesap bağlamı giriş hattı | P02-0a, P02-0b | Belge araştırması ile canlı hesap kabulü ayrı | `draft` |
| P02-0a | Güncel Platform/LLM sözleşmesi, endpoint SDK değerlendirmesi ve pilot planı | P01-2b, P01-3a, P01-5a, P01-5b | [Hazır araştırma kartı](tasks/p02-0a-contract-sdk-pilot.md); B03/B04 çözümü bu araştırmanın çıktısıdır | `ready` |
| P02-0b | Hesap/organizasyon/proje salt okunur keşfi ve context doğrulama | P02-0a; P01-2b/P01-3a/P01-5a | Hizmet başına güncel kimlik/yetki; açık proje seçimi | `draft` |
| P02-1 | Yerel normal dosya denetimi ve sürümlü manifest | P01-1a, P01-3b | Güncel içerik/kimlik, güvenli kök, sınırlı tarama ve atomik rapor | `draft` |
| P02-2 | Private oluşturma ve tek doğrulanmış upload yolu | P02-0a, ilgili P02-0b kabulü, P02-1; P01-4b/P01-5b | P02-2a–c; create/presign/PUT/confirm ve ilk kesinti güvenliği | `draft` |
| P02-3 | Resume/reconcile, indirme/verify ve veri sürüm bağları | Alt işe göre P02-2 veya P02-0b | P02-3a–c; ortak güvenli indirme bağımsız hazırlanabilir | `draft` |
| P02-4 | Veri/model kataloğu, sabit referans çözümü ve seçilmiş ağırlık indirme | P02-0a, ilgili P02-0b kabulü; P01-3a/P01-5a | P02-4a/b; indirme ayrıca P02-3b | `draft` |
| P02-5 | Native LLM ve temel çıkarım | P02-4a’nın ilgili hizmet/model kabulü; P01-5b | P02-5a–e; her görev ayrı typed girdi/çıktı ve maliyet sınırı | `draft` |
| P02-6 | GPU/kuyruk/rezervasyon bilgisi ve kota okuma | P02-0a; hesap verisi için ilgili P02-0b kabulü | P02-6a/b; yalnız okuma, tahsis/fatura garantisi yok | `draft` |
| P02-7 | Bütünleşik kullanıcı akışı ve faz kapanışı | Kapanışa alınan bütün P02 alt işleri | [Faz kabulü](#faz-kabulü); eksik hedef açıkça kalır | `draft` |

`P02-0b ilgili kabulü`, tüm Platform ve LLM keşfinin birbirini beklemesi anlamına gelmez. Kart, kullandığı hizmetin tamamlanmış alt kanıtını isimlendirir; yalnız epik kısmen geçti diye bağımlılık `verified` gösterilmez. Hizmet bazında bölünme gerekiyorsa alt ID’ler faza ve gerçek kartlara eklenir; downstream `depends_on` yalnız tamamlanmış somut ID’yi kullanır. Sağlayıcıda organizasyon/proje alanı yoksa uydurulmaz; null/erişim semantiği ve mevcut config/capability/plan bağına etkisi önce sözleşmede kapatılır.

B03’ün P01’de kapanan kısmı SDK’nın core bağımlılığı olmaması ve ortak taşıma politikasını atlamamasıdır; endpoint seçimi açık kalır. B04’ün P02 kısmı veri/çıkarım limitleridir; yönetilen eğitim durumları P03’te kalır. P02-0a bu kayıtları araştırır; kayıtların önceden çözülmesini bekleyen bir döngü yoktur.

## Uygulama birimleri ve sıra

Aşağıdaki alt ID’ler kapsam/bağımlılık sınırıdır; henüz hazır uygulama kartı değildir. Yakın iş ayrıntılandırılırken S/M karta dönüştürülür; L iş alt adımlara bölünür. Kesin format, sayısal sınır, deadline, schema/migration ve olumlu/negatif oracle o kartta tek yerde tutulur. Epik bir PR içinde teslim edilebilir; alt ID ayrı PR zorunluluğu değildir. [Paket akışı](README.md#p02-paket-akışı) geçerlidir.

| ID | Tek gözden geçirilebilir sonuç | Doğrudan P02 bağımlılığı | Durum |
|---|---|---|---|
| P02-2a | Private oluşturma planı, güncel onay ve kalıcı create/korelasyon kaydı | P02-0a, P02-0b Platform alt kabulü, P02-1 | `draft` |
| P02-2b | Yetkili depolama hedefinde bounded byte upload ve doğrulanmış confirm | P02-2a; aşağıdaki aktarım kararları | `draft` |
| P02-2c | İlk upload’ın kill/restart/kayıp cevap ve teslim kapanışı | P02-2b; belirsizlikte yeni create/PUT yok | `draft` |
| P02-3a | Kayıtlı aynı aktarımı uzlaştırma ve yalnız güvenliği kanıtlı eksik adımı sürdürme | P02-2c | `draft` |
| P02-3b | Ortak akışlı indirme, no-clobber yayın ve açık verify seviyesi | P02-0a, ilgili P02-0b kabulü | `draft` |
| P02-3c | Veri sürümü/bölme metadata’sı ve değişmez plan bağı | P02-3a, P02-3b; gerekirse açık sürüm oluşturma/freeze kararı | `draft` |
| P02-4a | Sayfalı veri/model kataloğu ve göreve uygun sabit referans çözümü | P02-0a, ilgili P02-0b kabulü | `draft` |
| P02-4b | Seçilmiş model ağırlığını ortak indirme portuyla teslim etme | P02-4a, P02-3b | `draft` |
| P02-5a | Tek nonstream metin görevi ve typed yanıt/kullanım sonucu | P02-4a LLM alt kabulü | `draft` |
| P02-5b | Sağlayıcı SSE’sini doğrulanmış StreamEvent/terminal sonucuna dönüştürme | P02-5a | `draft` |
| P02-5c | Sıra/boyut/sonluluğu doğrulanmış embedding sonucu | P02-4a LLM alt kabulü | `draft` |
| P02-5d | İndeks/skor/top-n eşlemesi doğrulanmış rerank sonucu | P02-4a LLM alt kabulü | `draft` |
| P02-5e | Tek keşfedilmiş görsel modelde bounded predict ve typed sonuç | P02-4a ilgili model/hizmet alt kabulü | `draft` |
| P02-6a | Kamu GPU/kuyruk/rezervasyon metadata görünümü | P02-0a; hesap endpoint’i varsa ilgili P02-0b kabulü | `draft` |
| P02-6b | Hizmete bağlı hesap kotası/kredi/ledger okuması | P02-0a, ilgili P02-0b kabulü | `draft` |

**Varsayılan sıra:** P02-0a → P02-0b → P02-1 → P02-2 → P02-3 → P02-4 → P02-5 → P02-6 → P02-7. Bu çalışma sırası teknik olarak gereksiz bir kapı oluşturmaz: yerel P02-1 uzak araştırmadan, P02-4a/P02-6 okumaları upload’dan, LLM işleri Platform hesabından bağımsız ilerleyebilir. P02-3b gerekirse ilk tüketicisi P02-4b’nin PR’ında özgün ID ve kendi kabul kaydıyla teslim edilir; katalog sorgusu ağırlık indirmeyi beklemez. Dal/PR kapsamı değişirse plan/current aynı anda güncellenir.

P02-2c ilk upload’ın güvenli kesinti durumunu ve en az mevcut kimlikle salt okunur uzlaştırma yolunu kapatır; kullanıcıyı yeni create veya DB düzenlemeye yönlendirmez. P02-3a bunun üzerine dosya/aşama bazlı güvenli devam deneyimini ekler. P02-2’nin hata sonrası asgari toparlanması sonraki epike bırakılmaz.

## P01’den devralınan sınırlar ve karar kapıları

P01 güvenilir temel sağlar; bütün P02 kullanım senaryolarını hazır uygulama haline getirmez. Aşağıdakiler ilgili uygulama kartının `ready` geçişinden önce kapatılır; araştırmanın başlamasını engellemez:

| Sınır | Bugünkü gerçek | P02’de gereken çıktı |
|---|---|---|
| Signed URL ve upload | [HTTP portu](../reference/http-transport.md) göreli endpoint, HTTPS/443, bytes request ≤1 MiB ve raw response ≤1 GiB kabul eder; genel imzalı URL/stream upload portu yok | Ayrı depolama hedef politikası, credential ayrımı, imzalı query gizliliği, süre/host/redirect ve bounded request streaming sözleşmesi; P02-2b/P02-3b öncesi güven sınırı ADR’si |
| Çok aşamalı aktarım | [Operation](../reference/operations.md) plan başına tek kayıt/kalıcı dispatch latch ve sonrası yeni attempt yasağı taşır | Create, presign, PUT, confirm ve yeniden başlatmanın kalıcı aşama/korelasyon modeli; her isteğin etki/replay kuralı, unknown uzlaştırması. Yeni attempt açarak latch aşılamaz; P02-2a öncesi karar gerekir |
| Bütçe ve kapasite | [Execution plan](../reference/execution-plan.md) ≤128 input/64 KiB body, çağrıda ≤1 GiB/30 s; store/operation kotaları ayrı | Büyük manifestin plan bağı, dosya/adet/toplam byte ve iş/istek süre modeli; 30 s validation ile tüm transfer süresi eş tutulmaz. Mevcut sınır değişiyorsa ADR; etkiden önce kapasite denetimi |
| Public producer | Mevcut validator tam girdi kapanışı/uzak yetki/endpoint adaptörü doğrulamaz; plan draft/blocked | İlk yan etkili tüketicide gerçek girdi/model/yetki kapanışı, güncel credential/onay ve ortak CLI/Python composition. Test producer’ını public backend yapmak kabul değildir |
| SSE ve çıkarım | [StreamEvent/NDJSON](../reference/stream-results.md) uygulandı; EVREN SSE codec’i ve native görev yanıtları yok | SSE framing, provider terminal/usage/hata ve message EOF eşlemesi; [ADR-0018](../decisions/0018-stream-results-and-cancellation.md) terminal güvenliği korunur, protokol farkı ayrıca sınanır |
| Context ve yeni state | Context genişlemesi, transfer/artefakt kayıtları ve yeni CLI/API şemaları henüz yok | Gereken tüketiciyle birlikte kapalı referans, compatibility ve [ADR-0015](../decisions/0015-checksummed-data-migrations.md) V2 migration/backup/reset kapsamı; mevcut restore yasağı sessizce açılmaz |

Bu tablo bir yeni tasarımın onayı değildir. P02-0a kararların seçenek/kanıt ve Proposed ADR ihtiyacını çıkarır; gerekli yeni ADR kullanıcı onayına sunulmadan bağımlı ürün kodu başlamaz. SDK kendi idempotency/retry davranışını belgelese bile [ADR-0017](../decisions/0017-bounded-http-transport.md) tek deneme/tek retry sahibi kararı kendiliğinden değişmez.

## Kabul matrisi ve kanıt sınırı

Bu matris gelecekteki kartlara zorunlu kapsamı dağıtır; ayrıntılı test/limit listesi kartta tutulur. Hedefler bugün geçmiş sayılmaz.

| Hat / sahip | Olumlu sonuç | Kritik negatif ve kanıt |
|---|---|---|
| P02-0a/0b | Sürüme/tarihe bağlı resmî kaynak; doğru hizmet/anahtar ve açık hesap/proje | 401/403/429, eksik scope, eski credential, çok/boş proje; ilk UUID seçilmez, 403 platform genelinde unsupported olmaz |
| Yerel dosya / P02-1 | Deterministik sürümlü manifest; her göreli dosya adı, boyut ve güncel hash korunur | Aynı boyutta değişim, symlink/ancestor yarışı, FIFO/device, hardlink/aynı hash farklı ad, Unicode/case çakışması, bozuk manifest; hash dedup dosya kimliklerini silmez. Ağ/sır/state zorunlu değildir |
| P02-2/3a | Private hedef ve dosya bazlı doğrulanmış teslim; kullanıcı aynı operation’a döner | Kayıp create/presign/PUT/confirm cevabı, kill/restart, stale journal/uzak silinme, local değişim, 2xx mantıksal hata ve lease kaybı; kör tekrar ve yeni dataset yok |
| P02-3b/3c/4b | Güvenli geçici dosyadan no-clobber sonuç, sürüm/manifest kökeni ve verify seviyesi | Kesik Range/ETag veya sürüm değişimi, checksum anlamı bilinmeyen ETag, hedef yarışı/path kaçışı/disk dolu; metadata eşliği byte hash doğrulaması diye sunulmaz. Model ağırlığında erişim/lisans/şart engeli ayrı kalır |
| P02-4a/6 | Bounded sayfalı/cache’li liste; sabit kimlik/revision ve kapsamlı kota/zaman | Cursor döngüsü, duplicate/değişen sayfa, N+1, belirsiz slug, eski cache, tarih/saat sınırı; upstream immutable revision yoksa pin garantisi uydurulmaz. Kamu GPU erişim kanıtı değildir |
| Çıkarım / P02-5 | Göreve özel typed çıktı, provider request kimliği ve bilinen kullanım | Boş/gömülü hata, yanlış model/görev, NaN/bozuk indeks/dimension, kesik SSE/terminal sonrası veri, 402/403/429, iptal/BrokenPipe; bilinmeyen kullanım sıfır maliyet değildir, inference POST otomatik tekrarlanmaz |
| Faz kapanışı / P02-7 | Aynı kullanım senaryolarının CLI ve Python’da tutarlı deneyimi | Non-TTY asılı prompt yok; JSON/NDJSON saflığı, doğru hata/exit/ID ve yerel iptal–uzak etki ayrımı; gerekli dosya eksikken success yok |

Her ağ kartı istek/sayfa/deneme ve toplam byte/süre tavanını endpoint verisinden önce açıkça seçer; sağlayıcı limiti ile Yörünge koruma tavanını ayırır. Büyük listeler/batch’ler sınırsız RAM veya stdout gerektirmez; rapor ve dosya çıktısı sınırları belirlenir. Aktarım kabulü gerçek upload/download yolunda 16/256/1.024 MiB, en çok 2 worker ve byte kuyruğu ile [performans standardına](../standards/performance.md) bağlanır. P01’in tek raw download benchmark’ı bu kabulün yerine geçmez. Sistem I/O’suna katı duvar saati garantisi verilmez.

## Faz kabulü

P02-7 şu kanıtları tek kapanış raporunda toplar:

1. Doğru profilden private oluşturma → upload → kesinti → aynı işi uzlaştırma → indirme/verify; yerel ve uzak dosya sayısı/kimliği, aynı hash farklı adlar ve byte doğrulaması bağımsız oracle ile korunur.
2. İlgili hesapta katalog/model çözümü → nonstream/stream metin → embedding → rerank → seçilmiş görsel predict; her görev için model/sürüm/format, erişim ve kullanımın doğrulanmış sınırı belirtilir. Model adı veya hız sonucu donanım/servis garantisi olmaz.
3. GPU/rezervasyon görünürlüğü ile hesap kotası ayrı kaynak/zaman/erişimle raporlanır; önceki iki akıştaki bilinmeyen kredi/yetki gizlenmez.
4. Hedefli contract/integration ve gerçek TLS/süreç/SQLite kesinti testleri, tam CI/temiz kurulum, kaynak bağlı startup/jobs kapıları ve yeni aktarım ölçümleri geçer. [Kanıt standardıyla](../standards/research-evidence.md) kompakt rapor/manifest, kayıpsız raw arşiv ve sabit oracle vektörleri ayrılır; mevcut kanıtlar ezilmez.
5. Yetkili küçük pilot, offline/loopback kabulünden ayrı kaydedilir. Pilot öncesi veri/proje/endpoint, azami istek/token/byte/tutar, durdurma koşulu ve geride kalacak kaynağın sahibi bellidir. Bu hazırlık canlı hesap çağrısı, şart kabulü veya uzak silme yetkisi vermez.
6. İlk kullanıcı görevlerinde süre, yardım, yanlış hedef ve çıktı bulma ölçülür; sayısal UX hedefi ilgili kartta **ölçümden önce** sabitlenir. README/örnekler/CLI/Python referansları, capability matrisi ve current gerçek teslimi gösterir; örnekler temiz kurulumda çalıştırılır.

Zorunlu alt işin kabulü eksikse epik/faz `verified` olmaz. Erişim kapalıysa bağımsız işler sürer; eksik hat `blocked`/`partial` ve açılma koşuluyla kalır. Araştırmanın “unknown/kapalı” sonucu araştırma kabulünü karşılayabilir, ürün entegrasyon kabulünü karşılamaz. Bir hedefi P02 dışına alma veya yalnız kısıtlı sürüm teslim etme kararı kullanıcıyla açık kaydedilmeden kapsam küçültülmez; [yayın kapısı](README.md#faz-kapısı-ve-yayın-kapısı) ayrıca geçerlidir.
