# P02-2 uygulama öncesi belge, kod ve kaynak incelemesi

**Tarih:** 2026-11-02 Europe/Istanbul. **Dal/taban:** `feat/p02-2-private-upload`, development `50d68b1`; kapanış commit'i `973cec5`. **Durum:** ADR-0024/0025 Accepted; bağımsız yerel uygulama ve dış wire/otorite araştırması başlıyor. Tarihsel Proposed/onay-bekleme ifadeleri aşağıdaki ilk review aşamasına aittir; güncel durum bu satır ve son kayıtlarla okunur. Henüz ürün/live upload kabulü değildir.

## Yöntem ve mevcut belge incelemesi

AGENTS/ajan çalışma rehberi; implement-task/plan-task/contract-change/review akışı; current/roadmap ve P02 fazı; ürün kapsamı/matris; datasets, mimari ve user journey; güvenlik/UX/test/performans/hata/belgeleme/kanıt/Git standartları; ADR-0011–0018/0020–0023'ün ilgili kararları; credential, capability, execution, operation/state, HTTP/stream, discovery ve manifest referansları karşılaştırıldı. İki bağımsız hazırlık ajanı mevcut state/operation/HTTP kodunu ve kapsam/bağımlılık/otorite belgelerini salt okudu. Önceki araştırma ve kullanıcı kılavuzu bilgisi güncel public web/SDK kaynağıyla yeniden kontrol edildi. Öneriler bunların üzerine yazıldı; gözlem uygulama desteği sayılmadı.

