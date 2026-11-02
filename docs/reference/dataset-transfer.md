# Private dataset aktarımı taslağı

**Durum:** Proposed; P02-2 ürün kodu yoktur. **Tarih:** 2026-11-02. [ADR-0024](../decisions/0024-durable-dataset-transfers.md) ve [ADR-0025](../decisions/0025-isolated-storage-streaming.md) kullanıcı onayı bekler. Bu belge mevcut inspect/verify, execution veya jobs sözleşmesini değiştirmez. [Dış kapılar](../roadmap/p02-2-delivery-plan.md#başlangıç-kapıları) kapanmadan remote uygulama hazır sayılmaz.

## Kullanıcı yüzeyi ve uyumluluk

Önerilen ayrı komut ailesi aşağıdadır; **henüz çalışmaz**. Ortak config/profile/state-dir ve text/JSON/NDJSON seçimleri mevcut parse/render ilkelerine uyacaktır; tam argüman/type/DTO/error wire'ı P02-2a yerel kod adımından önce bu referansta kapatılır.

```text
yorunge datasets upload plan ROOT --manifest FILE --name NAME --project UUID
    (--owner-user UUID | --owner-org UUID) --modality MODALITY
    [--storage-origin HTTPS_ORIGIN] [--config FILE] [--profile NAME] [--state-dir PATH]
yorunge datasets upload approve --plan-id UUID --confirm FULL_PLAN_DIGEST [...context]
yorunge datasets upload revoke --plan-id UUID [--state-dir PATH]
yorunge datasets upload start --plan-id UUID [...context]
yorunge datasets upload list [--plan-id UUID] [--limit N] [--cursor CURSOR] [--state-dir PATH]
yorunge datasets upload show (--operation-id UUID | --plan-id UUID) [--state-dir PATH]
yorunge datasets upload reconcile --operation-id UUID [...context]
```

Python karşılıkları aynı kullanım senaryolarına bağlanacak ayrı upload plan/approve/revoke/start/list/show/reconcile API'leridir; senkron köprü asyncio active-loop/PID/thread kapısını state/credential/etki öncesi uygular. Python çağıranından raw provider JSON, producer/verified flag, authorization listesi, HTTP client veya storage header dict'i alınmaz. JSON/NDJSON Result v1 korunur; bütün dosya/journal stdout'a basılmaz. Bilinen operation ID hem kontrollü hata hem belirsizlik/çıktı iptali yolunda korunur.

Bu ön yüz önerisi kesinleşmiş wire değildir. Product API adları, exact alanlar ve kapalı hata tetik/exit matrisi P02-2a'nın uygulama öncesi kabulüdür; genel CLI kataloğunda ikinci bağımsız hata tablosu tutulmaz. Kayıt bulunamadı, geçersiz plan, kapasite, hedef/yetki reddi ve belirsiz yan etki birbirinden ayrılır. Eski `plan execution` yeni upload planlarını import etmez; `jobs` mevcut execution kayıtlarını göstermeyi sürdürür. Transferin kanonik geçmiş/uzlaştırma yüzeyi bu yeni ailedir. List varsayılan 50/en çok 100 satır, immutable `(prepared_at, plan_id)` keyset cursor ve optional exact plan filtresiyle plan/nullable operation özetlerini verir; ağ/env/hash/onay istemez. Show'da iki ID karşılıklı dışlanır. `show --plan-id` commit edilmiş operation'ı exact FK ile bulur; henüz yoksa operation=null döner, yeni admission/permit üretmez. Admission/ilk ID çıktısı arasındaki kill/BrokenPipe sonrasında kullanıcı yalnız bu yüzeylerle aynı işi bulabilir; start'ı yeniden gönderme recovery önerisi değildir.

## Bağlanan veriler ve otorite

Planın canonical digest'i identity/store/clock, exact Platform target, owner türü/ID, proje ID, private oluşturma parametreleri, root kimliği, immutable manifest, storage policy, quota/deadline ve adapter/policy sürümünü kapsar. Her göreli dosya adı ayrı kimliktir; aynı hash farklı adlar sayısal dedup başarısı altında kaybolamaz. Provider bunu desteklemiyorsa etkiden önce açık sınırlama veya aktarımda doğrulanmış eksik teslim sonucu gerekir; sessiz rename/flatten/skip yoktur.

Kullanıcının owner/project seçimi niyettir; create/link/upload izni değildir. P02-0d sonucu bu yetki yerine geçirilemez. [P02-2a](../roadmap/tasks/p02-2a-private-create.md) exact API-key create kapsamını, project ilişki anlamını ve dataset için güncel upload/read otoritesini kapatır. Desteklenmeyen hedef ve bilinmeyen auth/parent/format bilinmeyen kalır. Profile account/project tercihi yalnız aynı exact hizmette açık doğrulanmış seçimle uyuşuyorsa kullanılabilir; scope'lar birleştirilmez.

Üretim codec'i tüketilen alan/control için strict JSON/type/size ve request/response ilişki doğrulaması yapar. Bilinmeyen ham metadata politikası her endpoint için açık seçilir; discovery'nin metadata istisnası otomatik miras değildir. Literal-secret denetimi seçili credential için mevcut kuraldır: tüm uzunluklarda tam eşitlik, ≥8 UTF-8 byte'ta ayrıca alt-dize. Genel sır/PII sınıflandırması veya kısa sırın sabit protokol metninde hiç görünmeme garantisi verilmez. Dinamik yerel owner/project/name/path alanları da ağ/kalıcılık/çıktı öncesi bu kapsamdadır.

## Kalıcı aşama modeli

Plan/approval/transfer operation ayrı strict sürümlü kayıtlar; immutable manifest ayrı bounded canonical payload'dır. Yeni 6→7 SQL-only V2 migration yeni boş transfer tablolarını/indekslerini ekler; eski kayıt/payload/checksum için backfill yoktur. Full/hot validation, backup, bakım preview/fingerprint ve global expiry hesabı birlikte gelir. Güncel development şeması 6'dır; eski migration/manifest/checksum değiştirilmez. Restore/recover'ın operation runtime yasağı korunur.

Owner/fence/CAS ortak güvenlik mekanizmasıdır; transferin 150 s lease'i, tek workflow attempt'i ve stage kotası ayrı aileye aittir. Genel execution'ın 30 s/16 attempt/256 business-event sınırları değiştirilmez veya transfer stage'ine uygulanmaz. Workflow latch ve aşama intent'leri yeniden gönderilemez. Aşama türleri create, project_link, presign, put, confirm; read verification etki izni üretmez. Her aşamanın key'i operation/kind/file index, request digest'i, kalıcı sıra/revision, gerçek UTC/clock alanı ve varsa güvenli resource bağını içerir. Tam private row/receipt alanları, canonical tipler, index/FK ve byte/counter eşitliği P02-2a yerel kayıt adımından önce sabitlenir. Raw signed URL, auth/header/body veya kullanıcı secret'ı journal değildir.

| Sınır | Sonraki izin |
|---|---|
| Henüz intent yok | Güncel bütün kapılar ve önceki aşamanın durable receipt'i ile ilk intent oluşturulabilir |
| Intent commit edildi, receipt yok | Gönderilmiş olabilir; read reconciliation dışında ilerleme yok |
| Strict receipt durable | Yalnız doğru sonraki aşama, yeni son yetki/lease/onay kontrolüyle ilk kez açılabilir |
| Owner/revoke/reset/deadline/yerel girdi değişti | Henüz arm edilmemiş aşamalar engellenir; intent COMMIT öncesi değişimde permit sıfır, sonrasında önceden arm edilmiş tek permit henüz HTTP başlamamış olsa da geri çekilmiş sayılamaz |
| Restart/takeover | Aynı operation üzerinde yalnız read; eksik etkili aşamayı sürdürmek P02-3a'nın ayrı kabulüdür |

Create cevabı yoksa bilinen dataset ID olmayabilir. Yerel operation/correlation korunur; aynı adla bulunan ilk dataset kesin eşleşme değildir. Exact oracle yoksa unknown dürüst son durumdur, yeni create önerilmez. Bilinen dataset için project ilişki listesi ve item metadata observation'ları yalnız kanıtladıkları bağları günceller. `not_found`/401/403/boş liste/eksik page işlemin olmadığını veya tekrarın güvenliğini kanıtlamaz. Değişen sayfa/cursor/çelişkili metadata tamlık iddiasını bozar.

## Gönderilen ve doğrulanan içerik

Plan/approve/start girdi kontrolü manifestin **tüm dosya kümesini** yeniden hash'ler; yalnız manifest dosyasını hash'lemez. Root/ancestor ve dosya descriptor kimliği, byte sayısı, stat imzası ve gözlenen yol değişimi P02-1 modeliyle denetlenir. Transferde descriptor'dan çıkan byte hash'i ayrıca plandaki hash/size ile eşleşir. Bu serial gözlem ve gönderim aralığıdır; atomik filesystem snapshot iddiası yoktur. Gönderilmiş fakat confirm edilmemiş nesne kalabilir; otomatik silme yoktur.

Sonuç üç kanıtı ayıracaktır: yerel güncel içerik kontrolü; gönderilen byte/hash eşliği; exact uzak öğe kimlik/adet/isim/boyut/hash metadata eşliği. Uzak byte'lar indirilip bağımsız hash'lenmediyse `remote_bytes_verified` benzeri bir doğru değer üretilemez. ETag SHA-256 diye yorumlanmaz. Confirm'de `created` sayısı veya HTTP 200/201 tek başına teslim değildir. Duplicate hash birden çok yerel adı kapsıyorsa her adın uzak karşılığı/oracle'ı ayrı raporlanır.

## Sabit sınırlar ve kabul sahibi

Sayısal kararın tek kaynağı ADR-0024/0025'tir: 128 dosya/500.000.000 byte dosya/1 GiB iş; ayrı 30 s yerel validation; 900 s transfer plan/onay/toplam; 150 s lease/120 s PUT/5 s pay; 2 worker/1 MiB chunk/2 MiB queue; 128 plan ve en çok 128 operation; 4.096 dosya/16 MiB canonical payload store kapasitesi. Süresi geçmiş/revoked/başlatılmamış planlar da plan/file/payload kotasına dahildir; niyet yenilemesi yeni plan kimliği üretiyorsa eski kayıt kotadan düşmez. 386 etkili stage intent için en çok birer immutable receipt; iki recovery/terminal rezervi ayrı bounded güncel kontrol kayıtlarıdır, unbounded event history değildir. Global expiry üst sınırı **13.696** (önceki 13.312 + 128 plan + 128 onay + 128 lease), kontrol sınırı **13.697**, sıcak frontier **yedi indeks** olur. Yeni tablolar boşken eski frontier sonucu aynıdır; her yeni expiry/clock mutasyonu ortak kapıyı kullanır. İlk sürüm dosya başına presign/confirm yapar; batch yoktur, response başına JSON 1 MiB kalır. Direct mod için storage origin açık ve digest'e bağlıdır; origin verilmemiş plan proxy-only'dir. Provider cardinality/response/page bütçesi bunlara ek olarak wire araştırmasında sabitlenecektir. Yeni quota mevcut execution kotalarından ayrı sayılır; otomatik geçmiş silme yoktur.

Gerçek loopback TLS/süreç/SQLite kill testleri [P02-2c](../roadmap/tasks/p02-2c-upload-recovery-acceptance.md), streaming/target testleri [P02-2b](../roadmap/tasks/p02-2b-verified-upload.md), gerçek authority/create/link ve local kayıt [P02-2a](../roadmap/tasks/p02-2a-private-create.md) sahibidir. Kanıt raporu ancak gerçek sonuçlarla güncellenir. Canlı kabul için ayrıca exact target/owner/project, sentetik veri, request/byte/süre/tutar tavanı ve kalan private kaynağın sahibi kullanıcı tarafından yetkilendirilir; eski read-only anahtar hazırlığı yazma yetkisi değildir.


## Gönderim ilerlemesi ve yavaş bağlantı

Text/TTY yolunda en çok saniyede 10 kez coalesce edilmiş ilerleme, HTTP taşımasına teslim edilen gerçek kaynak byte sayacından gelir; bu, provider'ın kabul ettiği/kalıcılaştırdığı byte değildir. Kesin onaylanmış dosya/byte ayrıca gösterilir. Her chunk DB/event/NDJSON kaydı oluşturmaz. Non-TTY/JSON/normal tek-result NDJSON çıktısına progress karışmaz; Result/StreamEvent v1 wire'ı değiştirilmez. Python aynı tipli sayacı içeride kullanır; tam public progress imzası API wire kapanışında belirlenir. 500.000.000 byte için 120 s yaklaşık 33,34 Mbit/s payload hızı gerektirir; küçük canlı pilot bu yüksek bant genişliği sınırını kanıtlamaz. Throttle/slow-read/cancel kabulü controlled stop, ID ve sıfır otomatik replay'i sınar.
