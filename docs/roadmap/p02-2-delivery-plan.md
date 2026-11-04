# P02-2 — Private create ve doğrulanmış upload teslim planı

**Tarih:** 2026-11-02. **Güncellendi:** 2026-11-04. **Durum:** ADR-0024–0028 Accepted; d–w kod/review kartları, r5 canlı metadata ve 06 tarihsel native kabulü; 07 ortam etiketi ret, 08 geçerli referansı beklenir tamamlandı. Son üç ortam CI/altı temiz kurulum ve yeni Linux çıktılarının kalıcı saklanması bekleniyor; a/b/c/epik draft. **Dal:** `feat/p02-2-private-upload`, development `50d68b1` tabanı. Tek [PR #14](https://github.com/HodeTech/Yorunge/pull/14); merge/Master/release kullanıcıdadır.

**ADR-0028 sınırı:** Tekrarlı SHA-256 upload’ı ağ/create öncesi açıkça reddedilir; yerel Manifest dosya kimliği korunur. Max128 kabulü 128 farklı hash/386 accepted aşamayla geçti. İki PNG/158-byte/8-graph runner ve iki fresh kod turu tamamlandı; r5 gerçek olumlu metadata kabulüdür. Önceki üç-PNG frozen helper/receipt ve r4 unknown korunur. Özgün çoklu-ad ihtiyacı P02-R2’de açık kalır.

## Kullanıcı sonucu

Kullanıcı güncel yerel manifestle doğru owner/projede private dataset oluşturur; normal dosyaları hedef/yetki/byte sınırları içinde yükler ve neyin doğrulandığını görür. Cevap kaybında aynı operation ID'sine dönüp salt okuma ile durumu inceler; ikinci create/PUT üretmez. Gelişmiş etkili resume P02-3a'dır; ilk kesinti güvenliği ve read reconciliation bu pakettedir.

## Başlangıç kapıları

| Kapı | Güncel kanıt ve sınır | Durum |
|---|---|---|
| Karar | ADR-0024–0028 kullanıcı onayı ve review düzeltmeleriyle Accepted; kalıcılık, storage, explicit/unpriced, create baseline ve içerik tekilliği ayrı tanımlı | Kapandı |
| Create/link consumer | Strict gerçek codec/current producer ve ayrı create/proje bağlantısı uygulanmış; r5 typed accepted graph ile geçti. Discovery veya UUID yetki oracle’ı değildir | İlk dar yol tamam |
| Upload/verification consumer | Proxy presign/PUT/confirm ve sayfalı item metadata, exact ad/size/SHA eşliği uygulanmış. Genel direct port sentetik TLS’te testlidir; gerçek direct provider wire desteği iddia edilmez | İlk proxy yolu tamam |
| Yetki ve fiyat | Verified-only tam grant/exact-work complete cost ister. Explicit/unpriced bilinmeyeni ayrı insan onayıyla risk olarak taşır; r5 authority/pricing/remote-bytes=false | Bilinmeyen görünür; doğrulanmış provider kaynağı gerekir |
| Canlı kabul | Ayrı bounded r5 gerçek create/link/iki dosya upload/aynı-ID read proof geçti; kaynak private kaldı. Önceki denemeler yeni gönderim hakkı üretmez | Dar metadata kabulü tamam |
| Son kaynak teslimi | 07 süre/bellek, iki temiz kurulum ve gizlilik/kanıt kapıları geçti; disk etiketi nedeniyle reference kapısı ret, 08 beklenir; yeni kaynak üç ortam CI/altı kurulum/Sonar ve zorunlu çıktıların saklaması beklenir | Üst kartlar draft |

[Kanonik consumer](../reference/platform-upload-consumer.md) endpoint ve typed oracle’ın, [v2 sözleşmesi](../reference/dataset-upload-v2.md) yetki/maliyet/onay kapısının sahibidir. Araştırma belgesi veya yerel OpenAPI örneği provider yetki/fiyat garantisi oluşturmaz. Yeni hesap çağrısı veya kapsam değişikliği bu teslim planından otomatik yetki çıkarmaz.

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

Somut scope, byte/istek/süre ve ilk belirsizlikte durma koşulları [nihai canlı planda](../research/p02-2-final-live-plan.md) önceden sabitlendi. Kullanıcının ayrı yetkileriyle yapılan ilk create/tanı ve r1–r4 denemeleri eksik/unknown tarihsel sonuçlarıyla korunur; otomatik replay yapılmadı. Accepted ADR-0028 sonrası iki farklı içerikli PNG ile [r5](../research/p02-2-implementation-validation.md#4-kasım--r5-tam-canlı-metadata-kabulü) **3,2064 s /23 GET /8 accepted aşama /158 byte** ve exact metadata proof üretti.

Sonuç yetki, fiyat veya indirilmiş uzak byte doğrulaması değildir. Explicit_attempt + unpriced ve sayısal CR tavanı uygulanmadığı açıkça onaylandı; süreğen depolama fiyatı bilinmiyor. Kaynak private kalır; şart kabulü, silme, indirme veya eğitim yapılmadı. Daha büyük veya yeni bir canlı çağrı bu eski yetkinin tekrarı sayılmaz.

## Teslim kaydı

[Uygulama ve kabul kaydı](../research/p02-2-implementation-validation.md), her kod diliminin commit/iki fresh turunu, doğrulanmış bulgu kapanışını, testleri, kurulumları, canlı denemeleri ve bütün ilk ölçüm sonuçlarını taşır. 03 jobs, 04 upload ve 05 startup retleri korunur; 06 kaynak değişikliklerinden sonraki ilk seridir ve geçti. Aynı kaynaktan iyi örnek seçmek için tekrar yapılmadı. Yerel tam takım gerekçesiz yeniden çalıştırılmaz; yeni source CI tam takımı ve altı kurulumu ayrıca doğrular.

Aşağıdaki bölümler tamamlanan uygulama sırasını özetler; kalan aktif iş [current](current.md#sıradaki-iş-ve-kalan-kapsam) ve üst P02-2c kartında izlenir. Nihai CI/saklama kapanmadan üst teslim verified sayılmaz.

## Bağımsız yerel kart sırası

P02-2d ayrı plan/manifest/onay, e durable journal ve f hedef/auth/bounded streaming temellerini tamamladı. F, hedef/request/source ve pin/peer/client entegrasyonu olarak iki kod diliminde kapandı. V1 tarihsel wire/golden/DDL ve ayrı genel execution/jobs davranışı korundu.

## ADR-0026 sonrası sıra

V2 politika geçişi kullanıcı review düzeltmeleri ve iki fresh belge turu sonrası Accepted ADR-0026 ile açıldı. Her kod dilimi commit, fresh R1/fix ve farklı fresh R2/fix ile kapandı; default verified_only korunurken explicit_attempt/unpriced ve aynı-ID explicit read ayrı insan seçimine bağlandı. Yeni politika known-negative, owner/private/input veya maliyet bağını atlamaz.

## V2 dar kartları

G exact-work maliyet; h policy/plan/approval; i union/full graph; j durable write kapıları; k read/reset/metadata kartları verified. Eski binary/history kabulü ve v1 byte golden’ları korunur. Bu temeller tek başına gerçek provider veya epik kabulü sayılmadı; sonraki consumer/public/live kabulü ayrıca yapıldı.

## Gerçek tüketiciye geçiş

| Kartlar | Tamamlanan dilim |
|---|---|
| l/m | Context/create/link ve proxy presign/confirm/items strict codec’leri |
| n | Literal URI provenance, pre-intent rezerv ve gerçek HTTP attempt/body/source sayaçları |
| o/p | Güncel input/current producer ve prepare/approve/revoke; ADR-0027 atomik create baseline/union/history/legacy mutation kapıları |
| q/r | Gerçek effect/metadata portu, invocation/admission/create-link, bounded dosya fazları ve initial-owner proof |
| s/t | Aynı-ID salt okuma controller’ı, dar summary ve ortak sekiz API/CLI, bounded ilerleme/iptal |
| u/w/v | Public süreç/kill/ID kurtarma/max128 kabulü; bakım sınırları; kurulu upload ölçüm araçları/bağımsız native kanıt |

[Port](../reference/dataset-upload-port.md), [koordinatör](../reference/dataset-upload-workflow.md), [public yüzey](../reference/dataset-upload-public.md) ve [ölçüm planı](../research/p02-2-upload-measurement-plan.md) kendi sözleşmelerinin kanonik sahibidir. Altı kurulum/son kaynak CI/kalıcı Linux saklama ve nihai belge/PR kabulü üst c’de kalır; bu teknik ayırma kapsamı daraltmaz. Etkili resume, indirme ve sürüm/bölme P02-3; doğrulanmış kimlik/bağ P02-R1; aynı içerikli çoklu-ad desteği P02-R2’dir. Sağlayıcıdan gerçek authority/complete-cost kanıtı gelmedikçe verified-only yazma kapısı açılmaz.