Kamu kaynakları credentialsız HTTPS GET ile alındı; web okuyucusu guide adresini açamadığı için bounded doğrudan HTTPS fallback kullanıldı. Toplam **13 GET / 1.329.541 byte**, redirect yok; her istek 8–10 s faz ve 64 KiB–2 MiB dosya tavanıyla sınırlıydı. İlk sekizli seri 2,393 s içinde bitti; sonraki bağımlı kaynaklar ayrı küçük okumalardır, tüm araştırmanın tek 30 s atomik koşu olduğu iddia edilmez. JavaScript çalıştırılmadı, SDK kurulmadı/import edilmedi. Anahtar/config/özel hesap kullanılmadı; **0 hesap isteği, 0 etkili istek**. HTML/bundle/SDK kaynak gövdeleri repoya kopyalanmadı. Tam URL/byte/SHA [kaynak receipt'indedir](p02-2-public-source-receipt.json); hash kaynak kimliğidir, imza veya API garantisi değildir.

## Doğrulanmış hazırlık boşlukları ve aksiyonlar

| Bulgu | Mevcut kanıt | Hazırlık aksiyonu |
|---|---|---|
| Çok aşamalı etki mevcut tek start'a sığmaz | `application/operations.py` tek start; `operation_repository.py` kalıcı latch sonrası yeni attempt'i reddeder; read portu yalnız observe | ADR-0024: ayrı transfer plan/operation ailesi, workflow + aşama intent/receipt, replay yasağı ve aynı-ID read recovery önerildi |
| Manifest/execution limitleri farklı | Manifest 4.096 dosya/8 MiB; execution 128 input/64 KiB ve yalnız manifest dosyasının hash bağı | Eski wire korunur; ayrı immutable manifest bağlı transfer, tam içerik kontrolü ve açık ilk 128 upload dosya sınırı önerildi |
| Discovery yazma otoritesi değildir | Platform modeli validation=unverified, authentication=unknown, authorization_scope=null | API-key create/link ve exact dataset upload/read yetkisi için ayrı current producer kapısı; fake prepared yok |
| Create ve proje ilişkisi ayrı | Dataset create body'de org_id seçeneği var, project_id yok; project hook ayrı link POST'u gösteriyor | Create→project_link açık aşama/yan etki olarak plana ve ADR'ye eklendi; ilişkisiz başarı yok |
| Signed/proxy hedefler aynı değildir | Service HttpRequest göreli endpoint/bytes≤1 MiB; frontend direct URL'de credentialsız XHR, proxy'de bağlı client kullanıyor | ADR-0025: explicit target sınıfları, önceden allowlist, exact wire URL, auth/cookie/log/expiry ve bounded stream |
| 30 s generic execution lease/bütçesi transfer bütçesi değildir | Operation port deadline'ı lease/total'dan 5 s düşüyor | Yeni transfer için ayrı 900 s plan/onay/toplam, 150 s lease ve 120 s PUT; mevcut execution 30/300 s kuralları değişmiyor |
| Kesinti güvenliği sonraki epike bırakılamaz | P02 fazı P02-2c'yi first-upload read reconciliation sahibi yapıyor | P02-2c show/reconcile ve her aşamada kill/kayıp cevap; P02-3a yalnız etkili güvenli resume |

Bunlar P02-1 veya P01'e ait doğrulanmış ürün kusurları değildir; yeni tüketicinin önkoşullarıdır. Mevcut accepted kararları bu hazırlıkta geriye dönük değiştirilmedi. Eski P02-0 araştırmasındaki upload bilgileri tarihli kaynaktır; bugünkü API davranışı diye kullanılamaz.

## Güncel public kaynakların söylediği ve söylemediği

| Kaynak | Bu turda tüketilen bilgi | Açık sınır |
|---|---|---|
| [Guide](https://evren.ssyz.org.tr/guide), [içerik asset'i](https://evren.ssyz.org.tr/assets/UserGuidePage-DTl0xmcl.js) | X-API-Key, presign→PUT→confirm ve item cursor; UI 500 MB/dosya anlatımı | Normatif auth/replay/fiyat/expiry ve raw strict şema değildir; direct MinIO anlatımı ve proxy örneği ayrı |
| [Dataset API](https://evren.ssyz.org.tr/assets/datasetApi-CA1WYT2w.js) | Create POST; detail owner/org/private alanları; item id/dataset_id/original_filename/file_size_bytes/nullable sha256_hash; items/next_cursor/total | Owner/auth/snapshot ve hash semantiği istemci şemasıyla kanıtlanmaz; `project_id` create alanı görülmedi |
| [Create UI](https://evren.ssyz.org.tr/assets/DatasetListPage-0ZBmWGZj.js) | name/modality/description/visibility/contributions_enabled/license/tags ve seçili org_id | Kişisel owner ve org_id'nin API key ile uygulanma koşulu belirsiz; org yokluğundan yanlış hesap varsayılmaz |
| [Project hook](https://evren.ssyz.org.tr/assets/useProject-C5SXBHgI.js) | `GET projects/{id}/datasets`, `POST projects/{id}/datasets` body dataset_id; ayrı DELETE yolu var | Link auth/idempotency/response şeması canlı doğrulanmadı; DELETE bu pakette kullanılmaz |
| [Role hook](https://evren.ssyz.org.tr/assets/useDatasetRole-BLM7Tb7t.js) | `GET datasets/{id}/my-role`, role/permissions ve upload/edit/read dışı UI yetki isimleri | UI kontrolü backend auth/key-scoping garantisi değildir. Read izin adı bu hook'ta açık değil; uydurulmaz |
| [Upload UI](https://evren.ssyz.org.tr/assets/DatasetDetailPage-BPeje7FE.js) | presign files'ta client_uid; direct_upload_url / upload_url ayrımı; content_type; confirm skip_dedup ve created/actual_count/batch_duplicates; UI retry yapıyor | Retry kopyalanmaz. Direct host/path/expiry/header ve same-hash ad cardinality garantisi yok; frontend fallback matching oracle alınmaz |
| [Sabit SDK client](https://github.com/speker/evren-sdk/blob/f4eaa4a71f324e61058f24fb90c0aec7a58ae24f/evren_sdk/client.py) ve [güncel metadata](https://pypi.org/pypi/evren-sdk/json) | Latest 0.11.0; bütün image bytes'ı okuyan presign/PUT/confirm; credentialed client ve duplicates shortcut | Yörünge için uygun stream/target/receipt/replay adaptörü değildir; import veya kod kopyalama yok |

Kaynak güncelliği araştırma gününe aittir; asset URL'si kalıcı API değildir. Provider'ın bilinmeyen alanları, başarı envelope'u, create response ID/owner/private ilişkisi, link sonucu, upload batch/ad cardinality, current grant ve fiyat için kapalı oracle üretilemedi. Bunlar [başlangıç kapılarıdır](../roadmap/p02-2-delivery-plan.md#başlangıç-kapıları); tahminle doldurulmaz.

## Kullanıcıya sunulan kararlar ve gereken dış bilgi

1. [ADR-0024](../decisions/0024-durable-dataset-transfers.md): Eski execution/Recipe/jobs biçimlerini koruyan ayrı transfer ailesi; görünür create+project link; kalıcı aşama intent'leri, aynı-ID read-only restart; ilk upload ve state/süre kotaları.
2. [ADR-0025](../decisions/0025-isolated-storage-streaming.md): Ayrı auth/target politikasıyla API proxy ve önceden allowlist'e alınmış direct storage, bounded descriptor streaming; signed URL kalıcı/çıktı verisi olmaz.
3. Canlı hazırlık için scoped salt okuma endpoint listesi ve yetkisi; sonraki canlı yazmada exact owner/proje/format/storage hedefi, ücret kaynağı ve azami CR. Önceki discovery anahtar/proje hazırlığı write/cost onayı değildir. Kullanıcıdan key değeri veya ham hesap JSON'u istenmez.

Yeni ADR onayı olmadan bağımlı ürün kodu yoktur. Onay, açık provider sözleşmesi veya fiyatı kendiliğinden doğrulamaz. Onay sonrası local domain/state/TLS fixture adımları bağımsız ilerleyebilir; remote adapter/live kapıları ayrıca kapatılır. Kullanıcının kapsamı, bu kapıları aşmak için sessizce read-only veya ilişkisiz create'a daraltılmaz.

## Review ve doğrulama kaydı

İlk preflight: iki bağımsız salt okunur agent (state/HTTP/code ve scope/docs/authority) ile ana kaynak incelemesi tamamlandı. Bununla yeni yazılmış ADR/metinlerin iki fresh review turu tamamlanmış sayılmaz. Doküman/rehber kontrolleri ve iki fresh turun gerçek sonuçları aşağıda kayıtlıdır. Ürün test/build/native ölçüm ve hesap API çağrısı bu hazırlıkta çalıştırılmadı.


### Fresh belge review R1

İlk hazırlık commit'i **2655c2b**, iki yeni reviewer ile state/authority (GPT-6 Astra, high) ve transport/evidence (GPT-6.1 Sol, high) eksenlerinde incelendi. State kolunun iki P2 bulgusu current metin/kodla doğrulandı: ilk prepare/approve için döngüsel approval/owner koşulu; total deadline için eksik 5 s sonuç payı. İkisi aşamaya özgü kapılar ve ortak total/lease/authority/URL formülüyle düzeltildi. Taşıma kolu yeni doğrulanmış bulgu bildirmedi. Ana inceleme ayrıca iki worker'dan birinin hatasında yeni intent/confirm'in durmasını, in-flight diğer etkinin geri alınmış sayılmamasını açıklaştırdı. R1 ürün testi veya gerçek hesap kabulü değildir; ikinci fresh tur düzeltme commit'inden sonra yapılacaktır.


### Fresh belge review R2 ve onay öncesi kapanış

Düzeltme commit'i **5e185a0**, R1 reviewer'larından farklı iki fresh ajanla state/authority (GPT-6.1 Sol, high) ve transport/secret/UX/evidence (GPT-6 Astra, high) eksenlerinde yeniden incelendi. İki R1 düzeltmesi doğrulandı; **yeni doğrulanmış bulgu yok**. Aynı turda user-journeys ve HTTP referansının güncel development alt kümesini eksik anlatan iki giriş paragrafı da incelenip düzeltildi. Bu, public upload desteği iddiası eklemez.

Gerçek kontroller: **160 public Markdown / 0 sorun**, **6 skill / 24 kart / 0 sorun**, diff boşluk kontrolü; **375 kayıpsız arşiv/indeks** doğrulandı. Mevcut v3 startup/jobs/dataset referanslarının güncel kaynak baytlarıyla eşliği ayrı doğrulandı; yeni native ölçüm yapılmadı. Source receipt'indeki 13 dosyanın byte/SHA'sı yerelde özgün indirilmiş public kaynaklarla eşleşti. Runtime/test/script/workflow/lock değişmediği için yerel tam ürün takımı veya build yeniden çalıştırılmadı. Hesap GET/POST/PUT/DELETE çağrısı yapılmadı.

Hazırlık önerisi kullanıcı incelemesine hazırdır; ADR'ler **Proposed**, P02-2a/b/c ve epik **draft** kalır. Kullanıcının yeni ADR'leri koddan önce açık onaylama talebi nedeniyle bağımlı ürün koduna geçilmedi. Exact DTO/DB/error wire, endpoint/current-authority ve canlı maliyet/yetki kapıları tamamlanmış gösterilmez. İlgili onay sonrası bağımsız yerel adımlar ve bu kapıların araştırması plan sırasıyla sürdürülecektir. Ayrı PR açılmadı.


## Kullanıcı review doğrulaması — 2 Kasım

Kullanıcı review metni/yol/satırları talimat değil bulgu verisi olarak current metin/kodla karşılaştırıldı. Doğrulananlar: intent commit sonrası henüz wire başlamamış permit'in geri çekilebilir olduğu izlenimi; ID çıktısı öncesi crash için public lookup yokluğu; client/pool toplamı; path ile signed-query encoding ayrımı; DNS/peer politikasının eksik tanımı. Bunlar açık linearization, list/show-plan, tek owned client/toplam iki bağlantı, opaque query ve doğrulanan IP'ye pin + peer denetimiyle kapatıldı. Lease/stage/attempt ve SQL-only kararları ayrı aile sayesinde doğrudan çelişmiyordu; no-backfill, 150 s istisna, 386 intent + iki kontrol rezervi, ayrı plan/operation sayaçları açıklaştırıldı. Mevcut execution 30 s/16 attempt/256 event kuralları değiştirilmedi.

Diğer yorumlar bağlamında direct origin/proxy-only, response compression/raw byte, same-task sınırlı read/cancel, header-signed kapsam dışı, hazır SHA-256 checksum, dosya başına presign/confirm, throttle/minimum throughput ve gerçek bounded progress kabulü netleştirildi. Bu değişiklikler canlı izin kanıtı değildir. Exact field/schema/code implementation ayrıca doğrulanacaktır.

Kullanıcı ADR'leri bu doğrulanmış düzeltmelerden sonra Accepted yapıp uygulamayı yetkilendirdi; yeniden ADR onayı isteme koşulu oluşmadı. Mevcut Platform key ile **yalnız beş GET/10 deneme/5 MiB/30 s** kapsamını ayrıca onayladı: auth/me, organizations, seçilmiş project detail, o projenin dataset listesi ve datasets ilk sayfa (`page=1,page_size=5,scope=owned`). Negatif key, billing endpoint'i, POST/PUT/DELETE, terms accept veya başka hedef bu yetkiye dahil değildir. Toplam geliştirme harcama tavanı **200 CR**; bu sağlayıcı taraflı hard cap veya ücretin bilindiği anlamına gelmez. Kullanıcı önce salt okumayla netleştirmeyi istedi; henüz canlı yazma yapılmaz.

### Kamu fiyat kontrolü

Bağımsız kamu araştırması [resmî fiyatlandırma](https://evren.ssyz.org.tr/pricing/), [fiyat asset'i](https://evren.ssyz.org.tr/assets/PricingPage-DW1uSLiR.js) ve [kredi merkezi asset'ini](https://evren.ssyz.org.tr/assets/BillingPage-BT0BPQZh.js) metin olarak okudu; kullanıcı hesabı kullanılmadı. 8 credentialsız GET denemesi, 6 başarılı statik kaynak/2 takip edilmeyen redirect, 795.794 başarılı gövde byte'ı; seriler 30 s altındadır. 2026-11-02 13:57:12 Europe/Istanbul gözlemi: pricing 12.780 byte/SHA `7ba4e08583624f03f62dc47573eabf21b768e589149d0848a15be585ed10c394`; billing 41.619 byte/SHA `bb55fbbafde0403b7b05adbc9aaf43380c1538ef4de786f389b468dd608c795b`. Guide'ın yereldeki 96.221 byte/SHA kaydı tekrar doğrulandı.

Create/link/normal upload/storage/read için fiyat veya ücretsiz garantisi ve dataset'e uygulanabilir provider hard spending cap doğrulanamadı. Eğitim hold/settle veya export/çıkarım fiyatı normal upload'a genellenmez; günlük kazanım tavanı harcama limiti değildir. **200 CR yeter/yetmez sonucu çıkarılamıyor.** Kaynak fiyatı/kalıcı depolama maliyeti ve uygulanabilir önleyici sınır kapanmadan yazma pilotu bütçe onayıyla otomatik açılmaz; offline/yerel iş sürer. Yetkili beş GET'i billing'e genişletme yapılmadı.


### Review düzeltmelerinin commit ve yerel yürütücü kaydı

Kullanıcı review düzeltmeleri **e760d2e** ile commit edildi. Fresh R1, temel ADR güvenlik modelinde yeni doğrulanmış engel bulmadı; planın eski 8 GET/16 attempt/8 MiB ve bilinmeyen bütçe satırları ile batch istisnasını doğruladı. Plan, kullanıcının **5/10/5 MiB/30 s ve 200 CR** yetki sınırına/per-file karara hizalandı. ADR'ler kullanıcının açık koşullu onayıyla Accepted'a çekildi; dış otorite/wire/fiyat kapıları korunur.

Yeni [beş GET yürütücüsü](probes/platform-upload-preflight-20261102/README.md) ayrı kaynak/test olarak hazırlandı; gerçek anahtarı/ağı kullanmayan **19 offline güvenlik testi** ve Ruff format/lint geçti. İlk mock koşusu response'un önceden tüketilmiş oluşunu ortaya çıkardı; fixture gerçek incremental AsyncByteStream'e çevrildi, gerçek kaynak sınırları gevşetilmedi. Yürütücü explicit execute, exact method/target/path/query/auth, toplam/tek-call attempt, daha dar 512 KiB response, aggregate byte/deadline ve raw-value yayınlamama guard'ı içerir. Kaynak/test review tamamlanmadan canlı çağrı yapılmaz; eski probe snapshot'ları değiştirilmedi.


Fresh kullanıcı-düzeltme R2 (7eae1ea, yeni GPT-6.1 Sol/high) güncel istek/bütçe/per-file ve güvenlik hükümlerini doğruladı; yeni güvenlik/sözleşme bulgusu yok. Üç eski durum ifadesi P3 olarak doğrulandı: araştırma başlığı ile P02-2a/b üst/teslim metni Accepted ADR'leri açık kapı gibi gösteriyordu. Güncel başlıklar Accepted, kalan kapılar yalnız endpoint/otorite/kabul olarak düzeltildi; tarihsel review kayıtları korunur.

Beş GET aracı fresh R1 (7eae1ea, GPT-6.1 Sol/high) ve 19 sentetik testten geçti; doğrulanmış engelleyici güvenlik bulgusu yok. Önleyici test iyileştirmesi olarak mevcut-output testinde gerçek transport kurucusu da fail-closed monkeypatch edildi; post-parse deadline ve son-endpoint erişim reddinin outcome kaydı netleştirildi. Body sayacı TLS/header değil tüketilen raw gövdeyi ölçer; süreç duvar saati ile kontrol noktası deadline'ı ayrı anlatıldı. İkinci fresh code review canlı giriş öncesi yapılır.


### Yetkili beş GET sonucu

Fresh kod R2 (106f65a, GPT-6 Astra/high) ve tekrar 19 offline testte yeni doğrulanmış engelleyici bulgu yoktu. Sonrasında kullanıcıca verilen **tek** beş-GET kapsamı yürütüldü: **5 GET/5 attempt, 1.794 tüketilen raw body byte, 1,237609 s, 0 etkili istek**. Beş uç da HTTP 200 döndü; project dataset listesi ve owned dataset ilk sayfası boştu. Me root success=true, organizations items/total ve project owner/org alanlarının türleri gözlendi; bakiye değeri veya kimlikler yayınlanmadı. Bu gözlem yazma izni, principal anlamı, fiyat, pagination tamlığı veya current grant değildir.

[Şekil/sayaç receipt'i](p02-2-five-get-observations.json) özgün baytlarla saklandı; SHA-256 **de42dc2364971ce9bcecade4db724ac5c54fcf8f294f5f56b6b2163cb888fe33**, producer source 106f65a, probe SHA **ebb64410c1929cf3a55a69399034bad0baf9dbd4de79e01f336918fb9acebac7**. Hash yeniden karşılaştırıldı. Yürütücü/test kaynağı artık bu canlı koşunun immutable snapshot'ıdır; değiştirilmez veya otomatik tekrar yapılmaz. Hiçbir billing/negative-key/POST/PUT/DELETE çağrısı yapılmadı. Özel dosya/anahtar/account ham yanıtı repoya alınmadı.

API-key ile create/link yetkisi, mevcut dataset olmadığı için my-role/upload/presign/confirm şeması ve maliyet hâlâ açık. Yetkili read sınırı bunları çözmek için genişletilmedi. Bağımsız yerel domain/state/storage temel işleri bu dış kapılardan ayrılan hazır kartlarla devam eder; remote başarı uydurulmaz.


## Kullanıcının sonraki canlı deneme tercihi

Beş GET ve bağımsız yerel uygulama sürerken kullanıcı scope etiketi/tarifeye ulaşamadığını, “deneyebiliriz” ve “200’ü geçerse de sorun yok” yanıtıyla bildirdi. Başlangıçtaki 200 CR kesin tavanı bu küçük deneme için esnetildi; önceki kaynak/receipt'ler geriye dönük değiştirilmez. Somut ilk yazma denemesi [paket planındaki](../roadmap/p02-2-delivery-plan.md#canlı-kabul-hazırlığı) tek private dataset, açık test projesi, en çok üç görsel/1 MiB ve sabit istek/byte/süre sınırlarıdır. Otomatik DELETE/terms accept veya kapsamı büyüten tekrar yoktur. Bu kayıt fiyatı ücretsiz, provider yetkisini doğrulanmış veya ürünün prepared/cost-bound kapısını kapanmış göstermez; canlı yazma henüz yapılmadı. Önce yerel journal/storage kontrolleri ve exact tüketici wire'ı tamamlanır.

## Küçük araştırma pilotunun yürütücü hazırlığı

P02-2d/e/f yerel temelinin iki fresh turla kapanmasından sonra ayrı [tek-seferlik araştırma yürütücüsü](probes/platform-upload-pilot-20261102/README.md) hazırlandı. Üç sentetik 16×16 PNG, **79+79+79=237 byte**; ilk ikisi farklı adla aynı içerik, üçüncü farklı içeriktir. Bunlar kullanıcı hesabından alınmış görseller değildir. Planlanan tek private dataset, mevcut private projenin gözlenen org/personal sahibiyle bağlanır; geride kullanıcı hesabında kalır. Normal ürün planı/authority/cost snapshot'ı üretilmez; current grant veya fiyatı fake proof ile doldurmak yerine bu araştırma daima unknown/unverified raporlanır.

Yürütücü proxy-only guard'ı ve tek transfer client'ını kullanır. Exclusive private dizin/journal, etki öncesi fsync intent, aynı dizinle reentry yasağı, her aşamada tek effect attempt ve dar method/route/credential/count/byte/deadline allowlist'i vardır. Object key/signed URL yalnız bellekte; dataset ID yalnız private journal'dadır. Public receipt kapalı stage/status/count/type/predicate'ler taşır. GET en çok 10/20 attempt, create/link birer, presign/PUT/confirm üçer; toplam 120 s/5 MiB raw consumed response sınırı uygulanır. Kaynak/test bağları ve source commit saklanır. Bu araştırma journal'ı ürün lease/recovery kabulü değildir.

**40 offline test / 0,26 s**, Ruff format/lint ve genel 164 Markdown kontrolü geçti. Başarı fixture'ı, her aşamada 403, bozuk/mismatched/secret metadata, direct-only descriptor, kayıp link/dosya, tekrar create/yeniden giriş, intent fsync hatası, auth/ambient header, body/toplam süre sınırları ve beklenmeyen CLI hata metni sınandı. Canlı kaynak/test review kapanmadı; henüz hesapta yazma yapılmadı. Eski beş-GET scope'u tekrar kullanılmaz; bu deneme kullanıcının sonraki dar yazma yetkisine dayanır.

### Pilot kaynak review R1

56cb41e iki fresh reviewer tarafından incelendi (GPT-6 Astra/high güvenlik, GPT-6.1 Sol/high consumer/kanıt). İki ortak doğrulanmış bulgu vardı: **P1** confirm cevabı atıldığı için `created=0`/eksik/yanlış tip veya PUT scalar yanıtında sonraki etkiler devam edebiliyordu; **P2** üç farklı dosya descriptor'ı aynı object key/PUT URL'yi paylaştığında üçüncü içerik önceki nesneyi ezebiliyordu. Bunlar ürün kodu veya canlı hesapta gözlenmiş hata değildir; helper canlıdan önce reddedildi/düzeltildi.

Düzeltme, PUT için empty/root success=true, confirm için created/actual_count/batch_duplicates strict oracle ve ilk PUT öncesi object key/exact URL tekilliği ekledi. Sonraki etkilerin sıfır kaldığı negatifler eklendi; aynı hash için shared-key dedup varsayılmadı. Belirsiz create sonrası elle inceleme için yalnız private journal'da üretilmiş dataset adı intent'ten önce tutulur; journal bitiş fsync hatasında FD yine kapanır. **56 offline test / 0,34 s** ve Ruff geçti. Yeni, farklı reviewer'larla R2 tamamlanmadan canlı çağrı yoktur.

### Pilot kaynak review R2

7838cec iki yeni reviewer ile incelendi (GPT-6.1 Sol/high güvenlik, GPT-6 Astra/high consumer). İki yeni **P2** doğrulandı: link'in scalar/bilinmeyen ACK'i sonraki GET olumlu olsa da şema ret kuralını atlıyordu; ayrıca farklı object key alanları ve percent-encoding'i farklı URL'ler aynı decoded proxy nesnesine yazabiliyordu. Gerçek provider'da gözlendiği iddia edilmez. Link için empty/root success=true kapısı; proxy için tek strict `key` query parametresiyle descriptor object key eşliği eklendi. Böylece kodlanmış URL alias'ı ile nesne değiştirme ilk PUT'tan önce reddedilir; geçerli eşdeğer percent-case kabulü korunur.

Son helper kümesi **66 passed / 0,38 s**, Ruff geçti. Daha erken descriptor ret noktası nedeniyle eski iki testin 3 presign beklentisi 1'e düştü (**63 passed / 2 failed**); senaryo oracılları erken ret ve sıfır PUT'a göre düzeltildi, guard gevşetilmedi. R2 düzeltme teyidi ve gerçek canlı sonuç henüz yoktur; kaynak freeze/call bu kapanıştan sonradır.

f1442d8 R2 teyitlerinde her iki bulgu kapandı: güvenlik kolu özgün URL alias/nonce denemelerinde ilk presign sonrası 0 PUT/0 storage object ve **66 / 0,32 s**; consumer kolu link scalar/nested logical failure örneklerinde yalnız create/link, root true/boş 204 pozitifleri ve **66 / 0,30 s** bildirdi. Son ana kaynak eşlemesinde guide/SDK'nın API köküne göreli `/datasets/{id}/upload/put` biçiminin origin-root yolu gibi yorumlandığı saptandı. Yalnız exact aynı dataset prefix'i için API root ekleme düzeltildi; host, dataset, path/query/secret kapıları korunur. Bu bağımsız pozitif fixture'la son helper **67 / 0,42 s**, Ruff geçti. Son dar URL değişikliğinin reviewer teyidi bekleniyor; canlı çağrı yapılmadı.

14bc774 için R2 safety teyidi **67 / 0,29 s**, ayrıca 14 bağımsız route/host/dataset/traversal/query/fragment ret deneyi ve üç geçerli relative/absolute biçimle tamamlandı. Yeni doğrulanmış bulgu yoktur. Böylece araştırma yürütücüsünün iki fresh turu ve tüm düzeltme teyitleri kapandı. İlk canlı giriş yalnız bu frozen source/test snapshot'ı ve kullanıcının sonraki tek küçük deneme yetkisiyle yapılabilir; sonuç ayrı kayıt olacaktır. Bu kapanış canlı başarı veya ürün authority/cost-bound kabulü değildir.

## İlk canlı koşu ve ayrı salt okuma hazırlığı

Frozen fdef990 kaynağıyla ilk küçük deneme yapıldı: **3 attempt, 1 create etkisi, 1.237 body byte, 1,159029 s**. Private create 201, devamındaki `/datasets/{id}` GET **405** döndü; kaynak durdu. Link/presign/PUT/confirm ve görsel aktarımı sıfırdır. [Receipt ve yöntem hatası](p02-2-private-create-observations.md) ayrı kanıttır; koşu başarısız/partial olarak korunur. Dataset hesabın private alanında kaldı; adı/ID'si yalnız private journal'da, ham cevap/secret/URL/object key saklanmadı. Create tekrarı veya otomatik DELETE yoktur. Fiyat/CR tüketimi hâlâ bilinmiyor.

Kamu dataset consumer'ı detail için username/slug kullanıyor; helper'ın ID detail varsayımı doğrulanmamıştı. Frozen kaynak/test canlıdan sonra değiştirilmez. Aynı ID'yi owned ilk sayfada bulup buradan gözlenen iki path bileşeniyle detail ve my-role okuyan [ayrı read-only takip](probes/platform-created-dataset-read-20261102/README.md) hazırlandı: **3 GET / 6 attempt / 1,5 MiB / 30 s**, effect sayısı transport'ta zorunlu sıfır. Sahte prefix/başka ID/metadata secret/parent/private/name uyuşmazlığı, 401/403/405, method/route widening ve byte sınırlarında **30 offline test / 0,20 s** geçti. Kaynak review ve bu yeni somut hesap çağrısı scope'unun onayı beklenir; canlı takip yapılmadı.

### Oluşturulmuş kaydın read-only takip review R1

8e7ee3b iki yeni reviewer ile incelendi (GPT-6.1 Sol/high güvenlik, GPT-6 Astra/high consumer/kanıt); iki **P2** doğrulandı. Frozen helper kaynak SHA'sından sonra importlib loader'ın stale timestamp/size `.pyc` yürütmesi mümkündü; aynı doğrulanmış byte buffer'ı compile/exec ile yeni ModuleType namespace'inde çalıştırma seçildi. Eski bytecode ve önceden yüklenmiş modül negatif/pozitifleri eklendi; bozuk hash kaynak yürütmeden reddedilir. İkinci bulguda eksik org_id açık null gibi eşleniyordu; iki consumed kayıtta key presence zorunlu tutuldu ve owned/detail/both missing retleri eklendi. Düzeltmeler sonrası **35 offline test / 0,23 s**, Ruff geçti; import sıralama uyarısı otomatik format düzeltmesiyle kapandı. Yeni fresh R2 ve hesap çağrı yetkisi henüz kapanmadı; takip çalıştırılmadı.

### Oluşturulmuş kaydın read-only takip review R2

3e4a3f8 iki farklı yeni reviewer ile incelendi. Consumer/kanıt kolu (GPT-6.1 Sol/high) **35 / 0,11 s**, 27 bağımsız malformed kayıt/permission/control deneyi ve yeni bulgu yok bildirdi. Güvenlik kolu (GPT-6 Astra/high) **35 / 0,16 s** ve bir **P2** doğruladı: son JSON/secret/shape doğrulaması transport context'i dışında deadline'ı aşsa da sonuç başarılı dönebiliyordu. Sentetik 20 ms bütçe + 30 ms son payload gecikmesinde 21,37 ms aşım ve pozitif sonuç görüldü; ek ağ isteği yoktu.

Düzeltmede GET öncesi, parse/shape sonrası ve nihai predicate dönüşü öncesi monotonic deadline tekrar denetlenir. Son validation'da deadline expiry regresyonu eklendi; **36 / 0,28 s**, Ruff geçti. R2 son düzeltme teyidi henüz bekleniyor; gerçek takip için yeni somut üç-GET scope'u onaylanmadı ve çağrı yapılmadı.

1ccccfc R2 teyidi tamamlandı: özgün 20 ms + 30 ms gecikme artık transport_timeout, geçmiş bütçe 0 attempt, **36 / 0,14 s**, yeni regresyon yok. Kaynak/test review kapanışı tamamdır. Hazırlıkta bu readonly takip için ayrıca onay gerekeceği varsayılmıştı; mevcut P02-2 uygulama, hesabı anahtarla inceleme ve sonraki küçük deneme talimatları aynı oluşturulmuş kaydın sıfır etkili incelenmesini kapsar. Bu yorum açıkça kaydedilir; yeni bir kullanıcı onay yanıtı uydurulmaz. Yeni write/başka kaynak/billing yoktur. İlk denemenin kalan etkileri kapalı kalır; ayrı 3 GET/6 attempt/1,5 MiB/30 s takip bu mevcut yetkiyle bir kez çalıştırılabilir. İlk pilotun 405 sonucu/kendi bütçe kaydı değişmez; bu ayrı yöntem o koşunun kabul başarısı değildir.

10fe9d4 frozen readonly takip tamamlandı: **3 GET/3 attempt/1.666 byte/0,327002 s**, üç HTTP 200, **0 effect**. Exact aynı private kayıt ve owner/org eşliği geçti; `upload` permission string'i gözlendi. [İki ayrı seri ve kaynak/receipt bütünlüğü](p02-2-private-create-observations.md#aynı-kaynak-için-ayrı-salt-okuma-sonucu) kanoniktir. Önceki 405 silinmedi veya başarıya çevrilmedi; yeni create/link/upload yapılmadı. API key ile bu üç gözleme erişim ve bir private create başarısı, genel güncel create/link/upload grant veya fiyat üst sınırı sayılmaz. Ürün hazırlığı için bu gerçek sınırın açık politika kararı gerekir; Accepted ADR-0024 kendi başına aşılamaz.

## Açık ürün kararı — ADR-0026 önerisi

Kullanıcının küçük deneme/200 CR aşımı talimatı research çağrısını açtı; genel public hazır plan/onay semantiğini kendiliğinden değiştirmez. [ADR-0026](../decisions/0026-explicit-unverified-transfer-attempts.md) bu nedenle Proposed olarak yazıldı: verified_only default korunur; explicit_attempt ile unknown authority ve ayrı unpriced seçimi yalnız açık digest-bound insan acknowledgement'ıyla denenebilir. Grant/cost fake üretilmez; numeric bütçe varsa bound hâlâ gerekir; bilinen ret/mismatch/over-budget hiçbir flag ile aşılmaz. V2 wire, v1 immutable compatibility ve mevcut tekil intent/permit/clock/credential kapıları somutlaştırıldı. Yeni ADR'leri bağımlı uygulama öncesi onaylama kullanıcı talebi geçerlidir; v2 ürün kodu yoktur. Belge iki fresh turdan geçmeden onaya sunulmaz.

### ADR-0026 fresh R1

4096265 iki yeni reviewer tarafından incelendi. Compatibility/kanıt kolu (GPT-6.1 Sol/high) yeni doğrulanmış maddi bulgu bulmadı; public iki receipt ve kaynak hash eşliklerini doğruladı. Policy kolu (GPT-6 Astra/high) bir **P2** doğruladı: null grant ile bilinen ret/oracle yokluğu ayrımı tanımlı reducer girdilerinde kapalı değildi. İç AuthorizationCheck allowed/not_exposed/denied/unavailable/invalid ayrımı, exact current scope/credential ve hata eşlemesi eklendi. Transport/malformed/401403 null proof'a düşürülemez; mandatory context/my-role her prepare/arm'da tazedir, gözlem yaşı en çok 30 s. Ayrı negatif cache eklenmez; actual write ret'i mevcut kalıcı namespace/intent'te kalır. Tam olmayan grant riski ve known fiyatın unpriced özetinde doğru gösterilmesi açıklaştırıldı.

R1'de mevcut read-grant kapısının değişmediği hata sayılmadı. Ana değerlendirmede yeni deneme yolunun provider read oracle yokken yalnız yerel show'a sıkışmaması için öneri açıkça genişletildi: yalnız v2 explicit operasyon, scoped read-attempt ve ayrı reconcile acknowledgement; complete accepted receipts + metadata proof ile metadata-level success, authority unknown ayrı. V1/default kapısı korunur. Bu bir R1 reviewer talebi veya kullanıcıca onaylanmış değişiklik diye sunulmaz; yeni kararın parçası olarak fresh R2 ve kullanıcı onayına tabidir. V2 Verification DTO/reason ve yazım-tazelik/historical validation ayrımı da açık tanımlandı. V2 ürün kodu başlamadı.

### ADR-0026 fresh R2

8b43e26 iki farklı yeni reviewer ile incelendi. Policy kolu (GPT-6.1 Sol/high) yeni doğrulanmış maddi bulgu bulmadı; iki receipt ve dört frozen kaynak/test hash'ini doğruladı. Compatibility kolu (GPT-6 Astra/high) bir **P2** doğruladı: yeni record reason'ları mevcut kapalı TransferControl v1'in verified↔proof-digest koşuluyla kalıcılaşamıyordu. Öneriye explicit **TransferControl v2**, operation/control/proof sürüm eşliği, metadata_verified yalnız terminal+nonnull digest ve read_unavailable yalnız recovery+null digest eklendi. V1 golden/digest ve 2 KiB/iki slot sınırı korunur; reset/recovery de operation sürümünü izler. Authority özeti metadata okumasıyla true'ya yükseltilemez. R2 bu dar düzeltmenin teyidinden sonra kapanır; kullanıcı onayı yoktur, bağımlı ürün kodu başlamadı.

6ecb2d9 dar R2 teyidi yeni maddi çelişki olmadan tamamlandı. Böylece ADR-0026 iki fresh belge review turu ve doğrulanmış bulgu kapanışlarıyla kullanıcı kararına hazırdır; durum **Proposed** kalır. Son genel belge/rehber/diff kontrolleri **166 Markdown / 6 skill / 27 kart**, 0 sorun. Bu belge review'sinde yeni runtime/build/native/CI veya live write yapılmadı. Yerel d/e/f verified; a/b/c ve epik draft. Kullanıcının yeni ADR'leri bağımlı uygulamadan önce onaylama koşulu nedeniyle v2 ürün kodu onaydan önce başlamaz; tek nihai P02-2 PR'ı henüz açılmadı.

## ADR-0026 kullanıcı review düzeltmesi

Kullanıcı supplied review bulgularını kapattıktan sonra ADR'yi Accepted yapıp implementasyona devam etmemizi açıkça istedi; aynı karar için yeniden onay gerekmez. 633c635'teki öneri ve mevcut v1 kod karşılaştırıldı. V1 cost yalnız scope/tutar/source/zaman bağlı olduğundan exact iş/dönem güvencesi veremiyordu; bu **P1** doğrulandı. Ayrıca v2 reducer/gates/current-binding/read/graph/control acceptance ifadeleri uygulama yorumu bırakıyordu. İki salt-okuma hazırlık ajanı (GPT-6 Astra/high maliyet, GPT-6.1 Sol/high gate/uyumluluk) mevcut kod etkilerini doğruladı; bu analiz fresh revizyon review turu sayılmaz.

Yeni [kanonik v2 referansı](../reference/dataset-upload-v2.md) sözleşmenin tek ayrıntı kaynağıdır. Maliyet; exact work digest, request limit/execution window, kategori ve charge period, post-period storage guarantee ile kapatıldı. Quote etiketi hesap kanıtı sayılmaz; partial bound numeric bütçeyi açamaz. V1 byte/golden/history korunur ama scope-only eski bound yeni approve/admit/arm vermez. Ayrı v2 reducer ve **96 literal durum**, gereksiz/eksik bool davranışı, bütün gate/error/deadline ve HTTP/my-role registry kapandı. Unpriced için her durumda approval-time cost ack seçildi; bilinen quote varken de kullanıcı tavanı seçilmediği açık kabul edilir.

Fresh evidence için seçenek A: saved snapshot/digest immutable, ayrı baseline/supplemental current kanıt; saved partial korunurken supplemental full eklenebilir, expiry/ret/semantic değişim bypass değildir. Read aktör/flag/current-grant matrisi, ayrı readonly çağrının error/exit istisnası, terminalimmutability, observation scope'un current/historical ayrımı ve public summary v2 tanımlandı. Success bütün **2+3N** exact stage grafiği + accepted receipt + metadata ister. Record/control version/digest/slot/coalescing/reset/takeover ve rezerv golden'ları kabul listesinde ayrı zorunludur. ADR-0024 partial-amendment ve phase-02/ref/kart/matris geçişi açık listelendi.

Revizyon henüz iki yeni fresh turu bitirmedi; durum Proposed ve bağımlı v2 src kodu yoktur. Yeni canlı hesap çağrısı, build/native veya yeni ürün testi bu belge düzeltmesinde yapılmadı. Genel belge/rehber/diff denetimi 167 Markdown, 6 skill/27 kart ve 0 sorun verdi.

### Kullanıcı revizyonu fresh R1

75c210b, önceki hazırlık reviewer'larından farklı iki fresh ajanla incelendi. Maliyet kolu (GPT-6 Astra/high) maddi bulgu bulmadı; exact work/period/storage, request caps, weak-v1 write kapanışı ve 96 matris tutarlı bulundu. Gate kolu (GPT-6.1 Sol/high) **P2** doğruladı: not_exposed registry yalnız create/link için yazılmıştı; observed profile grant üretmediğinden upload/read explicit fallback'i erişilemezdi. Dört action için ayrı oracle/mandatory gate tablosu eklendi; my-role label ayrı prerequisite kalır, grant'a çevrilmez. Denied/unavailable/invalid fallback olamaz. Kullanıcı revizyonunun fresh R2'si henüz kapanmadı; v2 ürün kodu başlamadı. Reviewer'lar test/canlı/özel dosya çağrısı yapmadı, yalnız statik sözleşme/kod okudu.

### Kullanıcı revizyonu fresh R2 ve Accepted kapanışı

B26cfa9 iki farklı yeni ajan tarafından incelendi. Maliyet/provenance kolu (GPT-6.1 Sol/high) ve gate/uyumluluk kolu (GPT-6 Astra/high) yeni maddi bulgu bulmadı; dört-action registry düzeltmesi kapandı. İkinci kol 96 oracle dağılımını bağımsız saydı: **65 draft, 2 prepared, 11 attempt_ready, 18 invalid**; onaylanabilir dokuz unpriced satırda cost ack zorunlu. İnceleme statikti, ürün/live testi diye sunulmaz.

Kullanıcının “bulguları gider, sonra Accepted yap ve devam et” talimatı uyarınca ADR-0026 Accepted yapıldı; aynı karar yeniden onaya sorulmadı. Yeni kanonik v2 ref, ADR-0024 forward amendment, ref/karar indeksleri, phase/current ve beş dar g/h/i/j/k kartı hizalandı. G maliyet adımı in_progress; h/i/j/k ve remote a/b/c draft. D/e/f v1 tarihsel kabulü korunur. Bu sırada yeni canlı çağrı, source-bound ölçüm/build/CI yapılmadı; eski M5 referans yeni kaynağın kabulü değildir.

## Gerçek provider codec hazırlığı — l sonrası

Yerel g–l çalışma dalı kabulünden sonra m proxy upload tüketici sözleşmesi kod öncesi yazıldı. Yeni Astra/high wire incelemesi **P2** doğruladı: guide/credentialed SDK ve lexical key sınırı, provider object_key'in ayrıca yetki taşımadığını kanıtlamaz. ADR-0026 bu kalıcılık kapısını değiştirmedi. Kanıt açığı düzeltilerek raw key URL gibi tamamen ephemeral tutuldu; ADR-0025'in mevcut güvenli file-binding seçeneği uygulanır. Yeni producer private StageReceipt.object_key slotunda raw key yerine bağımsız, ağa gönderilmeyen yerel UUID tutar. Client UID ayrı tutulur; semantic digest raw key/body hash'i içermez. Eski opaque wire/golden/history yeniden yazılmaz.

Aynı reviewer bu alternatifin ADR-0024 dosya/request bağı ve ADR-0025 file-binding sınırına uyduğunu, yeni yetki/replay/kalıcılık gevşemesi veya yeni ADR gerektirmediğini doğruladı. Private mapping immutable ve exact operation/dataset/file-index/manifest/target'a bağlı olacak; raw key/hedef bijeksiyonu ve descriptor takası/canary/restart negatifleri kod kabulüne eklendi. Provider non-authorizing kapısı kapanmış veya canlı upload gerçekleşmiş sayılmaz. m uygulaması başlayacak; saf codec uygulaması bu güncel referansa bağlıdır.

Sabit kamu SDK kaynağı bir credentialsız GET ile yeniden alındı: **32.318 byte**, SHA-256 `c9bebcd0ae0a7566cd08d9ec288265d01013a3edc829421746563e0be2409f98`; yerel public snapshot ile exact eşit, proxy fallback rotası kaynakta var. İki credentialsız OpenAPI yolu (`/openapi.json`, `/api/v1/openapi.json`) 404 döndü; gövde veya hesap verisi saklanmadı. Bu üç istek hesap/pilot çağrısı değildir; HTTP kaynağı güncelliği endpoint canlı uyumluluğu veya auth garantisi olmaz. SDK/JS çalıştırılmadı veya ürün bağımlılığına eklenmedi.


## O.2 öncesi tarihsel create bağının kalıcılığı — ADR-0027

Bağımsız Astra/high salt-okunur hazırlık incelemesi, provider referansındaki koşulsuz create/detail owner_id+org_id eşliği ile yalnız dataset_id saklayan StageReceipt v1 arasında restart kanıt boşluğunu doğruladı. Current owned→detail eşliği tarihsel create cevabı değildir; selected owner'a indirgeme mevcut metinde yoktur. [ADR-0027](../decisions/0027-durable-created-dataset-context.md) bu nedenle dar accepted-create v2 baseline'ı önerir; eski receipt alanı/hash'i aşırı yüklenmez, DDL 1–7 değişmez. Pre-create/current/prepare/approve bağımsız ilerleyebilir; yeni receipt/restart success kodu kullanıcı onayına bağlıdır.

0b241ba üzerinde iki fresh belge turu tamamlandı. R1 Sol/high contract ve Astra/high safety; R2 farklı yeni Astra/high contract ve Sol/high safety doğrulanmış bulgu bildirmedi. Dört inceleme exact kind/version/plan/owner union, atomik receipt+ID, 2 KiB reservation, immutable/reset current scope ayrımı, missing legacy baseline HTTP-sıfır/unknown, korunmuş terminal history, strict literal/PII ve geçiş listesini kontrol etti. R1 safety iki en fazla kaçışlı 256 UTF-8 byte ad temsilcisiyle canonical envelope'u 1.259 byte hesapladı; bu runtime/writer veya bütün Unicode uzayı ölçümü değildir, kabul testleri uygulamada zorunlu kalır. Ürün testi/canlı çağrı yapılmadı. ADR Proposed; onaya hazırdır.

## ADR-0027 kullanıcı review revizyonu — 3 Kasım

Kullanıcı bulgular kapandıktan sonra ADR'yi Accepted yapıp uygulamaya devam etmeyi açıkça yetkilendirdi; aynı karar yeniden sorulmayacak. Üç review çıktısındaki örtüşen P1/P2'ler tek sözleşmede kapatıldı: ADR-0026/v2 referansı için madde bazlı amendment; yeni v2 accepted-create insert'inde v1 yasağı ve tarihsel decode ayrımı; legacy nonterminal için tüm yeni arm/renew/read lease/permit/success öncesi yerel engel; owner/CAS/clock marker tablosu ve marker başarısızlığında eski business durumunu koruma. Ham response 1 MiB ile canonical receipt 2 KiB ayrıldı. Post-dispatch bozuk receipt/owner çelişkisi write sonucunda aynı ID/exit 5 ve replay yasağıdır; ayrı readonly hata istisnası korunur.

Kod yerleşimi açıklandı: union/full graph yalnız yapısal ve sürüm uyumu; receipt transaction yeni insert/DTO/owner-kind/plan bağı; controller ve repository pre-arm/read/renew engeli; yeni proof commit son savunma. Eski terminal v2+v1 geriye dönük yeni baseline şartıyla bozulmaz. Public summary receipt/view/baseline alanlarını serialize etmez; sentinel çıktı kabulü controller/public diliminde zorunlu. Commit öncesi/sonrası kill, expiry sonrası geç response ve eski çalışan binary'nin geri çekilemeyen permit sınırı ayrıldı. ProviderDataset'in tam dar DTO seçimi original/restart predicate eşliği içindir; parent ifadesi selected owner/project context olarak netleştirildi.

Ürün kodu henüz başlamadı; bu revizyonda yalnız ADR ve review kaydı değişti. İki fresh belge turu ardından Accepted doküman geçişi; sonra DTO/union/history ve writer/legacy gate iki ayrı commit/review dilimi uygulanacak. Her kod dilimi iki fresh tur ister; public/controller/native/live sonraki kabul sahibidir. Doc/link kontrolü 180 Markdown/0 problem; ürün testi/canlı çağrı yapılmadı.

87219a3 revizyonu fresh R1'de Sol/high contract ve Astra/high safety tarafından mevcut repository/store/versioning, read/cleanup owner/CAS, intent expiry ve eski terminal fixture'larla karşılaştırıldı. İki incelemede doğrulanmış kalan bulgu yok. Yeni insert/tarihsel okuma, marker'ın koşullu kalıcılığı, raw/receipt byte ayrımı ve public dar projeksiyon ayrı kapılar olarak uygulanabilir bulundu. Salt okuma yapıldı; ürün testi/canlı çağrı yok. Farklı fresh R2 henüz tamamlanmadı; ADR Proposed, bağımlı kod başlamadı.

Farklı fresh R2 Astra/high contract ve Sol/high safety, f68f69a üzerinde normative 87219a3 revizyonunu bağımsız karşılaştırdı; doğrulanmış kalan bulgu yok. Dört reviewer yeni insert/tarihsel history, pre-HTTP legacy mutation engeli, owner/CAS koşullu marker, raw1MiB/receipt2KiB ve public dar projection kabulünü uygulanabilir buldu. Ürün testi/canlı çağrı yapılmadı. Kullanıcının 3 Kasım koşullu talimatıyla ADR-0027 **Accepted**; aynı karar yeniden sorulmadı. ADR-0026 ve aktif v2/provider/preparation/transfer/current/plan/indeks referansları madde eşlemesiyle hizalandı; P02-2p iki kod dilimi ready. Bu geçiş ürün receipt kodunun veya live kabulünün tamamlandığı iddiası değildir.

Accepted geçişinin ilk agent-guide kontrolü p kartında gerekli exact bölüm başlıkları eksikliği nedeniyle reddedildi; başlıklar ve uygulama sınırı düzeltildi. Bu metadata reddi başarı diye sunulmaz.
İkinci denetim ayrıca ready kartta zorunlu Teslim kaydı bölümünü reddetti; henüz uygulanmadığını açıkça belirten bölüm eklendi. Üçüncü kontrolün gerçek sonucu commit kapısıdır.

## Q gerçek HTTP portu ön incelemesi

P verified sonrası bc70edb üzerinde yeni port referansı/card q iki fresh uzmanla salt okunur ön incelemeden geçti. Astra/high contract **P2** doğruladı: generic DispatchPermit sadece PID/one-shot; mevcut arm bağımsız tuple olduğundan port sözleşmesinin exact intent/permit/deadline bağı tek başına sağlanmıyordu. Sol/high safety bunu trusted composition sorumluluğu olarak not etti, başka substantive bulgu bulmadı.

Somut düzeltme: yeni private UploadArm, repository'nin COMMIT+final gate sonrası aynı intent snapshot/permit/deadline'ını immutable tek paket olarak taşır; gerçek port ayrı parça/tuple/deadline kabul etmez. Generic execution permit ve persisted DDL/wire/golden değişmez. Ordinary construction/copy/pickle, yanlış PID/thread/tek claim ve parça/deadline takası negatifleri q.1 kabulüdür. Trusted issuer DB kökenini sağlar; hostile in-process private kod çalıştırmaya karşı sandbox veya bağımsız DB attestasyonu iddia edilmez. Ortak semantic request fonksiyonu aynı golden byte'larını korur. Bu routine internal bağlama mevcut ADR intent/tek gönderim politikasını daraltarak uygular; yeni user policy/ADR gerektirmez. Q üç kod/review dilimine ayrıldı: issuance/semantic, control HTTP, PUT/items. Ürün kodu henüz başlamadı; her dilimin iki fresh kod review turu zorunlu.
